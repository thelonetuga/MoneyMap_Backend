from typing import List, Optional
from datetime import date as dt_date, datetime
from sqlalchemy import String, Float, ForeignKey, Integer, Boolean, Text
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship
from sqlalchemy.sql import func

class Base(DeclarativeBase):
    pass

# --- 1. CONFIGURAÇÕES E TIPOS (Lookups) ---

class AccountType(Base):
    """Ex: Conta à Ordem, Poupança, Corretora, Wallet Crypto"""
    __tablename__ = "account_types"
    
    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    name: Mapped[str] = mapped_column(String, unique=True)
    
    accounts: Mapped[List["Account"]] = relationship(back_populates="account_type")

class TransactionType(Base):
    """Ex: Despesa, Receita, Transferência, Compra (Asset), Venda (Asset)"""
    __tablename__ = "transaction_types"
    
    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    name: Mapped[str] = mapped_column(String, unique=True)
    is_investment: Mapped[bool] = mapped_column(Boolean, default=False) # Ajuda no frontend
    
    transactions: Mapped[List["Transaction"]] = relationship(back_populates="transaction_type")


# --- 2. UTILIZADOR E PERFIL ---

class User(Base):
    __tablename__ = "users"

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    email: Mapped[str] = mapped_column(String, unique=True, index=True)
    password_hash: Mapped[str] = mapped_column(String)
    created_at: Mapped[datetime] = mapped_column(server_default=func.now())

    # Relações
    profile: Mapped["UserProfile"] = relationship(back_populates="user", uselist=False, cascade="all, delete-orphan")
    accounts: Mapped[List["Account"]] = relationship(back_populates="user", cascade="all, delete-orphan")
    categories: Mapped[List["Category"]] = relationship(back_populates="user")

class UserProfile(Base):
    __tablename__ = "user_profiles"

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), unique=True)
    
    first_name: Mapped[Optional[str]] = mapped_column(String, nullable=True)
    last_name: Mapped[Optional[str]] = mapped_column(String, nullable=True)
    preferred_currency: Mapped[str] = mapped_column(String, default="EUR")
    
    user: Mapped["User"] = relationship(back_populates="profile")


# --- 3. CATEGORIZAÇÃO ---

class Category(Base):
    __tablename__ = "categories"

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    name: Mapped[str] = mapped_column(String)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id")) # Categorias personalizadas por user
    
    user: Mapped["User"] = relationship(back_populates="categories")
    sub_categories: Mapped[List["SubCategory"]] = relationship(back_populates="category", cascade="all, delete-orphan")

class SubCategory(Base):
    __tablename__ = "sub_categories"

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    name: Mapped[str] = mapped_column(String)
    category_id: Mapped[int] = mapped_column(ForeignKey("categories.id"))
    
    category: Mapped["Category"] = relationship(back_populates="sub_categories")
    transactions: Mapped[List["Transaction"]] = relationship(back_populates="sub_category")


# --- 4. CONTAS E ATIVOS ---

class Account(Base):
    __tablename__ = "accounts"

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    name: Mapped[str] = mapped_column(String)
    current_balance: Mapped[float] = mapped_column(Float, default=0.0)
    currency_code: Mapped[str] = mapped_column(String, default="EUR")
    
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"))
    account_type_id: Mapped[int] = mapped_column(ForeignKey("account_types.id"))

    user: Mapped["User"] = relationship(back_populates="accounts")
    account_type: Mapped["AccountType"] = relationship(back_populates="accounts")
    transactions: Mapped[List["Transaction"]] = relationship(back_populates="account")
    holdings: Mapped[List["Holding"]] = relationship(back_populates="account")

class Asset(Base):
    __tablename__ = "assets"

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    symbol: Mapped[str] = mapped_column(String, unique=True, index=True) # AAPL, BTC
    name: Mapped[str] = mapped_column(String)
    asset_type: Mapped[str] = mapped_column(String) # Stock, ETF, Crypto
    
    prices: Mapped[List["AssetPrice"]] = relationship(back_populates="asset")
    holdings: Mapped[List["Holding"]] = relationship(back_populates="asset")
    transactions: Mapped[List["Transaction"]] = relationship(back_populates="asset")

class AssetPrice(Base):
    __tablename__ = "asset_prices"

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    asset_id: Mapped[int] = mapped_column(ForeignKey("assets.id"))
    date: Mapped[dt_date] = mapped_column(index=True)
    close_price: Mapped[float] = mapped_column(Float)
    
    asset: Mapped["Asset"] = relationship(back_populates="prices")


# --- 5. O CERNE (TRANSAÇÕES E HOLDINGS) ---

class Holding(Base):
    """Representa o que possuo AGORA numa conta específica"""
    __tablename__ = "holdings"

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    account_id: Mapped[int] = mapped_column(ForeignKey("accounts.id"))
    asset_id: Mapped[int] = mapped_column(ForeignKey("assets.id"))
    
    quantity: Mapped[float] = mapped_column(Float, default=0.0)
    avg_buy_price: Mapped[float] = mapped_column(Float, default=0.0)

    account: Mapped["Account"] = relationship(back_populates="holdings")
    asset: Mapped["Asset"] = relationship(back_populates="holdings")

class Transaction(Base):
    """
    Tabela híbrida:
    - Se for supermercado: usa account_id, amount, sub_category_id.
    - Se for investimento: usa também asset_id, quantity, price_per_unit.
    """
    __tablename__ = "transactions"

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    date: Mapped[dt_date] = mapped_column(index=True)
    description: Mapped[str] = mapped_column(String)
    amount: Mapped[float] = mapped_column(Float) # Valor total monetário (sempre preenchido)
    
    # Chaves Estrangeiras Obrigatórias
    account_id: Mapped[int] = mapped_column(ForeignKey("accounts.id"))
    transaction_type_id: Mapped[int] = mapped_column(ForeignKey("transaction_types.id"))

    # Chaves Estrangeiras Opcionais
    sub_category_id: Mapped[Optional[int]] = mapped_column(ForeignKey("sub_categories.id"), nullable=True)
    asset_id: Mapped[Optional[int]] = mapped_column(ForeignKey("assets.id"), nullable=True)
    
    # Campos de Investimento Opcionais
    quantity: Mapped[Optional[float]] = mapped_column(Float, nullable=True)      # Quantas ações comprei?
    price_per_unit: Mapped[Optional[float]] = mapped_column(Float, nullable=True) # A que preço estava?

    # Relações
    account: Mapped["Account"] = relationship(back_populates="transactions")
    transaction_type: Mapped["TransactionType"] = relationship(back_populates="transactions")
    sub_category: Mapped[Optional["SubCategory"]] = relationship(back_populates="transactions")
    asset: Mapped[Optional["Asset"]] = relationship(back_populates="transactions")