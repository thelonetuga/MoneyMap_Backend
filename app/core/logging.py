import logging
import sys
from app.core.config import settings

# Configuração básica
LOG_FORMAT = "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
DATE_FORMAT = "%Y-%m-%d %H:%M:%S"

def setup_logging():
    """Configura o logger da aplicação."""
    
    # Define o nível de log base (DEBUG em dev, INFO em prod se quisesses diferenciar)
    log_level = logging.INFO
    
    # Configura o logger raiz
    logging.basicConfig(
        level=log_level,
        format=LOG_FORMAT,
        datefmt=DATE_FORMAT,
        handlers=[
            logging.StreamHandler(sys.stdout)
        ]
    )

    # Silenciar logs muito verbosos de bibliotecas externas se necessário
    logging.getLogger("uvicorn.access").setLevel(logging.WARNING) # Vamos usar o nosso próprio middleware de log
    
    logger = logging.getLogger(settings.APP_NAME)
    logger.setLevel(log_level)
    
    return logger

# Instância global do logger para importar noutros ficheiros
logger = setup_logging()