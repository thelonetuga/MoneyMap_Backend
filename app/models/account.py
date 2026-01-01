from sqlalchemy import Column, Integer, String, Float, ForeignKey, DateTime
from sqlalchemy.orm import relationship
from datetime import datetime
from .base import Base

class AccountType(Base):
    __tablename__ = "account_types"
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, unique=True, index=True)
    
    # Relação inversa (opcional, mas boa prática)
    accounts = relationship("Account", back_populates="account_type")

class Account(Base):
    __tablename__ = "accounts"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, index=True)
    current_balance = Column(Float, default=0.0)
    
    # Foreign Keys
    user_id = Column(Integer, ForeignKey("users.id"))
    account_type_id = Column(Integer, ForeignKey("account_types.id"))

    # Relações com STRING para evitar circular import
    user = relationship("User", back_populates="accounts")
    account_type = relationship("AccountType", back_populates="accounts")
    transactions = relationship("Transaction", back_populates="account", cascade="all, delete-orphan")
    holdings = relationship("Holding", back_populates="account", cascade="all, delete-orphan")