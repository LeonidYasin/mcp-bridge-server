def extract_mcp_tags(text: str, file_contents: Dict[str, str]) -> List[Dict]:
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
        
        # ПРОВЕРКА: если это плейсхолдер, пропускаем
        if args_str in ['{...}', '{tool_name}']:
            logger.debug(f"⏭️ Skipping placeholder for {tool_name}")
            continue
        
        # ПРОВЕРКА: если в args_str есть \", значит это экранированный JSON внутри строки
        if '\\"' in args_str:
            # Пробуем убрать экранирование
            try:
                # Заменяем \" на "
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
