def test_register_user(client):
    response = client.post(
        "/users/",
        json={"email": "novo@teste.com", "password": "123", "profile": {"first_name": "Test"}}
    )
    assert response.status_code == 201
    assert response.json()["email"] == "novo@teste.com"

def test_register_duplicate_email(client):
    # Primeiro registo
    client.post("/users/", json={"email": "duplo@teste.com", "password": "123"})
    # Segundo registo (deve falhar)
    response = client.post("/users/", json={"email": "duplo@teste.com", "password": "123"})
    assert response.status_code == 400
    assert "registered" in response.json()["detail"]

def test_login_success(client):
    client.post("/users/", json={"email": "login@teste.com", "password": "securepassword"})
    response = client.post("/token", data={"username": "login@teste.com", "password": "securepassword"})
    assert response.status_code == 200
    assert "access_token" in response.json()