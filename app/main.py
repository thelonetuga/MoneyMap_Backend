import time
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware

# Importa os teus routers
from app.routers import users, transactions, accounts, categories, analytics, portfolio, imports, auth, setup
from app.database.database import engine, Base
from app.core.logging import logger

# Base.metadata.create_all(bind=engine)  <--- COMENTADO: Agora usamos Alembic para gerir a BD!

app = FastAPI(title="MoneyMap API")

# --- MIDDLEWARE DE LOGGING ---
@app.middleware("http")
async def log_requests(request: Request, call_next):
    start_time = time.time()
    
    # Processar o pedido
    response = await call_next(request)
    
    process_time = (time.time() - start_time) * 1000 # ms
    formatted_process_time = "{0:.2f}".format(process_time)
    
    # Logar detalhes
    logger.info(
        f"Method={request.method} Path={request.url.path} "
        f"Status={response.status_code} Duration={formatted_process_time}ms"
    )
    
    return response
# -----------------------------

# --- CONFIGURAÇÃO CORS CRÍTICA ---
origins = [
    "http://localhost:3000",      # Next.js normal
    "http://127.0.0.1:3000",      # Next.js alternativo
    "http://localhost:8000",      # Swagger UI
]

# Configuração de CORS para permitir que o Frontend (porta 3000) comunique com a API
app.add_middleware(
    CORSMiddleware,
    allow_origins=origins, # Usar a lista de origens definida acima é mais seguro e correto com credentials=True
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
app.include_router(setup.router)

@app.get("/")
def read_root():
    logger.info("Root endpoint accessed")
    return {"message": "MoneyMap Backend a bombar! 🚀"}