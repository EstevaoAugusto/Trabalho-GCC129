from fastapi import FastAPI
from pydantic import BaseModel
from .parser import parse_order_text

app = FastAPI(title="IA 1 - CoffeeNet NLU Parser")

class NLURequest(BaseModel):
    text: str
    # O Backend envia os produtos que ele conhece para a IA
    # Isso torna a IA mais precisa e desacoplada da lógica de negócios
    product_keywords: list[str] 

class NLUResponse(BaseModel):
    items: list[dict] # ex: [{"product_guess": "cappuccino", "quantity": 2}]

@app.post("/parse", response_model=NLUResponse)
async def parse_order(request: NLURequest):
    """
    Recebe texto em linguagem natural e retorna itens estruturados.
    """
    parsed_items = parse_order_text(request.text, request.product_keywords)
    return NLUResponse(items=parsed_items)

@app.get("/")
def health_check():
    return {"status": "IA 1 (NLU) está online!"}