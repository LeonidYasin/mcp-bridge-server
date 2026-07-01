"""Извлечение маркеров из текста."""

import re
import json
import logging
from typing import List, Dict

logger = logging.getLogger(__name__)


def extract_file_markers(text: str) -> Dict[str, str]:
    """Извлекает маркеры ==FILE:...== ==END_FILE==."""
    files = {}
    pattern = r'==FILE:([^=]+?)==\s*([\s\S]*?)\s*==END_FILE=='
    for match in re.finditer(pattern, text):
        name = match.group(1).strip()
        content = match.group(2).strip()
        files[name] = content
        logger.debug(f"📁 Found file marker: {name} ({len(content)} chars)")
    return files


def extract_mcp_tags(text: str, file_contents: Dict[str, str]) -> List[Dict]:
    """Извлекает маркеры ==MCP:tool== {...} с учётом вложенных JSON."""
    tags = []
    
    # Удаляем блоки кода
    clean = re.sub(r'```[\s\S]*?```', '', text)
    clean = re.sub(r'textCopyDownload[\s\S]*?(?=```|$)', '', clean)
    clean = re.sub(r'`[^`]*?`', '', clean)
    
    # Сначала находим все маркеры ==MCP:tool==
    marker_pattern = r'==MCP:([a-z_]+)=='
    
    for match in re.finditer(marker_pattern, clean):
        tool_name = match.group(1)
        start_pos = match.end()
        
        # Находим открывающую скобку JSON
        json_start = clean.find('{', start_pos)
        if json_start == -1:
            logger.warning(f"⚠️ No JSON start for {tool_name}")
            continue
        
        # Ищем закрывающую скобку с учётом вложенности
        depth = 0
        json_end = -1
        in_string = False
        escape_next = False
        
        for i in range(json_start, len(clean)):
            char = clean[i]
            
            if escape_next:
                escape_next = False
                continue
            
            if char == '\\':
                escape_next = True
                continue
            
            if char == '"' and not escape_next:
                in_string = not in_string
                continue
            
            if not in_string:
                if char == '{':
                    depth += 1
                elif char == '}':
                    depth -= 1
                    if depth == 0:
                        json_end = i + 1
                        break
        
        if json_end == -1:
            logger.warning(f"⚠️ No JSON end for {tool_name}")
            continue
        
        args_str = clean[json_start:json_end]
        
        # Подставляем содержимое файлов, если есть ссылка
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
                'original': match.group(0) + args_str
            })
            logger.info(f"🔍 Found marker: ==MCP:{tool_name}== with args: {args}")
        except json.JSONDecodeError as e:
            logger.error(f"❌ JSON parse error for {tool_name}: {e}")
            logger.error(f"   Args string: {args_str[:200]}...")
    
    return tags
