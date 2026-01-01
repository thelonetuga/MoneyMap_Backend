from app.models.asset import Holding
from app.models.user import User
from .base import Base
from typing import List, Optional
from datetime import date as dt_date, datetime
from sqlalchemy import Column, Integer, String, Boolean, ForeignKey, Float, Date, DateTime, Transaction
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship
from sqlalchemy.sql import func


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


class AccountType(Base):
    """Ex: Conta à Ordem, Poupança, Corretora, Wallet Crypto"""
    __tablename__ = "account_types"
    
    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    name: Mapped[str] = mapped_column(String, unique=True)
    
    accounts: Mapped[List["Account"]] = relationship(back_populates="account_type")

