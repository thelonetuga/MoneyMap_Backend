from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session, joinedload
from typing import List
from datetime import date, timedelta
import models.models as models
import schemas.schemas as schemas
from dependencies import get_db, get_current_user

router = APIRouter(tags=["portfolio"])

@router.get("/portfolio", response_model=schemas.PortfolioResponse) 
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
            symbol=h.asset.symbol, quantity=h.quantity, avg_buy_price=h.avg_buy_price,
            current_price=curr_price, total_value=market_val, profit_loss=pnl
        ))
        total_invested += market_val

    return schemas.PortfolioResponse(
        user_id=user_id, total_net_worth=total_cash + total_invested,
        total_cash=total_cash, total_invested=total_invested, positions=positions
    )

@router.get("/history", response_model=List[schemas.HistoryPoint])
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