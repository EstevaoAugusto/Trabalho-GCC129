from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from typing import List, Optional
from .. import crud, schemas, auth, models, database
from ..websocket_manager import manager
from ..services import nlu_service, gemini_service
import asyncio

router = APIRouter(
    prefix="/orders",
    tags=["Pedidos"],
    dependencies=[Depends(auth.get_current_user)]
)

@router.post("/chat", response_model=schemas.ChatResponse)
async def handle_chat_message(
    chat_request: schemas.ChatRequest,
    db: Session = Depends(database.get_db),
    current_user: models.User = Depends(auth.get_current_user)
):
    """
    Ponto central:
    1. Pega o texto do cliente.
    2. Envia para a IA 1 (NLU) para extrair itens.
    3. Valida os itens com o banco de dados.
    4. Pega histórico e promoções.
    5. Envia tudo para a IA 2 (Gemini) para gerar upsell.
    6. Retorna a sugestão do Gemini e os itens entendidos.
    """
    
    # 1. Pega TODOS os produtos (incluindo fora de estoque) para mapeamento e checagem
    all_products = crud.get_all_products(db) 
    product_keywords_map = {kw: prod.id for prod in all_products for kw in prod.keywords.split(',')}
    product_id_map = {prod.id: prod for prod in all_products} 

    # 2. Chama IA 1 (NLU)
    nlu_response = await nlu_service.call_nlu_service(
        chat_request.text,
        list(product_keywords_map.keys())
    )

    # 3. Processa resposta da IA 1: separa itens em estoque, fora de estoque e não entendidos
    parsed_items_details: List[schemas.ParsedItemDetail] = [] 
    parsed_items_base: List[schemas.OrderItemBase] = []   
    current_items_names: List[str] = []

    if chat_request.current_items: # Se o frontend enviou um carrinho
        for item in chat_request.current_items:
            if item.produto_id in product_id_map:
                produto = product_id_map[item.produto_id]
                
                # Recalcula preço (caso tenha entrado/saído de promoção)
                preco_a_exibir = produto.preco
                is_promo = False
                if produto.em_promocao and produto.preco_promocional is not None:
                    preco_a_exibir = produto.preco_promocional
                    is_promo = True
                
                parsed_items_details.append(schemas.ParsedItemDetail(
                    produto_id=produto.id, quantidade=item.quantidade,
                    nome=produto.nome, preco=preco_a_exibir, is_promo=is_promo
                ))
                parsed_items_base.append(schemas.OrderItemBase(
                    produto_id=produto.id, quantidade=item.quantidade
                ))
                current_items_names.append(produto.nome)

    out_of_stock_items: List[str] = []                       # Nomes de itens entendidos mas sem estoque
    failed_to_understand_guesses: List[str] = []             # O que a IA1 tentou adivinhar mas não mapeamos
    new_items_found = False

    if not nlu_response.items and chat_request.text.lower() not in ["oi", "ola", "bom dia", "boa tarde", "boa noite"]:
        # Se a IA 1 não retornou NADA e não foi só um cumprimento, marcamos como não entendido geral
        intent = "clarify_general"
    else:
        # Processa cada item que a IA 1 retornou
        for item in nlu_response.items:
            product_id = product_keywords_map.get(item.product_guess.lower())

            if product_id and product_id in product_id_map:
                produto = product_id_map[product_id]
                new_items_found = True
                if produto.quantidade_estoque > 0:
                    # Produto ENCONTRADO e EM ESTOQUE
                    existing_item_details = next((p for p in parsed_items_details if p.produto_id == produto.id), None)
                    if existing_item_details:
                        existing_item_details.quantidade += item.quantity
                        # Atualiza também na base
                        existing_item_base = next((p for p in parsed_items_base if p.produto_id == produto.id), None)
                        if existing_item_base:
                            existing_item_base.quantidade += item.quantity
                    else:
                        # Novo item, adiciona
                        preco_a_exibir = produto.preco
                        is_promo = False
                        if produto.em_promocao and produto.preco_promocional is not None:
                            preco_a_exibir = produto.preco_promocional
                            is_promo = True

                        parsed_items_details.append(schemas.ParsedItemDetail(
                            produto_id=produto.id, quantidade=item.quantity,
                            nome=produto.nome, preco=preco_a_exibir, is_promo=is_promo
                        ))
                        parsed_items_base.append(schemas.OrderItemBase(
                            produto_id=produto.id, quantidade=item.quantity
                        ))
                        current_items_names.append(produto.nome)
                else:
                    # Produto ENCONTRADO mas FORA DE ESTOQUE
                    out_of_stock_items.append(produto.nome)
            else:
                # Produto NÃO MAPEADO (IA 1 "inventou" ou não temos keyword)
                failed_to_understand_guesses.append(item.product_guess)
        
        # Define a INTENT baseada no resultado do processamento
        if parsed_items_details: # Se achou PELO MENOS UM item em estoque
            intent = "confirm" # Pode confirmar ou sugerir mais
        elif out_of_stock_items: # Se não achou em estoque, mas achou fora de estoque
            intent = "clarify_stock"
        elif failed_to_understand_guesses: # Se não achou nada, mas IA1 tentou
             intent = "clarify_product"
        else: # Se IA1 retornou vazio (e era cumprimento) ou algo deu muito errado
             intent = "clarify_general"

    # 4. Pega histórico e promoções
    history = crud.get_user_order_history(db, current_user.id)
    products_in_stock = crud.get_products(db, only_in_stock=True) 
    active_promo_products = [p for p in products_in_stock if p.em_promocao and p.preco_promocional is not None]

    history_context, frequent_items = gemini_service.format_history(history)

    # 5. Determina sugestão
    suggested_item_details: Optional[schemas.ParsedItemDetail] = None
    
    # Lógica de sugestão só roda se a intent permitir (achou algo em estoque)
    if intent == "confirm":
        missing_favorites = []
        for item_name in frequent_items:
            fav_product = next((p for p in all_products if p.nome == item_name), None)
            if fav_product and fav_product.quantidade_estoque > 0 and item_name not in current_items_names:
                missing_favorites.append(item_name)
        
        if missing_favorites:
            item_para_sugerir_nome = missing_favorites[0]
            produto_sugerido = product_id_map.get( next((p.id for p in all_products if p.nome == item_para_sugerir_nome), None) )

            # Sugere apenas se o item favorito estiver EM ESTOQUE
            if produto_sugerido and produto_sugerido.quantidade_estoque > 0:
                 preco_sugestao = produto_sugerido.preco
                 is_promo_sugestao = False
                 if produto_sugerido.em_promocao and produto_sugerido.preco_promocional is not None:
                     preco_sugestao = produto_sugerido.preco_promocional
                     is_promo_sugestao = True

                 suggested_item_details = schemas.ParsedItemDetail(
                     produto_id=produto_sugerido.id, quantidade=1,
                     nome=produto_sugerido.nome, preco=preco_sugestao, is_promo=is_promo_sugestao
                 )
                 intent = "suggest" # Muda a intent para indicar sugestão

    recommendation_text = await gemini_service.get_gemini_recommendation(
        intent=intent, 
        parsed_items=parsed_items_base,
        history=history,
        promotions=active_promo_products, 
        out_of_stock_items=out_of_stock_items,
        failed_guesses=failed_to_understand_guesses,
        all_products=all_products
    )

    # 6. Retorna

    # Apenas trate o caso especial de cumprimento (oi, ola),
    # que deve SEMPRE ser 'clarify_general' (caso a lógica anterior não tenha pego)
    if not chat_request.text or chat_request.text.lower() in ["oi", "ola", "bom dia"]:
        intent = "clarify_general"
    
    # Se a intent for de sugestão, mas o Gemini falhou e não gerou uma
    # (ou a lógica de sugestão falhou), reverta para 'confirm'.
    if intent == "suggest" and not suggested_item_details:
        intent = "confirm"
        
    # Se a intent não for de clarificação, mas o carrinho ficou vazio,
    # reverta para clarificação.
    if not intent.startswith("clarify") and not parsed_items_details:
         intent = "clarify_general"

    return schemas.ChatResponse(
        recommendation=recommendation_text,
        parsed_items=parsed_items_details,
        intent=intent,
        suggested_item=suggested_item_details
    )

@router.post("/confirm", response_model=schemas.Order)
async def confirm_order(
    order_request: schemas.ConfirmOrderRequest,
    db: Session = Depends(database.get_db),
    current_user: models.User = Depends(auth.get_current_user)
):
    """
    O cliente confirmou os itens.
    1. Cria o pedido no banco de dados (Status 0: Recebido).
    2. Envia notificação via WebSocket para as Cozinhas.
    3. Retorna o pedido criado.
    """
    
    # 1. Cria o pedido
    new_order = crud.create_order(
        db, 
        user_id=current_user.id, 
        items=order_request.items
    )
    
    # 2. Notifica as cozinhas
    # Converte o objeto SQLAlchemy para um dict (usando Pydantic)
    order_data = schemas.Order.model_validate(new_order).model_dump(mode='json') 
    await manager.broadcast_to_kitchens({
        "type": "new_order",
        "data": order_data
    })
    
    # 3. Retorna
    return new_order


@router.get("/active", response_model=List[schemas.Order])
async def get_active_orders(
    db: Session = Depends(database.get_db),
    current_user: models.User = Depends(auth.get_current_active_kitchen_user)
):
    """Retorna todos os pedidos ativos (Recebido, Em Produção) para a cozinha."""
    return crud.get_active_orders(db)


@router.put("/{order_id}/status", response_model=schemas.Order)
async def update_order_status(
    order_id: int,
    status_request: schemas.UpdateStatusRequest,
    db: Session = Depends(database.get_db),
    current_user: models.User = Depends(auth.get_current_active_kitchen_user)
):
    """
    A cozinha atualiza o status de um pedido.
    1. Atualiza no banco.
    2. Notifica o Cliente dono do pedido via WebSocket.
    3. Notifica TODAS as cozinhas (para sincronizar painéis).
    """
    
    # 1. Atualiza no banco
    updated_order = crud.update_order_status(
        db, 
        order_id=order_id, 
        status=status_request.status
    )
    
    if not updated_order:
        raise HTTPException(status_code=404, detail="Pedido não encontrado")

    # 2. Notifica o cliente
    order_data = schemas.Order.model_validate(updated_order).model_dump(mode='json')
    message = {
        "type": "status_update",
        "data": order_data
    }
    
    await manager.send_to_user(updated_order.usuario_id, message)
    
    # 3. Notifica todas as cozinhas
    await manager.broadcast_to_kitchens(message)
    
    return updated_order