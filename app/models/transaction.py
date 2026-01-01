from app.models.account import Account
from app.models.asset import Asset
from app.models.user import User
from .base import Base
from typing import List, Optional
from datetime import date as dt_date, datetime
from sqlalchemy import Column, Integer, String, Boolean, ForeignKey, Float, Date, DateTime
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship
from sqlalchemy.sql import func


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

    
class TransactionType(Base):
    """Ex: Despesa, Receita, Transferência, Compra (Asset), Venda (Asset)"""
    __tablename__ = "transaction_types"
    
    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    name: Mapped[str] = mapped_column(String, unique=True)
    is_investment: Mapped[bool] = mapped_column(Boolean, default=False) # Ajuda no frontend
    
    transactions: Mapped[List["Transaction"]] = relationship(back_populates="transaction_type")


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