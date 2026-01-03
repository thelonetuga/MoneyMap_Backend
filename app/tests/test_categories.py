from app.models import Category, SubCategory


def test_create_and_delete_subcategory(client, auth_headers, db_session):
    # 1. Criar Categoria Pai (seed ou manual)
    # Vamos criar uma manual ligada ao user para garantir
    cat = Category(name="Pai Teste", user_id=1)
    db_session.add(cat)
    db_session.commit()
    
    # 2. Criar Subcategoria via API
    payload = {"name": "Sub Teste", "category_id": cat.id}
    res = client.post("/categories/subcategories", json=payload, headers=auth_headers)
    assert res.status_code == 200
    sub_id = res.json()["id"]

   # 3. Apagar Subcategoria
    del_res = client.delete(f"/categories/subcategories/{sub_id}", headers=auth_headers)
    
    # CORREÇÃO: O status correto para delete sem retorno é 204, não 200
    assert del_res.status_code == 204

def test_cannot_delete_category_with_transactions(client, auth_headers, db_session):
    # 1. Setup: Categoria -> Subcategoria -> Conta -> Transação
    # (Simplificado usando objetos DB diretos para rapidez)
    cat = Category(name="Pai Bloq", user_id=1)
    db_session.add(cat)
    db_session.commit()
    
    sub = SubCategory(name="Sub Bloq", category_id=cat.id)
    db_session.add(sub)
    db_session.commit() # Get ID
    
    # Criar conta e transação ligada a esta subcategoria
    # (Usamos a API para ser mais realista ou fixture se já tiveres)
    # Aqui vou criar conta via API para ser rápido
    acc_res = client.post("/accounts/", json={"name": "Conta Categ", "account_type_id": 1}, headers=auth_headers)
    acc_id = acc_res.json()["id"]
    
    tx_payload = {
        "date": "2024-01-01", "description": "Teste", "amount": 10.0,
        "account_id": acc_id, "transaction_type_id": 1, 
        "sub_category_id": sub.id # <--- LIGAÇÃO CRÍTICA
    }
    client.post("/transactions/", json=tx_payload, headers=auth_headers)
    
    # 2. Tentar apagar a subcategoria
    del_res = client.delete(f"/categories/subcategories/{sub.id}", headers=auth_headers)
    
    # 3. Deve falhar (Bad Request)
    assert del_res.status_code == 400
    assert "transações associadas" in del_res.json()["detail"]