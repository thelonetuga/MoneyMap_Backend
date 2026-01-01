from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session, joinedload
from typing import List

# --- IMPORTS CORRIGIDOS (Absolutos) ---
from app.models import models
from app.schemas import schemas
from app.dependencies import get_db, get_current_user
# --------------------------------------

router = APIRouter(prefix="/transactions", tags=["transactions"])

# --- LISTAR ---
@router.get("/", response_model=List[schemas.TransactionResponse])
def read_transactions(db: Session = Depends(get_db), current_user: models.User = Depends(get_current_user)):
    account_ids = [acc.id for acc in current_user.accounts]
    return db.query(models.Transaction).options(
            joinedload(models.Transaction.transaction_type),
            joinedload(models.Transaction.sub_category),
            joinedload(models.Transaction.asset)
        ).filter(models.Transaction.account_id.in_(account_ids))\
        .order_by(models.Transaction.date.desc()).limit(100).all()

# --- CRIAR ---
@router.post("/", response_model=schemas.TransactionResponse, status_code=status.HTTP_201_CREATED)
def create_transaction(tx: schemas.TransactionCreate, db: Session = Depends(get_db), current_user: models.User = Depends(get_current_user)):
    account = db.query(models.Account).filter(models.Account.id == tx.account_id).first()
    if not account or account.user_id != current_user.id:
        raise HTTPException(status_code=403, detail="Não tem permissão para usar esta conta.")

    tx_type = db.query(models.TransactionType).filter(models.TransactionType.id == tx.transaction_type_id).first()
    if not tx_type: raise HTTPException(status_code=404, detail="Tipo inválido")

    # Saldo
    negative_keywords = ["Despesa", "Expense", "Levantamento", "Compra", "Buy", "Saída"]
    is_negative = any(word in tx_type.name for word in negative_keywords)
    if is_negative: account.current_balance -= tx.amount
    else: account.current_balance += tx.amount
    
    # Investimentos
    if tx.asset_id and tx.quantity:
        holding = db.query(models.Holding).filter(models.Holding.account_id == account.id, models.Holding.asset_id == tx.asset_id).first()
        if not holding:
            holding = models.Holding(account_id=account.id, asset_id=tx.asset_id, quantity=0, avg_buy_price=0)
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
    tx_data = tx.model_dump() if hasattr(tx, 'model_dump') else tx.dict()
    db_tx = models.Transaction(**tx_data)
    
    db.add(db_tx)
    db.add(account)
    db.commit()
    db.refresh(db_tx)
    return db_tx

# --- APAGAR ---
@router.delete("/{transaction_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_transaction(transaction_id: int, db: Session = Depends(get_db), current_user: models.User = Depends(get_current_user)):
    tx = db.query(models.Transaction).filter(models.Transaction.id == transaction_id).first()
    if not tx: raise HTTPException(status_code=404, detail="Não encontrado")
    
    account = db.query(models.Account).filter(models.Account.id == tx.account_id).first()
    if not account or account.user_id != current_user.id: raise HTTPException(status_code=403, detail="Não permitido.")
    
    # Reverter Saldo
    negative_keywords = ["Despesa", "Expense", "Levantamento", "Compra", "Buy", "Saída"]
    # Carregar tipo se necessário
    if not tx.transaction_type:
         tx.transaction_type = db.query(models.TransactionType).filter(models.TransactionType.id == tx.transaction_type_id).first()

    is_negative_originally = any(word in tx.transaction_type.name for word in negative_keywords)
    if is_negative_originally: account.current_balance += tx.amount
    else: account.current_balance -= tx.amount

    # Reverter Investimento (Simplificado)
    if tx.asset_id and tx.quantity:
        holding = db.query(models.Holding).filter(models.Holding.account_id == account.id, models.Holding.asset_id == tx.asset_id).first()
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
def update_transaction(transaction_id: int, updated_tx: schemas.TransactionCreate, db: Session = Depends(get_db), current_user: models.User = Depends(get_current_user)):
    # 1. Buscar transação antiga
    db_tx = db.query(models.Transaction).filter(models.Transaction.id == transaction_id).first()
    if not db_tx: raise HTTPException(status_code=404, detail="Transação não encontrada")

    # 2. Validar permissão na conta ANTIGA
    old_account = db.query(models.Account).filter(models.Account.id == db_tx.account_id).first()
    if not old_account or old_account.user_id != current_user.id:
        raise HTTPException(status_code=403, detail="Sem permissão na conta original.")
        
    # 3. Validar permissão na conta NOVA
    new_account = db.query(models.Account).filter(models.Account.id == updated_tx.account_id).first()
    if not new_account or new_account.user_id != current_user.id:
        raise HTTPException(status_code=403, detail="Sem permissão na conta de destino.")

    # 4. REVERTER O EFEITO DA ANTIGA
    negative_keywords = ["Despesa", "Expense", "Levantamento", "Compra", "Buy", "Saída"]
    
    if not db_tx.transaction_type:
        db_tx.transaction_type = db.query(models.TransactionType).filter(models.TransactionType.id == db_tx.transaction_type_id).first()

    was_negative = any(word in db_tx.transaction_type.name for word in negative_keywords)
    
    if was_negative: old_account.current_balance += db_tx.amount
    else: old_account.current_balance -= db_tx.amount

    # (Lógica de Holdings omitida para brevidade, mas seria semelhante ao delete)

    # 5. ATUALIZAR DADOS DO OBJETO
    tx_data = updated_tx.model_dump() if hasattr(updated_tx, 'model_dump') else updated_tx.dict()
    for key, value in tx_data.items():
        setattr(db_tx, key, value)
    
    # 6. APLICAR O EFEITO DA NOVA
    new_type = db.query(models.TransactionType).filter(models.TransactionType.id == updated_tx.transaction_type_id).first()
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