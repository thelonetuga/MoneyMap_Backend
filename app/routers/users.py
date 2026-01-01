from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy.orm import Session

# --- IMPORTS CORRIGIDOS ---
from app.models import models
from app.schemas import schemas
from app.database.database import get_db
# MUDANÇA: Importar get_current_user diretamente de app.auth
from app.auth import verify_password, create_access_token, get_password_hash, get_current_user

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
        # Compatibilidade Pydantic v2
        profile_data = user.profile.model_dump() if hasattr(user.profile, 'model_dump') else user.profile.dict()
        db_profile = models.UserProfile(**profile_data, user_id=db_user.id)
        db.add(db_profile)
        db.commit()
    
    return db_user

@router.get("/users/me", response_model=schemas.UserResponse)
def read_users_me(current_user: models.User = Depends(get_current_user)):
    return current_user

@router.put("/users/profile", response_model=schemas.UserProfileResponse)
def update_user_profile(
    profile_data: schemas.UserProfileCreate,
    current_user: models.User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    db_profile = db.query(models.UserProfile).filter(models.UserProfile.user_id == current_user.id).first()
    
    data = profile_data.model_dump() if hasattr(profile_data, 'model_dump') else profile_data.dict()

    if not db_profile:
        db_profile = models.UserProfile(**data, user_id=current_user.id)
        db.add(db_profile)
    else:
        db_profile.first_name = profile_data.first_name
        db_profile.last_name = profile_data.last_name
        db_profile.preferred_currency = profile_data.preferred_currency
    
    db.commit()
    db.refresh(db_profile)
    return db_profile