from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session, joinedload
from typing import List

# Importações ajustadas aos teus modelos
from app.models.transaction import Category, SubCategory, Transaction
from app.models.user import User
from app.schemas import schemas
from app.database.database import get_db
from app.utils.auth import get_current_user

# --- CORREÇÃO: Adicionado prefixo aqui ---
router = APIRouter(prefix="/categories", tags=["categories"])

# Agora usamos "/" que o FastAPI resolve automaticamente para "/categories" e "/categories/"
@router.get("/", response_model=List[schemas.CategoryResponse])
def read_categories(db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    # CORREÇÃO: Adicionado .options(joinedload(Category.subcategories))
    return db.query(Category).options(joinedload(Category.subcategories)).filter(
        (Category.user_id == current_user.id) | (Category.user_id == None)
    ).all()

@router.post("/", response_model=schemas.CategoryResponse, status_code=status.HTTP_201_CREATED)
def create_category(category: schemas.CategoryCreate, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    # Verificar duplicados
    exists = db.query(Category).filter(Category.user_id == current_user.id, Category.name == category.name).first()
    if exists:
        raise HTTPException(status_code=400, detail="Categoria já existe")

    db_cat = Category(**category.model_dump(), user_id=current_user.id)
    db.add(db_cat)
    db.commit()
    db.refresh(db_cat)
    return db_cat

# Subcategorias (prefixo manual pois é diferente)
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

@router.delete("/subcategories/{subcategory_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_subcategory(
    subcategory_id: int, 
    db: Session = Depends(get_db), 
    current_user: User = Depends(get_current_user)
):
    # 1. Encontrar a subcategoria
    sub = db.query(SubCategory).filter(SubCategory.id == subcategory_id).first()
    if not sub:
        raise HTTPException(status_code=404, detail="Subcategoria não encontrada")
    
    # 2. Verificar permissão (User Dono)
    parent_category = db.query(Category).filter(Category.id == sub.category_id).first()
    if parent_category.user_id != current_user.id:
        raise HTTPException(status_code=403, detail="Não tem permissão.")

    # 3. VERIFICAÇÃO DE SEGURANÇA (NOVO) 🚨
    # Se houver alguma transação a usar esta subcategoria, bloqueia!
    usage_check = db.query(Transaction).filter(Transaction.subcategory_id == subcategory_id).first()
    if usage_check:
        raise HTTPException(
            status_code=400, 
            detail="Não é possível apagar: esta subcategoria tem transações associadas."
        )

    # 4. Apagar
    db.delete(sub)
    db.commit()
    return None