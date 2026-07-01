"""Модели данных для обработки сообщений."""

from pydantic import BaseModel
from typing import Optional, List


class ProcessRequest(BaseModel):
    """Запрос на обработку сообщения."""
    message: str
    config: dict = {}
    url: Optional[str] = None
    token: Optional[str] = None


class ToolResult(BaseModel):
    """Результат выполнения инструмента."""
    tool: str
    success: bool
    result: str
    error: Optional[str] = None


class ProcessResponse(BaseModel):
    """Ответ на обработку сообщения."""
    result: Optional[str] = None
    error: Optional[str] = None
    tools: List[ToolResult] = []
    files: dict = {}
