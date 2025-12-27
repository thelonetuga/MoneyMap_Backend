import random
from datetime import date, timedelta
from sqlalchemy import text

# --- IMPORTS ---
from database.database import SessionLocal, engine
from models.models import (
    Base, User, UserProfile, Account, AccountType, 
    Category, SubCategory, Transaction, TransactionType, 
    Asset, AssetPrice, Holding
)
from auth import get_password_hash 

def clean_database(db):
    print("🧹 A limpar base de dados antiga (TRUNCATE)...")
    try:
        # TRUNCATE CASCADE: A forma mais violenta e eficaz de limpar tabelas no Postgres.
        # Apaga os dados e reinicia os contadores de ID (RESTART IDENTITY).
        # Nota: As tabelas devem estar no plural, conforme definido no SQLAlchemy (ex: 'users', 'assets')
        
        tables = [
            "transactions", "holdings", "asset_prices", 
            "sub_categories", "categories", 
            "accounts", "user_profiles", "users", 
            "assets", "account_types", "transaction_types"
        ]
        
        # Montar a string SQL
        sql_command = f"TRUNCATE TABLE {', '.join(tables)} RESTART IDENTITY CASCADE;"
        
        db.execute(text(sql_command))
        db.commit()
        print("✨ Base de dados limpa com sucesso.")
        
    except Exception as e:
        print(f"⚠️ Erro ao limpar (se for a primeira vez, ignore): {e}")
        db.rollback()

def create_dummy_data():
    db = SessionLocal()
    
    # 1. Limpar tudo primeiro
    clean_database(db)
    
    print("🌱 A semear novos dados...")

    # --- 2. CONFIGURAÇÕES (TYPES) ---
    acc_types = [
        AccountType(name="Conta à Ordem"),    # ID 1
        AccountType(name="Poupança"),         # ID 2
        AccountType(name="Corretora"),        # ID 3
        AccountType(name="Wallet Crypto")     # ID 4
    ]
    db.add_all(acc_types)
    
    tx_types = [
        TransactionType(name="Despesa", is_investment=False),            # ID 1
        TransactionType(name="Receita", is_investment=False),            # ID 2
        TransactionType(name="Compra Investimento", is_investment=True), # ID 3
        TransactionType(name="Venda Investimento", is_investment=True)   # ID 4
    ]
    db.add_all(tx_types)
    db.commit()

    # Guardar referências
    t_expense = tx_types[0]
    t_income = tx_types[1]
    t_buy = tx_types[2]

    # --- 3. UTILIZADOR & LOGIN ---
    print("🔐 A criar utilizador seguro...")
    password_encriptada = get_password_hash("123456")
    
    user = User(email="joao@email.com", password_hash=password_encriptada)
    db.add(user)
    db.commit()
    
    profile = UserProfile(user_id=user.id, first_name="João", last_name="Silva", preferred_currency="EUR")
    db.add(profile)
    db.commit()

    # --- 4. CATEGORIAS ---
    cats_dict = {
        "Casa": ["Renda", "Luz & Água", "Internet", "Limpeza"],
        "Alimentação": ["Supermercado", "Restaurantes", "Uber Eats"],
        "Transporte": ["Combustível", "Uber", "Manutenção"],
        "Lazer": ["Cinema", "Subscrições (Netflix)", "Viagens"],
        "Rendimento": ["Salário", "Freelance", "Dividendos"]
    }
    
    subcats_map = {} 
    
    for c_name, subs in cats_dict.items():
        cat = Category(name=c_name, user_id=user.id)
        db.add(cat)
        db.commit()
        for s_name in subs:
            sub = SubCategory(name=s_name, category_id=cat.id)
            db.add(sub)
            subcats_map[s_name] = sub
    db.commit()

    # --- 5. ATIVOS & HISTÓRICO ---
    print("📈 A simular mercado financeiro...")
    assets_data = [
        ("AAPL", "Apple Inc.", 175.00),
        ("TSLA", "Tesla", 240.00),
        ("VWCE", "Vanguard All-World ETF", 105.00),
        ("BTC", "Bitcoin", 41000.00),
        ("ETH", "Ethereum", 2200.00)
    ]
    
    asset_objs = {}
    
    for symbol, name, base_price in assets_data:
        asset = Asset(symbol=symbol, name=name, asset_type=("Crypto" if base_price > 1000 else "Stock"))
        db.add(asset)
        db.commit()
        asset_objs[symbol] = asset
        
        # Gerar 90 dias de preços
        curr_price = base_price * 0.85 
        for day in range(90, -1, -1):
            date_price = date.today() - timedelta(days=day)
            change = random.uniform(0.98, 1.03) 
            curr_price = curr_price * change
            db.add(AssetPrice(asset_id=asset.id, date=date_price, close_price=curr_price))
    
    db.commit()

    # --- 6. CONTAS BANCÁRIAS ---
    acc_banco = Account(name="Millennium BCP", current_balance=0, user_id=user.id, account_type_id=1)
    acc_corretora = Account(name="XTB Invest", current_balance=0, user_id=user.id, account_type_id=3)
    acc_crypto = Account(name="Binance", current_balance=0, user_id=user.id, account_type_id=4)
    
    db.add_all([acc_banco, acc_corretora, acc_crypto])
    db.commit()

    # --- 7. TRANSAÇÕES ---
    print("💸 A simular a vida do João (3 Meses)...")
    
    start_date = date.today() - timedelta(days=90)
    
    # Depósito Inicial
    initial_deposit = Transaction(
        date=start_date, description="Saldo Inicial", amount=5000, 
        account_id=acc_banco.id, transaction_type_id=t_income.id, sub_category_id=subcats_map["Salário"].id
    )
    acc_banco.current_balance += 5000
    db.add(initial_deposit)

    for day in range(1, 91):
        current_date = start_date + timedelta(days=day)
        
        # Salário
        if current_date.day == 1:
            amount = 2500.00
            t = Transaction(date=current_date, description="Salário Google", amount=amount, account_id=acc_banco.id, transaction_type_id=t_income.id, sub_category_id=subcats_map["Salário"].id)
            acc_banco.current_balance += amount
            db.add(t)
        
        # Renda
        if current_date.day == 2:
            amount = 850.00
            t = Transaction(date=current_date, description="Pagamento Renda", amount=amount, account_id=acc_banco.id, transaction_type_id=t_expense.id, sub_category_id=subcats_map["Renda"].id)
            acc_banco.current_balance -= amount
            db.add(t)

        # Despesas Aleatórias
        if random.random() < 0.4:
            cat_choice = random.choice(["Supermercado", "Restaurantes", "Uber", "Luz & Água", "Cinema"])
            amount = round(random.uniform(15.0, 150.0), 2)
            t = Transaction(date=current_date, description=f"Compra {cat_choice}", amount=amount, account_id=acc_banco.id, transaction_type_id=t_expense.id, sub_category_id=subcats_map[cat_choice].id)
            acc_banco.current_balance -= amount
            db.add(t)

        # Investimentos
        if random.random() < 0.1:
            acc_corretora.current_balance += 500
            
            price = 100.00 
            qty = 2
            cost = price * qty
            
            t = Transaction(
                date=current_date, description="Compra VWCE", amount=cost, 
                account_id=acc_corretora.id, transaction_type_id=t_buy.id, 
                asset_id=asset_objs["VWCE"].id, quantity=qty, price_per_unit=price
            )
            acc_corretora.current_balance -= cost
            db.add(t)
            
            h = db.query(Holding).filter(Holding.account_id==acc_corretora.id, Holding.asset_id==asset_objs["VWCE"].id).first()
            if not h:
                h = Holding(account_id=acc_corretora.id, asset_id=asset_objs["VWCE"].id, quantity=0, avg_buy_price=0)
                db.add(h)
            
            total_val = (h.quantity * h.avg_buy_price) + cost
            h.quantity += qty
            h.avg_buy_price = total_val / h.quantity

    db.commit()
    
    print(f"💰 Saldo Banco: {acc_banco.current_balance:.2f}€")
    print(f"📈 Saldo Corretora: {acc_corretora.current_balance:.2f}€")
    print("✅ Seed concluído com sucesso!")
    db.close()

if __name__ == "__main__":
    create_dummy_data()