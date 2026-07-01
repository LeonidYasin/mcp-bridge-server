"""Модели данных."""

from pydantic import BaseModel
from typing import Optional, List


class ProcessRequest(BaseModel):
    message: str
    config: dict = {}
    url: Optional[str] = None
    token: Optional[str] = None


class ToolResult(BaseModel):
    tool: str
    success: bool
    result: str = ""  # значение по умолчанию
    error: Optional[str] = None


class ProcessResponse(BaseModel):
    result: Optional[str] = None
    error: Optional[str] = None
    tools: List[ToolResult] = []
    files: dict = {}
