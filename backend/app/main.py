# Bibliotecas para autenticação JWT (JSON Web Token)
from jose import JWTError, jwt

# FastAPI e funcionalidades relacionadas a WebSocket
from fastapi import FastAPI, Depends, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy.orm import Session # Sessão ORM do SQLAlchemy

# Importações de módulos internos da aplicação
from . import crud
from . import models, database, auth, schemas
from .database import engine
from .routers import users, orders, products
from .websocket_manager import manager
from starlette import status
import json

# Cria todas as tabelas no banco de dados (para desenvolvimento)
# Em produção, você usaria Alembic para migrações.
models.Base.metadata.create_all(bind=engine)

# Criação da instância principal do FastAPI
app = FastAPI(title="CoffeeNet Backend Principal")

# Configuração do CORS (Cross-Origin Resource Sharing)
# Permite que qualquer frontend acesse a API
app.add_middleware(
    CORSMiddleware, 
    allow_origins=["*"],       # Permite qualquer origem
    allow_credentials=True,
    allow_methods=["*"],       # Permite todos os métodos HTTP (GET, POST, etc.)   
    allow_headers=["*"],       # Permite todos os cabeçalhos
)

# Inclui as rotas de API
app.include_router(users.router)
app.include_router(orders.router)
app.include_router(products.router)


# Endpoint raiz para testar se o backend está online
@app.get("/")
def read_root():
    return {"Status": "CoffeeNet Backend Principal está online!"}


# Endpoint WebSocket para comunicação em tempo real
@app.websocket("/ws/{token}")
async def websocket_endpoint(
    websocket: WebSocket,
    token: str,
    db: Session = Depends(database.get_db) # Fornece sessão do DB automaticamente
):
    """
    Endpoint WebSocket.
    Espera um token JWT como parte da URL para autenticação.
    """
    user = None
    try:
        # 1. Autentica o usuário usando o token
        payload = jwt.decode(token, auth.SECRET_KEY, algorithms=[auth.ALGORITHM])
        email: str = payload.get("sub") # "sub" geralmente contém o identificador do usuário
        if email is None:
            await websocket.close(code=status.WS_1008_POLICY_VIOLATION)
            return
        
        # Busca o usuário no banco de dados pelo email
        user = crud.get_user_by_email(db, email=email)
        if user is None:
            await websocket.close(code=status.WS_1008_POLICY_VIOLATION)
            return
            
        user_id = user.id
        role = user.cargo.value # Obtém a função do usuário (cliente, cozinheiro, etc.)
        
        # 2. Adiciona o usuário ao gerenciador de conexões
        await manager.connect(websocket, user_id, role)
        print(f"WS Connect: User {user_id} ({role})")

        # 2.5 (Apenas para Cliente) Envia o cardápio inicial
        if role == "cliente":
            # Envia o cardápio
            products = crud.get_products(db) 
            menu_data = [schemas.Product.model_validate(p).model_dump(mode='json') for p in products] 
            await websocket.send_json({
                "type": "menu",
                "data": menu_data
            })
            
            # Envia pedidos ativos do cliente (se houver)
            active_client_orders = crud.get_active_orders_by_user(db, user_id=user_id)
            if active_client_orders: # Só envia se tiver algum
                orders_data = [schemas.Order.model_validate(o).model_dump(mode='json') for o in active_client_orders]
                await websocket.send_json({
                    "type": "active_orders", # Novo tipo de mensagem
                    "data": orders_data
                })

        # 3. (Apenas para Cozinha) Envia os pedidos ativos atuais
        if role == "cozinheiro":
            active_orders = crud.get_active_orders(db)
            orders_data = [schemas.Order.model_validate(o).model_dump(mode='json') for o in active_orders]
            await websocket.send_json({
                "type": "initial_state",
                "data": orders_data
            })

        # 4. Mantém a conexão viva
        try:
            while True:
                # Recebe qualquer mensagem enviada pelo cliente
                await websocket.receive_text()
                
        except WebSocketDisconnect:
            # Caso o cliente desconecte, remove do gerenciador
            print(f"WS Disconnect: User {user_id} ({role})")
            if user:
                manager.disconnect(websocket, user_id, role)

    except (JWTError, AttributeError):
        # Caso o token seja inválido ou falhe a autenticação
        await websocket.close(code=status.WS_1008_POLICY_VIOLATION)
        if user and user_id and role:
            manager.disconnect(websocket, user_id, role)
    finally:
        # Garante que a sessão do banco de dados seja fechada
        if 'db' in locals() and db:
            db.close()