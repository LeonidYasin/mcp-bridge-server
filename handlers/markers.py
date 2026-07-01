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
    """Извлекает маркеры ==MCP:tool== {...}."""
    tags = []
    
    # Ищем маркеры ==MCP:tool==
    marker_pattern = r'==MCP:([a-z_]+)=='
    
    for match in re.finditer(marker_pattern, text):
        tool_name = match.group(1)
        start_pos = match.end()
        
        # Находим JSON объект
        json_start = text.find('{', start_pos)
        if json_start == -1:
            continue
        
        # Ищем закрывающую скобку
        depth = 0
        json_end = -1
        in_string = False
        escape = False
        
        for i in range(json_start, len(text)):
            ch = text[i]
            if escape:
                escape = False
                continue
            if ch == '\\':
                escape = True
                continue
            if ch == '"' and not escape:
                in_string = not in_string
                continue
            if not in_string:
                if ch == '{':
                    depth += 1
                elif ch == '}':
                    depth -= 1
                    if depth == 0:
                        json_end = i + 1
                        break
        
        if json_end == -1:
            continue
        
        args_str = text[json_start:json_end]
        
        # Пропускаем плейсхолдеры
        if args_str in ['{...}', '{tool_name}']:
            logger.debug(f"⏭️ Skipping placeholder for {tool_name}")
            continue
        
        # Пробуем исправить экранированные кавычки
        if '\\"' in args_str:
            try:
                fixed_args = args_str.replace('\\"', '"')
                args = json.loads(fixed_args)
                tags.append({
                    'tool': tool_name,
                    'args': args,
                    'original': match.group(0) + fixed_args
                })
                logger.info(f"🔍 Found marker (fixed): ==MCP:{tool_name}== with args: {args}")
                continue
            except:
                logger.debug(f"⏭️ Skipping escaped JSON for {tool_name}")
                continue
        
        # Парсим JSON
        try:
            args = json.loads(args_str)
            tags.append({
                'tool': tool_name,
                'args': args,
                'original': match.group(0) + args_str
            })
            logger.info(f"✅ Found marker: ==MCP:{tool_name}== with args: {args}")
        except json.JSONDecodeError as e:
            # Просто логируем, но не прерываем
            logger.debug(f"⏭️ Skipping invalid JSON for {tool_name}: {e}")
    
    return tags
