import pandas as pd
from io import BytesIO
from sqlalchemy.orm import Session
from fastapi import UploadFile
from app.models import models # Nota: Se já tiveres feito a Fase 3, muda para 'from app.models import Transaction, Account...'

class ImportService:
    @staticmethod
    async def process_file(db: Session, account_id: int, file: UploadFile) -> dict:
        # 1. Ler Ficheiro para memória
        contents = await file.read()
        try:
            if file.filename.endswith('.csv'):
                try:
                    df = pd.read_csv(BytesIO(contents), sep=',')
                    if len(df.columns) < 2: df = pd.read_csv(BytesIO(contents), sep=';')
                except:
                    df = pd.read_csv(BytesIO(contents), sep=';')
            elif file.filename.endswith(('.xls', '.xlsx')):
                df = pd.read_excel(BytesIO(contents))
            else:
                raise ValueError("Formato não suportado. Use CSV ou Excel.")
        except Exception as e:
            raise ValueError(f"Erro ao ler ficheiro: {str(e)}")

        # 2. Normalizar
        df.columns = df.columns.str.lower().str.strip()
        col_map = {}
        for col in df.columns:
            if 'data' in col or 'date' in col: col_map['date'] = col
            elif 'desc' in col or 'movimento' in col: col_map['description'] = col
            elif 'valor' in col or 'montante' in col or 'amount' in col: 
                 if 'saldo' not in col: col_map['amount'] = col
        
        if not all(k in col_map.values() for k in ['date', 'amount']):
            raise ValueError("Colunas 'Data' e 'Valor' não identificadas.")

        # Buscar tipos de transação
        type_expense = db.query(models.TransactionType).filter(models.TransactionType.name.ilike("%Despesa%")).first()
        type_income = db.query(models.TransactionType).filter(models.TransactionType.name.ilike("%Receita%")).first()
        expense_id = type_expense.id if type_expense else 1
        income_id = type_income.id if type_income else 2

        added_count = 0
        errors_count = 0
        
        account = db.query(models.Account).filter(models.Account.id == account_id).first()

        # 3. Processar
        for _, row in df.iterrows():
            try:
                raw_date = row[col_map['date']]
                raw_desc = row.get(col_map.get('description'), 'Importado')
                raw_amount = row[col_map['amount']]

                # Data
                dt = pd.to_datetime(raw_date, dayfirst=True).date()
                
                # Valor
                if isinstance(raw_amount, str):
                    clean = raw_amount.lower().replace('eur','').replace('€','').strip()
                    if ',' in clean and '.' in clean: clean = clean.replace('.','').replace(',','.')
                    elif ',' in clean: clean = clean.replace(',','.')
                    amount = float(clean)
                else:
                    amount = float(raw_amount)

                # Tipo
                if amount < 0:
                    tx_type = expense_id
                    final_amount = abs(amount)
                    is_neg = True
                else:
                    tx_type = income_id
                    final_amount = amount
                    is_neg = False

                # Duplicados
                exists = db.query(models.Transaction).filter(
                    models.Transaction.account_id == account_id,
                    models.Transaction.date == dt,
                    models.Transaction.amount == final_amount,
                    models.Transaction.description == str(raw_desc)[:255]
                ).first()

                if not exists:
                    new_tx = models.Transaction(
                        date=dt, description=str(raw_desc)[:255], amount=final_amount,
                        account_id=account_id, transaction_type_id=tx_type
                    )
                    db.add(new_tx)
                    if is_neg: account.current_balance -= final_amount
                    else: account.current_balance += final_amount
                    added_count += 1

            except:
                errors_count += 1
                continue
        
        db.commit()
        return {"added": added_count, "errors": errors_count}