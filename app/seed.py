import random
from datetime import date, timedelta
from sqlalchemy.orm import Session
from app.db.database import SessionLocal, engine
from app.model.models import (
    Base, User, UserProfile, Account, AccountType, 
    Category, SubCategory, Transaction, TransactionType, 
    Asset, AssetPrice, Holding
)

def clean_database(db: Session):
    print("🧹 A limpar base de dados antiga...")
    # Ordem específica devido às Foreign Keys
    db.query(Transaction).delete()
    db.query(Holding).delete()
    db.query(AssetPrice).delete()
    db.query(SubCategory).delete()
    db.query(Category).delete()
    db.query(Account).delete()
    db.query(UserProfile).delete()
    db.query(User).delete()
    db.query(Asset).delete()
    db.query(AccountType).delete()
    db.query(TransactionType).delete()
    db.commit()

def create_dummy_data():
    db = SessionLocal()
    clean_database(db)
    print("🌱 A semear novos dados...")

    # --- 1. LOOKUPS (TIPOS) ---
    # Tipos de Conta
    acc_types = [
        AccountType(name="Conta à Ordem"),    # ID 1
        AccountType(name="Poupança"),         # ID 2
        AccountType(name="Corretora"),        # ID 3
        AccountType(name="Wallet Crypto")     # ID 4
    ]
    db.add_all(acc_types)
    
    # Tipos de Transação
    tx_types = [
        TransactionType(name="Despesa", is_investment=False),           # ID 1
        TransactionType(name="Receita", is_investment=False),           # ID 2
        TransactionType(name="Compra Investimento", is_investment=True), # ID 3
        TransactionType(name="Venda Investimento", is_investment=True)   # ID 4
    ]
    db.add_all(tx_types)
    db.commit()

    # Recarregar para ter acesso aos IDs
    type_expense = tx_types[0]
    type_income = tx_types[1]
    type_buy = tx_types[2]

    # --- 2. USER & PROFILE ---
    user = User(email="joao@email.com", password_hash="hash123")
    db.add(user)
    db.commit()
    
    profile = UserProfile(
        user_id=user.id, 
        first_name="João", 
        last_name="Silva", 
        preferred_currency="EUR"
    )
    db.add(profile)
    db.commit()
    print("✅ User João Silva criado.")

    # --- 3. CATEGORIAS & SUBCATEGORIAS ---
    categories_data = {
        "Casa": ["Renda", "Eletricidade", "Internet", "Manutenção"],
        "Alimentação": ["Supermercado", "Restaurantes", "Café"],
        "Transporte": ["Combustível", "Uber", "Passe"],
        "Lazer": ["Streaming", "Cinema", "Viagens", "Jogos"],
        "Rendimento": ["Salário", "Freelance", "Dividendos"]
    }

    subcat_objs = {} # Para usar nas transações (ex: "Supermercado": obj)

    for cat_name, subs in categories_data.items():
        cat = Category(name=cat_name, user_id=user.id)
        db.add(cat)
        db.commit()
        
        for sub_name in subs:
            sub = SubCategory(name=sub_name, category_id=cat.id)
            db.add(sub)
            subcat_objs[sub_name] = sub
    
    db.commit()
    print("✅ Categorias configuradas.")

    # --- 4. ATIVOS E PREÇOS (60 DIAS) ---
    assets_data = [
        ("AAPL", "Apple Inc.", "Stock", 180.00),
        ("NVDA", "NVIDIA Corp", "Stock", 450.00),
        ("VWCE", "Vanguard All-World", "ETF", 105.00),
        ("BTC", "Bitcoin", "Crypto", 42000.00),
        ("ETH", "Ethereum", "Crypto", 2300.00),
    ]

    assets_map = {}

    for symbol, name, atype, base_price in assets_data:
        asset = Asset(symbol=symbol, name=name, asset_type=atype)
        db.add(asset)
        db.commit() # Commit para gerar ID
        assets_map[symbol] = asset

        # Gerar histórico
        curr_price = base_price
        for i in range(60, -1, -1): # Do passado para hoje
            # Random Walk: Preço varia entre -2% e +2%
            change = random.uniform(0.98, 1.02)
            curr_price = curr_price * change
            
            price_entry = AssetPrice(
                asset_id=asset.id,
                date=date.today() - timedelta(days=i),
                close_price=round(curr_price, 2)
            )
            db.add(price_entry)
    
    db.commit()
    print("✅ Mercado financeiro simulado.")

    # --- 5. CONTAS ---
    # Vamos começar com saldos "iniciais" fictícios
    acc_bank = Account(name="Millennium BCP", current_balance=500.00, currency_code="EUR", user_id=user.id, account_type_id=1)
    acc_broker = Account(name="Trade Republic", current_balance=2000.00, currency_code="EUR", user_id=user.id, account_type_id=3)
    acc_crypto = Account(name="Binance", current_balance=500.00, currency_code="EUR", user_id=user.id, account_type_id=4)
    
    db.add_all([acc_bank, acc_broker, acc_crypto])
    db.commit()

    # --- 6. TRANSAÇÕES (SIMULAÇÃO DE VIDA) ---
    # Gerar dados para os últimos 2 meses
    
    start_date = date.today() - timedelta(days=60)
    
    # 6.1 Transações Recorrentes (Salário e Renda)
    for i in range(3): # 3 meses (aprox)
        month_date = start_date + timedelta(days=i*30)
        
        # Receber Salário (Dia 1)
        tx_salary = Transaction(
            date=month_date,
            description="Salário Google",
            amount=2500.00,
            account_id=acc_bank.id,
            transaction_type_id=type_income.id,
            sub_category_id=subcat_objs["Salário"].id
        )
        acc_bank.current_balance += 2500.00
        db.add(tx_salary)

        # Pagar Renda (Dia 2)
        tx_rent = Transaction(
            date=month_date + timedelta(days=1),
            description="Senhorio",
            amount=850.00,
            account_id=acc_bank.id,
            transaction_type_id=type_expense.id,
            sub_category_id=subcat_objs["Renda"].id
        )
        acc_bank.current_balance -= 850.00
        db.add(tx_rent)

    # 6.2 Transações Aleatórias (Cafés, Supermercado, Uber)
    for _ in range(40): # 40 transações aleatórias
        random_days = random.randint(0, 60)
        tx_date = date.today() - timedelta(days=random_days)
        
        choices = [
            ("Supermercado", 40.0, 150.0, "Continente"),
            ("Restaurantes", 15.0, 60.0, "Jantar Fora"),
            ("Café", 2.0, 5.0, "Starbucks"),
            ("Uber", 5.0, 15.0, "Uber Trip"),
            ("Streaming", 9.99, 14.99, "Netflix/Spotify"),
        ]
        cat_name, min_val, max_val, desc = random.choice(choices)
        amount = round(random.uniform(min_val, max_val), 2)
        
        tx = Transaction(
            date=tx_date,
            description=desc,
            amount=amount,
            account_id=acc_bank.id,
            transaction_type_id=type_expense.id,
            sub_category_id=subcat_objs[cat_name].id
        )
        acc_bank.current_balance -= amount
        db.add(tx)

    # 6.3 Investimentos (Compras)
    # Compra 1: VWCE há 45 dias
    price_vwce = 100.00
    qty_vwce = 10
    cost_vwce = price_vwce * qty_vwce
    
    tx_inv1 = Transaction(
        date=date.today() - timedelta(days=45),
        description="Compra VWCE Mensal",
        amount=cost_vwce,
        account_id=acc_broker.id,
        transaction_type_id=type_buy.id,
        asset_id=assets_map["VWCE"].id,
        quantity=qty_vwce,
        price_per_unit=price_vwce
    )
    acc_broker.current_balance -= cost_vwce
    
    # Holding para VWCE
    h1 = Holding(account_id=acc_broker.id, asset_id=assets_map["VWCE"].id, quantity=qty_vwce, avg_buy_price=price_vwce)

    # Compra 2: Bitcoin há 10 dias
    price_btc = 40000.00
    qty_btc = 0.05
    cost_btc = price_btc * qty_btc
    
    tx_inv2 = Transaction(
        date=date.today() - timedelta(days=10),
        description="Buy the dip BTC",
        amount=cost_btc,
        account_id=acc_crypto.id,
        transaction_type_id=type_buy.id,
        asset_id=assets_map["BTC"].id,
        quantity=qty_btc,
        price_per_unit=price_btc
    )
    acc_crypto.current_balance -= cost_btc
    
    # Holding para BTC
    h2 = Holding(account_id=acc_crypto.id, asset_id=assets_map["BTC"].id, quantity=qty_btc, avg_buy_price=price_btc)

    db.add_all([tx_inv1, tx_inv2, h1, h2])
    db.commit()

    print(f"💰 Saldo final Banco: {acc_bank.current_balance:.2f} €")
    print(f"📈 Saldo final Corretora: {acc_broker.current_balance:.2f} €")
    print("🚀 Seed concluído com sucesso!")

    db.close()

if __name__ == "__main__":
    create_dummy_data()