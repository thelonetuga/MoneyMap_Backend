from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

# Importa os teus routers
from app.routers import users, transactions, accounts, categories, analytics, portfolio, imports, auth
from app.database.database import engine, Base

Base.metadata.create_all(bind=engine)

app = FastAPI(title="MoneyMap API")

# --- CONFIGURAÇÃO CORS CRÍTICA ---
origins = [
    "http://localhost:3000",      # Next.js normal
    "http://127.0.0.1:3000",      # Next.js alternativo
    "http://localhost:8000",      # Swagger UI
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"], # ⚠️ Em dev, usamos "*" para aceitar TUDO e evitar dores de cabeça
    allow_credentials=True,
    allow_methods=["*"], # Permitir GET, POST, PUT, DELETE, etc.
    allow_headers=["*"], # Permitir todos os cabeçalhos
)
# --------------------------------

# Registar routers
app.include_router(auth.router)
app.include_router(users.router)
app.include_router(accounts.router)
app.include_router(transactions.router)
app.include_router(categories.router)
app.include_router(analytics.router)
app.include_router(portfolio.router)
app.include_router(imports.router)

@app.get("/")
def read_root():
    return {"message": "MoneyMap Backend a bombar! 🚀"}