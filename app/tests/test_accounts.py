import pytest
from fastapi import status
from app.models.account import Account, AccountType
from app.schemas import schemas

# Test case for unauthenticated user trying to access accounts
def test_get_accounts_unauthenticated(client):
    response = client.get("/accounts/")
    assert response.status_code == status.HTTP_401_UNAUTHORIZED

# Test case for creating an account successfully
def test_create_account(client, auth_headers, db_session):
    # First, create an account type to be used in the test
    # The test user created by `auth_headers` will have ID 1
    account_type = AccountType(name="Test Account Type")
    db_session.add(account_type)
    db_session.commit()
    db_session.refresh(account_type)

    account_data = {
        "name": "Test Account",
        "balance": 1000.0,
        "account_type_id": account_type.id,
    }
    response = client.post("/accounts/", json=account_data, headers=auth_headers)
    assert response.status_code == status.HTTP_201_CREATED
    data = response.json()
    assert data["name"] == account_data["name"]
    assert "id" in data
    assert data["user_id"] == 1

# Test case for listing accounts
def test_read_accounts(client, auth_headers, db_session):
    # Create an account type for the test user (ID 1)
    account_type = AccountType(name="Checking")
    db_session.add(account_type)
    db_session.commit()
    db_session.refresh(account_type)

    # Create an account to be listed
    account = Account(name="My Test Account", current_balance=500.0, user_id=1, account_type_id=account_type.id)
    db_session.add(account)
    db_session.commit()

    response = client.get("/accounts/", headers=auth_headers)
    assert response.status_code == status.HTTP_200_OK
    data = response.json()
    assert isinstance(data, list)
    assert len(data) > 0 # Check that we get at least one account back
