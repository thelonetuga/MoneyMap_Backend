from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session, joinedload
from typing import List

from app.models.transaction import Category, SubCategory
from app.models.user import User
from app.schemas import schemas
from app.database.database import get_db
from app.auth import get_current_user

router = APIRouter(tags=["categories"])

@router.get("/categories", response_model=List[schemas.CategoryResponse])
def read_categories(db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    # Categorias do User + Globais
    return db.query(Category).options(joinedload(Category.sub_categories)).filter(
        (Category.user_id == current_user.id) | (Category.user_id == None)
    ).all()

# --- MOVIDO DO SETUP.PY ---
@router.post("/categories/", response_model=schemas.CategoryResponse)
def create_category(category: schemas.CategoryCreate, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    db_cat = Category(**category.model_dump(), user_id=current_user.id)
    db.add(db_cat)
    db.commit()
    db.refresh(db_cat)
    return db_cat
# --------------------------

@router.post("/subcategories", response_model=schemas.SubCategoryResponse)
def create_subcategory(sub: schemas.SubCategoryCreate, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    parent = db.query(Category).filter(Category.id == sub.category_id).first()
    if not parent:
        raise HTTPException(status_code=404, detail="Categoria pai não encontrada")
    
    sub_data = sub.model_dump() if hasattr(sub, 'model_dump') else sub.dict()
    db_sub = SubCategory(**sub_data)
    db.add(db_sub)
    db.commit()
    db.refresh(db_sub)
    return db_sub

@router.delete("/subcategories/{sub_id}")
def delete_subcategory(sub_id: int, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    sub = db.query(SubCategory).filter(SubCategory.id == sub_id).first()
    if not sub: raise HTTPException(status_code=404, detail="Não encontrada")
    
    if sub.transactions:
         raise HTTPException(status_code=400, detail="Não pode apagar categoria com movimentos associados.")

    db.delete(sub)
    db.commit()
    return {"ok": True}