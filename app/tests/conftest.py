import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool
from fastapi.testclient import TestClient

# --- CORREÇÃO AQUI: Adicionar 'app.' antes dos módulos ---
from app.main import app
from app.database.database import get_db
from app.auth import create_access_token
from app.models.models import TransactionType, AccountType, Base

# 1. Configurar DB SQLite em Memória (Rápida e isolada)
SQLALCHEMY_DATABASE_URL = "sqlite:///:memory:"

engine = create_engine(
    SQLALCHEMY_DATABASE_URL, 
    connect_args={"check_same_thread": False}, 
    poolclass=StaticPool
)
TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

# 2. Fixture para a Base de Dados
@pytest.fixture(scope="function")
def db_session():
    # Cria as tabelas
    Base.metadata.create_all(bind=engine)
    session = TestingSessionLocal()
    try:
        yield session
    finally:
        session.close()
        # Destrói as tabelas no fim de cada teste
        Base.metadata.drop_all(bind=engine)

# 3. Fixture para o Cliente (Override da dependência get_db)
@pytest.fixture(scope="function")
def client(db_session):
    def override_get_db():
        try:
            yield db_session
        finally:
            db_session.close()
    
    app.dependency_overrides[get_db] = override_get_db
    with TestClient(app) as c:
        yield c

# 4. Fixture de Utilizador Autenticado (Atalho útil!)
@pytest.fixture
def auth_headers(client):
    # Registar um user
    client.post("/users/", json={"email": "test@example.com", "password": "pass"})
    # Login para obter token
    response = client.post("/token", data={"username": "test@example.com", "password": "pass"})
    token = response.json()["access_token"]
    return {"Authorization": f"Bearer {token}"}


from app.models.models import TransactionType, AccountType

@pytest.fixture(scope="function", autouse=True)
def seed_db(db_session):
    # Inserir dados essenciais para os testes funcionarem
    if not db_session.query(TransactionType).first():
        db_session.add(TransactionType(id=1, name="Despesa Geral", is_investment=False))
        db_session.add(TransactionType(id=2, name="Receita Salário", is_investment=False))
        db_session.add(AccountType(id=1, name="Conta Ordem"))
        db_session.commit()