from sqlalchemy import text
from sqlalchemy.orm import Session
from datetime import date, timedelta
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
    Includes multiple users, accounts, categories, assets, holdings, and a rich transaction history.
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
            Asset(symbol="BTC", name="Bitcoin", asset_type="Crypto"),
            Asset(symbol="ETH", name="Ethereum", asset_type="Crypto"),
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
        btc = db.query(Asset).filter(Asset.symbol == "BTC").first()
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
            main_account = Account(user_id=user.id, name=f"Banco Principal", account_type_id=1, current_balance=random.uniform(1000, 2500))
            db.add(main_account)

            investment_account = None
            if u_data["role"] in ["premium", "admin"]:
                investment_account = Account(user_id=user.id, name="Conta Corretora", account_type_id=2, current_balance=random.uniform(5000, 15000))
                db.add(investment_account)
            db.commit()

            # Create Categories & Sub-categories
            categories = {
                "Casa": ["Renda", "Supermercado", "Eletricidade", "Internet"],
                "Transporte": ["Combustível", "Transporte Público"],
                "Lazer": ["Restaurantes", "Cinema", "Viagens"],
                "Saúde": ["Farmácia", "Consulta"],
                "Salário": ["Ordenado"]
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

            # 6. Transaction History
            print(f"   💸 Seeding transaction history for {user.email}...")
            # Income
            db.add(Transaction(
                date=date.today() - timedelta(days=15), description="Salário do Mês", amount=3000,
                account_id=main_account.id, transaction_type_id=2, 
                category_id=user_categories["Salário"]["id"],
                subcategory_id=user_categories["Salário"]["sub"]["Ordenado"]
            ))

            # Expenses
            for day in range(1, 30):
                db.add(Transaction(
                    date=date.today() - timedelta(days=day), description="Compras Pingo Doce", amount=-random.uniform(15, 45),
                    account_id=main_account.id, transaction_type_id=1, 
                    category_id=user_categories["Casa"]["id"], subcategory_id=user_categories["Casa"]["sub"]["Supermercado"]
                ))
                if day % 5 == 0:
                     db.add(Transaction(
                        date=date.today() - timedelta(days=day), description="Jantar Fora", amount=-random.uniform(30, 80),
                        account_id=main_account.id, transaction_type_id=1, 
                        category_id=user_categories["Lazer"]["id"], subcategory_id=user_categories["Lazer"]["sub"]["Restaurantes"]
                    ))

            # Investment transactions for premium users
            if investment_account:
                # Buy AAPL
                db.add(Holding(account_id=investment_account.id, asset_id=aapl.id, quantity=10, avg_buy_price=150.0))
                db.add(Transaction(
                    date=date.today() - timedelta(days=40), description="Compra de 10 Ações Apple", amount=-1500.0,
                    account_id=investment_account.id, transaction_type_id=3, asset_id=aapl.id, quantity=10
                ))
                # Buy BTC
                db.add(Holding(account_id=investment_account.id, asset_id=btc.id, quantity=0.1, avg_buy_price=40000.0))
                db.add(Transaction(
                    date=date.today() - timedelta(days=35), description="Compra de 0.1 Bitcoin", amount=-4000.0,
                    account_id=investment_account.id, transaction_type_id=3, asset_id=btc.id, quantity=0.1
                ))
                # Buy MSFT
                db.add(Holding(account_id=investment_account.id, asset_id=msft.id, quantity=15, avg_buy_price=300.0))
                db.add(Transaction(
                    date=date.today() - timedelta(days=20), description="Compra de 15 Ações Microsoft", amount=-4500.0,
                    account_id=investment_account.id, transaction_type_id=3, asset_id=msft.id, quantity=15
                ))
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
