from datetime import timedelta
from typing import Annotated
from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy.orm import Session

from app.database.database import get_db
from app.models import User
# Importamos as tuas ferramentas do ficheiro que me mostraste:
from app.utils.auth import verify_password, create_access_token 
# Certifica-te que tens o schema Token definido (verificamos no passo 3)
from app.schemas.schemas import Token 
from app.core.config import settings

router = APIRouter(tags=["authentication"])

# Em app/routers/auth.py

@router.post("/token", response_model=Token)
def login_for_access_token(
    form_data: Annotated[OAuth2PasswordRequestForm, Depends()],
    db: Session = Depends(get_db)
):
    user = db.query(User).filter(User.email == form_data.username).first()
    
    # --- A CORREÇÃO ESTÁ AQUI ---
    # Mudámos de user.hashed_password para user.password_hash
    if not user or not verify_password(form_data.password, user.password_hash):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Email ou password incorretos",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    access_token_expires = timedelta(minutes=30)
    access_token = create_access_token(
        data={"sub": user.email}, expires_delta=access_token_expires
    )
    
    return {"access_token": access_token, "token_type": "bearer"}