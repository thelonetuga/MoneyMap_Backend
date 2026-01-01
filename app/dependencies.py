# app/dependencies.py
from fastapi import Depends
from fastapi.security import OAuth2PasswordBearer

# IMPORTANTE: Importar das fontes originais para garantir que o override dos testes funciona
from app.database.database import get_db
from app.auth import get_current_user, oauth2_scheme

# (Opcional) Se precisares de dependências extra no futuro, coloca-as aqui.
# Por agora, isto garante que quem importar de 'app.dependencies' 
# recebe as mesmas funções que o 'conftest.py' está a controlar.