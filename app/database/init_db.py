# init_db.py
from app.database.database import engine
from app.models.models import Base

def create_tables():
    print("A conectar ao PostgreSQL no Docker...")
    try:
        # Isto transforma as classes Python em tabelas SQL reais
        Base.metadata.create_all(bind=engine)
        print("✅ Sucesso! Tabelas criadas na base de dados 'moneymap_db'.")
    except Exception as e:
        print(f"❌ Erro ao conectar: {e}")

if __name__ == "__main__":
    create_tables()