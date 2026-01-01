from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session, joinedload
from datetime import date, timedelta

# --- IMPORTS CORRIGIDOS ---

from app.database.database import get_db
from app.dependencies import  get_current_user
from app.models import Transaction, User , SubCategory, TransactionType
# --------------------------

router = APIRouter(prefix="/analytics", tags=["analytics"])

@router.get("/spending")
def get_spending_breakdown(db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    start_date = date.today() - timedelta(days=30)
    account_ids = [acc.id for acc in current_user.accounts]
    
    transactions = db.query(Transaction)\
        .join(TransactionType)\
        .options(joinedload(Transaction.sub_category).joinedload(SubCategory.category))\
        .filter(Transaction.account_id.in_(account_ids))\
        .filter(Transaction.date >= start_date)\
        .all()

    spending = {}
    for tx in transactions:
        negative_keywords = ["Despesa", "Expense", "Levantamento", "Compra", "Buy", "Saída"]
        if any(word in tx.transaction_type.name for word in negative_keywords):
            if tx.sub_category and tx.sub_category.category:
                cat_name = tx.sub_category.category.name
            else:
                cat_name = "Outros / Sem Categoria"
            spending[cat_name] = spending.get(cat_name, 0) + tx.amount

    result = [{"name": k, "value": v} for k, v in spending.items() if v > 0]
    result.sort(key=lambda x: x['value'], reverse=True)
    return result

# Função auxiliar para Histórico (chamada pelo main.py)
def get_portfolio_history(db: Session, current_user: User):
    today = date.today()
    account_ids = [acc.id for acc in current_user.accounts]
    current_cash = sum(acc.current_balance for acc in current_user.accounts)
    
    history_points = []
    running_balance = current_cash

    for i in range(30):
        target_date = today - timedelta(days=i)
        
        daily_txs = db.query(Transaction).join(Transaction.transaction_type).filter(
            Transaction.account_id.in_(account_ids),
            Transaction.date == target_date
        ).all()

        history_points.append({
            "date": target_date.isoformat(),
            "value": running_balance
        })

        for tx in daily_txs:
            neg_keywords = ["Despesa", "Expense", "Levantamento", "Compra", "Buy", "Saída"]
            if any(w in tx.transaction_type.name for w in neg_keywords):
                 running_balance += tx.amount 
            else:
                 running_balance -= tx.amount

    return history_points[::-1]