from fastapi import APIRouter, Depends, HTTPException, UploadFile, File
from sqlalchemy.orm import Session
import pandas as pd
from io import BytesIO
from datetime import datetime

# --- IMPORTS DO PROJETO ---
from app.database.database import get_db
from app.models import models
from app.auth import get_current_user

router = APIRouter(prefix="/imports", tags=["imports"])

@router.post("/upload")
async def upload_transactions(
    account_id: int,
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user)
):
    # 1. Validar se a Conta pertence ao User
    account = db.query(models.Account).filter(models.Account.id == account_id).first()
    if not account or account.user_id != current_user.id:
        raise HTTPException(status_code=403, detail="Conta inválida ou sem permissão.")

    # 2. Ler o Ficheiro para memória
    contents = await file.read()
    try:
        if file.filename.endswith('.csv'):
            # Tenta ler com virgula ou ponto e virgula (comum em PT)
            try:
                df = pd.read_csv(BytesIO(contents), sep=',')
                if len(df.columns) < 2: # Se falhou, tenta ;
                    df = pd.read_csv(BytesIO(contents), sep=';')
            except:
                df = pd.read_csv(BytesIO(contents), sep=';')
                
        elif file.filename.endswith(('.xls', '.xlsx')):
            df = pd.read_excel(BytesIO(contents))
        else:
            raise HTTPException(status_code=400, detail="Formato não suportado. Use CSV ou Excel.")
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Erro ao ler ficheiro: {str(e)}")

    # 3. Normalizar Nomes das Colunas (Tudo minúsculo para facilitar)
    df.columns = df.columns.str.lower().str.strip()
    
    # 4. Mapeamento Inteligente de Colunas
    # Procura colunas que contenham palavras-chave
    col_map = {}
    for col in df.columns:
        if 'data' in col or 'date' in col: col_map['date'] = col
        elif 'desc' in col or 'movimento' in col or 'libelle' in col: col_map['description'] = col
        elif 'valor' in col or 'montante' in col or 'amount' in col or 'crédito' in col: 
             # Ignorar colunas de "Saldo Contabilístico" se existirem
             if 'saldo' not in col:
                 col_map['amount'] = col
    
    # Validação mínima
    if not all(k in col_map.values() for k in ['date', 'amount']):
        return {"error": "Não conseguimos identificar as colunas 'Data' e 'Valor'. Verifique o ficheiro."}

    # Buscar tipos padrão para categorizar (Despesa vs Receita)
    type_expense = db.query(models.TransactionType).filter(models.TransactionType.name.ilike("%Despesa%")).first()
    type_income = db.query(models.TransactionType).filter(models.TransactionType.name.ilike("%Receita%")).first()
    
    # Fallback se não existirem tipos na BD (Seed)
    if not type_expense: type_expense_id = 1
    else: type_expense_id = type_expense.id
    
    if not type_income: type_income_id = 2
    else: type_income_id = type_income.id

    transactions_added = 0
    errors = 0

    # 5. Processar Linha a Linha
    for index, row in df.iterrows():
        try:
            # Extrair valores
            raw_date = row[col_map['date']]
            raw_desc = row.get(col_map.get('description'), 'Importado') # Descrição opcional
            raw_amount = row[col_map['amount']]

            # A. Tratar Data (Pandas é bom nisto, mas dayfirst=True ajuda em PT)
            dt = pd.to_datetime(raw_date, dayfirst=True).date()

            # B. Tratar Valor (Remover símbolos de moeda, tratar virgulas)
            if isinstance(raw_amount, str):
                # Remover ' EUR', espaços, etc
                clean_amount = raw_amount.lower().replace('eur', '').replace('€', '').strip()
                # Em PT: 1.000,00 -> remove ponto, troca virgula por ponto
                if ',' in clean_amount and '.' in clean_amount:
                     clean_amount = clean_amount.replace('.', '').replace(',', '.')
                elif ',' in clean_amount:
                     clean_amount = clean_amount.replace(',', '.')
                amount = float(clean_amount)
            else:
                amount = float(raw_amount)

            # C. Decidir se é Receita ou Despesa
            # Assumimos: Valor Negativo = Despesa
            if amount < 0:
                tx_type_id = type_expense_id
                final_amount = abs(amount) # Guardamos sempre positivo, o tipo define o sinal
                is_negative = True
            else:
                tx_type_id = type_income_id
                final_amount = amount
                is_negative = False

            # D. Verificar Duplicados (Mesma conta, data, valor e descrição)
            exists = db.query(models.Transaction).filter(
                models.Transaction.account_id == account_id,
                models.Transaction.date == dt,
                models.Transaction.amount == final_amount,
                models.Transaction.description == str(raw_desc)
            ).first()

            if not exists:
                new_tx = models.Transaction(
                    date=dt,
                    description=str(raw_desc)[:255], # Limitar tamanho
                    amount=final_amount,
                    account_id=account_id,
                    transaction_type_id=tx_type_id
                )
                db.add(new_tx)
                
                # Atualizar Saldo da Conta
                if is_negative:
                    account.current_balance -= final_amount
                else:
                    account.current_balance += final_amount
                
                transactions_added += 1

        except Exception as e:
            # Log de erro (podemos melhorar isto depois)
            print(f"Erro linha {index}: {e}")
            errors += 1
            continue

    db.commit()
    return {
        "message": "Importação concluída",
        "added": transactions_added,
        "errors": errors
    }