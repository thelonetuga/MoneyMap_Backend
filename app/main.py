from fastapi import FastAPI, Depends, HTTPException, status
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy.orm import Session, joinedload
from typing import List
from datetime import timedelta, date # Certifique-se que tem este import no topo
# --- IMPORTS CORRIGIDOS ---
# Estrutura: from [nome_da_pasta] import [nome_do_ficheiro_sem_py]

from database.database import get_db, engine
# Nota: Às vezes é preciso importar o models para o SQLAlchemy o registar
import models.models as models 
import schemas.schemas as schemas

# ... resto do código igual ...

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

@app.get("/users/{user_id}/transactions/", response_model=List[schemas.TransactionResponse])
def read_transactions(user_id: int, db: Session = Depends(get_db)):
    # 1. Obter contas do user
    accounts = db.query(models.Account).filter(models.Account.user_id == user_id).all()
    account_ids = [acc.id for acc in accounts]
    
    # 2. Obter transações dessas contas (ordenadas por data recente)
    transactions = db.query(models.Transaction)\
        .options(
            joinedload(models.Transaction.transaction_type),
            joinedload(models.Transaction.sub_category),
            joinedload(models.Transaction.asset)
        )\
        .filter(models.Transaction.account_id.in_(account_ids))\
        .order_by(models.Transaction.date.desc())\
        .limit(100)\
        .all()
        
    return transactions


@app.delete("/transactions/{transaction_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_transaction(transaction_id: int, db: Session = Depends(get_db)):
    # 1. Buscar a transação
    tx = db.query(models.Transaction).filter(models.Transaction.id == transaction_id).first()
    if not tx:
        raise HTTPException(status_code=404, detail="Transação não encontrada")
    
    # 2. Buscar a conta associada
    account = db.query(models.Account).filter(models.Account.id == tx.account_id).first()
    if not account:
        raise HTTPException(status_code=404, detail="Conta não encontrada")
    
    # 3. Reverter o impacto no Saldo (Account Balance)
    # Lógica inversa à da criação:
    # Se era Despesa/Compra (diminuiu saldo) -> Agora devolvemos (soma)
    # Se era Receita/Venda (aumentou saldo) -> Agora retiramos (subtrai)
    
    negative_keywords = ["Despesa", "Expense", "Levantamento", "Compra", "Buy"]
    is_negative_originally = any(word in tx.transaction_type.name for word in negative_keywords)
    
    if is_negative_originally:
        account.current_balance += tx.amount # Devolve o dinheiro
    else:
        account.current_balance -= tx.amount # Retira o dinheiro

    # 4. Reverter o impacto nos Investimentos (Holdings)
    if tx.asset_id and tx.quantity:
        holding = db.query(models.Holding).filter(
            models.Holding.account_id == account.id,
            models.Holding.asset_id == tx.asset_id
        ).first()
        
        if holding:
            if "Compra" in tx.transaction_type.name or "Buy" in tx.transaction_type.name:
                holding.quantity -= tx.quantity # Se cancelei a compra, removo as ações
            elif "Venda" in tx.transaction_type.name or "Sell" in tx.transaction_type.name:
                holding.quantity += tx.quantity # Se cancelei a venda, devolvo as ações
            
            # Limpeza: Se ficar com quantidade negativa ou zero (opcional)
            if holding.quantity < 0: holding.quantity = 0

    # 5. Apagar efetivamente
    db.delete(tx)
    db.add(account) # Atualizar conta
    db.commit()
    
    return None

# --- Adicionar no main.py (Secção Transações) ---

@app.put("/transactions/{transaction_id}", response_model=schemas.TransactionResponse)
def update_transaction(
    transaction_id: int, 
    updated_tx: schemas.TransactionCreate, 
    db: Session = Depends(get_db)
):
    # 1. Buscar a transação original (Antiga)
    db_tx = db.query(models.Transaction).filter(models.Transaction.id == transaction_id).first()
    if not db_tx:
        raise HTTPException(status_code=404, detail="Transação não encontrada")

    # 2. REVERTER O EFEITO DA ANTIGA (Lógica igual ao Delete)
    # Buscar a conta antiga (caso o user mude de conta, temos de corrigir a antiga)
    old_account = db.query(models.Account).filter(models.Account.id == db_tx.account_id).first()
    
    if not old_account:
        raise HTTPException(status_code=404, detail="Conta não encontrada")
    
    # Identificar se era despesa ou receita
    negative_keywords = ["Despesa", "Expense", "Levantamento", "Compra", "Buy"]
    was_negative = any(word in db_tx.transaction_type.name for word in negative_keywords)
    
    # Desfazer o saldo
    if was_negative:
        old_account.current_balance += db_tx.amount
    else:
        old_account.current_balance -= db_tx.amount

    # Desfazer Investimento (se houver)
    if db_tx.asset_id and db_tx.quantity:
        holding = db.query(models.Holding).filter(
            models.Holding.account_id == db_tx.account_id,
            models.Holding.asset_id == db_tx.asset_id
        ).first()
        if holding:
            if "Compra" in db_tx.transaction_type.name: holding.quantity -= db_tx.quantity
            elif "Venda" in db_tx.transaction_type.name: holding.quantity += db_tx.quantity

    # 3. ATUALIZAR OS DADOS DO OBJETO
    for key, value in updated_tx.model_dump().items():
        setattr(db_tx, key, value)
    
    # 4. APLICAR O EFEITO DA NOVA (Lógica igual ao Create)
    # Buscar a (possivelmente nova) conta e tipo
    new_account = db.query(models.Account).filter(models.Account.id == updated_tx.account_id).first()
    new_type = db.query(models.TransactionType).filter(models.TransactionType.id == updated_tx.transaction_type_id).first()
    
    if not new_account or not new_type:
        raise HTTPException(status_code=404, detail="Conta ou Tipo de Transação não encontrados")
    
    is_negative_new = any(word in new_type.name for word in negative_keywords)
    
    # Aplicar novo saldo
    if is_negative_new:
        new_account.current_balance -= updated_tx.amount
    else:
        new_account.current_balance += updated_tx.amount

    # Aplicar novo Investimento
    if updated_tx.asset_id and updated_tx.quantity:
        holding = db.query(models.Holding).filter(
            models.Holding.account_id == new_account.id,
            models.Holding.asset_id == updated_tx.asset_id
        ).first()
        
        # Nota: Se o holding não existir, teríamos de criar. 
        # Para simplificar a edição, assumimos que se está a editar, o holding já existe ou a lógica é simples.
        if holding:
            if "Compra" in new_type.name: holding.quantity += updated_tx.quantity
            elif "Venda" in new_type.name: holding.quantity -= updated_tx.quantity

    # 5. Gravar tudo
    db.add(old_account)
    if new_account.id != old_account.id: db.add(new_account) # Se mudou de conta
    db.add(db_tx)
    db.commit()
    db.refresh(db_tx)
    
    return db_tx

# --- 6. PORTFÓLIO ---
@app.get("/users/{user_id}/portfolio", response_model=schemas.PortfolioResponse)
def get_portfolio(user_id: int, db: Session = Depends(get_db)):
    # 1. Buscar todas as contas do utilizador
    accounts = db.query(models.Account).filter(models.Account.user_id == user_id).all()
    account_ids = [acc.id for acc in accounts]

    # --- CÁLCULO 1: DINHEIRO (CASH) ---
    # Soma o saldo atual de todas as contas (Bancos, Corretoras com saldo não investido, etc.)
    total_cash = sum(acc.current_balance for acc in accounts)

    # 2. Buscar Holdings (Investimentos ativos)
    holdings = db.query(models.Holding)\
        .options(joinedload(models.Holding.asset))\
        .filter(models.Holding.account_id.in_(account_ids))\
        .filter(models.Holding.quantity > 0)\
        .all()

    positions = []
    total_invested = 0.0

    # --- CÁLCULO 2: INVESTIMENTOS ---
    for h in holdings:
        # Tenta buscar preço recente, senão usa o preço de compra
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
        
        total_invested += market_val

    # --- CÁLCULO 3: TOTAL GERAL ---
    total_net_worth = total_cash + total_invested

    return schemas.PortfolioResponse(
        user_id=user_id,
        total_net_worth=total_net_worth,
        total_cash=total_cash,
        total_invested=total_invested,
        positions=positions
    )


@app.get("/assets/", response_model=List[schemas.AssetResponse])
def get_all_assets(db: Session = Depends(get_db)):
    return db.query(models.Asset).all()


@app.get("/users/{user_id}/history", response_model=List[schemas.HistoryPoint])
def get_net_worth_history(user_id: int, db: Session = Depends(get_db)):
    # 1. Calcular o Património Atual (Igual ao portfólio)
    accounts = db.query(models.Account).filter(models.Account.user_id == user_id).all()
    total_cash = sum(acc.current_balance for acc in accounts)
    
    # Valor dos investimentos atuais
    holdings = db.query(models.Holding).filter(models.Holding.account_id.in_([a.id for a in accounts])).all()
    total_invested = 0.0
    for h in holdings:
        # Simplificação: Usar preço atual para histórico recente
        latest_price = db.query(models.AssetPrice)\
            .filter(models.AssetPrice.asset_id == h.asset_id)\
            .order_by(models.AssetPrice.date.desc()).first()
        price = latest_price.close_price if latest_price else h.avg_buy_price
        total_invested += h.quantity * price
        
    current_net_worth = total_cash + total_invested

    # 2. Buscar transações dos últimos 30 dias
    end_date = date.today()
    start_date = end_date - timedelta(days=30)
    
    transactions = db.query(models.Transaction)\
        .join(models.TransactionType)\
        .filter(models.Transaction.date >= start_date)\
        .order_by(models.Transaction.date.desc())\
        .all()

    # 3. Engenharia Reversa (Do hoje para o passado)
    history = []
    running_balance = current_net_worth
    
    # Criar um mapa de transações por dia para ser rápido
    tx_map = {}
    for tx in transactions:
        d = tx.date.strftime("%Y-%m-%d")
        if d not in tx_map: tx_map[d] = []
        tx_map[d].append(tx)

    # Loop dos últimos 30 dias (do PRESENTE para o PASSADO)
    for i in range(30):
        target_date = end_date - timedelta(days=i)
        date_str = target_date.strftime("%Y-%m-%d")
        
        # Adicionar ponto atual
        history.append(schemas.HistoryPoint(date=date_str, value=running_balance))

        # Ajustar saldo para o dia anterior
        if date_str in tx_map:
            for tx in tx_map[date_str]:
                # Se hoje gastei (Despesa), ontem tinha MAIS dinheiro.
                # Se hoje recebi (Receita), ontem tinha MENOS dinheiro.
                # Investimentos (Compra/Venda) são neutros no Net Worth (sai dinheiro, entra ativo)
                
                is_expense = any(x in tx.transaction_type.name for x in ["Despesa", "Levantamento", "Expense"])
                is_income = any(x in tx.transaction_type.name for x in ["Receita", "Depósito", "Income"])
                
                if is_expense:
                    running_balance += tx.amount
                elif is_income:
                    running_balance -= tx.amount

    # A lista está do Presente -> Passado. Vamos inverter para o Gráfico (Passado -> Presente)
    return history[::-1]

# --- HEALTH CHECK ---
@app.get("/")
def root():
    return {"message": "MoneyMap API v2.0 is running 🚀"}