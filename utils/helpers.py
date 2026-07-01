"""Вспомогательные функции."""

import json
from typing import Any, Optional


def escape_json(text: str) -> str:
    """Экранирует текст для вставки в JSON."""
    return json.dumps(text)[1:-1]


def truncate_text(text: str, max_length: int = 500) -> str:
    """Обрезает текст до указанной длины."""
    if len(text) <= max_length:
        return text
    return text[:max_length] + "..."


def safe_json_parse(text: str) -> Optional[dict]:
    """Безопасно парсит JSON."""
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        return None


def format_tool_result(tool_name: str, success: bool, result: str, error: str = None) -> str:
    """Форматирует результат выполнения инструмента."""
    if success:
        return f"✅ {tool_name}: {truncate_text(result)}"
    else:
        return f"❌ {tool_name}: {error or 'Unknown error'}"
