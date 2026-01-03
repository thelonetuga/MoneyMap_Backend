from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session
from sqlalchemy import func
from datetime import datetime, timedelta, date
from typing import List
import pandas as pd

from app.database.database import get_db
from app.utils.auth import get_current_user
from app.models import User, Transaction, Category, Account
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

# --- 2. HISTORY (Para o Gráfico de Evolução Curto Prazo) ---
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

# --- 3. EVOLUTION (Longo Prazo: Anual/Trimestral) ---
@router.get("/evolution", response_model=List[schemas.EvolutionPoint])
def get_evolution(
    period: str = Query("year", regex="^(year|quarter|month)$"),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Retorna a evolução macro do património, despesas e receitas.
    Garante que o último ponto reflete o estado ATUAL (Live) das contas.
    """
    # Identificar contas e seus tipos
    all_accounts = current_user.accounts
    user_account_ids = [acc.id for acc in all_accounts]
    
    # Identificar IDs de contas líquidas (Tipo 1=Ordem, 3=Poupança)
    liquid_account_ids = [
        acc.id for acc in all_accounts 
        if acc.account_type_id in [1, 3]
    ]

    if not user_account_ids:
        return []

    # 1. Buscar TODAS as transações
    transactions = db.query(Transaction).filter(
        Transaction.account_id.in_(user_account_ids)
    ).order_by(Transaction.date.asc()).all()

    # --- LÓGICA PANDAS (HISTÓRICO) ---
    result = []
    
    if transactions:
        # Converter para DataFrame
        data = [
            {
                "date": pd.to_datetime(tx.date), 
                "amount": tx.amount,
                "is_liquid": tx.account_id in liquid_account_ids
            }
            for tx in transactions
        ]
        df = pd.DataFrame(data)
        
        # Definir regra de resampling
        rule = "YE" if period == "year" else "QE" if period == "quarter" else "ME"
        
        # Calcular Receitas e Despesas
        df['income'] = df['amount'].apply(lambda x: x if x > 0 else 0)
        df['expense'] = df['amount'].apply(lambda x: abs(x) if x < 0 else 0)
        
        # Agrupar
        grouped = df.resample(rule, on='date').sum()
        
        # Calcular Net Worth Acumulado (Histórico)
        grouped['net_change'] = grouped['amount']
        grouped['cumulative_net_worth'] = grouped['net_change'].cumsum()
        
        # Ajuste de Offset Global (para alinhar o histórico com o presente)
        current_total_balance = sum(acc.current_balance for acc in all_accounts)
        calculated_final_total = grouped['cumulative_net_worth'].iloc[-1] if not grouped.empty else 0
        offset_total = current_total_balance - calculated_final_total
        grouped['cumulative_net_worth'] += offset_total

        # Calcular Liquidez Acumulada (Histórico)
        df['liquid_amount'] = df.apply(lambda row: row['amount'] if row['is_liquid'] else 0, axis=1)
        grouped_liquid = df.resample(rule, on='date')['liquid_amount'].sum()
        cumulative_liquid = grouped_liquid.cumsum()
        
        current_liquid_balance = sum(acc.current_balance for acc in all_accounts if acc.id in liquid_account_ids)
        calculated_final_liquid = cumulative_liquid.iloc[-1] if not cumulative_liquid.empty else 0
        offset_liquid = current_liquid_balance - calculated_final_liquid
        cumulative_liquid += offset_liquid

        # Formatar lista inicial
        for date_idx, row in grouped.iterrows():
            if period == "year":
                period_label = str(date_idx.year)
            elif period == "quarter":
                period_label = f"{date_idx.year}-Q{date_idx.quarter}"
            else:
                period_label = date_idx.strftime("%b %Y")
                
            income = row['income']
            expenses = row['expense']
            
            savings_rate = 0.0
            if income > 0:
                savings_rate = ((income - expenses) / income) * 100
                
            liquid_val = cumulative_liquid.loc[date_idx]
                
            result.append({
                "period": period_label,
                "net_worth": round(row['cumulative_net_worth'], 2),
                "liquid_cash": round(liquid_val, 2),
                "expenses": round(expenses, 2),
                "income": round(income, 2),
                "savings_rate": round(savings_rate, 1)
            })

    # --- LÓGICA LIVE SYNC (GARANTIR O PRESENTE) ---
    
    # 1. Calcular Totais Reais AGORA
    live_net_worth = sum(acc.current_balance for acc in all_accounts)
    live_liquid_cash = sum(acc.current_balance for acc in all_accounts if acc.id in liquid_account_ids)
    
    # 2. Determinar a Label do Período Atual
    today = date.today()
    if period == "year":
        current_label = str(today.year)
    elif period == "quarter":
        q = (today.month - 1) // 3 + 1
        current_label = f"{today.year}-Q{q}"
    else:
        current_label = today.strftime("%b %Y")
        
    # 3. Verificar e Atualizar/Adicionar
    if result and result[-1]["period"] == current_label:
        # Cenário A: O período atual já existe na lista (houve transações).
        # Forçamos os valores de Stock (Net Worth/Liquidez) para bater certo com o Live.
        # Mantemos os valores de Flow (Income/Expenses) que vieram do histórico.
        result[-1]["net_worth"] = round(live_net_worth, 2)
        result[-1]["liquid_cash"] = round(live_liquid_cash, 2)
    else:
        # Cenário B: O período atual NÃO existe (não houve transações este mês/ano ainda).
        # Adicionamos um ponto novo representando o "Agora".
        result.append({
            "period": current_label,
            "net_worth": round(live_net_worth, 2),
            "liquid_cash": round(live_liquid_cash, 2),
            "expenses": 0.0, # Sem transações, sem despesas registadas neste período
            "income": 0.0,
            "savings_rate": 0.0
        })
        
    return result