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

@router.post("/token", response_model=Token)
def login_for_access_token(
    form_data: Annotated[OAuth2PasswordRequestForm, Depends()],
    db: Session = Depends(get_db)
):
    # 1. Procurar o utilizador pelo email
    # O OAuth2PasswordRequestForm usa 'username' para o campo de login (que no nosso caso é o email)
    user = db.query(User).filter(User.email == form_data.username).first()
    
    # 2. Verificar se o user existe e se a password bate certo
    if not user or not verify_password(form_data.password, user.hashed_password):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Email ou password incorretos",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    # 3. Gerar o Token de Acesso
    # Se tiveres settings.ACCESS_TOKEN_EXPIRE_MINUTES, usa-o, senão mete 30 fixo
    access_token_expires = timedelta(minutes=30) 
    access_token = create_access_token(
        data={"sub": user.email}, expires_delta=access_token_expires
    )
    
    return {"access_token": access_token, "token_type": "bearer"}