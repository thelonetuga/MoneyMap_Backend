from __future__ import annotations # Importante para lidar com referências futuras de classes
from sqlalchemy import String, Float, ForeignKey, Date, Integer
from sqlalchemy.orm import relationship, Mapped, mapped_column, DeclarativeBase
from datetime import date, datetime
from typing import List, Optional
from .database import Base as DBBase # Importamos o Base antigo apenas para manter compatibilidade de ligação

# Para o Pylance ficar feliz com o Base, às vezes é preciso redefinir, 
# mas vamos usar a sintaxe Type Annotated nas colunas que é o mais importante.

class Account(DBBase):
    """
    Representa uma conta bancária ou corretora.
    """
    __tablename__ = "accounts"

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    name: Mapped[str] = mapped_column(String, unique=True, index=True)
    type: Mapped[str] = mapped_column(String)  # 'Bank', 'Investment', 'Crypto'
    current_balance: Mapped[float] = mapped_column(Float, default=0.0)
    
    # Relações: Usamos List["NomeClasse"] para o Pylance entender
    transactions: Mapped[List["Transaction"]] = relationship(back_populates="account")
    holdings: Mapped[List["Holding"]] = relationship(back_populates="account")

class Category(DBBase):
    __tablename__ = "categories"

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    name: Mapped[str] = mapped_column(String, unique=True)
    
    transactions: Mapped[List["Transaction"]] = relationship(back_populates="category")

class Transaction(DBBase):
    __tablename__ = "transactions"

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    amount: Mapped[float] = mapped_column(Float)
    description: Mapped[str] = mapped_column(String)
    date: Mapped[date] = mapped_column(Date, default=datetime.now)
    
    # Foreign Keys
    account_id: Mapped[int] = mapped_column(ForeignKey("accounts.id"))
    # Optional[int] significa que pode ser Null na base de dados (nullable=True)
    category_id: Mapped[Optional[int]] = mapped_column(ForeignKey("categories.id"), nullable=True)

    account: Mapped["Account"] = relationship(back_populates="transactions")
    category: Mapped[Optional["Category"]] = relationship(back_populates="transactions")

class Asset(DBBase):
    __tablename__ = "assets"

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    symbol: Mapped[str] = mapped_column(String, unique=True, index=True)
    name: Mapped[str] = mapped_column(String)
    asset_type: Mapped[str] = mapped_column(String)
    
    holdings: Mapped[List["Holding"]] = relationship(back_populates="asset")

class Holding(DBBase):
    __tablename__ = "holdings"

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    quantity: Mapped[float] = mapped_column(Float)
    avg_buy_price: Mapped[float] = mapped_column(Float)
    
    account_id: Mapped[int] = mapped_column(ForeignKey("accounts.id"))
    asset_id: Mapped[int] = mapped_column(ForeignKey("assets.id"))

    account: Mapped["Account"] = relationship(back_populates="holdings")
    asset: Mapped["Asset"] = relationship(back_populates="holdings")