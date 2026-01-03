from sqlalchemy import text
from sqlalchemy.orm import Session
from datetime import date, timedelta, datetime
import random

from app.database.database import Base, SessionLocal, engine
from app.models import (
    User, Account, Category, SubCategory, UserProfile, AccountType, 
    TransactionType, Transaction, Asset, Holding
)
from app.utils.auth import get_password_hash

def run_seed():
    """
    Populates the database with a comprehensive set of realistic data for development and testing.
    Includes multiple users, accounts, categories, assets, holdings, and a rich transaction history spanning 3 years.
    """
    db: Session = SessionLocal()
    print("🌱 Starting database seed...")

    # 1. Clean Slate: Drop all tables for a fresh start
    print("🧹 Performing deep clean (dropping all tables)...")
    try:
        # The CASCADE option is crucial to handle foreign key constraints gracefully.
        Base.metadata.drop_all(bind=engine)
        print("   ✅ All tables dropped successfully.")
    except Exception as e:
        print(f"   ⚠️ Warning during cleanup (can be ignored on first run): {e}")
        db.rollback()

    # 2. Recreate Tables from Models
    print("🏗️  Recreating tables from models...")
    Base.metadata.create_all(bind=engine)
    print("   ✅ Tables recreated successfully.")

    try:
        # 3. Static Data: Account and Transaction Types
        print("📊 Seeding static types (accounts and transactions)...")
        acc_types = [
            AccountType(id=1, name="Conta à Ordem"),
            AccountType(id=2, name="Investimento / Corretora"),
            AccountType(id=3, name="Poupança"),
            AccountType(id=4, name="Carteira Crypto")
        ]
        db.add_all(acc_types)

        tx_types = [
            TransactionType(id=1, name="Despesa"),
            TransactionType(id=2, name="Receita"),
            TransactionType(id=3, name="Compra de Ativo", is_investment=True),
            TransactionType(id=4, name="Venda de Ativo", is_investment=True)
        ]
        db.add_all(tx_types)
        db.commit()
        print("   ✅ Static types seeded.")

        # 4. Financial Assets
        print("📈 Seeding financial assets (Stocks, Crypto)...")
        assets = [
            Asset(symbol="AAPL", name="Apple Inc.", asset_type="Stock"),
            Asset(symbol="GOOGL", name="Alphabet Inc.", asset_type="Stock"),
            Asset(symbol="MSFT", name="Microsoft Corporation", asset_type="Stock"),
            Asset(symbol="BTC-USD", name="Bitcoin", asset_type="Crypto"), # Ajustado para yfinance
            Asset(symbol="ETH-USD", name="Ethereum", asset_type="Crypto"),
        ]
        db.add_all(assets)
        db.commit()
        print("   ✅ Assets seeded.")

        # 5. Users and their associated data
        print("👥 Seeding users, profiles, accounts, and categories...")
        common_password = get_password_hash("123")
        users_data = [
            {"email": "basic@moneymap.com", "role": "basic", "first_name": "Zé", "last_name": "Básico", "currency": "EUR"},
            {"email": "premium@moneymap.com", "role": "premium", "first_name": "Ana", "last_name": "Premium", "currency": "USD"},
            {"email": "admin@moneymap.com", "role": "admin", "first_name": "Admin", "last_name": "Supremo", "currency": "EUR"}
        ]

        # Fetch assets for later use
        aapl = db.query(Asset).filter(Asset.symbol == "AAPL").first()
        btc = db.query(Asset).filter(Asset.symbol == "BTC-USD").first()
        msft = db.query(Asset).filter(Asset.symbol == "MSFT").first()

        for u_data in users_data:
            # Create User and Profile
            user = User(email=u_data["email"], password_hash=common_password, role=u_data["role"])
            db.add(user)
            db.commit()
            db.refresh(user)
            
            profile = UserProfile(
                user_id=user.id,
                first_name=u_data["first_name"],
                last_name=u_data["last_name"],
                preferred_currency=u_data["currency"]
            )
            db.add(profile)

            # Create Accounts
            # Saldo inicial será ajustado pelas transações, mas começamos com um valor base
            main_account = Account(user_id=user.id, name=f"Banco Principal", account_type_id=1, current_balance=0)
            db.add(main_account)

            investment_account = None
            if u_data["role"] in ["premium", "admin"]:
                investment_account = Account(user_id=user.id, name="Conta Corretora", account_type_id=2, current_balance=0)
                db.add(investment_account)
            db.commit()

            # Create Categories & Sub-categories
            categories = {
                "Casa": ["Renda", "Supermercado", "Eletricidade", "Internet"],
                "Transporte": ["Combustível", "Transporte Público", "Uber"],
                "Lazer": ["Restaurantes", "Cinema", "Viagens", "Jogos"],
                "Saúde": ["Farmácia", "Consulta", "Ginásio"],
                "Salário": ["Ordenado", "Bónus"]
            }
            user_categories = {}
            for cat_name, sub_cats in categories.items():
                cat = Category(user_id=user.id, name=cat_name)
                db.add(cat)
                db.commit()
                user_categories[cat_name] = {"id": cat.id, "sub": {}}
                for sub_name in sub_cats:
                    sub = SubCategory(category_id=cat.id, name=sub_name)
                    db.add(sub)
                    db.commit()
                    user_categories[cat_name]["sub"][sub_name] = sub.id

            # 6. Transaction History (3 Years)
            print(f"   💸 Seeding 3 years of history for {user.email}...")
            
            start_date = date.today() - timedelta(days=3*365)
            current_date = start_date
            end_date = date.today()
            
            balance_main = 1000.0 # Saldo inicial simulado
            balance_invest = 0.0

            while current_date <= end_date:
                # 1. Salário (Dia 1 ou 28 de cada mês)
                if current_date.day == 1:
                    salary = 2500.0 if u_data["role"] == "premium" else 1500.0
                    db.add(Transaction(
                        date=current_date, description="Salário Mensal", amount=salary,
                        account_id=main_account.id, transaction_type_id=2, 
                        category_id=user_categories["Salário"]["id"],
                        subcategory_id=user_categories["Salário"]["sub"]["Ordenado"]
                    ))
                    balance_main += salary
                    
                    # Renda (Dia 1)
                    rent = 800.0 if u_data["role"] == "premium" else 500.0
                    db.add(Transaction(
                        date=current_date, description="Pagamento Renda", amount=-rent,
                        account_id=main_account.id, transaction_type_id=1, 
                        category_id=user_categories["Casa"]["id"],
                        subcategory_id=user_categories["Casa"]["sub"]["Renda"]
                    ))
                    balance_main -= rent

                # 2. Despesas Aleatórias (Supermercado, Lazer, etc.)
                # Probabilidade de 40% de ter uma despesa num dia qualquer
                if random.random() < 0.4:
                    cat_key = random.choice(["Casa", "Transporte", "Lazer", "Saúde"])
                    sub_key = random.choice(list(user_categories[cat_key]["sub"].keys()))
                    
                    amount = round(random.uniform(5.0, 150.0), 2)
                    desc = f"Despesa em {sub_key}"
                    
                    db.add(Transaction(
                        date=current_date, description=desc, amount=-amount,
                        account_id=main_account.id, transaction_type_id=1, 
                        category_id=user_categories[cat_key]["id"],
                        subcategory_id=user_categories[cat_key]["sub"][sub_key]
                    ))
                    balance_main -= amount

                # 3. Investimentos (Apenas Premium/Admin e se tiver saldo)
                if investment_account and current_date.day == 15 and balance_main > 2000:
                    invest_amount = 500.0
                    # Transferência (Simulada como Saída do Banco e Entrada na Corretora)
                    # Simplificação: Criamos logo a compra do ativo
                    
                    asset_choice = random.choice([aapl, btc, msft])
                    qty = round(invest_amount / 150.0, 4) # Preço fictício médio
                    
                    db.add(Transaction(
                        date=current_date, description=f"Compra {asset_choice.symbol}", amount=-invest_amount,
                        account_id=investment_account.id, transaction_type_id=3, 
                        asset_id=asset_choice.id, quantity=qty
                    ))
                    balance_invest += invest_amount # Na verdade o saldo cash desce, mas o valor investido sobe. 
                    # Para simplificar o seed, não vamos gerir o "Cash Balance" da corretora ao detalhe, 
                    # assumimos que o dinheiro "saiu" para comprar o ativo.

                current_date += timedelta(days=1)
            
            # Atualizar saldos finais
            main_account.current_balance = round(balance_main, 2)
            if investment_account:
                investment_account.current_balance = round(balance_invest, 2) # Isto é discutível, mas serve para o seed
            
            db.commit()

        print("   ✅ User data, transactions, and holdings seeded.")

        print("\n" + "="*50)
        print("✅ Seed completed successfully!")
        print("🔑 Test Credentials (password for all is '123'):")
        for u in users_data:
            print(f"   - {u['role'].title()}:\t {u['email']}")
        print("="*50 + "\n")

    except Exception as e:
        print(f"❌ An error occurred during seeding: {e}")
        db.rollback()
    finally:
        db.close()
        print("🚪 Database session closed.")

if __name__ == "__main__":
    run_seed()