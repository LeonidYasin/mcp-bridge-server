"""MCP Bridge Server — FastAPI сервер."""

import logging
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
import uvicorn

from config import config
from models.message import ProcessRequest, ProcessResponse
from handlers.messages import process_message
from handlers.executor import get_tools_list

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s"
)
logger = logging.getLogger(__name__)

app = FastAPI(
    title="MCP Bridge Server",
    description="Local server for MCP Browser Bridge extension",
    version="0.1.0"
)

# CORS для доступа из браузера
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


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
    
    Ожидает JSON:
    {
        "message": "текст сообщения с маркерами",
        "config": {"autoSend": true, "sendDelay": 1},
        "token": "github_token",
        "url": "http://127.0.0.1:3001/mcp"
    }
    """
    logger.info(f"📨 Processing message ({len(req.message)} chars)")
    
    # Берём токен из запроса или из конфига
    token = req.token or config.GITHUB_TOKEN
    
    if not token:
        logger.warning("⚠️ No GitHub token provided")
        return ProcessResponse(
            error="GitHub token is not configured. Please set it in extension settings."
        )
    
    # Передаём токен в обработчик
    req.token = token
    
    try:
        result = await process_message(req)
        return result
    except Exception as e:
        logger.error(f"❌ Process error: {e}")
        import traceback
        traceback.print_exc()
        return ProcessResponse(error=str(e))


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
