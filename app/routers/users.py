from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from typing import List

from app.database.database import get_db
from app.models.user import User, UserProfile
from app.schemas import schemas
from app.utils.auth import get_current_user, get_password_hash


router = APIRouter(prefix="/users", tags=["users"])

# --- 1. CRIAR UTILIZADOR (Público) ---
@router.post("/", response_model=schemas.UserResponse, status_code=status.HTTP_201_CREATED)
def create_user(user: schemas.UserCreate, db: Session = Depends(get_db)):
    db_user = db.query(User).filter(User.email == user.email).first()
    if db_user:
        raise HTTPException(status_code=400, detail="Email already registered")
    
    hashed_password = get_password_hash(user.password)
    # Define role default como 'basic' se não for passado
    role = user.role if hasattr(user, 'role') and user.role else "basic"
    
    # --- CORREÇÃO AQUI ---
    # Mudámos de 'hashed_password=' para 'password_hash='
    new_user = User(email=user.email, password_hash=hashed_password, role=role)
    
    db.add(new_user)
    db.commit()
    db.refresh(new_user)
    return new_user

# --- 2. PERFIL DO PRÓPRIO (Autenticado) ---
@router.get("/me", response_model=schemas.UserResponse)
def read_users_me(current_user: User = Depends(get_current_user)):
    return current_user

# --- 3. ATUALIZAR PRÓPRIO PERFIL (Autenticado) ---
@router.put("/me", response_model=schemas.UserResponse)
def update_user_me(
    user_update: schemas.UserUpdate, 
    db: Session = Depends(get_db), 
    current_user: User = Depends(get_current_user)
):
    # 1. Verificar se o user já tem perfil. Se não tiver, CRIA UM NOVO.
    if not current_user.profile:
        new_profile = UserProfile(user_id=current_user.id)
        db.add(new_profile)
        current_user.profile = new_profile # Associa imediatamente para usarmos abaixo
    
    # 2. Atualizar apenas os campos que foram enviados (diferentes de None)
    if user_update.first_name is not None:
        current_user.profile.first_name = user_update.first_name
        
    if user_update.last_name is not None:
        current_user.profile.last_name = user_update.last_name
        
    if user_update.preferred_currency is not None:
        current_user.profile.preferred_currency = user_update.preferred_currency

    # (Opcional: Se quiseres permitir mudar password aqui também)
    # if user_update.password:
    #     current_user.password_hash = get_password_hash(user_update.password)

    db.add(current_user.profile) # Garante que o profile é marcado para update
    db.commit()
    db.refresh(current_user)
    
    return current_user

# --- 4. LISTAR TODOS (ADMIN ONLY) - A ROTA QUE FALTAVA ---
@router.get("/", response_model=List[schemas.UserResponse])
def read_all_users(
    skip: int = 0, 
    limit: int = 100, 
    db: Session = Depends(get_db), 
    current_user: User = Depends(get_current_user)
):
    if current_user.role != "admin":
        raise HTTPException(status_code=403, detail="Acesso reservado a administradores.")
    
    users = db.query(User).offset(skip).limit(limit).all()
    return users

# --- 5. MUDAR ROLE (ADMIN ONLY) ---
@router.put("/{user_id}/role", response_model=schemas.UserResponse)
def update_user_role(
    user_id: int, 
    role: str, 
    db: Session = Depends(get_db), 
    current_user: User = Depends(get_current_user)
):
    if current_user.role != "admin":
        raise HTTPException(status_code=403, detail="Acesso negado.")
    
    if role not in ["admin", "premium", "basic"]:
        raise HTTPException(status_code=400, detail="Role inválida.")

    user_to_edit = db.query(User).filter(User.id == user_id).first()
    if not user_to_edit:
        raise HTTPException(status_code=404, detail="Utilizador não encontrado.")
    
    user_to_edit.role = role
    db.commit()
    db.refresh(user_to_edit)
    return user_to_edit