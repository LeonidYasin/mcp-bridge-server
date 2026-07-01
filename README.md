markdown
# MCP Bridge Server

Локальный сервер для браузерного расширения MCP Bridge.

## Установка

```bash
cd mcp-bridge-server
pip install -e .
Настройка
Создай файл .env:

env
MCP_BRIDGE_HOST=127.0.0.1
MCP_BRIDGE_PORT=8080
MCP_URL=http://127.0.0.1:3001/mcp
GITHUB_TOKEN=ghp_...
Запуск
bash
python server.py
Эндпоинты
GET /health — проверка состояния

GET /tools — список инструментов

POST /process — обработка сообщения

Использование
Отправь POST запрос на /process с телом:

json
{
  "message": "==MCP:list_commits== {...}",
  "config": {"autoSend": true}
}
Разработка
bash
pip install -e ".[dev]"
pytest
Лицензия
MIT
