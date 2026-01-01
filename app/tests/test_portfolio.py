from datetime import date
from app.models import Asset, Holding, AssetPrice


def test_portfolio_calculation(client, auth_headers, db_session):
    # 1. Setup: Criar Ativo (Apple)
    appl = Asset(symbol="AAPL", name="Apple Inc.", asset_type="Stock")
    db_session.add(appl)
    db_session.commit()

    # 2. Setup: Criar Conta e Holding (Tenho 10 AAPL compradas a 100€)
    # Criar conta via API
    acc_res = client.post("/accounts/", json={"name": "Broker", "account_type_id": 1}, headers=auth_headers)
    acc_id = acc_res.json()["id"]
    
    # Injetar Holding direto na BD (pois ainda não temos rota de 'Compra de Ativo' completa nos ficheiros que vi)
    holding = Holding(account_id=acc_id, asset_id=appl.id, quantity=10, avg_buy_price=100.0)
    db_session.add(holding)
    db_session.commit()

    # 3. Setup: Injetar Preço Atual (Ontem estava a 150€)
    price = AssetPrice(asset_id=appl.id, date=date(2024, 1, 1), close_price=150.0)
    db_session.add(price)
    db_session.commit()

    # 4. Chamar endpoint /portfolio
    res = client.get("/portfolio", headers=auth_headers)
    assert res.status_code == 200
    data = res.json()

    # 5. Validações
    # Investido = 10 qtd * 150 preço atual = 1500
    assert data["total_invested"] == 1500.0
    
    # Verificar Posição Individual
    pos = data["positions"][0]
    assert pos["symbol"] == "AAPL"
    assert pos["current_price"] == 150.0
    assert pos["profit_loss"] == 500.0 # (150 - 100) * 10