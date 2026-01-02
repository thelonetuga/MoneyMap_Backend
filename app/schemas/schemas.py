from pydantic import BaseModel, ConfigDict
from datetime import date, datetime
from typing import Optional, List

# --- 1. SCHEMAS AUXILIARES (Lookups) ---

class AccountTypeBase(BaseModel):
    name: str

class AccountTypeResponse(AccountTypeBase):
    id: int
    model_config = ConfigDict(from_attributes=True)

class TransactionTypeBase(BaseModel):
    name: str
    is_investment: bool = False

class TransactionTypeResponse(TransactionTypeBase):
    id: int
    model_config = ConfigDict(from_attributes=True)


# --- 2. PERFIL E UTILIZADOR ---

class UserProfileBase(BaseModel):
    first_name: Optional[str] = None
    last_name: Optional[str] = None
    preferred_currency: str = "EUR"

class UserProfileCreate(UserProfileBase):
    pass

class UserProfileResponse(UserProfileBase):
    id: int
    user_id: int
    model_config = ConfigDict(from_attributes=True)

class UserBase(BaseModel):
    email: str

class UserCreate(UserBase):
    password: str
    # Opcional: Criar perfil logo no registo
    profile: Optional[UserProfileCreate] = None

class UserUpdate(BaseModel):
    first_name: Optional[str] = None
    last_name: Optional[str] = None
    preferred_currency: Optional[str] = None
    password: Optional[str] = None

class UserResponse(UserBase):
    id: int
    created_at: datetime
    role: str
    profile: Optional[UserProfileResponse] = None
    
    model_config = ConfigDict(from_attributes=True)


# --- 3. CATEGORIAS ---

class SubCategoryBase(BaseModel):
    name: str

class SubCategoryCreate(SubCategoryBase):
    category_id: int

class SubCategoryResponse(SubCategoryBase):
    id: int
    category_id: int
    model_config = ConfigDict(from_attributes=True)

class CategoryBase(BaseModel):
    name: str

class CategoryCreate(CategoryBase):
    pass

class CategoryResponse(CategoryBase):
    id: int
    user_id: int
    # Inclui a lista de subcategorias automaticamente
    sub_categories: List[SubCategoryResponse] = []
    
    model_config = ConfigDict(from_attributes=True)


# --- 4. ATIVOS (ASSETS) ---

class AssetBase(BaseModel):
    symbol: str
    name: str
    asset_type: str

class AssetCreate(AssetBase):
    pass

class AssetResponse(AssetBase):
    id: int
    model_config = ConfigDict(from_attributes=True)


# --- 5. CONTAS ---

class AccountBase(BaseModel):
    name: str
    current_balance: float = 0.0

class AccountCreate(AccountBase):
    account_type_id: int # O utilizador escolhe o ID (ex: 1=Banco, 2=Corretora)

class AccountResponse(AccountBase):
    id: int
    user_id: int
    account_type: AccountTypeResponse # Devolve o objeto completo (nome, id)
    
    model_config = ConfigDict(from_attributes=True)


# --- 6. HOLDINGS (Carteira) ---

class HoldingBase(BaseModel):
    quantity: float
    avg_buy_price: float

class HoldingResponse(HoldingBase):
    id: int
    account_id: int
    asset: AssetResponse # Útil para mostrar o símbolo no frontend
    
    model_config = ConfigDict(from_attributes=True)


# --- 7. TRANSAÇÕES (O Coração do Sistema) ---

class TransactionBase(BaseModel):
    date: date
    description: str
    amount: float
    
    # Campos de Investimento (Opcionais)
    quantity: Optional[float] = None
    price_per_unit: Optional[float] = None
    symbol: Optional[str] = None  # <--- ESTE CAMPO FALTAVA! 🚨

class TransactionCreate(TransactionBase):
    account_id: int
    transaction_type_id: int
    
    # ALTERADO: Agora aceitamos category_id
    category_id: Optional[int] = None
    sub_category_id: Optional[int] = None
    asset_id: Optional[int] = None

class TransactionResponse(TransactionBase):
    id: int
    account_id: int
    
    transaction_type_id: int
    category_id: Optional[int] = None
    sub_category_id: Optional[int] = None
    asset_id: Optional[int] = None

    # Objetos Aninhados
    transaction_type: TransactionTypeResponse
    category: Optional[CategoryResponse] = None
    sub_category: Optional[SubCategoryResponse] = None
    asset: Optional[AssetResponse] = None
    
    model_config = ConfigDict(from_attributes=True)

# --- 8. RELATÓRIOS (Não são tabelas, são cálculos) ---

class PortfolioPosition(BaseModel):
    symbol: str
    quantity: float
    avg_buy_price: float
    current_price: float
    total_value: float
    profit_loss: float

class PortfolioResponse(BaseModel):
    user_id: int
    total_net_worth: float      # O Grande Total (Bancos + Investimentos)
    total_cash: float           # Apenas contas bancárias
    total_invested: float       # Apenas ações/crypto
    positions: List[PortfolioPosition]

class HistoryPoint(BaseModel):
    date: str   # "2023-11-01"
    value: float