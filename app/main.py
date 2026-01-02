from fastapi import FastAPI, Depends
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy.orm import Session

# --- IMPORTS CORRIGIDOS (Absolutos) ---
from app.routers import accounts, users, transactions, portfolio, setup, analytics, categories, imports
from app.database.database import Base, engine, get_db
from app.utils.auth import get_current_user
# --------------------------------------

# Inicializar Base de Dados
Base.metadata.create_all(bind=engine)

app = FastAPI(title="MoneyMap API", description="API Financeira Modular v4.0")

# Configuração CORS
origins = ["http://localhost:3000"]
app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Ligar os routers à aplicação
app.include_router(users.router)
app.include_router(transactions.router)
app.include_router(portfolio.router)
app.include_router(setup.router)
app.include_router(analytics.router)
app.include_router(categories.router)
app.include_router(imports.router)
app.include_router(accounts.router)

# --- ROTA QUE FALTAVA (Histórico) ---
# O Frontend chama /history na raiz, por isso definimos aqui
@app.get("/history")
def read_history_proxy(db: Session = Depends(get_db), current_user = Depends(get_current_user)):
    # Chama a função lógica que está dentro do analytics.py
    return analytics.get_portfolio_history(db, current_user)
# ------------------------------------

@app.get("/")
def root():
    return {"message": "MoneyMap API Modular is running 🚀"}