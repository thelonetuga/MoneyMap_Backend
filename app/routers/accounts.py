from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session, joinedload
from typing import List
from app.models.account import Account, AccountType
from app.models.user import User
from app.schemas import schemas
from app.database.database import get_db
from app.auth import get_current_user

router = APIRouter(tags=["accounts"])

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