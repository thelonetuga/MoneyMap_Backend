from fastapi import APIRouter, Depends, HTTPException, UploadFile, File
from sqlalchemy.orm import Session
from app.database.database import get_db
from app.dependencies import get_current_user # <--- Usa o standard get_current_user
from app.models import Account, User 
from app.services.import_service import ImportService 

router = APIRouter(prefix="/imports", tags=["imports"])

@router.post("/upload")
async def upload_transactions(
    account_id: int,
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user) # Pode ser require_premium se quiseres bloquear
):
    account = db.query(Account).filter(Account.id == account_id).first()
    if not account or account.user_id != current_user.id:
        raise HTTPException(status_code=403, detail="Conta inválida ou sem permissão.")

    try:
        # ATUALIZADO: Passamos current_user.id
        result = await ImportService.process_file(db, account_id, file, current_user.id)
        return {"message": "Importação concluída", **result}
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))