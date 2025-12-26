from fastapi import FastAPI, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import List, Dict, Any
import yfinance as yf

from . import models, schemas, database

# Criar tabelas na base de dados
database.Base.metadata.create_all(bind=database.engine)

# --- A DEFINIÇÃO DA APP (CRUCIAL) ---
app = FastAPI(
    title="MoneyMap API",
    description="Personal Finance & Investment Tracker",
    version="1.0.0"
)

# --- ACCOUNTS ---
@app.post("/accounts/", response_model=schemas.AccountResponse)
def create_account(account: schemas.AccountCreate, db: Session = Depends(database.get_db)) -> models.Account:
    db_account = models.Account(**account.model_dump())
    db.add(db_account)
    db.commit()
    db.refresh(db_account)
    return db_account

@app.get("/accounts/", response_model=List[schemas.AccountResponse])
def get_accounts(db: Session = Depends(database.get_db)) -> List[models.Account]:
    return db.query(models.Account).all()

# --- TRANSACTIONS ---
@app.post("/transactions/", response_model=schemas.TransactionResponse)
def create_transaction(transaction: schemas.TransactionCreate, db: Session = Depends(database.get_db)) -> models.Transaction:
    db_transaction = models.Transaction(**transaction.model_dump())
    db.add(db_transaction)
    
    # Atualizar saldo da conta
    account = db.query(models.Account).filter(models.Account.id == transaction.account_id).first()
    if not account:
        raise HTTPException(status_code=404, detail="Account not found")
    
    # Conversão explícita para evitar erros do Pylance com Mapped Columns
    current_bal = float(account.current_balance)
    account.current_balance = current_bal + transaction.amount
    
    db.commit()
    db.refresh(db_transaction)
    return db_transaction

# --- ASSETS ---
@app.post("/assets/", response_model=schemas.AssetResponse)
def create_asset(asset: schemas.AssetCreate, db: Session = Depends(database.get_db)) -> models.Asset:
    db_asset = models.Asset(**asset.model_dump())
    db.add(db_asset)
    db.commit()
    db.refresh(db_asset)
    return db_asset

@app.get("/assets/", response_model=List[schemas.AssetResponse])
def get_assets(db: Session = Depends(database.get_db)) -> List[models.Asset]:
    return db.query(models.Asset).all()

# --- HOLDINGS (PORTFOLIO) ---
@app.post("/holdings/", response_model=schemas.HoldingResponse)
def create_holding(holding: schemas.HoldingCreate, db: Session = Depends(database.get_db)) -> Any:
    # Verifica se já existe a posição
    existing_holding = db.query(models.Holding).filter(
        models.Holding.account_id == holding.account_id,
        models.Holding.asset_id == holding.asset_id
    ).first()
    
    asset = db.query(models.Asset).filter(models.Asset.id == holding.asset_id).first()
    if not asset:
        raise HTTPException(status_code=404, detail="Asset not found")

    if existing_holding:
        # Atualiza preço médio e quantidade
        # Convertemos para float para garantir cálculos corretos
        qty_old = float(existing_holding.quantity)
        price_old = float(existing_holding.avg_buy_price)
        qty_new = holding.quantity
        price_new = holding.avg_buy_price

        total_cost_old = qty_old * price_old
        total_cost_new = qty_new * price_new
        new_qty = qty_old + qty_new
        
        if new_qty > 0:
            existing_holding.avg_buy_price = (total_cost_old + total_cost_new) / new_qty
            existing_holding.quantity = new_qty
        else:
            existing_holding.quantity = 0.0
            existing_holding.avg_buy_price = 0.0

        db.commit()
        db.refresh(existing_holding)
        
        # Mapeamento manual para resposta
        response = schemas.HoldingResponse.model_validate(existing_holding)
        response.asset_symbol = str(asset.symbol)
        return response
    else:
        # Cria nova posição
        db_holding = models.Holding(**holding.model_dump())
        db.add(db_holding)
        db.commit()
        db.refresh(db_holding)
        
        response = schemas.HoldingResponse.model_validate(db_holding)
        response.asset_symbol = str(asset.symbol)
        return response

@app.get("/portfolio/{account_id}", response_model=schemas.PortfolioResponse)
def get_portfolio_value(account_id: int, db: Session = Depends(database.get_db)) -> Dict[str, Any]:
    holdings = db.query(models.Holding).filter(models.Holding.account_id == account_id).all()
    
    portfolio_positions = []
    total_value = 0.0

    for item in holdings:
        # Pylance type guards
        qty = float(item.quantity)
        if qty == 0: continue

        asset = db.query(models.Asset).filter(models.Asset.id == item.asset_id).first()
        if not asset: continue

        # Lógica de preço atual (Yahoo Finance)
        current_price = 0.0
        try:
            ticker_obj = yf.Ticker(str(asset.symbol))
            # Tentar fast_info primeiro
            if hasattr(ticker_obj, "fast_info") and ticker_obj.fast_info.last_price:
                 current_price = float(ticker_obj.fast_info.last_price)
            else:
                 # Fallback para histórico
                 hist = ticker_obj.history(period="1d")
                 if not hist.empty:
                    current_price = float(hist['Close'].iloc[-1])
                 else:
                    current_price = float(item.avg_buy_price)
        except Exception:
            current_price = float(item.avg_buy_price)

        avg_price = float(item.avg_buy_price)
        market_value = qty * current_price
        profit_loss = market_value - (qty * avg_price)

        portfolio_positions.append({
            "symbol": str(asset.symbol),
            "quantity": qty,
            "avg_buy_price": avg_price,
            "current_price": round(current_price, 2),
            "total_value": round(market_value, 2),
            "profit_loss": round(profit_loss, 2)
        })
        total_value += market_value

    return {
        "account_id": account_id,
        "total_portfolio_value": round(total_value, 2),
        "positions": portfolio_positions
    }