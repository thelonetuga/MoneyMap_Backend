from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy.orm import Session
import models.models as models
import schemas.schemas as schemas
from database.database import get_db
from dependencies import get_db, get_current_user
from auth import verify_password, create_access_token, get_password_hash

router = APIRouter(tags=["users"])

# --- 1. LOGIN (JÁ EXISTIA) ---
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

# --- 2. REGISTO (JÁ EXISTIA) ---
@router.post("/users/", response_model=schemas.UserResponse, status_code=status.HTTP_201_CREATED)
def create_user(user: schemas.UserCreate, db: Session = Depends(get_db)):
    if db.query(models.User).filter(models.User.email == user.email).first():
        raise HTTPException(status_code=400, detail="Email já registado")
    
    hashed_pw = get_password_hash(user.password)
    db_user = models.User(email=user.email, password_hash=hashed_pw)
    db.add(db_user)
    db.commit()
    db.refresh(db_user)
    
    # Cria perfil inicial se fornecido no registo
    if user.profile:
        # Nota: Usamos model_dump() porque parece estar a usar Pydantic v2
        db_profile = models.UserProfile(**user.profile.model_dump(), user_id=db_user.id)
        db.add(db_profile)
        db.commit()
    
    return db_user

# ========================================================
# --- NOVAS ROTAS ADICIONADAS PARA O PERFIL ---
# ========================================================

# --- 3. OBTER DADOS DO UTILIZADOR ATUAL (Para a página de Settings) ---
@router.get("/users/me", response_model=schemas.UserResponse)
def read_users_me(current_user: models.User = Depends(get_current_user)):
    """
    Retorna o objeto do utilizador logado (incluindo o perfil aninhado).
    O Frontend usa isto para preencher os inputs.
    """
    return current_user

# --- 4. ATUALIZAR PERFIL (Botão 'Guardar' nas Settings) ---
@router.put("/users/profile", response_model=schemas.UserProfileResponse)
def update_user_profile(
    profile_data: schemas.UserProfileCreate,
    current_user: models.User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Cria ou Atualiza o perfil do utilizador.
    """
    db_profile = db.query(models.UserProfile).filter(models.UserProfile.user_id == current_user.id).first()
    
    if not db_profile:
        # Criar novo se não existir
        # Se estiver a usar Pydantic v2 use .model_dump(), se v1 use .dict()
        data = profile_data.model_dump() if hasattr(profile_data, 'model_dump') else profile_data.dict()
        
        db_profile = models.UserProfile(**data, user_id=current_user.id)
        db.add(db_profile)
    else:
        # Atualizar existente
        db_profile.first_name = profile_data.first_name
        db_profile.last_name = profile_data.last_name
        db_profile.preferred_currency = profile_data.preferred_currency
    
    db.commit()
    db.refresh(db_profile)
    return db_profile