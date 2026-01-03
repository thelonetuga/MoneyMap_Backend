from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import desc
from sqlalchemy.orm import Session
from app.database.database import get_db
from app.models import Asset, AssetPrice, Holding, Account, User
from app.schemas import schemas
from app.utils.auth import get_current_user
import yfinance as yf
from datetime import date

router = APIRouter(prefix="/portfolio", tags=["portfolio"])

@router.post("/update-prices")
def update_asset_prices(db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    """
    Força a atualização dos preços de todos os ativos na carteira do utilizador usando yfinance.
    """
    # 1. Buscar todos os ativos que o user tem
    user_accounts = db.query(Account).filter(Account.user_id == current_user.id).all()
    acc_ids = [a.id for a in user_accounts]
    
    holdings = db.query(Holding).filter(Holding.account_id.in_(acc_ids)).all()
    asset_ids = set(h.asset_id for h in holdings)
    
    assets = db.query(Asset).filter(Asset.id.in_(asset_ids)).all()
    
    updated_count = 0
    errors = []
    
    for asset in assets:
        try:
            # Buscar preço no Yahoo Finance
            ticker = yf.Ticker(asset.symbol)
            history = ticker.history(period="1d")
            
            if not history.empty:
                current_price = history['Close'].iloc[-1]
                
                # Guardar na BD
                new_price = AssetPrice(
                    asset_id=asset.id,
                    date=date.today(),
                    close_price=current_price
                )
                db.add(new_price)
                updated_count += 1
            else:
                errors.append(f"No data for {asset.symbol}")
                
        except Exception as e:
            errors.append(f"Error updating {asset.symbol}: {str(e)}")
            
    db.commit()
    
    return {
        "message": f"Updated {updated_count} assets.",
        "errors": errors
    }

@router.get("", response_model=schemas.PortfolioResponse)
def get_portfolio(db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    accounts = db.query(Account).filter(Account.user_id == current_user.id).all()
    account_ids = [acc.id for acc in accounts]
    
    total_cash = sum(acc.current_balance for acc in accounts)
    
    # Buscar Holdings
    if not account_ids:
        holdings = []
    else:
        holdings = db.query(Holding).join(Asset).filter(Holding.account_id.in_(account_ids)).all()
    
    positions = []
    
    for h in holdings:
        # Ignorar posições minúsculas (pó)
        if h.quantity <= 0.0001: continue
        
        # Buscar o preço mais recente
        latest_price_entry = db.query(AssetPrice).filter(
            AssetPrice.asset_id == h.asset_id
        ).order_by(desc(AssetPrice.date)).first()
        
        # Se não houver preço histórico, usar o preço médio de compra como fallback
        # Se usarmos o fallback, o P/L será 0.
        current_price = latest_price_entry.close_price if latest_price_entry else h.avg_buy_price

        current_val = h.quantity * current_price
        pl = current_val - (h.quantity * h.avg_buy_price)
        
        positions.append({
            "symbol": h.asset.symbol,
            "quantity": h.quantity,
            "avg_buy_price": h.avg_buy_price,
            "current_price": current_price,
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