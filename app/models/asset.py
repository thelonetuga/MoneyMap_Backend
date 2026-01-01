from app.models.account import Account
from app.models.transaction import Transaction
from .base import Base
from typing import List, Optional
from datetime import date as dt_date, datetime
from sqlalchemy import Column, Integer, String, Boolean, ForeignKey, Float, Date, DateTime
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship
from sqlalchemy.sql import func


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