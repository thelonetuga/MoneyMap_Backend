from pydantic import BaseModel
from datetime import date
from typing import Optional, List

# --- Account Schemas ---
class AccountBase(BaseModel):
    name: str
    type: str
    current_balance: float

class AccountCreate(AccountBase):
    pass

class AccountResponse(AccountBase):
    id: int
    class Config:
        from_attributes = True

# --- Transaction Schemas ---
class TransactionCreate(BaseModel):
    amount: float
    description: str
    account_id: int
    category_id: Optional[int] = None
    date: date

class TransactionResponse(TransactionCreate):
    id: int
    class Config:
        from_attributes = True

# --- Asset Schemas ---
class AssetCreate(BaseModel):
    symbol: str
    name: str
    asset_type: str

class AssetResponse(AssetCreate):
    id: int
    class Config:
        from_attributes = True

# --- Holding Schemas ---
class HoldingCreate(BaseModel):
    account_id: int
    asset_id: int
    quantity: float
    avg_buy_price: float

class HoldingResponse(HoldingCreate):
    id: int
    asset_symbol: str
    current_price: Optional[float] = None
    total_value: Optional[float] = None
    
    class Config:
        from_attributes = True

# --- Portfolio Summary Schema ---
class PortfolioPosition(BaseModel):
    symbol: str
    quantity: float
    avg_buy_price: float
    current_price: float
    total_value: float
    profit_loss: float

class PortfolioResponse(BaseModel):
    account_id: int
    total_portfolio_value: float
    positions: List[PortfolioPosition]