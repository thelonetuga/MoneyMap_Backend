from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session, joinedload
from typing import List
import models.models as models
import schemas.schemas as schemas
from dependencies import get_db, get_current_user

router = APIRouter(prefix="/transactions", tags=["transactions"])

@router.get("/", response_model=List[schemas.TransactionResponse])
def read_transactions(db: Session = Depends(get_db), current_user: models.User = Depends(get_current_user)):
    account_ids = [acc.id for acc in current_user.accounts]
    return db.query(models.Transaction).options(
            joinedload(models.Transaction.transaction_type),
            joinedload(models.Transaction.sub_category),
            joinedload(models.Transaction.asset)
        ).filter(models.Transaction.account_id.in_(account_ids))\
        .order_by(models.Transaction.date.desc()).limit(100).all()

@router.post("/", response_model=schemas.TransactionResponse, status_code=status.HTTP_201_CREATED)
def create_transaction(tx: schemas.TransactionCreate, db: Session = Depends(get_db), current_user: models.User = Depends(get_current_user)):
    account = db.query(models.Account).filter(models.Account.id == tx.account_id).first()
    if not account or account.user_id != current_user.id:
        raise HTTPException(status_code=403, detail="Não tem permissão para usar esta conta.")

    tx_type = db.query(models.TransactionType).filter(models.TransactionType.id == tx.transaction_type_id).first()
    if not tx_type: raise HTTPException(status_code=404, detail="Tipo inválido")

    # Atualizar Saldo
    negative_keywords = ["Despesa", "Expense", "Levantamento", "Compra", "Buy"]
    is_negative = any(word in tx_type.name for word in negative_keywords)
    if is_negative: account.current_balance -= tx.amount
    else: account.current_balance += tx.amount
    
    # Atualizar Investimentos
    if tx.asset_id and tx.quantity:
        holding = db.query(models.Holding).filter(models.Holding.account_id == account.id, models.Holding.asset_id == tx.asset_id).first()
        if not holding:
            holding = models.Holding(account_id=account.id, asset_id=tx.asset_id, quantity=0, avg_buy_price=0)
            db.add(holding)
        
        if "Compra" in tx_type.name or "Buy" in tx_type.name:
            curr_val = holding.quantity * holding.avg_buy_price
            new_val = tx.quantity * (tx.price_per_unit if tx.price_per_unit else (tx.amount/tx.quantity))
            holding.quantity += tx.quantity
            holding.avg_buy_price = (curr_val + new_val) / holding.quantity
        elif "Venda" in tx_type.name or "Sell" in tx_type.name:
            holding.quantity -= tx.quantity
            if holding.quantity < 0: holding.quantity = 0

    db_tx = models.Transaction(**tx.model_dump())
    db.add(db_tx)
    db.add(account)
    db.commit()
    db.refresh(db_tx)
    return db_tx

@router.delete("/{transaction_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_transaction(transaction_id: int, db: Session = Depends(get_db), current_user: models.User = Depends(get_current_user)):
    tx = db.query(models.Transaction).filter(models.Transaction.id == transaction_id).first()
    if not tx: raise HTTPException(status_code=404, detail="Não encontrado")
    
    account = db.query(models.Account).filter(models.Account.id == tx.account_id).first()
    if not account or account.user_id != current_user.id: raise HTTPException(status_code=403, detail="Não permitido.")
    
    # Reverter Saldo
    negative_keywords = ["Despesa", "Expense", "Levantamento", "Compra", "Buy"]
    is_negative_originally = any(word in tx.transaction_type.name for word in negative_keywords)
    if is_negative_originally: account.current_balance += tx.amount
    else: account.current_balance -= tx.amount

    # Reverter Investimento
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

@router.put("/transactions/{transaction_id}", response_model=schemas.TransactionResponse)
def update_transaction(transaction_id: int, updated_tx: schemas.TransactionCreate, db: Session = Depends(get_db), current_user: models.User = Depends(get_current_user)):
    db_tx = db.query(models.Transaction).filter(models.Transaction.id == transaction_id).first()
    if not db_tx: raise HTTPException(status_code=404, detail="Não encontrado")

    # 1. Validar Conta Antiga
    old_account = db.query(models.Account).filter(models.Account.id == db_tx.account_id).first()
    if not old_account: raise HTTPException(status_code=404, detail="Conta antiga não encontrada")
    if old_account.user_id != current_user.id: raise HTTPException(status_code=403, detail="Sem permissão.")
        
    # 2. Validar Conta Nova (CORREÇÃO AQUI)
    new_account = db.query(models.Account).filter(models.Account.id == updated_tx.account_id).first()
    # Adicionamos esta verificação explícita:
    if not new_account: 
        raise HTTPException(status_code=404, detail="Conta destino não encontrada")
    
    if new_account.user_id != current_user.id: raise HTTPException(status_code=403, detail="Conta destino não permitida.")

    # 3. REVERTER ANTIGA
    negative_keywords = ["Despesa", "Expense", "Levantamento", "Compra", "Buy"]
    was_negative = any(word in db_tx.transaction_type.name for word in negative_keywords)
    
    if was_negative: old_account.current_balance += db_tx.amount
    else: old_account.current_balance -= db_tx.amount

    if db_tx.asset_id and db_tx.quantity:
        holding = db.query(models.Holding).filter(models.Holding.account_id == db_tx.account_id, models.Holding.asset_id == db_tx.asset_id).first()
        if holding:
            if "Compra" in db_tx.transaction_type.name: holding.quantity -= db_tx.quantity
            elif "Venda" in db_tx.transaction_type.name: holding.quantity += db_tx.quantity

    # 4. ATUALIZAR DADOS
    for key, value in updated_tx.model_dump().items():
        setattr(db_tx, key, value)
    
    # 5. APLICAR NOVA
    new_type = db.query(models.TransactionType).filter(models.TransactionType.id == updated_tx.transaction_type_id).first()
    if not new_type: raise HTTPException(status_code=404, detail="Tipo de transação não encontrado") # +Correção extra

    is_negative_new = any(word in new_type.name for word in negative_keywords)
    
    if is_negative_new: new_account.current_balance -= updated_tx.amount
    else: new_account.current_balance += updated_tx.amount

    if updated_tx.asset_id and updated_tx.quantity:
        holding = db.query(models.Holding).filter(models.Holding.account_id == new_account.id, models.Holding.asset_id == updated_tx.asset_id).first()
        if holding:
            if "Compra" in new_type.name: holding.quantity += updated_tx.quantity
            elif "Venda" in new_type.name: holding.quantity -= updated_tx.quantity

    db.add(old_account)
    if new_account.id != old_account.id: db.add(new_account)
    db.add(db_tx)
    db.commit()
    db.refresh(db_tx)
    return db_tx