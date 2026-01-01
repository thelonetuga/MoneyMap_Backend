from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import List

# --- IMPORTS CORRIGIDOS ---
from app.models import models
from app.schemas import schemas
from app.database.database import get_db
from app.auth import get_current_user
# --------------------------

router = APIRouter(tags=["portfolio"])

@router.get("/portfolio", response_model=schemas.PortfolioResponse)
def get_portfolio(db: Session = Depends(get_db), current_user: models.User = Depends(get_current_user)):
    # Calcular Totais
    total_cash = sum(acc.current_balance for acc in current_user.accounts)
    
    # Calcular Investimentos (Holdings)
    # Precisamos iterar todas as contas e somar holdings
    total_invested = 0.0
    positions = []

    for acc in current_user.accounts:
        for holding in acc.holdings:
            # Em sistema real, iríamos buscar o PREÇO ATUAL à tabela AssetPrice
            # Aqui vamos assumir que current_price = avg_buy_price para simplificar (ou buscar o último preço)
            current_price = holding.avg_buy_price # Placeholder
            
            # Tentar buscar preço real se existir
            last_price = db.query(models.AssetPrice).filter(models.AssetPrice.asset_id == holding.asset_id).order_by(models.AssetPrice.date.desc()).first()
            if last_price:
                current_price = last_price.close_price

            val = holding.quantity * current_price
            total_invested += val
            
            positions.append({
                "symbol": holding.asset.symbol,
                "quantity": holding.quantity,
                "avg_buy_price": holding.avg_buy_price,
                "current_price": current_price,
                "total_value": val,
                "profit_loss": val - (holding.quantity * holding.avg_buy_price)
            })

    # Agrupar posições por símbolo (caso tenha o mesmo ativo em várias contas)
    # (Opcional, mas recomendado)
    
    return {
        "user_id": current_user.id,
        "total_net_worth": total_cash + total_invested,
        "total_cash": total_cash,
        "total_invested": total_invested,
        "positions": positions
    }

@router.get("/accounts", response_model=List[schemas.AccountResponse])
def read_accounts(db: Session = Depends(get_db), current_user: models.User = Depends(get_current_user)):
    return current_user.accounts

@router.get("/assets", response_model=List[schemas.AssetResponse])
def read_assets(db: Session = Depends(get_db)):
    return db.query(models.Asset).all()