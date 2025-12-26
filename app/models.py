from typing import List, Optional
from datetime import date as dt_date, datetime
from sqlalchemy import String, Float, ForeignKey, Integer
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship
from sqlalchemy.sql import func

# 1. Nova forma de declarar a Base (Type Annotated)
class Base(DeclarativeBase):
    pass

# --- Tabela de Utilizadores ---
class User(Base):
    __tablename__ = "users"

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    email: Mapped[str] = mapped_column(String, unique=True, index=True)
    password_hash: Mapped[str] = mapped_column(String)
    # 'func.now()' deixa a base de dados gerir a data, é mais seguro que datetime.utcnow
    created_at: Mapped[datetime] = mapped_column(server_default=func.now())

    # Relações (Note o uso de List[...] para "muitos")
    accounts: Mapped[List["Account"]] = relationship(back_populates="user")
    categories: Mapped[List["Category"]] = relationship(back_populates="user")


# --- Tabela de Contas ---
class Account(Base):
    __tablename__ = "accounts"

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    name: Mapped[str] = mapped_column(String, index=True)
    type: Mapped[str] = mapped_column(String)  # Bank, Brokerage
    currency_code: Mapped[str] = mapped_column(String, default="EUR")
    current_balance: Mapped[float] = mapped_column(Float, default=0.0)
    
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"))

    # Relações
    user: Mapped["User"] = relationship(back_populates="accounts")
    transactions: Mapped[List["Transaction"]] = relationship(back_populates="account")
    holdings: Mapped[List["Holding"]] = relationship(back_populates="account")


# --- Tabela de Categorias ---
class Category(Base):
    __tablename__ = "categories"

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    name: Mapped[str] = mapped_column(String, index=True)
    type: Mapped[str] = mapped_column(String) # Expense, Income
    
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"))

    user: Mapped["User"] = relationship(back_populates="categories")
    transactions: Mapped[List["Transaction"]] = relationship(back_populates="category")


# --- Tabela de Ativos (Global) ---
class Asset(Base):
    __tablename__ = "assets"

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    symbol: Mapped[str] = mapped_column(String, unique=True, index=True)
    name: Mapped[str] = mapped_column(String)
    asset_type: Mapped[str] = mapped_column(String)
    currency_code: Mapped[str] = mapped_column(String, default="USD")

    holdings: Mapped[List["Holding"]] = relationship(back_populates="asset")
    prices: Mapped[List["AssetPrice"]] = relationship(back_populates="asset")
    transactions: Mapped[List["Transaction"]] = relationship(back_populates="asset")


# --- Histórico de Preços ---
class AssetPrice(Base):
    __tablename__ = "asset_prices"

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    date: Mapped[dt_date] = mapped_column(index=True)
    close_price: Mapped[float] = mapped_column(Float)
    
    asset_id: Mapped[int] = mapped_column(ForeignKey("assets.id"))

    asset: Mapped["Asset"] = relationship(back_populates="prices")


# --- Holdings (Carteira) ---
class Holding(Base):
    __tablename__ = "holdings"

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    quantity: Mapped[float] = mapped_column(Float, default=0.0)
    avg_buy_price: Mapped[float] = mapped_column(Float, default=0.0)

    account_id: Mapped[int] = mapped_column(ForeignKey("accounts.id"))
    asset_id: Mapped[int] = mapped_column(ForeignKey("assets.id"))

    account: Mapped["Account"] = relationship(back_populates="holdings")
    asset: Mapped["Asset"] = relationship(back_populates="holdings")


# --- Transações ---
class Transaction(Base):
    __tablename__ = "transactions"

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    date: Mapped[dt_date] = mapped_column()
    description: Mapped[str] = mapped_column(String)
    transaction_type: Mapped[str] = mapped_column(String) # BUY, SELL, DEPOSIT
    
    amount: Mapped[float] = mapped_column(Float)
    
    # Campos Opcionais (Investimento) - Note o uso de Optional[...]
    price_per_unit: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    quantity: Mapped[Optional[float]] = mapped_column(Float, nullable=True)

    # Foreign Keys
    account_id: Mapped[int] = mapped_column(ForeignKey("accounts.id"))
    
    # Campos Opcionais (Foreign Keys)
    category_id: Mapped[Optional[int]] = mapped_column(ForeignKey("categories.id"), nullable=True)
    asset_id: Mapped[Optional[int]] = mapped_column(ForeignKey("assets.id"), nullable=True)

    # Relações
    account: Mapped["Account"] = relationship(back_populates="transactions")
    # Para relações opcionais, usamos Optional["Classe"]
    category: Mapped[Optional["Category"]] = relationship(back_populates="transactions")
    asset: Mapped[Optional["Asset"]] = relationship(back_populates="transactions")