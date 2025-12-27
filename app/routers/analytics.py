from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session, joinedload
from typing import List
from datetime import date, timedelta
import models.models as models
# Importar do novo ficheiro de dependências!
from dependencies import get_db, get_current_user

# Criar o Router
router = APIRouter(
    prefix="/analytics",
    tags=["analytics"]
)

@router.get("/spending")
def get_spending_breakdown(db: Session = Depends(get_db), current_user: models.User = Depends(get_current_user)):
    # 1. Definir período (últimos 30 dias)
    start_date = date.today() - timedelta(days=30)
    
    # 2. Buscar transações deste user
    account_ids = [acc.id for acc in current_user.accounts]
    
    transactions = db.query(models.Transaction)\
        .join(models.TransactionType)\
        .options(
            joinedload(models.Transaction.sub_category).joinedload(models.SubCategory.category)
        )\
        .filter(models.Transaction.account_id.in_(account_ids))\
        .filter(models.Transaction.date >= start_date)\
        .all()

    # 3. Somar por Categoria
    spending = {}
    
    for tx in transactions:
        # Verificar se é Despesa
        negative_keywords = ["Despesa", "Expense", "Levantamento"]
        if any(word in tx.transaction_type.name for word in negative_keywords):
            # Descobrir o nome da Categoria Principal
            if tx.sub_category and tx.sub_category.category:
                cat_name = tx.sub_category.category.name
            else:
                cat_name = "Outros / Sem Categoria"
            
            # Somar
            spending[cat_name] = spending.get(cat_name, 0) + tx.amount

    # 4. Formatar para o Gráfico
    result = [{"name": k, "value": v} for k, v in spending.items() if v > 0]
    result.sort(key=lambda x: x['value'], reverse=True)
    
    return result