from fastapi import APIRouter, Depends, HTTPException, UploadFile, File
from sqlalchemy.orm import Session
from app.database.database import get_db
from app.dependencies import require_premium 
from app.models.account import Account
from app.models.user import User
from app.services.import_service import ImportService # <--- Importar Serviço

router = APIRouter(prefix="/imports", tags=["imports"])

@router.post("/upload")
async def upload_transactions(
    account_id: int,
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
    current_user: User = Depends(require_premium)
):
    account = db.query(Account).filter(Account.id == account_id).first()
    if not account or account.user_id != current_user.id:
        raise HTTPException(status_code=403, detail="Conta inválida ou sem permissão.")

    try:
        # Chama o serviço
        result = await ImportService.process_file(db, account_id, file)
        return {"message": "Importação concluída", **result}
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))