from sqlalchemy.orm import Session
from app.database.database import Base, SessionLocal, engine
from app.auth import get_password_hash
from app.models import Transaction, Account, User , UserProfile,Category, SubCategory, TransactionType,AssetPrice, Holding,Account, AccountType


# 1. Garantir que as tabelas existem na BD
Base.metadata.create_all(bind=engine)

def seed_data():
    db: Session = SessionLocal()
    
    print("🌱 A iniciar a Seed...")

    # ---------------------------------------------------------
    # 2. LIMPEZA (ORDEM CORRIGIDA 🛠️)
    # ---------------------------------------------------------
    # Primeiro apagamos tudo o que depende de outras tabelas
    db.query(Transaction).delete()    # Depende de Account e SubCategory
    db.query(Holding).delete()        # Depende de Account e Asset
    db.query(AssetPrice).delete()     # Depende de Asset (se tiveres esta tabela)
    db.query(SubCategory).delete()    # Depende de Category
    
    # Agora podemos apagar as Categorias (que dependem do User)
    db.query(Category).delete()       
    
    # Agora as Contas (que dependem do User)
    db.query(Account).delete()
    
    # Perfis (que dependem do User)
    db.query(UserProfile).delete()
    
    # FINALMENTE, podemos apagar os Users (agora que não têm dependências)
    db.query(User).delete()
    
    # Tipos estáticos
    db.query(TransactionType).delete()
    db.query(AccountType).delete()
    
    db.commit()
    print("🧹 Base de dados limpa com sucesso.")

    # ---------------------------------------------------------
    # 3. DADOS ESTÁTICOS
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
    # 4. UTILIZADORES E PERFIS (RBAC)
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
        db.commit() # Commit para gerar user.id
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

        # D. Criar Categorias Padrão
        cat_casa = Category(user_id=user.id, name="Casa")
        cat_lazer = Category(user_id=user.id, name="Lazer")
        db.add(cat_casa)
        db.add(cat_lazer)
        db.commit() # Gerar IDs das categorias

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