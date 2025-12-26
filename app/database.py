from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from typing import Generator

# ATUALIZADO: O nome da base de dados agora é 'moneymap_db' para bater certo com o Docker
SQLALCHEMY_DATABASE_URL = "postgresql://admin:segredo@localhost:5432/moneymap_db"

engine = create_engine(SQLALCHEMY_DATABASE_URL)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

def get_db() -> Generator:
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()