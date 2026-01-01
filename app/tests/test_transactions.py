import pytest
from app.models.models import Account, Transaction

# Fixture auxiliar para criar uma conta rapidamente
@pytest.fixture
def test_account(client, auth_headers, db_session):
    # Criar uma conta para o utilizador de teste
    # Assumimos que o AccountType ID 1 (Conta à Ordem) já foi criado pelo seed do conftest
    res = client.post("/accounts/", json={"name": "Conta Teste", "account_type_id": 1}, headers=auth_headers)
    return res.json()

def test_create_expense_updates_balance(client, auth_headers, test_account, db_session):
    """Testar se uma Despesa subtrai o saldo corretamente"""
    
    # 1. Criar Despesa de 50€ (TransactionType 1 = Despesa)
    payload = {
        "date": "2024-01-01",
        "description": "Supermercado",
        "amount": 50.00,
        "account_id": test_account["id"],
        "transaction_type_id": 1
    }
    
    res = client.post("/transactions/", json=payload, headers=auth_headers)
    assert res.status_code == 201
    
    # 2. Verificar Saldo na Base de Dados
    # O saldo inicial era 0.0, menos 50 deve dar -50.0
    account = db_session.query(Account).filter(Account.id == test_account["id"]).first()
    assert account.current_balance == -50.0

def test_create_income_updates_balance(client, auth_headers, test_account, db_session):
    """Testar se uma Receita soma o saldo"""
    
    # TransactionType 2 = Receita
    payload = {
        "date": "2024-01-01", "description": "Salário", "amount": 1000.00,
        "account_id": test_account["id"], "transaction_type_id": 2
    }
    client.post("/transactions/", json=payload, headers=auth_headers)
    
    account = db_session.query(Account).filter(Account.id == test_account["id"]).first()
    assert account.current_balance == 1000.0

def test_security_cannot_use_others_account(client, db_session):
    """Tentar criar transação na conta de outra pessoa"""
    
    # 1. Criar dois utilizadores (o conftest já cria um 'test@example.com')
    # Vamos criar um 'hacker' e fazer login com ele
    client.post("/users/", json={"email": "hacker@teste.com", "password": "123"})
    login_res = client.post("/token", data={"username": "hacker@teste.com", "password": "123"})
    hacker_token = login_res.json()["access_token"]
    hacker_headers = {"Authorization": f"Bearer {hacker_token}"}

    # 2. Tentar usar a conta do utilizador original (criada na fixture test_account)
    # Precisamos do ID da conta original. Como não temos a fixture aqui direta, vamos buscar à BD.
    # (Ou simplificando: criar uma conta com o user normal e tentar aceder com o hacker)
    
    # Criar conta com User A
    # (Precisamos de auth headers do User A, vamos simular manualmente para ser rápido)
    # ...
    # Para este teste ser limpo, o ideal é tentar aceder a um ID hardcoded que sabemos não ser nosso
    # ou criar uma conta com o setup inicial.
    
    pass # (Deixo este desafio para ti: Tenta implementar a lógica de 'Cross-User Access')

def test_delete_transaction_reverts_balance(client, auth_headers, test_account, db_session):
    """Apagar uma despesa deve devolver o dinheiro à conta"""
    
    # 1. Criar Despesa (-50€)
    payload = {"date": "2024-01-01", "description": "Erro", "amount": 50.00, "account_id": test_account["id"], "transaction_type_id": 1}
    create_res = client.post("/transactions/", json=payload, headers=auth_headers)
    tx_id = create_res.json()["id"]
    
    # 2. Apagar Transação
    del_res = client.delete(f"/transactions/{tx_id}", headers=auth_headers)
    assert del_res.status_code == 204
    
    # 3. Verificar se o saldo voltou a 0
    db_session.expire_all() # Forçar refresh do SQLAlchemy
    account = db_session.query(Account).filter(Account.id == test_account["id"]).first()
    assert account.current_balance == 0.0