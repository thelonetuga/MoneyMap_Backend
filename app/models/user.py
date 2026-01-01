from sqlalchemy import Column, Integer, String, DateTime, ForeignKey
from sqlalchemy.orm import relationship
from datetime import datetime
from .base import Base

class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    email = Column(String, unique=True, index=True)
    password_hash = Column(String)
    role = Column(String, default="basic")
    created_at = Column(DateTime, default=datetime.utcnow)

    # Strings mágicas novamente
    accounts = relationship("Account", back_populates="user")
    profile = relationship("UserProfile", back_populates="user", uselist=False)
    categories = relationship("Category", back_populates="user")

class UserProfile(Base):
    __tablename__ = "user_profiles"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), unique=True)
    first_name = Column(String, nullable=True)
    last_name = Column(String, nullable=True)
    preferred_currency = Column(String, default="EUR")
    avatar_url = Column(String, nullable=True)

    user = relationship("User", back_populates="profile")