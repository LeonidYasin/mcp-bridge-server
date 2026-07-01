"""Извлечение маркеров из текста."""

import re
import json
import logging
from typing import List, Dict, Optional

logger = logging.getLogger(__name__)


def extract_file_markers(text: str) -> Dict[str, str]:
    """
    Извлекает маркеры ==FILE:...== ==END_FILE==.
    
    Пример:
        ==FILE:test.txt==
        содержимое файла
        ==END_FILE==
    
    Returns:
        {filename: content}
    """
    files = {}
    pattern = r'==FILE:([^==]+?)==\s*([\s\S]*?)\s*==END_FILE=='
    
    for match in re.finditer(pattern, text):
        name = match.group(1).strip()
        content = match.group(2).strip()
        files[name] = content
        logger.debug(f"📁 Found file marker: {name} ({len(content)} chars)")
    
    return files


def extract_mcp_tags(text: str, file_contents: Dict[str, str]) -> List[Dict]:
    """
    Извлекает маркеры ==MCP:tool== {...}.
    
    Пример:
        ==MCP:create_or_update_file== {"owner":"...","content":"==FILE:test.txt=="}
    
    Returns:
        [{'tool': 'create_or_update_file', 'args': {...}}, ...]
    """
    tags = []
    
    # Удаляем блоки кода
    clean = re.sub(r'```[\s\S]*?```', '', text)
    clean = re.sub(r'textCopyDownload[\s\S]*?(?=```|$)', '', clean)
    clean = re.sub(r'`[^`]*?`', '', clean)
    
    # Ищем маркеры
    pattern = r'==MCP:([a-z_]+)==\s*(\{[^]*?\})'
    
    for match in re.finditer(pattern, clean):
        tool_name = match.group(1)
        args_str = match.group(2)
        
        # Подставляем содержимое файлов
        # Ищем ссылку на файл: "content":"==FILE:filename=="
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
                logger.info(f"📄 Replaced ==FILE:{filename}== ({len(content)} chars)")
            else:
                logger.warning(f"⚠️ File not found: {filename}")
        
        try:
            args = json.loads(args_str)
            tags.append({
                'tool': tool_name,
                'args': args,
                'original': match.group(0)
            })
            logger.debug(f"🔍 Found marker: ==MCP:{tool_name}==")
        except json.JSONDecodeError as e:
            logger.error(f"❌ JSON parse error for {tool_name}: {e}")
            logger.debug(f"   Args string: {args_str[:200]}...")
    
    return tags


def extract_all_markers(text: str) -> Dict:
    """
    Извлекает все маркеры из текста.
    
    Returns:
        {'files': {...}, 'tools': [...]}
    """
    files = extract_file_markers(text)
    tools = extract_mcp_tags(text, {})
    return {'files': files, 'tools': tools}
