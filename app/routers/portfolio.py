from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from app.database.database import get_db
from app.models.asset import Holding, Asset
from app.models.account import Account
from app.models.user import User
from app.utils.auth import get_current_user

router = APIRouter(prefix="/portfolio", tags=["portfolio"])

@router.get("/")
def get_portfolio(db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    # 1. Buscar todas as contas do user
    accounts = db.query(Account).filter(Account.user_id == current_user.id).all()
    account_ids = [acc.id for acc in accounts]

    total_cash = sum(acc.current_balance for acc in accounts)
    
    # 2. Buscar todas as posições (Holdings) dessas contas
    holdings = db.query(Holding).join(Asset).filter(Holding.account_id.in_(account_ids)).all()
    
    positions = []
    total_invested = 0

    for h in holdings:
        # Se a quantidade for 0 (já vendeu tudo), ignora
        if h.quantity <= 0.0001: 
            continue
            
        current_val = h.quantity * h.asset.current_price
        invested_val = h.quantity * h.avg_buy_price
        profit = current_val - invested_val
        
        positions.append({
            "symbol": h.asset.symbol,
            "quantity": h.quantity,
            "current_price": h.asset.current_price,
            "total_value": current_val,
            "profit_loss": profit
        })
        total_invested += current_val

    return {
        "total_net_worth": total_cash + total_invested, # Atenção: Depende se o teu saldo já desconta o investimento
        "total_cash": total_cash,
        "total_invested": total_invested,
        "positions": positions
    }