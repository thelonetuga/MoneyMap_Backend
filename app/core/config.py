# app/core/config.py
from pydantic_settings import BaseSettings, SettingsConfigDict
from functools import lru_cache

class Settings(BaseSettings):
    APP_NAME: str = "MoneyMap"
    
    # URL de conexão ao PostgreSQL (Baseado no teu docker-compose)
    # Formato: postgresql://user:password@host:port/dbname
    DATABASE_URL: str = "postgresql://admin:segredo@localhost:5432/moneymap_db"
    
    SECRET_KEY: str = "uma_chave_secreta_muito_segura_aqui"
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 30
    
    # Permite ler de um ficheiro .env se existirem overrides
    model_config = SettingsConfigDict(env_file="/.env")

@lru_cache
def get_settings():
    return Settings()

settings = get_settings()