from wsgiref.validate import validator
from pydantic import BaseModel, EmailStr, Field, model_validator
from typing import Optional, List, Any
from datetime import datetime
from .models import OrderStatus, UserRole

class UserBase(BaseModel):
    email: EmailStr

class UserCreate(UserBase):
    password: str
    cargo: UserRole = UserRole.cliente

class User(UserBase):
    id: int
    cargo: UserRole
    class Config:
        from_attributes = True

class Token(BaseModel):
    access_token: str
    token_type: str

class TokenData(BaseModel):
    email: Optional[str] = None

class ProductBase(BaseModel):
    nome: str
    preco: float
    categoria: Optional[str] = None
    keywords: Optional[str] = ""
    quantidade_estoque: int = Field(..., ge=0) # Garante que estoque >= 0

class ProductCreate(ProductBase):
    pass 

class ProductUpdate(BaseModel):
    nome: Optional[str] = None
    preco: Optional[float] = None
    categoria: Optional[str] = None
    keywords: Optional[str] = None
    quantidade_estoque: Optional[int] = Field(None, ge=0) # Garante >= 0 se fornecido

class ProductPromotionUpdate(BaseModel):
    em_promocao: bool
    preco_promocional: Optional[float] = None

    @model_validator(mode='after')
    def check_promotional_price(self) -> 'ProductPromotionUpdate':
        em_promocao = self.em_promocao
        preco_promocional = self.preco_promocional

        if em_promocao:
            if preco_promocional is None:
                raise ValueError('Preço promocional é obrigatório quando o produto está em promoção.')
            if preco_promocional <= 0:
                raise ValueError('Preço promocional deve ser maior que zero.')
        else:
             self.preco_promocional = None 
             
        return self
    
class Product(BaseModel):
    id: int
    nome: str
    preco: float
    categoria: str
    keywords: Optional[str] = None
    quantidade_estoque: int
    em_promocao: bool
    preco_promocional: Optional[float] = None
    class Config:
        from_attributes = True

class OrderItemBase(BaseModel):
    produto_id: int
    quantidade: int

class OrderItem(OrderItemBase):
    id: int
    preco_no_momento: float
    produto: Product
    class Config:
        from_attributes = True

class OrderBase(BaseModel):
    pass

class Order(OrderBase):
    id: int
    usuario_id: int
    status: OrderStatus
    created_at: datetime
    total: float
    itens: List[OrderItem] = []
    class Config:
        from_attributes = True


class NLUItem(BaseModel):
    product_guess: str
    quantity: int

class NLUResponse(BaseModel):
    items: List[NLUItem]

class GeminiRecommendation(BaseModel):
    suggestion_text: str 
    parsed_items: List[OrderItemBase] 

class ParsedItemDetail(BaseModel):
    produto_id: int
    quantidade: int
    nome: str
    preco: float
    is_promo: bool = False
    
class ChatRequest(BaseModel):
    text: str
    current_items: Optional[List[OrderItemBase]] = None

class ChatResponse(BaseModel):
    recommendation: str
    parsed_items: List[ParsedItemDetail]
    # O "contexto" para o frontend saber o que fazer
    # 'confirm' (IA entendeu, aguarda confirmação)
    # 'clarify' (IA não entendeu, pede mais infos)
    intent: str 
    suggested_item: Optional[ParsedItemDetail] = None

class ConfirmOrderRequest(BaseModel):
    items: List[OrderItemBase]

class UpdateStatusRequest(BaseModel):
    status: OrderStatus

