from fastapi import FastAPI, Depends, HTTPException, status
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy.orm import Session, joinedload
from sqlalchemy import func
from typing import List

# Importar os ficheiros locais
import models
import schemas
from database import get_db

app = FastAPI(title="MoneyMap API", description="API Financeira v2.0")

# --- CONFIGURAÇÃO CORS ---
origins = ["http://localhost:3000"]
app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# --- 1. ENDPOINTS DE LOOKUPS (Para as Dropdowns do Frontend) ---

@app.get("/lookups/account-types", response_model=List[schemas.AccountTypeResponse])
def get_account_types(db: Session = Depends(get_db)):
    return db.query(models.AccountType).all()

@app.get("/lookups/transaction-types", response_model=List[schemas.TransactionTypeResponse])
def get_transaction_types(db: Session = Depends(get_db)):
    return db.query(models.TransactionType).all()


# --- 2. UTILIZADORES ---

@app.post("/users/", response_model=schemas.UserResponse, status_code=status.HTTP_201_CREATED)
def create_user(user: schemas.UserCreate, db: Session = Depends(get_db)):
    # Verificar email duplicado
    if db.query(models.User).filter(models.User.email == user.email).first():
        raise HTTPException(status_code=400, detail="Email já registado")
    
    # Criar User
    fake_hashed_pw = user.password + "hash"
    db_user = models.User(email=user.email, password_hash=fake_hashed_pw)
    db.add(db_user)
    db.commit()
    db.refresh(db_user)
    
    # Criar Perfil (Opcional ou Default)
    if user.profile:
        db_profile = models.UserProfile(**user.profile.model_dump(), user_id=db_user.id)
        db.add(db_profile)
        db.commit()
        db.refresh(db_user) # Recarregar user para trazer o perfil
        
    return db_user

@app.get("/users/{user_id}", response_model=schemas.UserResponse)
def read_user(user_id: int, db: Session = Depends(get_db)):
    # joinedload traz o profile numa só query
    db_user = db.query(models.User).options(joinedload(models.User.profile)).filter(models.User.id == user_id).first()
    if not db_user:
        raise HTTPException(status_code=404, detail="User not found")
    return db_user


# --- 3. CONTAS ---

@app.post("/users/{user_id}/accounts/", response_model=schemas.AccountResponse)
def create_account(user_id: int, account: schemas.AccountCreate, db: Session = Depends(get_db)):
    # Validar se o AccountType existe
    if not db.query(models.AccountType).filter(models.AccountType.id == account.account_type_id).first():
         raise HTTPException(status_code=400, detail="Tipo de conta inválido")

    db_account = models.Account(**account.model_dump(), user_id=user_id)
    db.add(db_account)
    db.commit()
    db.refresh(db_account)
    return db_account

@app.get("/users/{user_id}/accounts/", response_model=List[schemas.AccountResponse])
def get_user_accounts(user_id: int, db: Session = Depends(get_db)):
    return db.query(models.Account)\
        .options(joinedload(models.Account.account_type))\
        .filter(models.Account.user_id == user_id).all()


# --- 4. CATEGORIAS E SUBCATEGORIAS ---

@app.post("/categories/", response_model=schemas.CategoryResponse)
def create_category(category: schemas.CategoryCreate, user_id: int, db: Session = Depends(get_db)):
    # Nota: user_id vem na query string por simplicidade, num caso real viria do token de auth
    db_cat = models.Category(**category.model_dump(), user_id=user_id)
    db.add(db_cat)
    db.commit()
    db.refresh(db_cat)
    return db_cat

@app.post("/subcategories/", response_model=schemas.SubCategoryResponse)
def create_subcategory(subcat: schemas.SubCategoryCreate, db: Session = Depends(get_db)):
    db_sub = models.SubCategory(**subcat.model_dump())
    db.add(db_sub)
    db.commit()
    db.refresh(db_sub)
    return db_sub

@app.get("/users/{user_id}/categories/", response_model=List[schemas.CategoryResponse])
def get_categories(user_id: int, db: Session = Depends(get_db)):
    # Traz as categorias e as suas subcategorias automaticamente
    return db.query(models.Category)\
        .options(joinedload(models.Category.sub_categories))\
        .filter(models.Category.user_id == user_id).all()


# --- 5. TRANSAÇÕES (A Lógica Pesada) ---

@app.post("/transactions/", response_model=schemas.TransactionResponse)
def create_transaction(tx: schemas.TransactionCreate, db: Session = Depends(get_db)):
    # 1. Buscar Conta e Tipo de Transação
    account = db.query(models.Account).filter(models.Account.id == tx.account_id).first()
    tx_type = db.query(models.TransactionType).filter(models.TransactionType.id == tx.transaction_type_id).first()
    
    if not account or not tx_type:
        raise HTTPException(status_code=404, detail="Conta ou Tipo de Transação não encontrados")

    # 2. Atualizar Saldo da Conta
    # Regra simples: Se o nome contiver "Despesa", "Levantamento" ou "Compra", subtrai.
    # Caso contrário (Receita, Depósito, Venda), soma.
    negative_keywords = ["Despesa", "Expense", "Levantamento", "Withdraw", "Compra", "Buy"]
    
    is_negative = any(word in tx_type.name for word in negative_keywords)
    
    if is_negative:
        account.current_balance -= tx.amount
    else:
        account.current_balance += tx.amount

    # 3. Lógica de Investimento (Se for Compra/Venda de Ações)
    if tx.asset_id and tx.quantity:
        # Procurar se já temos este ativo nesta conta
        holding = db.query(models.Holding).filter(
            models.Holding.account_id == account.id,
            models.Holding.asset_id == tx.asset_id
        ).first()

        if "Compra" in tx_type.name or "Buy" in tx_type.name:
            if holding:
                # Recalcular Preço Médio: (Valor Antigo + Valor Novo) / Quantidade Nova
                total_value_old = holding.quantity * holding.avg_buy_price
                total_value_new = tx.quantity * (tx.price_per_unit or 0)
                new_qty = holding.quantity + tx.quantity
                holding.avg_buy_price = (total_value_old + total_value_new) / new_qty
                holding.quantity = new_qty
            else:
                # Nova Posição
                holding = models.Holding(
                    account_id=account.id,
                    asset_id=tx.asset_id,
                    quantity=tx.quantity,
                    avg_buy_price=tx.price_per_unit or 0
                )
                db.add(holding)
        
        elif "Venda" in tx_type.name or "Sell" in tx_type.name:
            if holding:
                holding.quantity -= tx.quantity
                # Se vender tudo, podíamos apagar o holding, mas deixamos ficar a 0 por histórico
                if holding.quantity < 0: holding.quantity = 0

    # 4. Guardar Transação
    db_tx = models.Transaction(**tx.model_dump())
    
    db.add(db_tx)
    db.add(account) # Guardar novo saldo
    db.commit()
    db.refresh(db_tx)
    return db_tx


# --- 6. PORTFÓLIO ---

@app.get("/users/{user_id}/portfolio", response_model=schemas.PortfolioResponse)
def get_portfolio(user_id: int, db: Session = Depends(get_db)):
    # 1. IDs das contas do user
    accounts = db.query(models.Account).filter(models.Account.user_id == user_id).all()
    account_ids = [acc.id for acc in accounts]

    # 2. Buscar Holdings
    holdings = db.query(models.Holding)\
        .options(joinedload(models.Holding.asset))\
        .filter(models.Holding.account_id.in_(account_ids))\
        .filter(models.Holding.quantity > 0)\
        .all()

    positions = []
    total_val = 0.0

    for h in holdings:
        # Preço mais recente
        latest_price = db.query(models.AssetPrice)\
            .filter(models.AssetPrice.asset_id == h.asset_id)\
            .order_by(models.AssetPrice.date.desc())\
            .first()
        
        curr_price = latest_price.close_price if latest_price else h.avg_buy_price
        market_val = h.quantity * curr_price
        pnl = market_val - (h.quantity * h.avg_buy_price)

        positions.append(schemas.PortfolioPosition(
            symbol=h.asset.symbol,
            quantity=h.quantity,
            avg_buy_price=h.avg_buy_price,
            current_price=curr_price,
            total_value=market_val,
            profit_loss=pnl
        ))
        total_val += market_val

    return schemas.PortfolioResponse(
        user_id=user_id,
        total_portfolio_value=total_val,
        positions=positions
    )

# --- HEALTH CHECK ---
@app.get("/")
def root():
    return {"message": "MoneyMap API v2.0 is running 🚀"}