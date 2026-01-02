import pytest
from io import BytesIO
from app.models import Transaction, Category, Account
import pandas as pd

def test_import_csv_creates_transactions_and_category(client, auth_headers, db_session):
    # 1. Setup: Criar Conta para onde importar
    acc_res = client.post("/accounts/", json={"name": "Conta Import", "account_type_id": 1}, headers=auth_headers)
    assert acc_res.status_code == 201
    account_id = acc_res.json()["id"]

    # 2. Criar ficheiro CSV simulado em memória
    csv_content = """Data,Descrição,Valor
    01-01-2024,Supermercado Continente,-50.00
    02-01-2024,Receita Salário,1500.00
    03-01-2024,Café,-2.50
    """
    
    # Simular UploadFile
    files = {
        'file': ('extrato.csv', BytesIO(csv_content.encode('utf-8')), 'text/csv')
    }

    # 3. Chamar Endpoint de Importação
    # Nota: O endpoint espera query param ?account_id=...
    res = client.post(f"/imports/upload?account_id={account_id}", files=files, headers=auth_headers)
    
    # 4. Verificações
    assert res.status_code == 200, f"Erro: {res.text}"
    data = res.json()
    assert data["added"] == 3
    assert data["errors"] == 0

    # 5. Verificar na Base de Dados se criou a Categoria "Importações"
    # O user_id=1 vem da fixture auth_headers
    cat = db_session.query(Category).filter(Category.name == "Importações").first()
    assert cat is not None
    assert cat.user_id is not None

    # 6. Verificar se as transações ficaram ligadas a essa categoria
    txs = db_session.query(Transaction).filter(Transaction.account_id == account_id).all()
    assert len(txs) == 3
    for tx in txs:
        assert tx.category_id == cat.id
        if "Salário" in tx.description:
            assert tx.amount == 1500.00
            assert tx.transaction_type_id == 2 # Receita (assumindo IDs padrão)
        elif "Continente" in tx.description:
            assert tx.amount == 50.00 # Guardamos absoluto
            assert tx.transaction_type_id == 1 # Despesa