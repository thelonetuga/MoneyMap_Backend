from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from typing import List

# --- IMPORTS CORRIGIDOS ---
from app.models import User , AssetPrice
from app.schemas import schemas
from app.database.database import get_db
from app.auth import get_current_user
# --------------------------

router = APIRouter(tags=["portfolio"])

@router.get("/portfolio", response_model=schemas.PortfolioResponse)
def get_portfolio(db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    # Calcular Total de Dinheiro (Contas Bancárias)
    total_cash = sum(acc.current_balance for acc in current_user.accounts)
    
    # Dicionário de Agregação: "AAPL" -> { qtd: 10, cost: 1000, value: 1500 ... }
    assets_map = {}

    for acc in current_user.accounts:
        for holding in acc.holdings:
            # 1. Determinar o Preço Atual
            # (Num sistema real, isto viria de uma cache ou API externa)
            current_price = holding.avg_buy_price 
            last_price = db.query(AssetPrice).filter(
                AssetPrice.asset_id == holding.asset_id
            ).order_by(AssetPrice.date.desc()).first()
            
            if last_price:
                current_price = last_price.close_price

            # 2. Calcular Valores desta parcela
            market_value = holding.quantity * current_price
            cost_basis = holding.quantity * holding.avg_buy_price
            symbol = holding.asset.symbol

            # 3. Agregar ao Mapa Global
            if symbol not in assets_map:
                assets_map[symbol] = {
                    "quantity": 0.0,
                    "total_value": 0.0,
                    "total_cost": 0.0,
                    "current_price": current_price
                }
            
            assets_map[symbol]["quantity"] += holding.quantity
            assets_map[symbol]["total_value"] += market_value
            assets_map[symbol]["total_cost"] += cost_basis
            # Atualizamos o preço para garantir que é o mais recente encontrado
            assets_map[symbol]["current_price"] = current_price

    # 4. Construir a Lista Final
    positions = []
    total_invested = 0.0

    for symbol, data in assets_map.items():
        total_invested += data["total_value"]
        
        # Calcular Preço Médio Ponderado Global
        avg_price = 0.0
        if data["quantity"] > 0:
            avg_price = data["total_cost"] / data["quantity"]

        positions.append({
            "symbol": symbol,
            "quantity": data["quantity"],
            "avg_buy_price": avg_price,
            "current_price": data["current_price"],
            "total_value": data["total_value"],
            "profit_loss": data["total_value"] - data["total_cost"]
        })

    return {
        "user_id": current_user.id,
        "total_net_worth": total_cash + total_invested,
        "total_cash": total_cash,
        "total_invested": total_invested,
        "positions": positions
    }

@router.get("/accounts", response_model=List[schemas.AccountResponse])
def read_accounts(db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    return current_user.accounts

@router.get("/assets", response_model=List[schemas.AssetResponse])
def read_assets(db: Session = Depends(get_db)):
    return db.query(Asset).all()