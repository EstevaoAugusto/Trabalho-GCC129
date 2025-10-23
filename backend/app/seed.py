# Este script popula o banco com dados iniciais.

from .database import SessionLocal, engine
from .models import Base, User, Product, Promotion
from .auth import get_password_hash
from .models import UserRole

def seed_data():
    # Cria as tabelas (caso ainda não existam)
    Base.metadata.create_all(bind=engine)
    
    db = SessionLocal()
    
    try:
        # --- Criar Usuários ---
        if not db.query(User).first():
            print("Criando usuários de teste...")
            
            # Cliente 1
            db.add(User(
                email="cliente@teste.com",
                hashed_password=get_password_hash("123"),
                cargo=UserRole.cliente
            ))
            
            # Cozinheiro 1
            db.add(User(
                email="cozinha@teste.com",
                hashed_password=get_password_hash("123"),
                cargo=UserRole.cozinheiro
            ))
            
            db.commit()
        else:
            print("Usuários já existem.")

        # --- Criar Produtos ---
        if not db.query(Product).first():
            print("Criando produtos...")
            
            db.add_all([
                Product(
                    nome="Café Espresso", 
                    preco=5.00, 
                    categoria="Bebidas",
                    keywords="espresso,expresso,cafe,café",
                    quantidade_estoque=100
                ),
                Product(
                    nome="Cappuccino", 
                    preco=8.50, 
                    categoria="Bebidas",
                    keywords="cappuccino,caputino",
                    quantidade_estoque=50
                ),
                Product(
                    nome="Pão de Queijo", 
                    preco=4.00, 
                    categoria="Salgados",
                    keywords="pão de queijo,pao de queijo,pao,queijo",
                    quantidade_estoque=50
                ),
                Product(
                    nome="Bolo de Fubá", 
                    preco=7.00, 
                    categoria="Doces",
                    keywords="bolo,fubá,bolo de fubá",
                    quantidade_estoque=30
                ),
                Product(
                    nome="Suco de Laranja", 
                    preco=9.00, 
                    categoria="Bebidas",
                    keywords="suco,laranja,suco de laranja",
                    quantidade_estoque=0
                )
            ])
            db.commit()
        else:
            print("Produtos já existem.")
            
        # --- Criar Promoções ---
        if not db.query(Promotion).first():
            print("Criando promoções...")
            
            # Pega o Pão de Queijo
            pdq = db.query(Product).filter(Product.nome == "Pão de Queijo").first()
            
            if pdq:
                db.add(Promotion(
                    descricao="Leve um Pão de Queijo por R$ 2,00 na compra de qualquer café!",
                    produto_associado_id=pdq.id,
                    ativa=True
                ))
            
            db.commit()
        else:
            print("Promoções já existem.")
            
    finally:
        db.close()

if __name__ == "__main__":
    print("Iniciando o seed do banco de dados...")
    seed_data()
    print("Seed concluído.")