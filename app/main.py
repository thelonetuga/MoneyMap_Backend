from fastapi import FastAPI, Depends, HTTPException, status
from sqlalchemy.orm import Session
from typing import List

# Importar os ficheiros locais
import models
import schemas
from database import get_db

# Inicializar a App
app = FastAPI(title="MoneyMap API", description="API de Gestão Financeira Pessoal")

# --- ROTAS DE UTILIZADORES (USERS) ---

@app.post("/users/", response_model=schemas.UserResponse, status_code=status.HTTP_201_CREATED)
def create_user(user: schemas.UserCreate, db: Session = Depends(get_db)):
    # 1. Verificar se o email já existe
    db_user = db.query(models.User).filter(models.User.email == user.email).first()
    if db_user:
        raise HTTPException(status_code=400, detail="Email já registado")
    
    # 2. Criar o utilizador (Numa app real, faríamos hash da password aqui)
    fake_hashed_password = user.password + "notreallyhashed"
    db_user = models.User(email=user.email, password_hash=fake_hashed_password)
    
    db.add(db_user)
    db.commit()
    db.refresh(db_user)
    return db_user

@app.get("/users/{user_id}", response_model=schemas.UserResponse)
def read_user(user_id: int, db: Session = Depends(get_db)):
    db_user = db.query(models.User).filter(models.User.id == user_id).first()
    if db_user is None:
        raise HTTPException(status_code=404, detail="Utilizador não encontrado")
    return db_user


# --- ROTAS DE CONTAS (ACCOUNTS) ---

@app.post("/users/{user_id}/accounts/", response_model=schemas.AccountResponse)
def create_account_for_user(user_id: int, account: schemas.AccountCreate, db: Session = Depends(get_db)):
    # 1. Validar se o utilizador existe
    user = db.query(models.User).filter(models.User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="Utilizador não encontrado")

    # 2. Criar conta
    db_account = models.Account(**account.model_dump(), user_id=user_id)
    db.add(db_account)
    db.commit()
    db.refresh(db_account)
    return db_account

@app.get("/users/{user_id}/accounts/", response_model=List[schemas.AccountResponse])
def read_accounts_for_user(user_id: int, db: Session = Depends(get_db)):
    accounts = db.query(models.Account).filter(models.Account.user_id == user_id).all()
    return accounts


# --- ROTAS DE CATEGORIAS ---

@app.post("/users/{user_id}/categories/", response_model=schemas.CategoryResponse)
def create_category_for_user(user_id: int, category: schemas.CategoryCreate, db: Session = Depends(get_db)):
    db_category = models.Category(**category.model_dump(), user_id=user_id)
    db.add(db_category)
    db.commit()
    db.refresh(db_category)
    return db_category

@app.get("/users/{user_id}/categories/", response_model=List[schemas.CategoryResponse])
def read_categories(user_id: int, db: Session = Depends(get_db)):
    return db.query(models.Category).filter(models.Category.user_id == user_id).all()


# --- ROTAS DE TRANSAÇÕES ---

@app.post("/transactions/", response_model=schemas.TransactionResponse)
def create_transaction(transaction: schemas.TransactionCreate, db: Session = Depends(get_db)):
    # 1. Verificar se a conta existe
    account = db.query(models.Account).filter(models.Account.id == transaction.account_id).first()
    if not account:
        raise HTTPException(status_code=404, detail="Conta não encontrada")

    # 2. Criar transação
    db_transaction = models.Transaction(**transaction.model_dump())
    
    # 3. Atualizar o saldo da conta automaticamente
    # Lógica simples: Se for WITHDRAW ou BUY, subtrai. Se for DEPOSIT ou SELL, soma.
    if transaction.transaction_type in ["WITHDRAW", "BUY"]:
        account.current_balance -= transaction.amount
    elif transaction.transaction_type in ["DEPOSIT", "SELL"]:
        account.current_balance += transaction.amount
    
    db.add(db_transaction)
    db.add(account) # Atualiza a conta também
    db.commit()
    db.refresh(db_transaction)
    return db_transaction

@app.get("/accounts/{account_id}/transactions/", response_model=List[schemas.TransactionResponse])
def read_transactions(account_id: int, db: Session = Depends(get_db)):
    return db.query(models.Transaction).filter(models.Transaction.account_id == account_id).all()


# --- ROTA DE SAÚDE (HEALTH CHECK) ---
@app.get("/")
def read_root():
    return {"message": "API do MoneyMap está online! 🚀 Visite /docs para testar."}