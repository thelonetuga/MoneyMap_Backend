import random
from datetime import date, timedelta
from sqlalchemy.orm import Session
from database import SessionLocal, engine
from models import Base, User, Account, Category, Transaction, Asset, AssetPrice, Holding

# Função auxiliar para limpar dados antigos (opcional)
def clean_database(db: Session):
    print("🧹 A limpar dados antigos...")
    # A ordem importa devido às chaves estrangeiras
    db.query(Transaction).delete()
    db.query(Holding).delete()
    db.query(AssetPrice).delete()
    db.query(Account).delete()
    db.query(Category).delete()
    db.query(Asset).delete()
    db.query(User).delete()
    db.commit()

def create_dummy_data():
    db = SessionLocal()
    
    # 1. Limpar base de dados para não duplicar erros
    clean_database(db)

    print("🌱 A iniciar o povoamento (Seeding)...")

    # --- 2. CRIAR UTILIZADOR ---
    user = User(email="joao@email.com", password_hash="segredo123")
    db.add(user)
    db.commit()
    db.refresh(user)
    print(f"✅ Utilizador criado: {user.email}")

    # --- 3. CRIAR ATIVOS (ASSETS) ---
    assets_data = [
        {"symbol": "AAPL", "name": "Apple Inc.", "asset_type": "Stock", "currency": "USD"},
        {"symbol": "TSLA", "name": "Tesla Inc.", "asset_type": "Stock", "currency": "USD"},
        {"symbol": "BTC", "name": "Bitcoin", "asset_type": "Crypto", "currency": "USD"},
        {"symbol": "VWCE", "name": "Vanguard All-World", "asset_type": "ETF", "currency": "EUR"},
    ]
    
    assets_objs = []
    for asset in assets_data:
        new_asset = Asset(
            symbol=asset["symbol"],
            name=asset["name"],
            asset_type=asset["asset_type"],
            currency_code=asset["currency"]
        )
        db.add(new_asset)
        assets_objs.append(new_asset)
    
    db.commit()
    # Recarregar para ter os IDs
    for a in assets_objs: db.refresh(a)
    print(f"✅ {len(assets_objs)} Ativos financeiros criados.")

    # --- 4. CRIAR HISTÓRICO DE PREÇOS (30 DIAS) ---
    print("📈 A gerar histórico de preços...")
    for asset in assets_objs:
        base_price = random.uniform(100, 500)
        if asset.symbol == "BTC": base_price = 45000
        
        for i in range(30):
            # Preço flutua +/- 2% ao dia
            base_price = base_price * random.uniform(0.98, 1.02) 
            price_entry = AssetPrice(
                date=date.today() - timedelta(days=30-i),
                close_price=round(base_price, 2),
                asset_id=asset.id
            )
            db.add(price_entry)
    db.commit()

    # --- 5. CRIAR CONTAS ---
    acc_bank = Account(name="Millennium BCP", type="Bank", currency_code="EUR", current_balance=2500.00, user_id=user.id)
    acc_broker = Account(name="XTB Invest", type="Brokerage", currency_code="EUR", current_balance=10000.00, user_id=user.id)
    
    db.add(acc_bank)
    db.add(acc_broker)
    db.commit()
    db.refresh(acc_bank)
    db.refresh(acc_broker)
    print("✅ Contas bancárias criadas.")

    # --- 6. CRIAR CATEGORIAS ---
    cats = [
        Category(name="Salário", type="Income", user_id=user.id),
        Category(name="Supermercado", type="Expense", user_id=user.id),
        Category(name="Renda", type="Expense", user_id=user.id),
        Category(name="Restaurantes", type="Expense", user_id=user.id),
        Category(name="Investimentos", type="Expense", user_id=user.id), # Saída de dinheiro para investir
    ]
    db.add_all(cats)
    db.commit()
    cat_salary = cats[0]
    cat_groceries = cats[1]
    
    # --- 7. CRIAR TRANSAÇÕES (MÊS CORRENTE) ---
    print("💸 A gerar transações...")
    
    # 7.1 Receber Salário
    t1 = Transaction(
        date=date.today().replace(day=1),
        description="Ordenado Google",
        transaction_type="DEPOSIT",
        amount=3000.00,
        account_id=acc_bank.id,
        category_id=cat_salary.id
    )
    
    # 7.2 Gastos Diversos
    t2 = Transaction(
        date=date.today().replace(day=5),
        description="Continente",
        transaction_type="WITHDRAW",
        amount=150.50,
        account_id=acc_bank.id,
        category_id=cat_groceries.id
    )

    # 7.3 Compra de Ações (INVESTIMENTO)
    # Compra 10 Ações da Apple a 150€
    stock_to_buy = assets_objs[0] # Apple
    qty = 10
    price = 150.00
    total_cost = qty * price
    
    t3 = Transaction(
        date=date.today(),
        description=f"Compra {stock_to_buy.symbol}",
        transaction_type="BUY",
        amount=total_cost,
        account_id=acc_broker.id,
        asset_id=stock_to_buy.id,
        price_per_unit=price,
        quantity=qty
    )
    
    # Atualizar saldo da corretora
    acc_broker.current_balance -= total_cost

    db.add_all([t1, t2, t3])
    db.commit()

    # --- 8. ATUALIZAR HOLDINGS (CARTEIRA) ---
    # Como comprámos Apple, temos de registar que as temos
    holding = Holding(
        account_id=acc_broker.id,
        asset_id=stock_to_buy.id,
        quantity=qty,
        avg_buy_price=price
    )
    db.add(holding)
    db.commit()

    print("🚀 Base de dados preenchida com sucesso!")
    db.close()

if __name__ == "__main__":
    create_dummy_data()