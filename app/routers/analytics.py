from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from sqlalchemy import func
from datetime import datetime, timedelta
from typing import List

from app.database.database import get_db
from app.utils.auth import get_current_user
from app.models import User, Transaction, Category # <--- Adicionei Category
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
    Retorna a evolução do património nos últimos 30 dias.
    (Versão Simplificada para MVP e Testes)
    """
    end_date = datetime.now().date()
    start_date = end_date - timedelta(days=30)
    
    history_data = []
    
    # Calcula o património ATUAL (para ter um valor de referência)
    current_net_worth = 0
    for acc in current_user.accounts:
        current_net_worth += acc.current_balance
    
    # Gera 30 pontos de dados
    # Num sistema real, lerias de uma tabela 'DailySnapshot'.
    # Aqui, devolvemos o valor atual para desenhar uma linha reta (melhor que zero).
    for i in range(31):
        target_date = start_date + timedelta(days=i)
        
        history_data.append({
            "date": target_date.strftime("%Y-%m-%d"),
            "value": current_net_worth 
        })
        
    return history_data