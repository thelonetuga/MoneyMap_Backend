from fastapi import APIRouter, Depends
from sqlalchemy import desc
from sqlalchemy.orm import Session
from app.database.database import get_db
from app.models.asset import AssetPrice, Holding, Asset
from app.models.account import Account
from app.models.user import User
from app.schemas import schemas
from app.utils.auth import get_current_user

router = APIRouter(prefix="/portfolio", tags=["portfolio"])

@router.get("/", response_model=schemas.PortfolioResponse)
def get_portfolio(db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    accounts = db.query(Account).filter(Account.user_id == current_user.id).all()
    account_ids = [acc.id for acc in accounts]
    
    total_cash = sum(acc.current_balance for acc in accounts)
    
    # Buscar Holdings
    holdings = db.query(Holding).join(Asset).filter(Holding.account_id.in_(account_ids)).all()
    
    positions = []
    
    for h in holdings:
        if h.quantity <= 0.0001: continue
        
        # --- CORREÇÃO: Buscar o preço mais recente ---
        latest_price_entry = db.query(AssetPrice).filter(
            AssetPrice.asset_id == h.asset_id
        ).order_by(desc(AssetPrice.date)).first()
        
        # Se não houver preço, assumimos o preço de compra para não dar erro (ou 0)
        current_price = latest_price_entry.close_price if latest_price_entry else h.avg_buy_price
        # ---------------------------------------------

        current_val = h.quantity * current_price
        pl = current_val - (h.quantity * h.avg_buy_price)
        
        positions.append({
            "symbol": h.asset.symbol,
            "quantity": h.quantity,
            "avg_buy_price": h.avg_buy_price,
            "current_price": current_price, # Agora já temos esta variável
            "total_value": current_val,
            "profit_loss": pl
        })
        
    total_invested = sum(p["total_value"] for p in positions)
    
    return {
        "user_id": current_user.id,
        "total_net_worth": total_cash + total_invested,
        "total_cash": total_cash,
        "total_invested": total_invested,
        "positions": positions
    }