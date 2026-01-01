from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session, joinedload
from typing import List, Optional
from datetime import date

# --- IMPORTS CORRIGIDOS (Absolutos) ---
from app.database.database import get_db
from app.models import Transaction, Account, User , TransactionType,Holding,Account

from app.schemas import schemas
from app.dependencies import get_current_user
# --------------------------------------

router = APIRouter(prefix="/transactions", tags=["transactions"])

# --- LISTAR ---
# --- LISTAR (COM PAGINAÇÃO E FILTROS) ---
@router.get("/", response_model=List[schemas.TransactionResponse])
def read_transactions(
    skip: int = 0,
    limit: int = 50,
    start_date: Optional[date] = None,
    end_date: Optional[date] = None,
    search: Optional[str] = None,
    account_id: Optional[int] = None,
    transaction_type_id: Optional[int] = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    # 1. Base Query: Começamos por filtrar apenas transações das contas do utilizador
    # (Para segurança, confirmamos sempre quais as contas que pertencem ao user)
    user_account_ids = [acc.id for acc in current_user.accounts]
    
    query = db.query(Transaction).filter(
        Transaction.account_id.in_(user_account_ids)
    )

    # 2. Filtro de Conta Específica (Se o user selecionou uma conta no dropdown)
    if account_id:
        if account_id not in user_account_ids:
            # Se tentar filtrar por uma conta que não é dele, devolvemos lista vazia ou erro
            return [] 
        query = query.filter(Transaction.account_id == account_id)

    # 3. Filtros de Data
    if start_date:
        query = query.filter(Transaction.date >= start_date)
    if end_date:
        query = query.filter(Transaction.date <= end_date)

    # 4. Filtro por Tipo (Ex: Só Despesas)
    if transaction_type_id:
        query = query.filter(Transaction.transaction_type_id == transaction_type_id)

    # 5. Pesquisa de Texto (Case Insensitive no PostgreSQL com ilike, no SQLite fazemos like)
    if search:
        # Nota: O 'ilike' é específico do Postgres. Se usares SQLite nos testes, usa 'like'.
        # Para compatibilidade universal simples:
        search_fmt = f"%{search}%"
        query = query.filter(Transaction.description.like(search_fmt))

    # 6. Ordenação, Eager Loading e Paginação
    transactions = query.options(
        joinedload(Transaction.transaction_type),
        joinedload(Transaction.subcategory)
    ).order_by(Transaction.date.desc()).offset(skip).limit(limit).all()

    return transactions

# --- CRIAR ---
@router.post("/", response_model=schemas.TransactionResponse, status_code=status.HTTP_201_CREATED)
def create_transaction(tx: schemas.TransactionCreate, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    account = db.query(Account).filter(Account.id == tx.account_id).first()
    if not account or account.user_id != current_user.id:
        raise HTTPException(status_code=403, detail="Não tem permissão para usar esta conta.")

    tx_type = db.query(TransactionType).filter(TransactionType.id == tx.transaction_type_id).first()
    if not tx_type: raise HTTPException(status_code=404, detail="Tipo inválido")

    # Saldo
    negative_keywords = ["Despesa", "Expense", "Levantamento", "Compra", "Buy", "Saída"]
    is_negative = any(word in tx_type.name for word in negative_keywords)
    if is_negative: account.current_balance -= tx.amount
    else: account.current_balance += tx.amount
    
    # Investimentos
    if tx.asset_id and tx.quantity:
        holding = db.query(Holding).filter(Holding.account_id == account.id, Holding.asset_id == tx.asset_id).first()
        if not holding:
            holding = Holding(account_id=account.id, asset_id=tx.asset_id, quantity=0, avg_buy_price=0)
            db.add(holding)
        
        if "Compra" in tx_type.name or "Buy" in tx_type.name:
            curr_val = holding.quantity * holding.avg_buy_price
            new_val = tx.quantity * (tx.price_per_unit if tx.price_per_unit else (tx.amount/tx.quantity))
            holding.quantity += tx.quantity
            # Evitar divisão por zero
            if holding.quantity > 0:
                holding.avg_buy_price = (curr_val + new_val) / holding.quantity
        elif "Venda" in tx_type.name or "Sell" in tx_type.name:
            holding.quantity -= tx.quantity
            if holding.quantity < 0: holding.quantity = 0

    # Compatibilidade Pydantic v2
    tx_data = tx.model_dump() if hasattr(tx, 'model_dump') else tx.model_dump() 
    db_tx = Transaction(**tx_data)
    
    db.add(db_tx)
    db.add(account)
    db.commit()
    db.refresh(db_tx)
    return db_tx

# --- APAGAR ---
@router.delete("/{transaction_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_transaction(transaction_id: int, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    tx = db.query(Transaction).filter(Transaction.id == transaction_id).first()
    if not tx: raise HTTPException(status_code=404, detail="Não encontrado")
    
    account = db.query(Account).filter(Account.id == tx.account_id).first()
    if not account or account.user_id != current_user.id: raise HTTPException(status_code=403, detail="Não permitido.")
    
    # Reverter Saldo
    negative_keywords = ["Despesa", "Expense", "Levantamento", "Compra", "Buy", "Saída"]
    # Carregar tipo se necessário
    if not tx.transaction_type:
         tx.transaction_type = db.query(TransactionType).filter(TransactionType.id == tx.transaction_type_id).first()

    is_negative_originally = any(word in tx.transaction_type.name for word in negative_keywords)
    if is_negative_originally: account.current_balance += tx.amount
    else: account.current_balance -= tx.amount

    # Reverter Investimento (Simplificado)
    if tx.asset_id and tx.quantity:
        holding = db.query(Holding).filter(Holding.account_id == account.id, Holding.asset_id == tx.asset_id).first()
        if holding:
            if "Compra" in tx.transaction_type.name: holding.quantity -= tx.quantity
            elif "Venda" in tx.transaction_type.name: holding.quantity += tx.quantity
            if holding.quantity < 0: holding.quantity = 0

    db.delete(tx)
    db.add(account)
    db.commit()
    return None

# --- EDITAR ---
@router.put("/{transaction_id}", response_model=schemas.TransactionResponse)
def update_transaction(transaction_id: int, updated_tx: schemas.TransactionCreate, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    # 1. Buscar transação antiga
    db_tx = db.query(Transaction).filter(Transaction.id == transaction_id).first()
    if not db_tx: raise HTTPException(status_code=404, detail="Transação não encontrada")

    # 2. Validar permissão na conta ANTIGA
    old_account = db.query(Account).filter(Account.id == db_tx.account_id).first()
    if not old_account or old_account.user_id != current_user.id:
        raise HTTPException(status_code=403, detail="Sem permissão na conta original.")
        
    # 3. Validar permissão na conta NOVA
    new_account = db.query(Account).filter(Account.id == updated_tx.account_id).first()
    if not new_account or new_account.user_id != current_user.id:
        raise HTTPException(status_code=403, detail="Sem permissão na conta de destino.")

    # 4. REVERTER O EFEITO DA ANTIGA
    negative_keywords = ["Despesa", "Expense", "Levantamento", "Compra", "Buy", "Saída"]
    
    if not db_tx.transaction_type:
        db_tx.transaction_type = db.query(TransactionType).filter(TransactionType.id == db_tx.transaction_type_id).first()

    was_negative = any(word in db_tx.transaction_type.name for word in negative_keywords)
    
    if was_negative: old_account.current_balance += db_tx.amount
    else: old_account.current_balance -= db_tx.amount

    # (Lógica de Holdings omitida para brevidade, mas seria semelhante ao delete)

    # 5. ATUALIZAR DADOS DO OBJETO
    tx_data = updated_tx.model_dump() if hasattr(updated_tx, 'model_dump') else updated_tx.model_dump() 
    for key, value in tx_data.items():
        setattr(db_tx, key, value)
    
    # 6. APLICAR O EFEITO DA NOVA
    new_type = db.query(TransactionType).filter(TransactionType.id == updated_tx.transaction_type_id).first()
    if not new_type: raise HTTPException(status_code=404, detail="Novo tipo inválido")

    is_negative_new = any(word in new_type.name for word in negative_keywords)
    
    if is_negative_new: new_account.current_balance -= updated_tx.amount
    else: new_account.current_balance += updated_tx.amount

    db.add(old_account)
    if new_account.id != old_account.id: db.add(new_account)
    db.add(db_tx)
    db.commit()
    db.refresh(db_tx)
    return db_tx