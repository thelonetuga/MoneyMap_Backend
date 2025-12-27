from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy.orm import Session
import models.models as models
import schemas.schemas as schemas
from database.database import get_db

# IMPORTANTE: Importar do ficheiro 'auth.py' que está na pasta principal
from auth import verify_password, create_access_token, get_password_hash

# Nota: Mudei a tag para "users" para ficar organizado na documentação
router = APIRouter(tags=["users"])

@router.post("/token")
def login_for_access_token(form_data: OAuth2PasswordRequestForm = Depends(), db: Session = Depends(get_db)):
    user = db.query(models.User).filter(models.User.email == form_data.username).first()
    if not user or not verify_password(form_data.password, user.password_hash):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Email ou password incorretos",
            headers={"WWW-Authenticate": "Bearer"},
        )
    access_token = create_access_token(data={"sub": user.email})
    return {"access_token": access_token, "token_type": "bearer"}

@router.post("/users/", response_model=schemas.UserResponse, status_code=status.HTTP_201_CREATED)
def create_user(user: schemas.UserCreate, db: Session = Depends(get_db)):
    if db.query(models.User).filter(models.User.email == user.email).first():
        raise HTTPException(status_code=400, detail="Email já registado")
    
    hashed_pw = get_password_hash(user.password)
    db_user = models.User(email=user.email, password_hash=hashed_pw)
    db.add(db_user)
    db.commit()
    db.refresh(db_user)
    
    if user.profile:
        db_profile = models.UserProfile(**user.profile.model_dump(), user_id=db_user.id)
        db.add(db_profile)
        db.commit()
    
    return db_user

