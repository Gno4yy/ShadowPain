import logging
import os
from datetime import datetime

# Корень проекта — для абсолютных путей
PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
LOG_DIR = os.path.join(PROJECT_ROOT, "output")
os.makedirs(LOG_DIR, exist_ok=True)

def setup_logger(name="shadowpain"):
    """Настройка логгера"""
    logger = logging.getLogger(name)
    
    if logger.handlers:
        return logger
    
    logger.setLevel(logging.DEBUG)
    
    # Файл логов
    log_file = os.path.join(
        LOG_DIR,
        f"shadowpain_{datetime.now().strftime('%Y%m%d_%H%M%S')}.log"
    )
    
    fh = logging.FileHandler(log_file, encoding='utf-8')
    fh.setLevel(logging.DEBUG)
    
    # Консоль
    ch = logging.StreamHandler()
    ch.setLevel(logging.INFO)
    
    formatter = logging.Formatter(
        '%(asctime)s [%(levelname)s] %(message)s',
        datefmt='%H:%M:%S'
    )
    fh.setFormatter(formatter)
    ch.setFormatter(formatter)
    
    logger.addHandler(fh)
    logger.addHandler(ch)
    
    return logger
