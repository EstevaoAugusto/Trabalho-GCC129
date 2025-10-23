import httpx
import os
from typing import List, Dict
from .. import schemas

IA_1_NLU_URL = os.getenv("IA_1_NLU_URL")

async def call_nlu_service(text: str, product_keywords: List[str]) -> schemas.NLUResponse:
    """
    Chama o microsserviço de IA 1 (NLU)
    """
    url = f"{IA_1_NLU_URL}/parse"
    payload = {"text": text, "product_keywords": product_keywords}
    
    async with httpx.AsyncClient() as client:
        try:
            response = await client.post(url, json=payload, timeout=5.0)
            response.raise_for_status() # Lança exceção se for 4xx ou 5xx
            
            data = response.json()
            return schemas.NLUResponse(items=data.get("items", []))
            
        except httpx.RequestError as e:
            print(f"Erro ao chamar IA 1 (NLU): {e}")
            # Retorna uma resposta vazia em caso de falha
            return schemas.NLUResponse(items=[])