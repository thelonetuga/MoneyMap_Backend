# app/dependencies.py
from fastapi import Depends, HTTPException, status
from typing import List
from app.auth import get_current_user
from app.models import User


# Classe reutilizável para verificar roles
class RoleChecker:
    def __init__(self, allowed_roles: List[str]):
        self.allowed_roles = allowed_roles

    def __call__(self, user: User = Depends(get_current_user)):
        if user.role not in self.allowed_roles:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN, 
                detail="Operação permitida apenas para utilizadores Premium ou Admin."
            )
        return user

# Atalhos para usar nas rotas
require_admin = RoleChecker(["admin"])
require_premium = RoleChecker(["premium", "admin"]) # Admin também pode fazer coisas de premium