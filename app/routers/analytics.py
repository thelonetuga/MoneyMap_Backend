from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from sqlalchemy import func
from datetime import datetime, timedelta
from typing import List

from app.database.database import get_db
from app.utils.auth import get_current_user
from app.models import User, Transaction, Category
from app.schemas import schemas

router = APIRouter(prefix="/analytics", tags=["analytics"])

# --- 1. SPENDING ANALYTICS (Para o Gráfico de Despesas) ---
@router.get("/spending", response_model=List[dict])
def get_spending_analytics(db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    # Identificar as contas do utilizador
    user_account_ids = [acc.id for acc in current_user.accounts]
    
    if not user_account_ids:
        return []

    # Query: Agrupar por Categoria e Somar os valores ABSOLUTOS das despesas
    # Consideramos "Despesa" qualquer transação com valor negativo (< 0)
    results = db.query(
        Category.name, 
        func.sum(func.abs(Transaction.amount)).label("total")
    ).join(Transaction.category).filter(
        Transaction.account_id.in_(user_account_ids),
        Transaction.amount < 0 
    ).group_by(Category.name).all()
    
    # Formatar para o Frontend (Recharts gosta de "name" e "value")
    return [{"name": cat_name, "value": total} for cat_name, total in results]

# --- 2. HISTORY (Para o Gráfico de Evolução) ---
@router.get("/history") 
def get_history(db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    """
    Retorna a evolução do património (Saldo das Contas) nos últimos 30 dias.
    Calculado retroativamente com base nas transações.
    """
    end_date = datetime.now().date()
    start_date = end_date - timedelta(days=30)
    
    # 1. Calcular o Saldo Atual Total (Ponto de Partida)
    current_total_balance = sum(acc.current_balance for acc in current_user.accounts)
    
    # 2. Buscar transações dos últimos 30 dias para as contas do user
    user_account_ids = [acc.id for acc in current_user.accounts]
    
    if not user_account_ids:
        return [{"date": (end_date - timedelta(days=i)).strftime("%Y-%m-%d"), "value": 0} for i in range(31)][::-1]

    transactions = db.query(Transaction).filter(
        Transaction.account_id.in_(user_account_ids),
        Transaction.date >= start_date
    ).all()

    # 3. Agrupar transações por data
    daily_changes = {}
    for tx in transactions:
        d_str = tx.date.strftime("%Y-%m-%d")
        daily_changes[d_str] = daily_changes.get(d_str, 0) + tx.amount

    # 4. Reconstruir o histórico de trás para a frente
    history_data = []
    running_balance = current_total_balance
    
    for i in range(31):
        target_date = end_date - timedelta(days=i)
        d_str = target_date.strftime("%Y-%m-%d")
        
        history_data.append({
            "date": d_str,
            "value": round(running_balance, 2)
        })
        
        # SaldoOntem = SaldoHoje - ChangeHoje
        change_on_day = daily_changes.get(d_str, 0)
        running_balance -= change_on_day

    # 5. Ordenar cronologicamente
    return history_data[::-1]