from sqlalchemy import Column, Integer, String, Float, ForeignKey, Date, Boolean
from sqlalchemy.orm import relationship
from .base import Base

class TransactionType(Base):
    __tablename__ = "transaction_types"
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, unique=True)
    is_investment = Column(Boolean, default=False)

class Category(Base):
    __tablename__ = "categories"
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"))
    name = Column(String)
    
    user = relationship("User", back_populates="categories")
    subcategories = relationship("SubCategory", back_populates="category", cascade="all, delete-orphan")

class SubCategory(Base):
    __tablename__ = "subcategories"
    id = Column(Integer, primary_key=True, index=True)
    category_id = Column(Integer, ForeignKey("categories.id"))
    name = Column(String)

    category = relationship("Category", back_populates="subcategories")
    
    # --- NOVO: Relação inversa para sabermos as transações desta subcategoria ---
    transactions = relationship("Transaction", back_populates="subcategory") 

class Transaction(Base):
    __tablename__ = "transactions"

    id = Column(Integer, primary_key=True, index=True)
    date = Column(Date)
    description = Column(String)
    amount = Column(Float)
    
    account_id = Column(Integer, ForeignKey("accounts.id"))
    transaction_type_id = Column(Integer, ForeignKey("transaction_types.id"))
    subcategory_id = Column(Integer, ForeignKey("subcategories.id"), nullable=True)

    account = relationship("Account", back_populates="transactions")
    transaction_type = relationship("TransactionType")
    
    # --- ATUALIZADO: Adicionado back_populates ---
    subcategory = relationship("SubCategory", back_populates="transactions")