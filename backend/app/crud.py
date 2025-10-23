from sqlalchemy.orm import Session, joinedload
from fastapi import HTTPException, status
from . import models, schemas, auth
from .models import UserRole
from typing import List, Optional

def get_user_by_email(db: Session, email: str):
    return db.query(models.User).filter(models.User.email == email).first()

def create_user(db: Session, user: schemas.UserCreate):
    hashed_password = auth.get_password_hash(user.password)
    db_user = models.User(
        email=user.email, 
        hashed_password=hashed_password, 
        cargo=user.cargo
    )
    db.add(db_user)
    db.commit()
    db.refresh(db_user)
    return db_user

# --- Product ---
def get_products(db: Session, only_in_stock: bool = True) -> List[models.Product]:
    query = db.query(models.Product)
    if only_in_stock:
        query = query.filter(models.Product.quantidade_estoque > 0)
    return query.order_by(models.Product.nome).all()

def get_all_products(db: Session) -> List[models.Product]:
     return get_products(db, only_in_stock=False)

def get_product_by_id(db: Session, product_id: int, lock_for_update: bool = False):
    query = db.query(models.Product).filter(models.Product.id == product_id)
    if lock_for_update:

        query = query.with_for_update() 
    return query.first()

def create_product(db: Session, product: schemas.ProductCreate) -> models.Product:
    db_product = models.Product(**product.model_dump())
    db.add(db_product)
    db.commit()
    db.refresh(db_product)
    return db_product

def update_product(db: Session, product_id: int, product_update: schemas.ProductUpdate) -> Optional[models.Product]:
    db_product = get_product_by_id(db, product_id)
    if db_product:
        update_data = product_update.model_dump(exclude_unset=True)
        for key, value in update_data.items():
            setattr(db_product, key, value)
        db.commit()
        db.refresh(db_product)
    return db_product

def delete_product(db: Session, product_id: int) -> bool:
    db_product = get_product_by_id(db, product_id)
    if db_product:
        db.delete(db_product)
        db.commit()
        return True
    return False

def update_product_promotion(db: Session, product_id: int, promo_update: schemas.ProductPromotionUpdate) -> Optional[models.Product]:
    db_product = get_product_by_id(db, product_id)
    if db_product:
        db_product.em_promocao = promo_update.em_promocao
        db_product.preco_promocional = promo_update.preco_promocional
        db.commit()
        db.refresh(db_product)
    return db_product

# --- Order ---
def get_user_order_history(db: Session, user_id: int) -> List[models.Order]:
    return db.query(models.Order)\
             .filter(models.Order.usuario_id == user_id)\
             .options(joinedload(models.Order.itens))\
             .order_by(models.Order.created_at.desc())\
             .limit(5)\
             .all()

def get_active_orders(db: Session) -> List[models.Order]:
    return db.query(models.Order)\
             .filter(models.Order.status.in_([
                 models.OrderStatus.RECEBIDO,
                 models.OrderStatus.EM_PRODUCAO
              ]))\
             .options(joinedload(models.Order.itens).joinedload(models.OrderItem.produto))\
             .order_by(models.Order.created_at.asc())\
             .all()

def get_active_orders_by_user(db: Session, user_id: int) -> List[models.Order]:
    return db.query(models.Order)\
             .filter(models.Order.usuario_id == user_id)\
             .filter(models.Order.status.in_([
                 models.OrderStatus.RECEBIDO,
                 models.OrderStatus.EM_PRODUCAO
              ]))\
             .options(joinedload(models.Order.itens).joinedload(models.OrderItem.produto))\
             .order_by(models.Order.created_at.asc())\
             .all()

def get_order_by_id(db: Session, order_id: int) -> models.Order:
     return db.query(models.Order)\
             .options(joinedload(models.Order.itens).joinedload(models.OrderItem.produto))\
             .filter(models.Order.id == order_id)\
             .first()


def create_order(db: Session, user_id: int, items: List[schemas.OrderItemBase]) -> models.Order:
    """
    Cria um novo pedido, validando e decrementando o estoque de forma transacional.
    """
    
    # Inicia a transação
    try:
        db_order = models.Order(
            usuario_id=user_id,
            status=models.OrderStatus.RECEBIDO
        )
        db.add(db_order)
        # É preciso "dar um flush" para obter o ID do pedido
        db.flush() 

        total = 0.0
        
        # --- Lógica de verificação de estoque ---
        for item in items:
            # Pega o produto e BLOQUEIA a linha para este update
            product = get_product_by_id(db, item.produto_id, lock_for_update=True)
            
            if not product:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail=f"Produto com ID {item.produto_id} não encontrado."
                )
            
            # 1. Verifica o estoque
            if product.quantidade_estoque < item.quantidade:
                raise HTTPException(
                    status_code=status.HTTP_409_CONFLICT, # 409 Conflict
                    detail=f"Estoque insuficiente para '{product.nome}'. " \
                           f"Temos apenas {product.quantidade_estoque} unidades."
                )
            
            # 2. Se tiver estoque, decrementa
            product.quantidade_estoque -= item.quantidade
            
            price_at_moment = product.preco
            total += price_at_moment * item.quantidade
            
            db_item = models.OrderItem(
                pedido_id=db_order.id,
                produto_id=item.produto_id,
                quantidade=item.quantidade,
                preco_no_momento=price_at_moment
            )
            db.add(db_item)

        db_order.total = total
        
        # Se tudo deu certo, commita a transação
        db.commit()
        
        # Atualiza a instância do db_order
        db.refresh(db_order)
        
        # Recarrega o pedido com os itens e produtos para retornar o objeto completo
        full_order = get_order_by_id(db, db_order.id)
        return full_order

    except HTTPException as e:
        db.rollback()
        raise e
    except Exception as e:
        db.rollback()
        print(f"Erro inesperado no banco: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Ocorreu um erro ao processar seu pedido."
        )

def update_order_status(db: Session, order_id: int, status: models.OrderStatus) -> models.Order:
    db_order = get_order_by_id(db, order_id)
    if db_order:
        db_order.status = status
        db.commit()
        db.refresh(db_order)
    return db_order