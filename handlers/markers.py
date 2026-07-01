# handlers/markers.py — исправленная версия

import re
import json
import logging
from typing import List, Dict

logger = logging.getLogger(__name__)


def extract_file_markers(text: str) -> Dict[str, str]:
    files = {}
    pattern = r'==FILE:([^=]+?)==\s*([\s\S]*?)\s*==END_FILE=='
    for match in re.finditer(pattern, text):
        name = match.group(1).strip()
        content = match.group(2).strip()
        files[name] = content
        logger.debug(f"📁 Found file marker: {name} ({len(content)} chars)")
    return files


def extract_mcp_tags(text: str, file_contents: Dict[str, str]) -> List[Dict]:
    tags = []
    
    # Удаляем блоки кода
    clean = re.sub(r'```[\s\S]*?```', '', text)
    clean = re.sub(r'textCopyDownload[\s\S]*?(?=```|$)', '', clean)
    clean = re.sub(r'`[^`]*?`', '', clean)
    
    # Ищем маркеры ==MCP:tool== {...}
    # Используем более гибкое выражение — ищем от { до } с учётом вложенности
    pattern = r'==MCP:([a-z_]+)==\s*(\{([^{}]|(?R))*\})'
    
    for match in re.finditer(pattern, clean, re.DOTALL):
        tool_name = match.group(1)
        args_str = match.group(2)
        
        # Проверяем, есть ли ссылка на файл
        file_ref = re.search(r'"content":"==FILE:([^"]+?)==', args_str)
        if file_ref:
            filename = file_ref.group(1)
            if filename in file_contents:
                content = file_contents[filename]
                escaped = json.dumps(content)[1:-1]
                args_str = args_str.replace(
                    f'"content":"==FILE:{filename}=="',
                    f'"content":"{escaped}"'
                )
                logger.info(f"📄 Replaced ==FILE:{filename}== ({len(content)} chars)")
        
        try:
            args = json.loads(args_str)
            tags.append({
                'tool': tool_name,
                'args': args,
                'original': match.group(0)
            })
            logger.info(f"🔍 Found marker: ==MCP:{tool_name}== with args: {args}")
        except json.JSONDecodeError as e:
            logger.error(f"❌ JSON parse error for {tool_name}: {e}")
            logger.error(f"   Args string: {args_str[:200]}...")
    
    return tags
