"""MCP Bridge Server — обрабатывает маркеры и вызывает MCP-инструменты."""

import json
import re
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
import httpx
import uvicorn

app = FastAPI(title="MCP Bridge Server")

# Конфигурация
MCP_SERVER_URL = "http://127.0.0.1:3001/mcp"
GITHUB_TOKEN = ""  # Загружается из настроек

# Модели
class ProcessRequest(BaseModel):
    message: str
    config: dict

class ProcessResponse(BaseModel):
    result: str | None
    error: str | None

# Хранилище файлов из ==FILE:...==
file_contents = {}

# ============================================================
# 1. Парсинг маркеров
# ============================================================

def extract_file_markers(text: str) -> dict:
    """Извлекает ==FILE:...== ==END_FILE== маркеры"""
    files = {}
    pattern = r'==FILE:([^==]+?)==\s*([\s\S]*?)\s*==END_FILE=='
    for match in re.finditer(pattern, text):
        name = match.group(1).strip()
        content = match.group(2)
        files[name] = content
    return files

def extract_mcp_tags(text: str) -> list:
    """Извлекает ==MCP:tool== {...} маркеры"""
    tags = []
    # Удаляем блоки кода
    clean = re.sub(r'```[\s\S]*?```', '', text)
    clean = re.sub(r'textCopyDownload[\s\S]*?(?=```|$)', '', clean)
    
    # Ищем маркеры для известных инструментов
    # Сначала запрашиваем список из MCP-сервера
    pattern = r'==MCP:([a-z_]+)==\s*(\{[^]*?\})'
    for match in re.finditer(pattern, clean):
        tool_name = match.group(1)
        args_str = match.group(2)
        
        # Подставляем содержимое файлов
        # Ищем ссылки на файлы в аргументах
        file_ref = re.search(r'"content":"==FILE:([^"]+?)==', args_str)
        if file_ref:
            filename = file_ref.group(1)
            if filename in file_contents:
                content = file_contents[filename]
                # Экранируем для JSON
                escaped = json.dumps(content)[1:-1]
                args_str = args_str.replace(
                    f'"content":"==FILE:{filename}=="',
                    f'"content":"{escaped}"'
                )
        
        try:
            args = json.loads(args_str)
            tags.append({
                'tool': tool_name,
                'args': args,
                'original': match.group(0)
            })
        except json.JSONDecodeError as e:
            print(f"❌ JSON parse error: {e}")
    
    return tags

# ============================================================
# 2. Выполнение инструментов
# ============================================================

async def execute_tool(tool_name: str, args: dict) -> str:
    """Вызывает MCP-инструмент через HTTP"""
    async with httpx.AsyncClient() as client:
        response = await client.post(
            MCP_SERVER_URL,
            json={
                "jsonrpc": "2.0",
                "id": "1",
                "method": "tools/call",
                "params": {"name": tool_name, "arguments": args}
            },
            headers={"Authorization": f"Bearer {GITHUB_TOKEN}"}
        )
        
        if response.status_code != 200:
            raise Exception(f"HTTP {response.status_code}: {response.text}")
        
        data = response.json()
        if data.get("error"):
            raise Exception(data["error"]["message"])
        
        # Извлекаем текст из ответа
        content = data.get("result", {}).get("content", [])
        if content and isinstance(content, list):
            return "\n".join(c.get("text", "") for c in content)
        return str(data.get("result", {}))

# ============================================================
# 3. Обработка сообщения
# ============================================================

@app.post("/process")
async def process_message(req: ProcessRequest) -> ProcessResponse:
    """Обрабатывает сообщение из чата"""
    try:
        # 1. Извлекаем файлы
        files = extract_file_markers(req.message)
        file_contents.update(files)
        
        # 2. Извлекаем MCP-теги
        tags = extract_mcp_tags(req.message)
        
        if not tags:
            return ProcessResponse(result=None)
        
        # 3. Выполняем инструменты
        results = []
        for tag in tags:
            try:
                result = await execute_tool(tag['tool'], tag['args'])
                results.append(f"✅ {tag['tool']}: {result[:500]}")
            except Exception as e:
                results.append(f"❌ {tag['tool']}: {str(e)}")
        
        # 4. Формируем ответ
        summary = "[MCP Tools Executed]\n\n" + "\n\n".join(results)
        return ProcessResponse(result=summary)
        
    except Exception as e:
        return ProcessResponse(error=str(e))

# ============================================================
# 4. Health check
# ============================================================

@app.get("/health")
async def health():
    return {"status": "ok", "tools": list(file_contents.keys())}

# ============================================================
# 5. Запуск
# ============================================================

if __name__ == "__main__":
    uvicorn.run(app, host="127.0.0.1", port=8080)
