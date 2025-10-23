from jose import JWTError, jwt
from fastapi import FastAPI, Depends, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy.orm import Session
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

app = FastAPI(title="CoffeeNet Backend Principal")


app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],     
    allow_credentials=True,
    allow_methods=["*"],      
    allow_headers=["*"],    
)

# Inclui as rotas de API
app.include_router(users.router)
app.include_router(orders.router)
app.include_router(products.router)

@app.get("/")
def read_root():
    return {"Status": "CoffeeNet Backend Principal está online!"}


@app.websocket("/ws/{token}")
async def websocket_endpoint(
    websocket: WebSocket,
    token: str,
    db: Session = Depends(database.get_db)
):
    """
    Endpoint WebSocket.
    Espera um token JWT como parte da URL para autenticação.
    """
    user = None
    try:
        # 1. Autentica o usuário usando o token
        payload = jwt.decode(token, auth.SECRET_KEY, algorithms=[auth.ALGORITHM])
        email: str = payload.get("sub")
        if email is None:
            await websocket.close(code=status.WS_1008_POLICY_VIOLATION)
            return
        
        user = crud.get_user_by_email(db, email=email)
        if user is None:
            await websocket.close(code=status.WS_1008_POLICY_VIOLATION)
            return
            
        user_id = user.id
        role = user.cargo.value
        
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
                await websocket.receive_text()
                
        except WebSocketDisconnect:
            print(f"WS Disconnect: User {user_id} ({role})")
            if user:
                manager.disconnect(websocket, user_id, role)

    except (JWTError, AttributeError):
        await websocket.close(code=status.WS_1008_POLICY_VIOLATION)
        if user and user_id and role:
            manager.disconnect(websocket, user_id, role)
    finally:
        if 'db' in locals() and db:
            db.close()