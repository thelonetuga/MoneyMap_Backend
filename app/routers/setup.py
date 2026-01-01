from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session, joinedload
from typing import List
from app.models.account import Account, AccountType
from app.models.asset import Asset
from app.models.transaction import Category, TransactionType
from app.models.user import User
from app.schemas import schemas
from app.dependencies import get_db, get_current_user

router = APIRouter(tags=["setup"])

# LOOKUPS
@router.get("/lookups/account-types", response_model=List[schemas.AccountTypeResponse])
def get_account_types(db: Session = Depends(get_db)):
    return db.query(AccountType).all()

@router.get("/lookups/transaction-types", response_model=List[schemas.TransactionTypeResponse])
def get_transaction_types(db: Session = Depends(get_db)):
    return db.query(TransactionType).all()

@router.get("/assets/", response_model=List[schemas.AssetResponse])
def get_all_assets(db: Session = Depends(get_db)):
    return db.query(Asset).all()

# CONTAS
@router.get("/accounts", response_model=List[schemas.AccountResponse])
def read_accounts(db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    return db.query(Account).options(joinedload(Account.account_type)).filter(Account.user_id == current_user.id).all()

@router.post("/accounts/", response_model=schemas.AccountResponse, status_code=status.HTTP_201_CREATED)
def create_account(account: schemas.AccountCreate, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    if not db.query(AccountType).filter(AccountType.id == account.account_type_id).first():
         raise HTTPException(status_code=400, detail="Tipo de conta inválido")
    db_account = Account(**account.model_dump(), user_id=current_user.id)
    db.add(db_account)
    db.commit()
    db.refresh(db_account)
    return db_account

# CATEGORIAS
@router.get("/categories", response_model=List[schemas.CategoryResponse])
def read_categories(db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    return db.query(Category).options(joinedload(Category.sub_categories)).filter(Category.user_id == current_user.id).all()

@router.post("/categories/", response_model=schemas.CategoryResponse)
def create_category(category: schemas.CategoryCreate, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    db_cat = Category(**category.model_dump(), user_id=current_user.id)
    db.add(db_cat)
    db.commit()
    db.refresh(db_cat)
    return db_cat