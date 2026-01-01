from datetime import date

def test_spending_analytics(client, auth_headers, db_session):
    """Verificar se o gráfico de despesas agrupa por categoria"""
    
    # 1. Setup: Criar Conta, Categoria e Transação
    # (Podes abstrair isto para fixtures se quiseres código mais limpo)
    acc_res = client.post("/accounts/", json={"name": "Analytics Acc", "account_type_id": 1}, headers=auth_headers)
    acc_id = acc_res.json()["id"]
    
    cat_res = client.post("/categories/", json={"name": "Comida"}, headers=auth_headers)
    cat_id = cat_res.json()["id"]
    
    sub_res = client.post("/subcategories", json={"name": "Pizza", "category_id": cat_id}, headers=auth_headers)
    sub_id = sub_res.json()["id"]
    
    # Criar Despesa
    client.post("/transactions/", json={
        "date": date.today().isoformat(),
        "description": "Jantar",
        "amount": 25.00,
        "account_id": acc_id,
        "transaction_type_id": 1, # Despesa
        "sub_category_id": sub_id
    }, headers=auth_headers)
    
    # 2. Testar Endpoint
    res = client.get("/analytics/spending", headers=auth_headers)
    assert res.status_code == 200
    data = res.json()
    
    # Deve retornar lista: [{"name": "Comida", "value": 25.0}]
    assert len(data) > 0
    assert data[0]["name"] == "Comida"
    assert data[0]["value"] == 25.0

def test_history_endpoint(client, auth_headers):
    """O gráfico de evolução deve retornar sempre 30 pontos (dias)"""
    res = client.get("/history", headers=auth_headers)
    assert res.status_code == 200
    data = res.json()
    
    assert isinstance(data, list)
    assert len(data) == 30 # Garante que cobre os últimos 30 dias
    assert "date" in data[0]
    assert "value" in data[0]