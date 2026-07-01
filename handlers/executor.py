"""Выполнение MCP-инструментов."""

import httpx
import logging
import json
import re
from typing import Optional

logger = logging.getLogger(__name__)


async def get_tools_list(mcp_url: str, token: str) -> list:
    """Получает список доступных инструментов."""
    if not token:
        return []
    
    if not mcp_url:
        mcp_url = "http://127.0.0.1:3001/mcp"
    
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


async def execute_tool(
    tool_name: str,
    args: dict,
    token: str,
    mcp_url: str = "http://127.0.0.1:3001/mcp"
) -> str:
    """Вызывает MCP-инструмент через HTTP."""
    if not token:
        raise Exception("GitHub token is not configured")
    
    if not mcp_url:
        mcp_url = "http://127.0.0.1:3001/mcp"
    
    logger.debug(f"🔧 Executing {tool_name} with args: {args}")
    
    # Если args пустой — пробуем извлечь из строки
    if not args:
        text = str(args)
        json_match = re.search(r'\{[^}]*\}', text)
        if json_match:
            try:
                args = json.loads(json_match.group(0))
                logger.info(f"🔧 Extracted args from text: {args}")
            except:
                pass
    
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
        
        content = data.get("result", {}).get("content", [])
        if content and isinstance(content, list):
            texts = []
            for item in content:
                if isinstance(item, dict) and "text" in item:
                    texts.append(item["text"])
                elif isinstance(item, str):
                    texts.append(item)
            return "\n".join(texts) if texts else "Success (no text content)"
        
        result = data.get("result")
        if isinstance(result, str):
            return result
        elif isinstance(result, dict):
            return json.dumps(result, ensure_ascii=False, indent=2)
        
        return str(result) if result else "Success (empty result)"
