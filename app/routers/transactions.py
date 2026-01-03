from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session, joinedload
from typing import List, Optional
from datetime import date

from app.database.database import get_db
# USAMOS A TUA IMPORTAÇÃO (Assume que app/models expõe estas classes)
from app.models import Transaction, Account, User, TransactionType, Holding, Category, SubCategory, Asset
from app.schemas import schemas
from app.utils.auth import get_current_user

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

    # Nota: Verifica se no teu model o nome da relação é 'sub_category' (com underscore) ou 'subcategory'.
    # Baseado no upload original era 'sub_category', mas ajusta se tiveres mudado.
    transactions = query.options(
        joinedload(Transaction.transaction_type),
        joinedload(Transaction.subcategory), 
        joinedload(Transaction.asset),
        joinedload(Transaction.account)
    ).order_by(Transaction.date.desc()).offset(skip).limit(limit).all()

    return transactions

# --- CRIAR ---
@router.post("/", response_model=schemas.TransactionResponse, status_code=status.HTTP_201_CREATED)
def create_transaction(tx: schemas.TransactionCreate, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    # 1. Validar Conta
    account = db.query(Account).filter(Account.id == tx.account_id).first()
    if not account or account.user_id != current_user.id:
        raise HTTPException(status_code=403, detail="Não tem permissão para usar esta conta.")

    tx_type = db.query(TransactionType).filter(TransactionType.id == tx.transaction_type_id).first()
    if not tx_type: raise HTTPException(status_code=404, detail="Tipo inválido")

    # 2. DEFINIR O SINAL DO VALOR
    negative_keywords = ["Despesa", "Expense", "Levantamento", "Compra", "Buy", "Saída"]
    is_negative_action = any(word in tx_type.name for word in negative_keywords)
    
    # Normalizar o valor (Despesa/Investimento = Negativo)
    final_amount = -abs(tx.amount) if is_negative_action else abs(tx.amount)

    asset_id_to_save = None

    # 3. Lógica de Investimentos
    if tx.symbol and tx.quantity:
        symbol_upper = tx.symbol.upper()
        
        # Verificar ou Criar Asset
        asset = db.query(Asset).filter(Asset.symbol == symbol_upper).first()
        if not asset:
            # --- CORREÇÃO DO ERRO ---
            # Removemos 'current_price' porque não existe no teu model Asset.
            # Adicionamos 'asset_type' com valor default "Stock" (ou outro genérico).
            asset = Asset(symbol=symbol_upper, name=symbol_upper, asset_type="Stock")
            db.add(asset)
            db.commit()
            db.refresh(asset)
        
        asset_id_to_save = asset.id

        # Gerir Holding (Posição na Carteira)
        holding = db.query(Holding).filter(Holding.account_id == account.id, Holding.asset_id == asset.id).first()
        if not holding:
            holding = Holding(account_id=account.id, asset_id=asset.id, quantity=0, avg_buy_price=0)
            db.add(holding)
        
        # Compra vs Venda
        is_buy_asset = any(k in tx_type.name for k in ["Compra", "Buy"])
        
        if is_buy_asset:
            # Cálculo de Preço Médio
            current_total_val = holding.quantity * holding.avg_buy_price
            
            # Preço da nova compra
            p_unit = tx.price_per_unit if (tx.price_per_unit and tx.price_per_unit > 0) else (abs(final_amount) / tx.quantity if tx.quantity > 0 else 0)
            
            cost_of_this_buy = tx.quantity * p_unit
            new_total_val = current_total_val + cost_of_this_buy
            
            holding.quantity += tx.quantity
            
            if holding.quantity > 0:
                holding.avg_buy_price = new_total_val / holding.quantity
        else:
            # Venda
            holding.quantity -= tx.quantity
            if holding.quantity < 0: holding.quantity = 0

    # 4. Atualizar Saldo da Conta
    account.current_balance += final_amount
    
    # 5. Criar Objeto da Transação
    tx_data = tx.model_dump() if hasattr(tx, 'model_dump') else tx.dict()
    
    # Forçar o valor com sinal correto
    tx_data['amount'] = final_amount

    # Limpar campos que não pertencem à tabela Transactions
    tx_data.pop('symbol', None)
    tx_data.pop('quantity', None)
    tx_data.pop('price_per_unit', None)
    
    # Ligar o Asset ID se existir
    if asset_id_to_save:
        tx_data['asset_id'] = asset_id_to_save
    else:
         tx_data.pop('asset_id', None)

    # Corrigir nome do campo subcategoria: o schema usa 'sub_category_id', o modelo usa 'subcategory_id'
    if 'sub_category_id' in tx_data:
        tx_data['subcategory_id'] = tx_data.pop('sub_category_id')

    # Criar e Salvar
    db_tx = Transaction(**tx_data)
    
    db.add(db_tx)
    db.add(account)
    # Holding já foi adicionada ao session acima se criada/editada
    
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
    account.current_balance -= tx.amount

    # Reverter Holding
    if tx.asset_id and tx.quantity:
        holding = db.query(Holding).filter(Holding.account_id == account.id, Holding.asset_id == tx.asset_id).first()
        if holding:
            if not tx.transaction_type:
                 tx.transaction_type = db.query(TransactionType).filter(TransactionType.id == tx.transaction_type_id).first()
            
            is_buy = any(k in tx.transaction_type.name for k in ["Compra", "Buy"])
            
            if is_buy:
                holding.quantity -= tx.quantity
            else:
                holding.quantity += tx.quantity
            
            if holding.quantity < 0: holding.quantity = 0

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
        raise HTTPException(status_code=403, detail="Sem permissão.")
        
    new_account = db.query(Account).filter(Account.id == updated_tx.account_id).first()
    if not new_account or new_account.user_id != current_user.id:
        raise HTTPException(status_code=403, detail="Sem permissão no destino.")

    # 1. Reverter Saldo Antigo
    old_account.current_balance -= db_tx.amount

    # 2. Calcular Novo Valor com Sinal
    new_type = db.query(TransactionType).filter(TransactionType.id == updated_tx.transaction_type_id).first()
    if not new_type: raise HTTPException(status_code=404, detail="Tipo inválido")
    
    negative_keywords = ["Despesa", "Expense", "Levantamento", "Compra", "Buy", "Saída"]
    is_negative_new = any(word in new_type.name for word in negative_keywords)
    
    final_new_amount = -abs(updated_tx.amount) if is_negative_new else abs(updated_tx.amount)

    # 3. Aplicar Novo Saldo
    new_account.current_balance += final_new_amount

    # 4. Atualizar Objeto Transaction
    tx_data = updated_tx.model_dump() if hasattr(updated_tx, 'model_dump') else updated_tx.dict()
    tx_data['amount'] = final_new_amount
    
    # Limpeza para evitar erros de campos inexistentes ou lógica complexa de holdings no update
    tx_data.pop('symbol', None)
    tx_data.pop('quantity', None)
    tx_data.pop('price_per_unit', None)
    tx_data.pop('asset_id', None) 
    
    if 'sub_category_id' in tx_data:
        tx_data['subcategory_id'] = tx_data.pop('sub_category_id')

    for key, value in tx_data.items():
        if hasattr(db_tx, key):
            setattr(db_tx, key, value)
    
    db.add(old_account)
    if new_account.id != old_account.id: db.add(new_account)
    db.add(db_tx)
    db.commit()
    db.refresh(db_tx)
    return db_tx