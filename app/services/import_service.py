import pandas as pd
from io import BytesIO
from sqlalchemy.orm import Session
from fastapi import UploadFile
from datetime import datetime

# Importar os Modelos Corretos
from app.models import Transaction, Account, TransactionType, Category

class ImportService:
    @staticmethod
    async def process_file(db: Session, account_id: int, file: UploadFile, user_id: int) -> dict:
        # 1. Ler Ficheiro para memória
        contents = await file.read()
        filename = file.filename.lower()
        
        try:
            if filename.endswith('.csv'):
                try:
                    # Tenta vírgula primeiro
                    df = pd.read_csv(BytesIO(contents), sep=',')
                    if len(df.columns) < 2: 
                        # Se falhar, tenta ponto e vírgula
                        df = pd.read_csv(BytesIO(contents), sep=';')
                except:
                    df = pd.read_csv(BytesIO(contents), sep=';')
            elif filename.endswith(('.xls', '.xlsx')):
                df = pd.read_excel(BytesIO(contents))
            else:
                raise ValueError("Formato não suportado. Use CSV ou Excel.")
        except Exception as e:
            raise ValueError(f"Erro ao ler ficheiro: {str(e)}")

        # 2. Normalizar Colunas (Remove espaços e mete minúsculas)
        df.columns = df.columns.str.lower().str.strip()
        col_map = {}
        
        # Mapa inteligente de colunas
        for col in df.columns:
            if 'data' in col or 'date' in col: col_map['date'] = col
            elif 'desc' in col or 'movimento' in col or 'narração' in col: col_map['description'] = col
            elif 'valor' in col or 'montante' in col or 'amount' in col: 
                 if 'saldo' not in col: col_map['amount'] = col
        
        # --- CORREÇÃO AQUI ---
        # Verificamos se as chaves ('date', 'amount') existem no dicionário mapeado
        if not all(k in col_map for k in ['date', 'amount']):
            raise ValueError(f"Colunas obrigatórias não encontradas. Detetadas: {list(df.columns)}")

        # 3. Preparar Dados Auxiliares
        
        # Buscar ou Criar Categoria "Importações"
        default_cat = db.query(Category).filter(
            Category.user_id == user_id, 
            Category.name == "Importações"
        ).first()
        
        if not default_cat:
            default_cat = Category(user_id=user_id, name="Importações")
            db.add(default_cat)
            db.commit()
            db.refresh(default_cat)

        # Tipos de Transação
        type_expense = db.query(TransactionType).filter(TransactionType.name.ilike("%Despesa%")).first()
        type_income = db.query(TransactionType).filter(TransactionType.name.ilike("%Receita%")).first()
        
        expense_id = type_expense.id if type_expense else 1
        income_id = type_income.id if type_income else 2

        added_count = 0
        errors_count = 0
        
        account = db.query(Account).filter(Account.id == account_id).first()
        if not account:
             raise ValueError("Conta não encontrada.")

        # 4. Processar Linhas
        for _, row in df.iterrows():
            try:
                raw_date = row[col_map['date']]
                # Se não houver coluna de descrição mapeada, usa texto genérico
                desc_col = col_map.get('description')
                raw_desc = row[desc_col] if desc_col else 'Transação Importada'
                
                raw_amount = row[col_map['amount']]

                # Parse Data
                dt = None
                if isinstance(raw_date, str):
                    try:
                        dt = pd.to_datetime(raw_date, dayfirst=True).date()
                    except:
                        pass
                else:
                    dt = raw_date.date() if hasattr(raw_date, 'date') else raw_date
                
                if not dt:
                    errors_count += 1
                    continue

                # Parse Valor
                if isinstance(raw_amount, str):
                    clean = raw_amount.lower().replace('eur','').replace('€','').strip()
                    if ',' in clean and '.' in clean: 
                        clean = clean.replace('.','').replace(',','.')
                    elif ',' in clean: 
                        clean = clean.replace(',','.')
                    amount = float(clean)
                else:
                    amount = float(raw_amount)

                # Lógica de Sinal vs Tipo
                if amount < 0:
                    tx_type = expense_id
                    final_amount = abs(amount)
                    is_neg = True
                else:
                    tx_type = income_id
                    final_amount = amount
                    is_neg = False

                # Verificação de Duplicados
                exists = db.query(Transaction).filter(
                    Transaction.account_id == account_id,
                    Transaction.date == dt,
                    Transaction.amount == final_amount,
                    Transaction.description == str(raw_desc)[:255]
                ).first()

                if not exists:
                    new_tx = Transaction(
                        date=dt, 
                        description=str(raw_desc)[:255], 
                        amount=final_amount,
                        account_id=account_id, 
                        transaction_type_id=tx_type,
                        category_id=default_cat.id
                    )
                    db.add(new_tx)
                    
                    if is_neg: account.current_balance -= final_amount
                    else: account.current_balance += final_amount
                    
                    added_count += 1

            except Exception:
                errors_count += 1
                continue
        
        db.commit()
        return {"added": added_count, "errors": errors_count}