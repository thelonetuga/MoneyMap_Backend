from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from typing import List

# Importar os seus módulos (ajuste os caminhos se necessário)
from database.database import get_db
import models.models as models
import schemas.schemas as schemas
from dependencies import get_db, get_current_user


# Criação do Router
router = APIRouter(tags=["Categories"])

# --- 1. LISTAR TODAS AS CATEGORIAS (Mães + Filhas) ---
@router.get("/categories", response_model=List[schemas.CategoryResponse])
def get_categories(
    current_user: models.User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Retorna a lista de categorias principais e as suas subcategorias.
    Usado para preencher os dropdowns no Frontend.
    """
    # Se quiser filtrar apenas categorias do user + globais, adicione filtros aqui.
    # Por enquanto, retorna todas:
    categories = db.query(models.Category).all()
    return categories


# --- 2. CRIAR NOVA SUBCATEGORIA ---
@router.post("/subcategories", response_model=schemas.SubCategoryResponse, status_code=status.HTTP_201_CREATED)
def create_subcategory(
    sub_cat: schemas.SubCategoryCreate,
    current_user: models.User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Cria uma nova subcategoria (ex: 'Internet') dentro de uma Categoria Pai (ex: 'Casa').
    """
    # Opcional: Validar se a categoria pai existe
    parent_cat = db.query(models.Category).filter(models.Category.id == sub_cat.category_id).first()
    if not parent_cat:
        raise HTTPException(status_code=404, detail="Categoria principal não encontrada.")

    # Criar e guardar
    new_sub = models.SubCategory(
        name=sub_cat.name, 
        category_id=sub_cat.category_id
    )
    
    db.add(new_sub)
    db.commit()
    db.refresh(new_sub)
    
    return new_sub


# --- 3. APAGAR SUBCATEGORIA ---
@router.delete("/subcategories/{id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_subcategory(
    id: int,
    current_user: models.User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Apaga uma subcategoria.
    CUIDADO: Se houver transações ligadas a esta subcategoria, o SQL pode dar erro 
    (IntegrityError) dependendo da configuração da Foreign Key.
    """
    sub_to_delete = db.query(models.SubCategory).filter(models.SubCategory.id == id).first()
    
    if not sub_to_delete:
        raise HTTPException(status_code=404, detail="Subcategoria não encontrada.")
    
    # Verificação de segurança simples: Verificar se há transações a usar isto
    # (Isto evita um erro feio de SQL 500 para o utilizador)
    usage_check = db.query(models.Transaction).filter(models.Transaction.sub_category_id == id).first()
    if usage_check:
        raise HTTPException(
            status_code=400, 
            detail="Não é possível apagar: Existem transações associadas a esta categoria."
        )

    db.delete(sub_to_delete)
    db.commit()
    
    return None