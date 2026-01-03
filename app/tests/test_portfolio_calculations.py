from fastapi.testclient import TestClient
from app.main import app
from datetime import date
from app.models import AssetPrice, Asset
from app.database.database import SessionLocal

def test_avg_price_and_pl_calculation(client, auth_headers, db_session):
    """
    Valida o cálculo de Preço Médio Ponderado e Profit/Loss.
    """
    # 1. Criar Conta Investimento
    acc_res = client.post("/accounts/", json={"name": "Binance", "account_type_id": 2}, headers=auth_headers)
    acc_id = acc_res.json()["id"]
    
    # 2. Compra 1: 1 BTC a 20.000
    client.post("/transactions/", json={
        "date": "2023-01-01", "description": "Buy BTC 1", "amount": 20000.0,
        "account_id": acc_id, "transaction_type_id": 3,
        "symbol": "BTC", "quantity": 1.0, "price_per_unit": 20000.0
    }, headers=auth_headers)
    
    # 3. Compra 2: 1 BTC a 40.000
    client.post("/transactions/", json={
        "date": "2023-01-02", "description": "Buy BTC 2", "amount": 40000.0,
        "account_id": acc_id, "transaction_type_id": 3,
        "symbol": "BTC", "quantity": 1.0, "price_per_unit": 40000.0
    }, headers=auth_headers)
    
    # 4. Verificar Estado Intermédio (Preço Médio)
    # Como ainda não temos preço de mercado, o endpoint usa o avg_price como current_price, logo P/L = 0.
    port_res = client.get("/portfolio", headers=auth_headers)
    data = port_res.json()
    pos = data["positions"][0]
    
    assert pos["symbol"] == "BTC"
    assert pos["quantity"] == 2.0
    assert pos["avg_buy_price"] == 30000.0 # (20k + 40k) / 2
    
    # 5. Injetar Preço de Mercado Manualmente (Simular yfinance)
    # Precisamos do ID do Asset criado
    asset = db_session.query(Asset).filter(Asset.symbol == "BTC").first()
    
    # Inserir preço de 50.000
    price_entry = AssetPrice(asset_id=asset.id, date=date.today(), close_price=50000.0)
    db_session.add(price_entry)
    db_session.commit()
    
    # 6. Verificar P/L Final
    port_res_final = client.get("/portfolio", headers=auth_headers)
    data_final = port_res_final.json()
    pos_final = data_final["positions"][0]
    
    # Validações Matemáticas
    expected_value = 2.0 * 50000.0 # 100k
    expected_pl = (50000.0 - 30000.0) * 2.0 # 40k
    
    assert pos_final["current_price"] == 50000.0
    assert pos_final["total_value"] == expected_value
    assert pos_final["profit_loss"] == expected_pl
    
    print(f"\n✅ Teste Passou: AvgPrice={pos_final['avg_buy_price']}, Current={pos_final['current_price']}, P/L={pos_final['profit_loss']}")