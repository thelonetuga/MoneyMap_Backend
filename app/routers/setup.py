from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session, joinedload
from typing import List
import models.models as models
import schemas.schemas as schemas
from dependencies import get_db, get_current_user

router = APIRouter(tags=["setup"])

# LOOKUPS
@router.get("/lookups/account-types", response_model=List[schemas.AccountTypeResponse])
def get_account_types(db: Session = Depends(get_db)):
    return db.query(models.AccountType).all()

@router.get("/lookups/transaction-types", response_model=List[schemas.TransactionTypeResponse])
def get_transaction_types(db: Session = Depends(get_db)):
    return db.query(models.TransactionType).all()

@router.get("/assets/", response_model=List[schemas.AssetResponse])
def get_all_assets(db: Session = Depends(get_db)):
    return db.query(models.Asset).all()

# CONTAS
@router.get("/accounts", response_model=List[schemas.AccountResponse])
def read_accounts(db: Session = Depends(get_db), current_user: models.User = Depends(get_current_user)):
    return db.query(models.Account).options(joinedload(models.Account.account_type)).filter(models.Account.user_id == current_user.id).all()

@router.post("/accounts/", response_model=schemas.AccountResponse, status_code=status.HTTP_201_CREATED)
def create_account(account: schemas.AccountCreate, db: Session = Depends(get_db), current_user: models.User = Depends(get_current_user)):
    if not db.query(models.AccountType).filter(models.AccountType.id == account.account_type_id).first():
         raise HTTPException(status_code=400, detail="Tipo de conta inválido")
    db_account = models.Account(**account.model_dump(), user_id=current_user.id)
    db.add(db_account)
    db.commit()
    db.refresh(db_account)
    return db_account

# CATEGORIAS
@router.get("/categories", response_model=List[schemas.CategoryResponse])
def read_categories(db: Session = Depends(get_db), current_user: models.User = Depends(get_current_user)):
    return db.query(models.Category).options(joinedload(models.Category.sub_categories)).filter(models.Category.user_id == current_user.id).all()

@router.post("/categories/", response_model=schemas.CategoryResponse)
def create_category(category: schemas.CategoryCreate, db: Session = Depends(get_db), current_user: models.User = Depends(get_current_user)):
    db_cat = models.Category(**category.model_dump(), user_id=current_user.id)
    db.add(db_cat)
    db.commit()
    db.refresh(db_cat)
    return db_cat