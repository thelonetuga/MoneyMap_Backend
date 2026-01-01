from sqlalchemy import text
from sqlalchemy.orm import Session
from app.database.database import Base, SessionLocal, engine
from app.models import User, Account, Transaction, Category, SubCategory, UserProfile, AccountType, TransactionType
from app.auth import get_password_hash

# 1. Garantir que as tabelas existem (serão recriadas após o drop)
# Nota: O create_all só cria se não existirem, por isso fazemos drop manual primeiro
Base.metadata.create_all(bind=engine)

def seed_data():
    db: Session = SessionLocal()
    
    print("🌱 A iniciar a Seed...")

    # ---------------------------------------------------------
    # 2. NUCLEAR CLEANUP (Resolver tabelas fantasma) ☢️
    # ---------------------------------------------------------
    # Vamos forçar a remoção de tabelas antigas que possam estar a causar conflitos
    # O CASCADE garante que removemos as constraints de Foreign Key
    print("🧹 A executar limpeza profunda...")
    try:
        # Tenta apagar tabelas antigas (com underscore) e novas
        statements = [
            "DROP TABLE IF EXISTS sub_categories CASCADE",  # A culpada!
            "DROP TABLE IF EXISTS subcategories CASCADE",
            "DROP TABLE IF EXISTS transactions CASCADE",
            "DROP TABLE IF EXISTS holdings CASCADE",
            "DROP TABLE IF EXISTS asset_prices CASCADE",
            "DROP TABLE IF EXISTS assets CASCADE",
            "DROP TABLE IF EXISTS categories CASCADE",
            "DROP TABLE IF EXISTS user_profiles CASCADE",
            "DROP TABLE IF EXISTS accounts CASCADE",
            "DROP TABLE IF EXISTS users CASCADE",
            "DROP TABLE IF EXISTS transaction_types CASCADE",
            "DROP TABLE IF EXISTS account_types CASCADE",
            "DROP TABLE IF EXISTS alembic_version CASCADE" # Se usares alembic
        ]
        
        for statement in statements:
            db.execute(text(statement))
        
        db.commit()
        print("   ✅ Tabelas removidas com sucesso.")
        
    except Exception as e:
        print(f"   ⚠️ Aviso na limpeza (pode ser ignorado se for a 1ª vez): {e}")
        db.rollback()

    # ---------------------------------------------------------
    # 3. RECRIAR TABELAS (Schema Limpo)
    # ---------------------------------------------------------
    print("🏗️  A recriar tabelas...")
    Base.metadata.create_all(bind=engine)

    # ---------------------------------------------------------
    # 4. DADOS ESTÁTICOS
    # ---------------------------------------------------------
    acc_types = [
        AccountType(id=1, name="Conta à Ordem"), 
        AccountType(id=2, name="Investimento"),
        AccountType(id=3, name="Poupança"),
        AccountType(id=4, name="Crypto Wallet")
    ]
    db.add_all(acc_types)
    
    tx_types = [
        TransactionType(id=1, name="Despesa", is_investment=False), 
        TransactionType(id=2, name="Receita", is_investment=False),
        TransactionType(id=3, name="Compra Ativo", is_investment=True),
        TransactionType(id=4, name="Venda Ativo", is_investment=True)
    ]
    db.add_all(tx_types)
    db.commit()

    # ---------------------------------------------------------
    # 5. UTILIZADORES E PERFIS
    # ---------------------------------------------------------
    common_password = get_password_hash("123") 
    
    users_data = [
        {
            "email": "basic@moneymap.com", 
            "role": "basic", 
            "first_name": "Zé", 
            "last_name": "Básico",
            "currency": "EUR"
        },
        {
            "email": "premium@moneymap.com", 
            "role": "premium", 
            "first_name": "Ana", 
            "last_name": "Premium",
            "currency": "USD"
        },
        {
            "email": "admin@moneymap.com", 
            "role": "admin", 
            "first_name": "Admin", 
            "last_name": "Supremo",
            "currency": "EUR"
        }
    ]

    for u_data in users_data:
        # A. Criar User
        user = User(
            email=u_data["email"], 
            password_hash=common_password, 
            role=u_data["role"]
        )
        db.add(user)
        db.commit()
        db.refresh(user)
        
        # B. Criar Perfil
        profile = UserProfile(
            user_id=user.id,
            first_name=u_data["first_name"],
            last_name=u_data["last_name"],
            preferred_currency=u_data["currency"]
        )
        db.add(profile)
        
        # C. Criar Contas
        acc1 = Account(
            user_id=user.id, 
            name=f"Banco {u_data['first_name']}", 
            account_type_id=1, 
            current_balance=1500.00
        )
        db.add(acc1)

        if u_data["role"] in ["premium", "admin"]:
            acc2 = Account(
                user_id=user.id, 
                name="Degiro / XTB", 
                account_type_id=2, 
                current_balance=5000.00
            )
            db.add(acc2)

        # D. Criar Categorias
        cat_casa = Category(user_id=user.id, name="Casa")
        cat_lazer = Category(user_id=user.id, name="Lazer")
        db.add(cat_casa)
        db.add(cat_lazer)
        db.commit()

        # Subcategorias
        db.add(SubCategory(category_id=cat_casa.id, name="Renda"))
        db.add(SubCategory(category_id=cat_casa.id, name="Supermercado"))
        db.add(SubCategory(category_id=cat_lazer.id, name="Restaurantes"))
        db.add(SubCategory(category_id=cat_lazer.id, name="Cinema"))

    db.commit()
    
    print("✅ Seed concluída com sucesso!")
    print("------------------------------------------------")
    print("🔑 Credenciais para Teste (Password: '123'):")
    print("   1. Basic:   basic@moneymap.com")
    print("   2. Premium: premium@moneymap.com")
    print("   3. Admin:   admin@moneymap.com")
    print("------------------------------------------------")
    
    db.close()

if __name__ == "__main__":
    seed_data()