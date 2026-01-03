from sqlalchemy import Column, Integer, String, Float, ForeignKey, Date, DateTime
from sqlalchemy.orm import relationship
from .base import Base

class Asset(Base):
    __tablename__ = "assets"
    id = Column(Integer, primary_key=True, index=True)
    symbol = Column(String, unique=True, index=True) # Ex: AAPL, BTC
    name = Column(String)
    asset_type = Column(String) # Stock, Crypto, ETF

    prices = relationship("AssetPrice", back_populates="asset")
    holdings = relationship("Holding", back_populates="asset")
    transactions = relationship("Transaction", back_populates="asset")

class AssetPrice(Base):
    __tablename__ = "asset_prices"
    id = Column(Integer, primary_key=True, index=True)
    asset_id = Column(Integer, ForeignKey("assets.id"))
    date = Column(Date)
    close_price = Column(Float)

    asset = relationship("Asset", back_populates="prices")

class Holding(Base):
    __tablename__ = "holdings"
    id = Column(Integer, primary_key=True, index=True)
    account_id = Column(Integer, ForeignKey("accounts.id"))
    asset_id = Column(Integer, ForeignKey("assets.id"))
    quantity = Column(Float)
    avg_buy_price = Column(Float)

    # Relação com String "Account"
    account = relationship("Account", back_populates="holdings")
    asset = relationship("Asset", back_populates="holdings")