# --- IMPORTS ---
from fastapi import FastAPI, Depends, HTTPException, status
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy.orm import Session, joinedload
from typing import List
from datetime import timedelta, date 
from fastapi.security import OAuth2PasswordBearer, OAuth2PasswordRequestForm
from jose import jwt, JWTError

# Importar configurações de segurança e DB
from auth import get_password_hash, verify_password, create_access_token, SECRET_KEY, ALGORITHM
from database.database import get_db, engine
import models.models as models 
import schemas.schemas as schemas

# Inicializar Base de Dados (cria tabelas se não existirem, mas usamos o seed.py para isso)
models.Base.metadata.create_all(bind=engine)

app = FastAPI(title="MoneyMap API", description="API Financeira Segura v3.0")

# Configuração do Token
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="token")

# --- CONFIGURAÇÃO CORS (Para o Frontend falar com o Backend) ---
origins = ["http://localhost:3000"]
app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ==========================================
# 🔐 SISTEMA DE SEGURANÇA (DEPENDENCY)
# ==========================================

async def get_current_user(token: str = Depends(oauth2_scheme), db: Session = Depends(get_db)):
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Credenciais inválidas",
        headers={"WWW-Authenticate": "Bearer"},
    )
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        email: str = payload.get("sub")
        if email is None:
            raise credentials_exception
    except JWTError:
        raise credentials_exception
        
    user = db.query(models.User).filter(models.User.email == email).first()
    if user is None:
        raise credentials_exception
    return user

# ==========================================
# 🚪 AUTENTICAÇÃO (LOGIN & REGISTO)
# ==========================================

@app.post("/token")
def login_for_access_token(form_data: OAuth2PasswordRequestForm = Depends(), db: Session = Depends(get_db)):
    user = db.query(models.User).filter(models.User.email == form_data.username).first()
    
    if not user or not verify_password(form_data.password, user.password_hash):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Email ou password incorretos",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    access_token = create_access_token(data={"sub": user.email})
    return {"access_token": access_token, "token_type": "bearer"}

@app.post("/users/", response_model=schemas.UserResponse, status_code=status.HTTP_201_CREATED)
def create_user(user: schemas.UserCreate, db: Session = Depends(get_db)):
    if db.query(models.User).filter(models.User.email == user.email).first():
        raise HTTPException(status_code=400, detail="Email já registado")
    
    hashed_pw = get_password_hash(user.password)
    db_user = models.User(email=user.email, password_hash=hashed_pw)
    db.add(db_user)
    db.commit()
    db.refresh(db_user)
    
    if user.profile:
        db_profile = models.UserProfile(**user.profile.model_dump(), user_id=db_user.id)
        db.add(db_profile)
        db.commit()
    
    return db_user

# ==========================================
# 🔍 LOOKUPS (Públicos ou Protegidos)
# ==========================================

@app.get("/lookups/account-types", response_model=List[schemas.AccountTypeResponse])
def get_account_types(db: Session = Depends(get_db)):
    return db.query(models.AccountType).all()

@app.get("/lookups/transaction-types", response_model=List[schemas.TransactionTypeResponse])
def get_transaction_types(db: Session = Depends(get_db)):
    return db.query(models.TransactionType).all()

@app.get("/assets/", response_model=List[schemas.AssetResponse])
def get_all_assets(db: Session = Depends(get_db)):
    return db.query(models.Asset).all()

# ==========================================
# 🏦 CONTAS (Protegido)
# ==========================================

@app.get("/accounts", response_model=List[schemas.AccountResponse])
def read_accounts(db: Session = Depends(get_db), current_user: models.User = Depends(get_current_user)):
    return db.query(models.Account).options(joinedload(models.Account.account_type)).filter(models.Account.user_id == current_user.id).all()

@app.post("/accounts/", response_model=schemas.AccountResponse, status_code=status.HTTP_201_CREATED)
def create_account(account: schemas.AccountCreate, db: Session = Depends(get_db), current_user: models.User = Depends(get_current_user)):
    if not db.query(models.AccountType).filter(models.AccountType.id == account.account_type_id).first():
         raise HTTPException(status_code=400, detail="Tipo de conta inválido")

    db_account = models.Account(**account.model_dump(), user_id=current_user.id)
    db.add(db_account)
    db.commit()
    db.refresh(db_account)
    return db_account

# ==========================================
# 📂 CATEGORIAS (Protegido)
# ==========================================

@app.get("/categories", response_model=List[schemas.CategoryResponse])
def read_categories(db: Session = Depends(get_db), current_user: models.User = Depends(get_current_user)):
    return db.query(models.Category).options(joinedload(models.Category.sub_categories)).filter(models.Category.user_id == current_user.id).all()

@app.post("/categories/", response_model=schemas.CategoryResponse)
def create_category(category: schemas.CategoryCreate, db: Session = Depends(get_db), current_user: models.User = Depends(get_current_user)):
    db_cat = models.Category(**category.model_dump(), user_id=current_user.id)
    db.add(db_cat)
    db.commit()
    db.refresh(db_cat)
    return db_cat

@app.post("/subcategories/", response_model=schemas.SubCategoryResponse)
def create_subcategory(subcat: schemas.SubCategoryCreate, db: Session = Depends(get_db), current_user: models.User = Depends(get_current_user)):
    # Nota: Idealmente verificaríamos se a categoria pai pertence ao user, mas simplificamos aqui.
    db_sub = models.SubCategory(**subcat.model_dump())
    db.add(db_sub)
    db.commit()
    db.refresh(db_sub)
    return db_sub

# ==========================================
# 💸 TRANSAÇÕES (CORE LOGIC - Protegido)
# ==========================================

@app.get("/transactions", response_model=List[schemas.TransactionResponse])
def read_transactions(db: Session = Depends(get_db), current_user: models.User = Depends(get_current_user)):
    # Buscar apenas contas deste user
    account_ids = [acc.id for acc in current_user.accounts]
    
    return db.query(models.Transaction)\
        .options(
            joinedload(models.Transaction.transaction_type),
            joinedload(models.Transaction.sub_category),
            joinedload(models.Transaction.asset)
        )\
        .filter(models.Transaction.account_id.in_(account_ids))\
        .order_by(models.Transaction.date.desc())\
        .limit(100)\
        .all()

@app.post("/transactions/", response_model=schemas.TransactionResponse, status_code=status.HTTP_201_CREATED)
def create_transaction(tx: schemas.TransactionCreate, db: Session = Depends(get_db), current_user: models.User = Depends(get_current_user)):
    # 1. SEGURANÇA: Verificar se a conta é do user
    account = db.query(models.Account).filter(models.Account.id == tx.account_id).first()
    if not account:
        raise HTTPException(status_code=404, detail="Conta não encontrada")
    if account.user_id != current_user.id:
        raise HTTPException(status_code=403, detail="Não tem permissão para usar esta conta.")

    # 2. Atualizar Saldo
    tx_type = db.query(models.TransactionType).filter(models.TransactionType.id == tx.transaction_type_id).first()
    
    # --- CORREÇÃO AQUI ---
    if not tx_type:
        raise HTTPException(status_code=404, detail="Tipo de transação não encontrado")
    
    # Agora o Pylance sabe que tx_type existe e tem .name
    negative_keywords = ["Despesa", "Expense", "Levantamento", "Compra", "Buy"]
    is_negative = any(word in tx_type.name for word in negative_keywords)

    if is_negative:
        account.current_balance -= tx.amount
    else:
        account.current_balance += tx.amount
    
    # 3. Atualizar Investimentos
    if tx.asset_id and tx.quantity:
        holding = db.query(models.Holding).filter(
            models.Holding.account_id == account.id,
            models.Holding.asset_id == tx.asset_id
        ).first()

        if not holding:
            holding = models.Holding(account_id=account.id, asset_id=tx.asset_id, quantity=0, avg_buy_price=0)
            db.add(holding)
        
        if "Compra" in tx_type.name or "Buy" in tx_type.name:
            curr_val = holding.quantity * holding.avg_buy_price
            new_val = tx.quantity * (tx.price_per_unit if tx.price_per_unit else (tx.amount/tx.quantity))
            holding.quantity += tx.quantity
            holding.avg_buy_price = (curr_val + new_val) / holding.quantity
        
        elif "Venda" in tx_type.name or "Sell" in tx_type.name:
            holding.quantity -= tx.quantity
            if holding.quantity < 0: holding.quantity = 0

    # 4. Criar
    db_tx = models.Transaction(**tx.model_dump())
    db.add(db_tx)
    db.add(account)
    db.commit()
    db.refresh(db_tx)
    return db_tx

@app.delete("/transactions/{transaction_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_transaction(transaction_id: int, db: Session = Depends(get_db), current_user: models.User = Depends(get_current_user)):
    tx = db.query(models.Transaction).filter(models.Transaction.id == transaction_id).first()
    if not tx: raise HTTPException(status_code=404, detail="Não encontrado")
    
    # --- CORREÇÃO AQUI ---
    account = db.query(models.Account).filter(models.Account.id == tx.account_id).first()
    
    # Temos de garantir que 'account' não é None antes de ler o user_id
    if not account:
        raise HTTPException(status_code=404, detail="Conta associada não encontrada")
        
    if account.user_id != current_user.id:
        raise HTTPException(status_code=403, detail="Não permitido.")
    
    # REVERSÃO
    negative_keywords = ["Despesa", "Expense", "Levantamento", "Compra", "Buy"]
    is_negative_originally = any(word in tx.transaction_type.name for word in negative_keywords)
    
    # Agora o Pylance sabe que 'account' existe
    if is_negative_originally: account.current_balance += tx.amount
    else: account.current_balance -= tx.amount

    if tx.asset_id and tx.quantity:
        holding = db.query(models.Holding).filter(models.Holding.account_id == account.id, models.Holding.asset_id == tx.asset_id).first()
        if holding:
            if "Compra" in tx.transaction_type.name: holding.quantity -= tx.quantity
            elif "Venda" in tx.transaction_type.name: holding.quantity += tx.quantity
            if holding.quantity < 0: holding.quantity = 0

    db.delete(tx)
    db.add(account)
    db.commit()
    return None

@app.put("/transactions/{transaction_id}", response_model=schemas.TransactionResponse)
def update_transaction(transaction_id: int, updated_tx: schemas.TransactionCreate, db: Session = Depends(get_db), current_user: models.User = Depends(get_current_user)):
    db_tx = db.query(models.Transaction).filter(models.Transaction.id == transaction_id).first()
    if not db_tx: raise HTTPException(status_code=404, detail="Não encontrado")

    # 1. Validar Conta Antiga
    old_account = db.query(models.Account).filter(models.Account.id == db_tx.account_id).first()
    if not old_account: raise HTTPException(status_code=404, detail="Conta antiga não encontrada")
    if old_account.user_id != current_user.id: raise HTTPException(status_code=403, detail="Sem permissão.")
        
    # 2. Validar Conta Nova (CORREÇÃO AQUI)
    new_account = db.query(models.Account).filter(models.Account.id == updated_tx.account_id).first()
    # Adicionamos esta verificação explícita:
    if not new_account: 
        raise HTTPException(status_code=404, detail="Conta destino não encontrada")
    
    if new_account.user_id != current_user.id: raise HTTPException(status_code=403, detail="Conta destino não permitida.")

    # 3. REVERTER ANTIGA
    negative_keywords = ["Despesa", "Expense", "Levantamento", "Compra", "Buy"]
    was_negative = any(word in db_tx.transaction_type.name for word in negative_keywords)
    
    if was_negative: old_account.current_balance += db_tx.amount
    else: old_account.current_balance -= db_tx.amount

    if db_tx.asset_id and db_tx.quantity:
        holding = db.query(models.Holding).filter(models.Holding.account_id == db_tx.account_id, models.Holding.asset_id == db_tx.asset_id).first()
        if holding:
            if "Compra" in db_tx.transaction_type.name: holding.quantity -= db_tx.quantity
            elif "Venda" in db_tx.transaction_type.name: holding.quantity += db_tx.quantity

    # 4. ATUALIZAR DADOS
    for key, value in updated_tx.model_dump().items():
        setattr(db_tx, key, value)
    
    # 5. APLICAR NOVA
    new_type = db.query(models.TransactionType).filter(models.TransactionType.id == updated_tx.transaction_type_id).first()
    if not new_type: raise HTTPException(status_code=404, detail="Tipo de transação não encontrado") # +Correção extra

    is_negative_new = any(word in new_type.name for word in negative_keywords)
    
    if is_negative_new: new_account.current_balance -= updated_tx.amount
    else: new_account.current_balance += updated_tx.amount

    if updated_tx.asset_id and updated_tx.quantity:
        holding = db.query(models.Holding).filter(models.Holding.account_id == new_account.id, models.Holding.asset_id == updated_tx.asset_id).first()
        if holding:
            if "Compra" in new_type.name: holding.quantity += updated_tx.quantity
            elif "Venda" in new_type.name: holding.quantity -= updated_tx.quantity

    db.add(old_account)
    if new_account.id != old_account.id: db.add(new_account)
    db.add(db_tx)
    db.commit()
    db.refresh(db_tx)
    return db_tx

# ==========================================
# 📊 DASHBOARD & HISTÓRICO (Protegido)
# ==========================================

@app.get("/portfolio", response_model=schemas.PortfolioResponse) 
def get_portfolio(current_user: models.User = Depends(get_current_user), db: Session = Depends(get_db)):
    user_id = current_user.id
    accounts = db.query(models.Account).filter(models.Account.user_id == user_id).all()
    account_ids = [acc.id for acc in accounts]

    total_cash = sum(acc.current_balance for acc in accounts)

    holdings = db.query(models.Holding).options(joinedload(models.Holding.asset)).filter(models.Holding.account_id.in_(account_ids)).filter(models.Holding.quantity > 0).all()

    positions = []
    total_invested = 0.0

    for h in holdings:
        latest_price = db.query(models.AssetPrice).filter(models.AssetPrice.asset_id == h.asset_id).order_by(models.AssetPrice.date.desc()).first()
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
        total_invested += market_val

    return schemas.PortfolioResponse(
        user_id=user_id,
        total_net_worth=total_cash + total_invested,
        total_cash=total_cash,
        total_invested=total_invested,
        positions=positions
    )

@app.get("/history", response_model=List[schemas.HistoryPoint])
def get_net_worth_history(db: Session = Depends(get_db), current_user: models.User = Depends(get_current_user)):
    # 1. Calcular Neto Atual
    accounts = db.query(models.Account).filter(models.Account.user_id == current_user.id).all()
    total_cash = sum(acc.current_balance for acc in accounts)
    
    holdings = db.query(models.Holding).filter(models.Holding.account_id.in_([a.id for a in accounts])).all()
    total_invested = 0.0
    for h in holdings:
        latest_price = db.query(models.AssetPrice).filter(models.AssetPrice.asset_id == h.asset_id).order_by(models.AssetPrice.date.desc()).first()
        price = latest_price.close_price if latest_price else h.avg_buy_price
        total_invested += h.quantity * price
        
    current_net_worth = total_cash + total_invested

    # 2. Transações Recentes
    end_date = date.today()
    start_date = end_date - timedelta(days=30)
    
    # Filtrar transações apenas das contas do user
    transactions = db.query(models.Transaction)\
        .join(models.TransactionType)\
        .filter(models.Transaction.account_id.in_([a.id for a in accounts]))\
        .filter(models.Transaction.date >= start_date)\
        .order_by(models.Transaction.date.desc())\
        .all()

    # 3. Engenharia Reversa
    history = []
    running_balance = current_net_worth
    tx_map = {}
    for tx in transactions:
        d = tx.date.strftime("%Y-%m-%d")
        if d not in tx_map: tx_map[d] = []
        tx_map[d].append(tx)

    for i in range(30):
        target_date = end_date - timedelta(days=i)
        date_str = target_date.strftime("%Y-%m-%d")
        
        history.append(schemas.HistoryPoint(date=date_str, value=running_balance))

        if date_str in tx_map:
            for tx in tx_map[date_str]:
                is_expense = any(x in tx.transaction_type.name for x in ["Despesa", "Levantamento", "Expense"])
                is_income = any(x in tx.transaction_type.name for x in ["Receita", "Depósito", "Income"])
                
                if is_expense: running_balance += tx.amount
                elif is_income: running_balance -= tx.amount

    return history[::-1]

@app.get("/")
def root():
    return {"message": "MoneyMap API Segura v3.0 🚀"}