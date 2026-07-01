"""MCP Bridge Server — FastAPI сервер."""

import logging
import sys
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
import uvicorn

from config import config
from models.message import ProcessRequest, ProcessResponse
from handlers.messages import process_message
from handlers.executor import get_tools_list

# Настройка логирования
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s"
)
logger = logging.getLogger(__name__)

# Создаём приложение
app = FastAPI(
    title="MCP Bridge Server",
    description="Local server for MCP Browser Bridge extension",
    version="0.1.0"
)

# CORS для доступа из браузера
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

# ============================================================
# Эндпоинты
# ============================================================

@app.get("/health")
async def health():
    """Проверка состояния сервера."""
    return {
        "status": "ok",
        "version": "0.1.0",
        "mcp_url": config.MCP_URL,
        "token_configured": bool(config.GITHUB_TOKEN)
    }


@app.get("/tools")
async def tools_list():
    """Список доступных инструментов."""
    try:
        tools = await get_tools_list(config.MCP_URL, config.GITHUB_TOKEN)
        return {"tools": tools}
    except Exception as e:
        logger.error(f"Failed to get tools: {e}")
        return {"tools": [], "error": str(e)}


@app.post("/process")
async def process(req: ProcessRequest) -> ProcessResponse:
    """
    Обрабатывает сообщение из чата.
    
    Пример тела запроса:
    {
        "message": "==MCP:list_commits== {...}",
        "config": {"autoSend": true}
    }
    """
    logger.info(f"📨 Processing message ({len(req.message)} chars)")
    
    # Передаём токен и URL из запроса или из конфига
    token = req.token or config.GITHUB_TOKEN
    url = req.url or config.MCP_URL
    
    if not token:
        logger.warning("⚠️ No GitHub token provided")
    
    result = await process_message(req)
    return result


# ============================================================
# Запуск
# ============================================================

def main():
    """Запуск сервера."""
    logger.info(f"🚀 Starting MCP Bridge Server v0.1.0")
    logger.info(f"   Host: {config.HOST}")
    logger.info(f"   Port: {config.PORT}")
    logger.info(f"   MCP URL: {config.MCP_URL}")
    logger.info(f"   Token: {'✅ configured' if config.GITHUB_TOKEN else '❌ not set'}")
    
    config.ensure_dirs()
    
    uvicorn.run(
        app,
        host=config.HOST,
        port=config.PORT,
        log_level="info"
    )


if __name__ == "__main__":
    main()
