from sqlalchemy import Boolean, Column, ForeignKey, Integer, String, Float, DateTime, Enum
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
import enum
from .database import Base

class UserRole(str, enum.Enum):
    cliente = "cliente"
    cozinheiro = "cozinheiro"

class User(Base):
    __tablename__ = "usuarios"
    id = Column(Integer, primary_key=True, index=True)
    email = Column(String, unique=True, index=True, nullable=False)
    hashed_password = Column(String, nullable=False)
    cargo = Column(Enum(UserRole), nullable=False, default=UserRole.cliente)
    pedidos = relationship("Order", back_populates="usuario")

class Product(Base):
    __tablename__ = "produtos"
    id = Column(Integer, primary_key=True, index=True)
    nome = Column(String, index=True, nullable=False)
    preco = Column(Float, nullable=False)
    categoria = Column(String, index=True)
    # Palavras-chave para a IA 1 (NLU)
    keywords = Column(String, default="") # ex: "cappuccino,caputino,capuccino"
    quantidade_estoque = Column(Integer, default=0, nullable=False)
    em_promocao = Column(Boolean, default=False, nullable=False)
    preco_promocional = Column(Float, nullable=True)

class Promotion(Base):
    __tablename__ = "promocoes"
    id = Column(Integer, primary_key=True, index=True)
    descricao = Column(String, nullable=False)
    produto_associado_id = Column(Integer, ForeignKey("produtos.id"))
    ativa = Column(Boolean, default=True)
    data_inicio = Column(DateTime(timezone=True), server_default=func.now())
    data_fim = Column(DateTime(timezone=True))
    produto = relationship("Product")

class OrderStatus(int, enum.Enum):
    RECEBIDO = 0
    EM_PRODUCAO = 1
    CANCELADO = 2
    PRONTO = 3

class Order(Base):
    __tablename__ = "pedidos"
    id = Column(Integer, primary_key=True, index=True)
    usuario_id = Column(Integer, ForeignKey("usuarios.id"))
    status = Column(Enum(OrderStatus), default=OrderStatus.RECEBIDO)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    total = Column(Float, default=0.0)
    
    usuario = relationship("User", back_populates="pedidos")
    itens = relationship("OrderItem", back_populates="pedido")

class OrderItem(Base):
    __tablename__ = "itens_pedido"
    id = Column(Integer, primary_key=True, index=True)
    pedido_id = Column(Integer, ForeignKey("pedidos.id"))
    produto_id = Column(Integer, ForeignKey("produtos.id"))
    quantidade = Column(Integer, nullable=False)
    # Requisito: "congelar" o preço no momento da compra
    preco_no_momento = Column(Float, nullable=False)
    
    pedido = relationship("Order", back_populates="itens")
    produto = relationship("Product")