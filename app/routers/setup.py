from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from typing import List
from app.models.account import AccountType
from app.models.asset import Asset
from app.models.transaction import TransactionType
from app.schemas import schemas
from app.database.database import get_db

router = APIRouter(tags=["setup"])

# --- APENAS LOOKUPS (Dados Estáticos) ---

@router.get("/lookups/account-types", response_model=List[schemas.AccountTypeResponse])
def get_account_types(db: Session = Depends(get_db)):
    return db.query(AccountType).all()

@router.get("/lookups/transaction-types", response_model=List[schemas.TransactionTypeResponse])
def get_transaction_types(db: Session = Depends(get_db)):
    return db.query(TransactionType).all()

@router.get("/assets/", response_model=List[schemas.AssetResponse])
def get_all_assets(db: Session = Depends(get_db)):
    return db.query(Asset).all()