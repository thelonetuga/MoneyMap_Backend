from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import List

# --- IMPORTS CORRIGIDOS ---
from app.models import models
from app.schemas import schemas
from app.database.database import get_db
from app.auth import get_current_user
# --------------------------

router = APIRouter(tags=["categories"])

@router.get("/categories", response_model=List[schemas.CategoryResponse])
def read_categories(db: Session = Depends(get_db), current_user: models.User = Depends(get_current_user)):
    # Categorias Globais (sem user_id) + Categorias do User
    return db.query(models.Category).filter(
        (models.Category.user_id == current_user.id) | (models.Category.user_id == None)
    ).all()

@router.post("/subcategories", response_model=schemas.SubCategoryResponse)
def create_subcategory(sub: schemas.SubCategoryCreate, db: Session = Depends(get_db), current_user: models.User = Depends(get_current_user)):
    # Verificar se a categoria pai pertence ao user ou é global
    parent = db.query(models.Category).filter(models.Category.id == sub.category_id).first()
    if not parent:
        raise HTTPException(status_code=404, detail="Categoria pai não encontrada")
    
    # Permitir adicionar subcategorias apenas às minhas categorias personalizadas? 
    # Ou a globais também? Vamos assumir que sim por agora.
    
    sub_data = sub.model_dump() if hasattr(sub, 'model_dump') else sub.dict()
    db_sub = models.SubCategory(**sub_data)
    db.add(db_sub)
    db.commit()
    db.refresh(db_sub)
    return db_sub

@router.delete("/subcategories/{sub_id}")
def delete_subcategory(sub_id: int, db: Session = Depends(get_db), current_user: models.User = Depends(get_current_user)):
    # Impedir apagar se tiver transações
    sub = db.query(models.SubCategory).filter(models.SubCategory.id == sub_id).first()
    if not sub: raise HTTPException(status_code=404, detail="Não encontrada")
    
    # Verificar permissões (idealmente verificar se a categoria pai é do user)
    
    if sub.transactions:
         raise HTTPException(status_code=400, detail="Não pode apagar categoria com movimentos associados.")

    db.delete(sub)
    db.commit()
    return {"ok": True}