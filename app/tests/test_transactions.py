import pytest
from app.models import Account

# Fixture auxiliar para criar uma conta rapidamente
@pytest.fixture
def test_account(client, auth_headers):
    # Criar uma conta para o utilizador de teste
    # Assumimos que o AccountType ID 1 (Conta à Ordem) já existe (seed_db)
    res = client.post("/accounts/", json={"name": "Conta Teste", "account_type_id": 1}, headers=auth_headers)
    return res.json()

def test_create_expense_updates_balance(client, auth_headers, test_account, db_session):
    """Testar se uma Despesa subtrai o saldo corretamente"""
    payload = {
        "date": "2024-01-01", "description": "Supermercado", "amount": 50.00,
        "account_id": test_account["id"], "transaction_type_id": 1
    }
    
    res = client.post("/transactions/", json=payload, headers=auth_headers)
    assert res.status_code == 201
    
    # Verificar Saldo na BD
    account = db_session.query(Account).filter(Account.id == test_account["id"]).first()
    assert account.current_balance == -50.0

def test_create_income_updates_balance(client, auth_headers, test_account, db_session):
    """Testar se uma Receita soma o saldo"""
    payload = {
        "date": "2024-01-01", "description": "Salário", "amount": 1000.00,
        "account_id": test_account["id"], "transaction_type_id": 2
    }
    client.post("/transactions/", json=payload, headers=auth_headers)
    
    account = db_session.query(Account).filter(Account.id == test_account["id"]).first()
    assert account.current_balance == 1000.0

def test_security_cannot_use_others_account(client, test_account):
    """Tentar criar transação na conta de outra pessoa deve falhar"""
    
    # 1. O 'test_account' pertence ao User A (criado em auth_headers)
    target_account_id = test_account["id"]

    # 2. Criar User B (Hacker) e fazer login
    client.post("/users/", json={"email": "hacker@test.com", "password": "123", "profile": {"first_name": "Hacker"}})
    login_res = client.post("/token", data={"username": "hacker@test.com", "password": "123"})
    hacker_token = login_res.json()["access_token"]
    hacker_headers = {"Authorization": f"Bearer {hacker_token}"}

    # 3. Tentar inserir despesa na conta do User A usando o token do Hacker
    payload = {
        "date": "2024-01-01", "description": "Roubo", "amount": 100.00,
        "account_id": target_account_id, "transaction_type_id": 1
    }
    
    res = client.post("/transactions/", json=payload, headers=hacker_headers)
    
    # Deve dar 404 (Conta não encontrada para este user) ou 403 (Proibido)
    # Recomendamos 404 para não revelar que a conta existe.
    assert res.status_code in [404, 403]

def test_delete_transaction_reverts_balance(client, auth_headers, test_account, db_session):
    """Apagar uma despesa deve devolver o dinheiro à conta"""
    # 1. Criar
    payload = {"date": "2024-01-01", "description": "Erro", "amount": 50.00, "account_id": test_account["id"], "transaction_type_id": 1}
    create_res = client.post("/transactions/", json=payload, headers=auth_headers)
    tx_id = create_res.json()["id"]
    
    # 2. Apagar
    del_res = client.delete(f"/transactions/{tx_id}", headers=auth_headers)
    assert del_res.status_code == 204 # No Content
    
    # 3. Verificar Saldo (Refresh DB)
    db_session.expire_all()
    account = db_session.query(Account).filter(Account.id == test_account["id"]).first()
    assert account.current_balance == 0.0