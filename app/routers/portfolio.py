from fastapi import APIRouter, Depends, HTTPException, Body
from sqlalchemy import desc
from sqlalchemy.orm import Session
from app.database.database import get_db
from app.models import Asset, AssetPrice, Holding, Account, User
from app.schemas import schemas
from app.utils.auth import get_current_user
from datetime import date
from pydantic import BaseModel

router = APIRouter(prefix="/portfolio", tags=["portfolio"])

# Schema simples para o update manual (interno ao router para não poluir o schemas.py global)
class ManualPriceUpdate(BaseModel):
    symbol: str
    price: float

@router.post("/price")
def set_asset_price(
    update: ManualPriceUpdate, 
    db: Session = Depends(get_db), 
    current_user: User = Depends(get_current_user)
):
    """
    Define manualmente o preço atual de mercado de um ativo.
    Usado para calcular o P/L sem depender de APIs externas.
    """
    # 1. Encontrar o ativo pelo símbolo
    asset = db.query(Asset).filter(Asset.symbol == update.symbol.upper()).first()
    if not asset:
        raise HTTPException(status_code=404, detail=f"Ativo '{update.symbol}' não encontrado.")
    
    # 2. Registar o novo preço na tabela de histórico
    new_price = AssetPrice(
        asset_id=asset.id,
        date=date.today(),
        close_price=update.price
    )
    db.add(new_price)
    db.commit()
    
    return {"message": f"Preço de {asset.symbol} atualizado para {update.price}"}

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
        
        # Buscar o preço mais recente registado na BD (inserido manualmente ou via transação)
        latest_price_entry = db.query(AssetPrice).filter(
            AssetPrice.asset_id == h.asset_id
        ).order_by(desc(AssetPrice.date), desc(AssetPrice.id)).first()
        
        # Se não houver preço histórico, usar o preço médio de compra como fallback
        # (Neste caso o P/L será 0)
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