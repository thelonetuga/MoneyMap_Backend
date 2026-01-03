from fastapi.testclient import TestClient
from app.main import app

def test_create_investment_updates_portfolio(client, auth_headers):
    """
    Simula a criação de uma transação de investimento e verifica se o portfolio é atualizado.
    """
    # 1. Criar Conta de Investimento
    acc_res = client.post("/accounts/", json={"name": "Binance", "account_type_id": 2}, headers=auth_headers)
    acc_id = acc_res.json()["id"]
    
    # 2. Criar Transação de COMPRA de BTC
    # Payload esperado pelo backend para ativar a lógica de investimento
    payload = {
        "date": "2023-10-27",
        "description": "Compra Bitcoin",
        "amount": 1000.0, # Valor gasto
        "account_id": acc_id,
        "transaction_type_id": 3, # Compra de Ativo
        "symbol": "BTC",     # <--- CRÍTICO
        "quantity": 0.05,    # <--- CRÍTICO
        "price_per_unit": 20000.0 # Opcional, mas bom enviar
    }
    
    tx_res = client.post("/transactions/", json=payload, headers=auth_headers)
    assert tx_res.status_code == 201
    
    # 3. Verificar Portfolio
    port_res = client.get("/portfolio", headers=auth_headers)
    assert port_res.status_code == 200
    data = port_res.json()
    
    # Debug
    print("Portfolio Data:", data)
    
    # Validações
    assert data["total_invested"] > 0
    assert len(data["positions"]) > 0
    assert data["positions"][0]["symbol"] == "BTC"
    assert data["positions"][0]["quantity"] == 0.05