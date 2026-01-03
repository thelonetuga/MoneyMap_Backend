def test_get_me(client, auth_headers):
    res = client.get("/users/me", headers=auth_headers)
    assert res.status_code == 200
    assert res.json()["email"] == "test@example.com"

def test_update_profile(client, auth_headers):
    payload = {
        "first_name": "Administrador",
        "last_name": "Supremo",
        "preferred_currency": "USD"
    }
    res = client.put("/users/me", json=payload, headers=auth_headers)
    assert res.status_code == 200
    
    # CORREÇÃO: Aceder ao objeto 'profile' primeiro
    data = res.json()
    assert data["profile"]["first_name"] == "Administrador"
    assert res.json()["preferred_currency"] == "USD"