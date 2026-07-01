"""Выполнение MCP-инструментов."""

import httpx
import logging
from typing import Optional

logger = logging.getLogger(__name__)


async def execute_tool(
    tool_name: str,
    args: dict,
    token: str,
    mcp_url: str = "http://127.0.0.1:3001/mcp"
) -> str:
    """
    Вызывает MCP-инструмент через HTTP.
    
    Args:
        tool_name: Имя инструмента
        args: Аргументы
        token: GitHub токен
        mcp_url: URL MCP-сервера
    
    Returns:
        Текстовый результат выполнения
    """
    if not token:
        raise Exception("GitHub token is not configured")
    
    async with httpx.AsyncClient(timeout=30.0) as client:
        response = await client.post(
            mcp_url,
            json={
                "jsonrpc": "2.0",
                "id": "1",
                "method": "tools/call",
                "params": {
                    "name": tool_name,
                    "arguments": args
                }
            },
            headers={
                "Content-Type": "application/json",
                "Authorization": f"Bearer {token}"
            }
        )
        
        if response.status_code != 200:
            raise Exception(f"HTTP {response.status_code}: {response.text[:200]}")
        
        data = response.json()
        
        if data.get("error"):
            raise Exception(data["error"].get("message", "Unknown error"))
        
        # Извлекаем текст из ответа
        content = data.get("result", {}).get("content", [])
        if content and isinstance(content, list):
            texts = []
            for item in content:
                if isinstance(item, dict) and "text" in item:
                    texts.append(item["text"])
                elif isinstance(item, str):
                    texts.append(item)
            return "\n".join(texts) if texts else "Success (no text content)"
        
        # Если нет content, пробуем получить result как строку
        result = data.get("result")
        if isinstance(result, str):
            return result
        elif isinstance(result, dict):
            import json
            return json.dumps(result, ensure_ascii=False, indent=2)
        
        return str(result) if result else "Success (empty result)"


async def get_tools_list(mcp_url: str, token: str) -> list:
    """
    Получает список доступных инструментов.
    """
    async with httpx.AsyncClient(timeout=10.0) as client:
        response = await client.post(
            mcp_url,
            json={
                "jsonrpc": "2.0",
                "id": "list",
                "method": "tools/list",
                "params": {}
            },
            headers={
                "Content-Type": "application/json",
                "Authorization": f"Bearer {token}"
            }
        )
        
        if response.status_code != 200:
            return []
        
        data = response.json()
        return data.get("result", {}).get("tools", [])
