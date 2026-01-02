from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session, joinedload
from typing import List, Optional
from datetime import date

from app.database.database import get_db
# ADICIONADO: Importar Asset para podermos criar/buscar ativos
from app.models import Transaction, Account, User, TransactionType, Holding, Category, SubCategory, Asset
from app.schemas import schemas
from app.dependencies import get_current_user

router = APIRouter(prefix="/transactions", tags=["transactions"])

# --- LISTAR ---
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
    user_account_ids = [acc.id for acc in current_user.accounts]
    
    query = db.query(Transaction).filter(
        Transaction.account_id.in_(user_account_ids)
    )

    if account_id:
        if account_id not in user_account_ids:
            return [] 
        query = query.filter(Transaction.account_id == account_id)

    if start_date:
        query = query.filter(Transaction.date >= start_date)
    if end_date:
        query = query.filter(Transaction.date <= end_date)

    if transaction_type_id:
        query = query.filter(Transaction.transaction_type_id == transaction_type_id)

    if search:
        search_fmt = f"%{search}%"
        query = query.filter(Transaction.description.like(search_fmt))

    transactions = query.options(
        joinedload(Transaction.transaction_type),
        joinedload(Transaction.category),
        joinedload(Transaction.subcategory)
        # joinedload(Transaction.asset) # Só descomentar se tiveres adicionado asset_id à Transação
    ).order_by(Transaction.date.desc()).offset(skip).limit(limit).all()

    return transactions

# --- CRIAR (LÓGICA CORRIGIDA) ---
@router.post("/", response_model=schemas.TransactionResponse, status_code=status.HTTP_201_CREATED)
def create_transaction(tx: schemas.TransactionCreate, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    # 1. Validar Conta
    account = db.query(Account).filter(Account.id == tx.account_id).first()
    if not account or account.user_id != current_user.id:
        raise HTTPException(status_code=403, detail="Não tem permissão para usar esta conta.")

    tx_type = db.query(TransactionType).filter(TransactionType.id == tx.transaction_type_id).first()
    if not tx_type: raise HTTPException(status_code=404, detail="Tipo inválido")

    # 2. Lógica de Investimentos (A MÁGICA ACONTECE AQUI) 🎩✨
    # Verificamos se veio Símbolo e Quantidade do frontend
    if tx.symbol and tx.quantity:
        symbol_upper = tx.symbol.upper()
        
        # Procura o ativo pelo símbolo
        asset = db.query(Asset).filter(Asset.symbol == symbol_upper).first()
        
        # Se não existir, CRIA O ATIVO
        if not asset:
            initial_price = tx.amount / tx.quantity if tx.quantity > 0 else 0
            asset = Asset(symbol=symbol_upper, name=symbol_upper, current_price=initial_price)
            db.add(asset)
            db.commit()
            db.refresh(asset)
        
        # Atualizar Carteira (Holdings)
        holding = db.query(Holding).filter(Holding.account_id == account.id, Holding.asset_id == asset.id).first()
        if not holding:
            holding = Holding(account_id=account.id, asset_id=asset.id, quantity=0, avg_buy_price=0)
            db.add(holding)
        
        # Lógica de Compra vs Venda
        negative_keywords = ["Despesa", "Saída", "Compra", "Buy"]
        is_buy = any(k in tx_type.name for k in negative_keywords)
        
        if is_buy:
            # Recalcular Preço Médio (Média Ponderada)
            current_total_val = holding.quantity * holding.avg_buy_price
            new_total_val = current_total_val + tx.amount
            holding.quantity += tx.quantity
            if holding.quantity > 0:
                holding.avg_buy_price = new_total_val / holding.quantity
        else:
            # Venda
            holding.quantity -= tx.quantity
            if holding.quantity < 0: holding.quantity = 0

    # 3. Atualizar Saldo da Conta
    negative_keywords = ["Despesa", "Expense", "Levantamento", "Compra", "Buy", "Saída"]
    is_negative = any(word in tx_type.name for word in negative_keywords)
    
    if is_negative: account.current_balance -= tx.amount
    else: account.current_balance += tx.amount
    
    # 4. Preparar dados para a DB
    tx_data = tx.model_dump() if hasattr(tx, 'model_dump') else tx.model_dump()
    
    # LIMPEZA DE CAMPOS VIRTUAIS
    # Removemos estes campos porque a tabela 'transactions' não tem colunas para eles
    # (A informação do investimento ficou guardada na tabela 'holdings')
    tx_data.pop('symbol', None)
    tx_data.pop('quantity', None)
    tx_data.pop('price_per_unit', None)
    tx_data.pop('asset_id', None) 

    if 'sub_category_id' in tx_data:
        tx_data['subcategory_id'] = tx_data.pop('sub_category_id')

    db_tx = Transaction(**tx_data)
    
    db.add(db_tx)
    db.add(account)
    # Importante: só adicionamos holding se ela tiver sido criada/alterada
    if 'holding' in locals(): 
        db.add(holding)
    
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
    if not tx.transaction_type:
         tx.transaction_type = db.query(TransactionType).filter(TransactionType.id == tx.transaction_type_id).first()

    is_negative_originally = any(word in tx.transaction_type.name for word in negative_keywords)
    if is_negative_originally: account.current_balance += tx.amount
    else: account.current_balance -= tx.amount

    db.delete(tx)
    db.add(account)
    db.commit()
    return None

# --- EDITAR ---
@router.put("/{transaction_id}", response_model=schemas.TransactionResponse)
def update_transaction(transaction_id: int, updated_tx: schemas.TransactionCreate, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    db_tx = db.query(Transaction).filter(Transaction.id == transaction_id).first()
    if not db_tx: raise HTTPException(status_code=404, detail="Transação não encontrada")

    old_account = db.query(Account).filter(Account.id == db_tx.account_id).first()
    if not old_account or old_account.user_id != current_user.id:
        raise HTTPException(status_code=403, detail="Sem permissão na conta original.")
        
    new_account = db.query(Account).filter(Account.id == updated_tx.account_id).first()
    if not new_account or new_account.user_id != current_user.id:
        raise HTTPException(status_code=403, detail="Sem permissão na conta de destino.")

    # Reverter Saldo Antigo
    negative_keywords = ["Despesa", "Expense", "Levantamento", "Compra", "Buy", "Saída"]
    if not db_tx.transaction_type:
        db_tx.transaction_type = db.query(TransactionType).filter(TransactionType.id == db_tx.transaction_type_id).first()
    was_negative = any(word in db_tx.transaction_type.name for word in negative_keywords)
    if was_negative: old_account.current_balance += db_tx.amount
    else: old_account.current_balance -= db_tx.amount

    # Aplicar Saldo Novo
    new_type = db.query(TransactionType).filter(TransactionType.id == updated_tx.transaction_type_id).first()
    if not new_type: raise HTTPException(status_code=404, detail="Novo tipo inválido")
    is_negative_new = any(word in new_type.name for word in negative_keywords)
    if is_negative_new: new_account.current_balance -= updated_tx.amount
    else: new_account.current_balance += updated_tx.amount

    # Atualizar Objeto
    tx_data = updated_tx.model_dump() if hasattr(updated_tx, 'model_dump') else updated_tx.model_dump()
    
    # LIMPEZA
    tx_data.pop('symbol', None)
    tx_data.pop('quantity', None)
    tx_data.pop('price_per_unit', None)
    tx_data.pop('asset_id', None)
    
    if 'sub_category_id' in tx_data:
        tx_data['subcategory_id'] = tx_data.pop('sub_category_id')

    for key, value in tx_data.items():
        setattr(db_tx, key, value)
    
    db.add(old_account)
    if new_account.id != old_account.id: db.add(new_account)
    db.add(db_tx)
    db.commit()
    db.refresh(db_tx)
    return db_tx