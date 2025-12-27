from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from database.database import engine
import models.models as models

# Importar os nossos novos routers organizados
from routers import auth, transactions, portfolio, setup, analytics

# Inicializar Base de Dados
models.Base.metadata.create_all(bind=engine)

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
app.include_router(auth.router)
app.include_router(transactions.router)
app.include_router(portfolio.router)
app.include_router(setup.router)
app.include_router(analytics.router)

@app.get("/")
def root():
    return {"message": "MoneyMap API Modular is running 🚀"}