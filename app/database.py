from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, declarative_base
from typing import Generator

# URL de conexão (em produção, usar variáveis de ambiente)
SQLALCHEMY_DATABASE_URL = "postgresql://admin:segredo@localhost:5432/financas_db"

engine = create_engine(SQLALCHEMY_DATABASE_URL)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

Base = declarative_base()

# Type hint para o gerador de dependência
def get_db() -> Generator:
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()