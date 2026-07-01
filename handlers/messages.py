"""Основной обработчик сообщений."""

import logging
from typing import Optional

from models.message import ProcessRequest, ProcessResponse, ToolResult
from handlers.markers import extract_file_markers, extract_mcp_tags
from handlers.executor import execute_tool

logger = logging.getLogger(__name__)

_file_contents: dict = {}


def get_file_content(filename: str) -> Optional[str]:
    return _file_contents.get(filename)


def set_file_contents(files: dict):
    _file_contents.update(files)


async def process_message(req: ProcessRequest) -> ProcessResponse:
    """Обрабатывает сообщение из чата."""
    try:
        files = extract_file_markers(req.message)
        if files:
            set_file_contents(files)
            logger.info(f"📁 Found files: {list(files.keys())}")
        
        tags = extract_mcp_tags(req.message, _file_contents)
        
        if not tags:
            return ProcessResponse(result=None, files=files)
        
        logger.info(f"🔍 Found tools: {[t['tool'] for t in tags]}")
        
        results = []
        for tag in tags:
            try:
                result_text = await execute_tool(
                    tag['tool'],
                    tag['args'],
                    req.token or "",
                    req.url or ""
                )
                results.append(ToolResult(
                    tool=tag['tool'],
                    success=True,
                    result=result_text  # <-- обязательно передаём result
                ))
                logger.info(f"✅ {tag['tool']}: success")
            except Exception as e:
                results.append(ToolResult(
                    tool=tag['tool'],
                    success=False,
                    error=str(e)
                ))
                logger.error(f"❌ {tag['tool']}: {e}")
        
        if results:
            summary_lines = ["[MCP Tools Executed]", ""]
            for r in results:
                if r.success:
                    prefix = "✅"
                    text = r.result[:500] if r.result else "Success"
                else:
                    prefix = "❌"
                    text = r.error or "Unknown error"
                summary_lines.append(f"{prefix} {r.tool}: {text}")
                summary_lines.append("")
            
            summary = "\n".join(summary_lines).strip()
            return ProcessResponse(result=summary, tools=results, files=files)
        
        return ProcessResponse(result=None, files=files)
        
    except Exception as e:
        logger.error(f"❌ Process error: {e}")
        import traceback
        traceback.print_exc()
        return ProcessResponse(error=str(e))
