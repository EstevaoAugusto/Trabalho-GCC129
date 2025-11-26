from sqlalchemy import create_engine # Importa o módulo para criar a engine de conexão com o banco de dados
from sqlalchemy.ext.declarative import declarative_base # Importa a função para criar classes base de modelos ORM
from sqlalchemy.orm import sessionmaker # Importa o gerenciador de sessões do SQLAlchemy
import os # Importa o módulo para acessar variáveis de ambiente
from dotenv import load_dotenv # Importa a função para carregar variáveis de ambiente de um arquivo .env

# Carrega as variáveis de ambiente do arquivo .env
load_dotenv()

# Pega a URL do banco de dados armazenada na variável de ambiente DATABASE_URL
SQLALCHEMY_DATABASE_URL = os.getenv("DATABASE_URL")

# Cria a engine de conexão com o banco de dados
engine = create_engine(SQLALCHEMY_DATABASE_URL)

# Cria uma classe de sessão:
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

# Cria a classe base para declarar os modelos ORM
Base = declarative_base()

# Função geradora para fornecer uma sessão de banco de dados
def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
