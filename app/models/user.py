from app.models.account import Account
from app.models.transaction import Category
from .base import Base
from typing import List, Optional
from datetime import date as dt_date, datetime
from sqlalchemy import Column, Integer, String, Boolean, ForeignKey, Float, Date, DateTime
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship
from sqlalchemy.sql import func

class User(Base):
    __tablename__ = "users"

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    email: Mapped[str] = mapped_column(String, unique=True, index=True)
    password_hash: Mapped[str] = mapped_column(String)
    # Valores esperados: "basic", "premium", "admin"
    role = Column(String, default="basic")
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