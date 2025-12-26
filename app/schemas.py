from pydantic import BaseModel
from datetime import date, datetime
from typing import Optional, List

# --- USER SCHEMAS (Novo) ---
class UserBase(BaseModel):
    email: str

class UserCreate(UserBase):
    password: str  # A password é necessária para criar...

class UserResponse(UserBase):
    id: int
    created_at: datetime
    # ...mas nunca devolvemos a password na resposta!

    class Config:
        from_attributes = True


# --- ACCOUNT SCHEMAS ---
class AccountBase(BaseModel):
    name: str
    type: str
    currency_code: str = "EUR" # Novo campo
    current_balance: float = 0.0

class AccountCreate(AccountBase):
    pass

class AccountResponse(AccountBase):
    id: int
    user_id: int

    class Config:
        from_attributes = True


# --- CATEGORY SCHEMAS ---
class CategoryBase(BaseModel):
    name: str
    type: str # Ex: Expense, Income

class CategoryCreate(CategoryBase):
    pass

class CategoryResponse(CategoryBase):
    id: int
    user_id: int

    class Config:
        from_attributes = True


# --- ASSET SCHEMAS ---
class AssetBase(BaseModel):
    symbol: str
    name: str
    asset_type: str
    currency_code: str = "USD" # Novo campo

class AssetCreate(AssetBase):
    pass

class AssetResponse(AssetBase):
    id: int

    class Config:
        from_attributes = True


# --- ASSET PRICE HISTORY (Novo) ---
class AssetPriceBase(BaseModel):
    date: date
    close_price: float

class AssetPriceCreate(AssetPriceBase):
    asset_id: int

class AssetPriceResponse(AssetPriceBase):
    id: int
    asset_id: int

    class Config:
        from_attributes = True


# --- TRANSACTION SCHEMAS ---
class TransactionBase(BaseModel):
    amount: float
    description: str
    date: date
    transaction_type: str # BUY, SELL, DEPOSIT, WITHDRAW

class TransactionCreate(TransactionBase):
    account_id: int
    category_id: Optional[int] = None
    
    # Campos de Investimento (Opcionais)
    asset_id: Optional[int] = None
    price_per_unit: Optional[float] = None
    quantity: Optional[float] = None

class TransactionResponse(TransactionCreate):
    id: int
    
    # Podemos incluir objetos aninhados se quisermos, 
    # mas por agora mantemos simples com IDs
    
    class Config:
        from_attributes = True


# --- HOLDING SCHEMAS ---
class HoldingBase(BaseModel):
    quantity: float
    avg_buy_price: float

class HoldingCreate(HoldingBase):
    account_id: int
    asset_id: int

class HoldingResponse(HoldingBase):
    id: int
    account_id: int
    asset_id: int
    
    # Campos calculados (não vêm da base de dados, seriam inseridos pela lógica da API)
    # current_value: Optional[float] = None 
    
    class Config:
        from_attributes = True