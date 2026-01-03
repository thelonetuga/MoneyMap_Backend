import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool
from fastapi.testclient import TestClient

# --- IMPORTS CORRIGIDOS ---
from app.main import app
from app.database.database import Base, get_db
from app.models import AccountType, TransactionType

# 1. Configurar DB SQLite em Memória (Rápida e isolada)
SQLALCHEMY_DATABASE_URL = "sqlite:///:memory:"

engine = create_engine(
    SQLALCHEMY_DATABASE_URL, 
    connect_args={"check_same_thread": False}, 
    poolclass=StaticPool
)
TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

@pytest.fixture(scope="function")
def db_session():
    # Cria as tabelas antes do teste
    Base.metadata.create_all(bind=engine)
    session = TestingSessionLocal()
    try:
        yield session
    finally:
        session.close()
        # Destrói as tabelas no fim de cada teste
        Base.metadata.drop_all(bind=engine)

@pytest.fixture(scope="function")
def client(db_session):
    def override_get_db():
        try:
            yield db_session
        finally:
            # --- CORREÇÃO CRÍTICA AQUI ---
            # Deixamos 'pass' porque quem fecha a sessão é a fixture 'db_session' acima.
            # Se fecharmos aqui, o próximo pedido do mesmo teste falha (dá erro 401).
            pass 
    
    app.dependency_overrides[get_db] = override_get_db
    with TestClient(app) as c:
        yield c

@pytest.fixture
def auth_headers(client):
    # 1. Registar user
    client.post("/users/", json={"email": "test@example.com", "password": "pass", "profile": {"first_name": "Test"}})
    # 2. Login para obter token
    response = client.post("/token", data={"username": "test@example.com", "password": "pass"})
    token = response.json()["access_token"]
    return {"Authorization": f"Bearer {token}"}

@pytest.fixture(scope="function", autouse=True)
def seed_db(db_session):
    # Garante que existem tipos de conta e transação antes de testar
    if not db_session.query(TransactionType).first():
        # Tipos de Transação
        db_session.add(TransactionType(id=1, name="Despesa", is_investment=False))
        db_session.add(TransactionType(id=2, name="Receita", is_investment=False))
        db_session.add(TransactionType(id=3, name="Compra Ativo", is_investment=True))
        db_session.add(TransactionType(id=4, name="Venda Ativo", is_investment=True))
        
        # Tipos de Conta
        db_session.add(AccountType(id=1, name="Conta Ordem"))
        db_session.add(AccountType(id=2, name="Investimento"))
        db_session.add(AccountType(id=3, name="Poupança"))
        db_session.add(AccountType(id=4, name="Crypto"))

        db_session.commit()