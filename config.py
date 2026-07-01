"""Настройки сервера."""

import os
from pathlib import Path

# Загружаем .env файл
try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass

class Config:
    """Конфигурация сервера."""
    
    # Сервер
    HOST = os.getenv("MCP_BRIDGE_HOST", "127.0.0.1")
    PORT = int(os.getenv("MCP_BRIDGE_PORT", "8080"))
    
    # MCP-сервер
    MCP_URL = os.getenv("MCP_URL", "http://127.0.0.1:3001/mcp")
    GITHUB_TOKEN = os.getenv("GITHUB_TOKEN", "")
    
    # Настройки по умолчанию
    DEFAULT_AUTO_SEND = True
    DEFAULT_SEND_DELAY = 1.0
    
    # Пути
    BASE_DIR = Path(__file__).parent
    LOGS_DIR = BASE_DIR / "logs"
    
    @classmethod
    def ensure_dirs(cls):
        """Создаёт необходимые директории."""
        cls.LOGS_DIR.mkdir(exist_ok=True)

config = Config()
