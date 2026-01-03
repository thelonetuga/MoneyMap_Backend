from fastapi.testclient import TestClient
from app.main import app

def test_user_cannot_access_others_account(client, db_session):
    """
    Cenário:
    - User A (Autenticado via client/fixture) cria uma conta.
    - Criamos um User B manualmente.
    - User B tenta aceder à conta do User A.
    """
    # 1. User A (o default da fixture 'client') cria uma conta
    # Precisamos do header do User A. A fixture 'auth_headers' já faz isso, 
    # mas aqui vamos fazer manualmente para ter controlo sobre DOIS users.
    
    # --- SETUP USER A ---
    client.post("/users/", json={"email": "userA@test.com", "password": "123", "profile": {"first_name": "A"}})
    token_a = client.post("/token", data={"username": "userA@test.com", "password": "123"}).json()["access_token"]
    headers_a = {"Authorization": f"Bearer {token_a}"}
    
    # User A cria conta ID X
    res = client.post("/accounts/", json={"name": "Conta A", "account_type_id": 1}, headers=headers_a)
    assert res.status_code == 201 # <--- CORREÇÃO: Esperar 201 Created
    account_id_a = res.json()["id"]
    
    # --- SETUP USER B ---
    client.post("/users/", json={"email": "userB@test.com", "password": "123", "profile": {"first_name": "B"}})
    token_b = client.post("/token", data={"username": "userB@test.com", "password": "123"}).json()["access_token"]
    headers_b = {"Authorization": f"Bearer {token_b}"}
    
    # --- O ATAQUE ---
    # User B tenta ler a conta do User A
    res_attack = client.get(f"/accounts/{account_id_a}", headers=headers_b)
    
    # Esperamos 404 ou 403. Ambos impedem o acesso.
    assert res_attack.status_code in [404, 403]

def test_user_cannot_delete_others_transaction(client):
    """
    Cenário: User B tenta apagar transação do User A.
    """
    # --- SETUP USER A ---
    client.post("/users/", json={"email": "rich@test.com", "password": "123"})
    token_a = client.post("/token", data={"username": "rich@test.com", "password": "123"}).json()["access_token"]
    headers_a = {"Authorization": f"Bearer {token_a}"}
    
    # Conta e Transação do A
    acc_res = client.post("/accounts/", json={"name": "Cofre", "account_type_id": 1}, headers=headers_a)
    acc_id = acc_res.json()["id"]
    
    # Precisamos de categorias (User A cria as suas ou usa globais se existirem)
    # Vamos criar uma rápida
    cat_res = client.post("/categories/", json={"name": "Geral"}, headers=headers_a)
    cat_id = cat_res.json()["id"]
    
    tx_res = client.post("/transactions/", json={
        "date": "2023-01-01", "description": "Segredo", "amount": -1000,
        "account_id": acc_id, "transaction_type_id": 1, "category_id": cat_id
    }, headers=headers_a)
    tx_id = tx_res.json()["id"]
    
    # --- SETUP USER B (O Hacker) ---
    client.post("/users/", json={"email": "hacker@test.com", "password": "123"})
    token_b = client.post("/token", data={"username": "hacker@test.com", "password": "123"}).json()["access_token"]
    headers_b = {"Authorization": f"Bearer {token_b}"}
    
    # --- O ATAQUE ---
    res_attack = client.delete(f"/transactions/{tx_id}", headers=headers_b)
    
    # Aceitamos 403 (Forbidden) ou 404 (Not Found).
    # O importante é que NÃO seja 200/204 (Sucesso).
    assert res_attack.status_code in [403, 404]

def test_evolution_empty_state(client):
    """
    Cenário: User novo sem contas nem transações chama /evolution.
    Não deve dar erro 500.
    """
    client.post("/users/", json={"email": "newbie@test.com", "password": "123"})
    token = client.post("/token", data={"username": "newbie@test.com", "password": "123"}).json()["access_token"]
    headers = {"Authorization": f"Bearer {token}"}
    
    res = client.get("/analytics/evolution?period=year", headers=headers)
    
    assert res.status_code == 200
    data = res.json()
    assert isinstance(data, list)
    assert len(data) == 0 # Deve retornar lista vazia limpa