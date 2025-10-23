from fastapi import WebSocket
from typing import Dict, List

class ConnectionManager:
    def __init__(self):
        # Mapeia user_id para uma lista de WebSockets ativos
        # (um usuário pode estar conectado em várias abas)
        self.active_connections: Dict[int, List[WebSocket]] = {}
        # Conexões da cozinha (todos recebem todos os pedidos)
        self.kitchen_connections: List[WebSocket] = []

    async def connect(self, websocket: WebSocket, user_id: int, role: str):
        await websocket.accept()
        if role == "cozinheiro":
            self.kitchen_connections.append(websocket)
        else:
            if user_id not in self.active_connections:
                self.active_connections[user_id] = []
            self.active_connections[user_id].append(websocket)

    def disconnect(self, websocket: WebSocket, user_id: int, role: str):
        if role == "cozinheiro":
            if websocket in self.kitchen_connections:
                self.kitchen_connections.remove(websocket)
        else:
            if user_id in self.active_connections:
                self.active_connections[user_id].remove(websocket)
                if not self.active_connections[user_id]:
                    del self.active_connections[user_id]

    async def send_to_user(self, user_id: int, message: dict):
        """Envia uma mensagem específica para todas as conexões de um usuário."""
        if user_id in self.active_connections:
            for connection in self.active_connections[user_id]:
                await connection.send_json(message)

    async def broadcast_to_kitchens(self, message: dict):
        """Envia uma mensagem para todas as cozinhas conectadas."""
        for connection in self.kitchen_connections:
            await connection.send_json(message)

# Instância global do gerenciador
manager = ConnectionManager()