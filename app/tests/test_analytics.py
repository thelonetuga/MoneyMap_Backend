from datetime import date, timedelta

def test_spending_analytics(client, auth_headers, db_session):
    """Verificar se o gráfico de despesas agrupa por categoria"""
    
    # 1. Setup
    acc_res = client.post("/accounts/", json={"name": "Analytics Acc", "account_type_id": 1}, headers=auth_headers)
    acc_id = acc_res.json()["id"]
    
    cat_res = client.post("/categories/", json={"name": "Comida"}, headers=auth_headers)
    cat_id = cat_res.json()["id"]
    
    sub_res = client.post("/categories/subcategories", json={"name": "Pizza", "category_id": cat_id}, headers=auth_headers)
    sub_id = sub_res.json()["id"]
    
    # Criar Despesa
    client.post("/transactions/", json={
        "date": date.today().isoformat(),
        "description": "Jantar",
        "amount": -25.00,       # <--- CORREÇÃO 1: Valor negativo para ser considerado despesa
        "account_id": acc_id,
        "transaction_type_id": 1, 
        "category_id": cat_id,  # <--- CORREÇÃO 2: Associar a Categoria Pai explicitamente
        "sub_category_id": sub_id
    }, headers=auth_headers)
    
    # 2. Testar Endpoint
    res = client.get("/analytics/spending", headers=auth_headers)
    assert res.status_code == 200
    data = res.json()
    
    # Agora sim, deve encontrar os dados
    assert len(data) > 0
    assert data[0]["name"] == "Comida"
    assert data[0]["value"] == 25.0

def test_history_endpoint(client, auth_headers):
    """O gráfico de evolução deve retornar sempre 31 pontos (últimos 30 dias + hoje)"""
    res = client.get("/analytics/history", headers=auth_headers)
    assert res.status_code == 200
    data = res.json()
    
    assert isinstance(data, list)
    assert len(data) == 31 # <--- CORREÇÃO: O backend gera 31 pontos (range(31))
    assert "date" in data[0]
    assert "value" in data[0]

def test_evolution_endpoint(client, auth_headers, db_session):
    """
    Testa a evolução macro (Anual) com distinção de Liquidez vs Investimento
    E valida a sincronização LIVE (Live Sync).
    """
    from app.models import Account
    
    # 1. Criar Conta Bancária (Líquida - Tipo 1)
    bank_res = client.post("/accounts/", json={"name": "Banco", "account_type_id": 1}, headers=auth_headers)
    bank_id = bank_res.json()["id"]

    # 2. Criar Conta Investimento (Não Líquida - Tipo 2)
    invest_res = client.post("/accounts/", json={"name": "Corretora", "account_type_id": 2}, headers=auth_headers)
    invest_id = invest_res.json()["id"]
    
    today = date.today()
    last_year = today.replace(year=today.year - 1)
    
    # --- ANO PASSADO ---
    # Recebeu 1000 no Banco
    client.post("/transactions/", json={
        "date": last_year.isoformat(), "description": "Salário", "amount": 1000.0,
        "account_id": bank_id, "transaction_type_id": 2
    }, headers=auth_headers)
    
    # --- ESTE ANO ---
    # Gastou 100 do Banco
    client.post("/transactions/", json={
        "date": today.isoformat(), "description": "Jantar", "amount": -100.0,
        "account_id": bank_id, "transaction_type_id": 1
    }, headers=auth_headers)
    
    # ATÉ AQUI:
    # Saldo Banco Calculado pelas Transações: 1000 - 100 = 900.
    # Saldo Corretora: 0.
    
    # --- SIMULAR DESVIO (LIVE SYNC) ---
    # Vamos alterar manualmente o saldo da conta na BD para 5000 (simulando um ajuste manual ou erro)
    # O endpoint deve retornar 5000 para o ano atual, e não 900.
    
    # Precisamos de fazer isto via SQL direto ou hack, pois a API atualiza o saldo com transações.
    # Como temos acesso à db_session via fixture (adicionei db_session aos argumentos):
    
    acc_obj = db_session.query(Account).filter(Account.id == bank_id).first()
    acc_obj.current_balance = 5000.0
    db_session.commit()
    
    # 3. Chamar Endpoint
    res = client.get("/analytics/evolution?period=year", headers=auth_headers)
    assert res.status_code == 200
    data = res.json()
    
    # 4. Validações
    
    # Ano Atual (Live Sync)
    point_this_year = next((d for d in data if d["period"] == str(today.year)), None)
    assert point_this_year is not None
    
    # O Net Worth deve ser 5000 (o valor Live que forçámos), e não 900 (o histórico).
    assert point_this_year["net_worth"] == 5000.0
    assert point_this_year["liquid_cash"] == 5000.0
    
    # As despesas devem continuar a ser 100 (Flow não muda)
    assert point_this_year["expenses"] == 100.0