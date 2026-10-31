"""
DeepSeek OCR Click & Input Debugger (Python + OCR + Animated Cursor)
===================================================================
Скрипт автоматически находит поле ввода и кнопку отправки DeepSeek на экране
с помощью оптического распознавания текста (OCR), вставляет текст и плавно
кликает по кнопке с наглядной анимацией курсора мыши.

Установка библиотек:
    pip install easyocr pyautogui pyperclip pillow

(Если easyocr еще не установлен, скрипт также проверит rapidocr, pytesseract или winocr).
"""

import os
import sys
import time
import math
import ssl
from PIL import Image, ImageDraw, ImageFont

# Обход SSL ошибки загрузки моделей EasyOCR в Windows (CERTIFICATE_VERIFY_FAILED)
try:
    ssl._create_default_https_context = ssl._create_unverified_context
except Exception:
    pass

# Проверка базовых библиотек управления экраном
try:
    import pyautogui
    import pyperclip
except ImportError:
    print("\n❌ Ошибка: Не установлены базовые библиотеки.")
    print("Установите их командой:")
    print("    pip install pyautogui pyperclip pillow\n")
    sys.exit(1)

pyautogui.FAILSAFE = True
pyautogui.PAUSE = 0.05

# ── Инициализация OCR движка с авто-выбором ─────────────────────────────────
ocr_engine = None
ocr_engine_name = None

def init_ocr():
    global ocr_engine, ocr_engine_name
    
    # 1. Пробуем EasyOCR (наиболее точный для русского + английского)
    try:
        import easyocr
        print("⏳ Инициализация EasyOCR (русский + английский)...")
        ocr_engine = easyocr.Reader(['ru', 'en'], gpu=False)
        ocr_engine_name = 'easyocr'
        print("✓ EasyOCR готов к работе.")
        return True
    except ImportError:
        pass

    # 2. Пробуем RapidOCR (быстрый ONNX)
    try:
        from rapidocr_onnxruntime import RapidOCR
        print("⏳ Инициализация RapidOCR...")
        ocr_engine = RapidOCR()
        ocr_engine_name = 'rapidocr'
        print("✓ RapidOCR готов к работе.")
        return True
    except ImportError:
        pass

    # 3. Пробуем PyTesseract
    try:
        import pytesseract
        ocr_engine = pytesseract
        ocr_engine_name = 'pytesseract'
        print("✓ PyTesseract обнаружен.")
        return True
    except ImportError:
        pass

    # 4. Пробуем WinOCR (Windows 10/11 native)
    try:
        import winocr
        ocr_engine = winocr
        ocr_engine_name = 'winocr'
        print("✓ WinOCR обнаружен.")
        return True
    except ImportError:
        pass

    print("\n" + "=" * 65)
    print("❌ ДВИЖОК OCR НЕ НАЙДЕН!")
    print("=" * 65)
    print("Для автоматического поиска элементов установите EasyOCR:")
    print("    pip install easyocr")
    print("\nИли более легкий RapidOCR:")
    print("    pip install rapidocr-onnxruntime")
    print("=" * 65 + "\n")
    return False


def run_ocr_on_image(pil_image):
    """
    Выполняет OCR на переданном изображении PIL и возвращает список элементов:
    [{ 'text': '...', 'box': (x1, y1, x2, y2), 'center': (cx, cy) }, ...]
    """
    results = []

    if ocr_engine_name == 'easyocr':
        import numpy as np
        img_np = np.array(pil_image)
        raw_res = ocr_engine.readtext(img_np)
        for item in raw_res:
            bbox, text, conf = item
            if conf < 0.2:
                continue
            x1 = int(min(p[0] for p in bbox))
            y1 = int(min(p[1] for p in bbox))
            x2 = int(max(p[0] for p in bbox))
            y2 = int(max(p[1] for p in bbox))
            cx = (x1 + x2) // 2
            cy = (y1 + y2) // 2
            results.append({
                'text': text.strip(),
                'box': (x1, y1, x2, y2),
                'center': (cx, cy),
                'conf': conf
            })

    elif ocr_engine_name == 'rapidocr':
        import numpy as np
        img_np = np.array(pil_image)
        raw_res, _ = ocr_engine(img_np)
        if raw_res:
            for item in raw_res:
                bbox, text, conf = item
                x1 = int(min(p[0] for p in bbox))
                y1 = int(min(p[1] for p in bbox))
                x2 = int(max(p[0] for p in bbox))
                y2 = int(max(p[1] for p in bbox))
                results.append({
                    'text': text.strip(),
                    'box': (x1, y1, x2, y2),
                    'center': ((x1 + x2) // 2, (y1 + y2) // 2),
                    'conf': conf
                })

    elif ocr_engine_name == 'pytesseract':
        import pytesseract
        data = pytesseract.image_to_data(pil_image, lang='rus+eng', output_type=pytesseract.Output.DICT)
        n_boxes = len(data['text'])
        for i in range(n_boxes):
            txt = data['text'][i].strip()
            if not txt:
                continue
            x1 = data['left'][i]
            y1 = data['top'][i]
            w = data['width'][i]
            h = data['height'][i]
            results.append({
                'text': txt,
                'box': (x1, y1, x1 + w, y1 + h),
                'center': (x1 + w // 2, y1 + h // 2),
                'conf': float(data['conf'][i]) / 100.0
            })

    return results


def find_deepseek_ui_by_ocr():
    """
    Сканирует экран, распознает ключевые маркеры интерфейса DeepSeek:
    - 'Глубокое мышление' / 'мышление' / 'Умный поиск' / 'поиск' (нижняя панель)
    - 'Спросите' / 'Message' / 'Tool' / 'Result' (зона поля ввода)
    - 'Сгенерировано ИИ' (подвал под полем ввода)
    
    Возвращает словарь:
    {
        'input_coords': (x, y),
        'button_coords': (x, y),
        'landmarks': [...]
    }
    """
    screen_w, screen_h = pyautogui.size()
    print(f"\n📸 Снимок экрана ({screen_w}x{screen_h})...")
    
    # Делаем скриншот нижней половины экрана (где всегда располагается окно ввода чата)
    crop_top = int(screen_h * 0.35)
    crop_height = screen_h - crop_top
    screenshot = pyautogui.screenshot(region=(0, crop_top, screen_w, crop_height))

    print(f"🔍 Запуск распознавания текста (OCR) в нижней части экрана (Y от {crop_top}px)...")
    ocr_items = run_ocr_on_image(screenshot)
    print(f"✓ Распознано {len(ocr_items)} текстовых блоков на экране.")

    # Переводим локальные координаты скриншота в абсолютные координаты экрана
    for it in ocr_items:
        bx1, by1, bx2, by2 = it['box']
        cx, cy = it['center']
        it['abs_box'] = (bx1, by1 + crop_top, bx2, by2 + crop_top)
        it['abs_center'] = (cx, cy + crop_top)

    # Ищем маркеры DeepSeek (СТРОГО исключая панель задач Windows)
    toolbar_item = None
    input_item = None
    taskbar_boundary = screen_h - 55  # Все, что ниже этого, является панелью задач Windows

    for it in ocr_items:
        # 1. Защита: полностью игнорируем любые элементы на панели задач Windows
        if it['abs_center'][1] >= taskbar_boundary:
            continue

        t = it['text'].lower()

        # 2. Поиск маркеров тулбара DeepSeek (слова, которых НЕТ на панели задач Windows)
        if any(w in t for w in ['мышлен', 'глубок', 'deepthink']):
            toolbar_item = it
            print(f"  🎯 Найден тулбар DeepSeek («{it['text']}») в ({it['abs_center'][0]}, {it['abs_center'][1]})")
        elif 'умный' in t and 'поиск' in t:
            if not toolbar_item:
                toolbar_item = it
                print(f"  🎯 Найден «Умный поиск» в ({it['abs_center'][0]}, {it['abs_center'][1]})")

        # 3. Поиск поля ввода DeepSeek («Сообщение для DeepSeek», «Спросите» и т.д.)
        if any(w in t for w in ['сообщение', 'deepseek', 'спросите', 'message', 'tool result', 'tool execution', 'completed']):
            input_item = it
            print(f"  📝 Найдено поле ввода («{it['text']}») в ({it['abs_center'][0]}, {it['abs_center'][1]})")

    if not toolbar_item and not input_item:
        print("\n⚠ OCR не нашел «Глубокое мышление» или поле ввода DeepSeek.")
        print("Распознанные строки выше панели задач:")
        for it in ocr_items:
            if it['abs_center'][1] < taskbar_boundary:
                print(f"   - «{it['text']}» в {it['abs_center']}")
        return None

    # Вычисляем базовую высоту строки кнопок тулбара DeepSeek
    if toolbar_item:
        base_y = toolbar_item['abs_center'][1]
        ref_x = toolbar_item['abs_center'][0]
    else:
        base_y = input_item['abs_center'][1] + 55
        ref_x = input_item['abs_center'][0]

    # Координаты поля ввода (textarea гарантированно находится на 55px выше «Глубокое мышление»)
    input_x = ref_x + 60
    input_y = base_y - 55

    print(f"📍 Опорные точки DeepSeek:")
    print(f"   Поле ввода (Textarea): x={input_x}, y={input_y}")
    print(f"   Линия тулбара: Y={base_y}")

    return {
        'input_coords': (input_x, input_y),
        'toolbar_y': base_y,
        'ref_x': ref_x,
        'crop_top': crop_top
    }


def find_active_blue_send_button(toolbar_y, ref_x):
    """
    Сканирует горизонтальную полосу тулбара (toolbar_y ± 20px) в поисках
    круглой синей кнопки отправки, которая стала ярко-синей ПОСЛЕ ввода текста.
    """
    screen_w, screen_h = pyautogui.size()
    strip_top = max(0, toolbar_y - 20)
    strip_bottom = min(screen_h - 45, toolbar_y + 20)
    strip_h = strip_bottom - strip_top
    strip_w = screen_w

    print(f"🔍 Сканирование полосы тулбара Y={toolbar_y} в поисках активной синей кнопки DeepSeek...")
    strip_img = pyautogui.screenshot(region=(0, strip_top, strip_w, strip_h))

    found_blue_pixels = []
    # Сканируем справа налево, начиная с правой границы экрана к центру
    for x in range(strip_w - 30, max(20, ref_x + 100), -2):
        for y in range(0, strip_h, 2):
            r, g, b = strip_img.getpixel((x, y))
            # Яркий насыщенный синий цвет активированной кнопки отправки DeepSeek (#2563eb / #1d4ed8 / #1e80ff)
            if b > 180 and (b - r) > 70 and (b - g) > 30:
                found_blue_pixels.append((x, strip_top + y))
        if len(found_blue_pixels) > 16:
            break

    if found_blue_pixels:
        btn_x = sum(p[0] for p in found_blue_pixels) // len(found_blue_pixels)
        btn_y = sum(p[1] for p in found_blue_pixels) // len(found_blue_pixels)
        print(f"✓ ТОЧНО НАЙДЕНА СИНЯЯ КНОПКА ОТПРАВКИ: x={btn_x}, y={btn_y}")
        return btn_x, btn_y

    # Резервный расчет по геометрии контейнера
    fallback_x = min(screen_w - 80, ref_x + 650)
    print(f"⚠ Синие пиксели не найдены с первой попытки, используем геометрию: x={fallback_x}, y={toolbar_y}")
    return fallback_x, toolbar_y


def animated_circle_around_point(center_x, center_y, radius=22, steps=20):
    """Анимация вращения курсора вокруг цели для четкой видимости."""
    for i in range(steps + 1):
        angle = (2 * math.pi / steps) * i
        x = center_x + int(radius * math.cos(angle))
        y = center_y + int(radius * math.sin(angle))
        pyautogui.moveTo(x, y, duration=0.015)


def play_sound(freq=1200, duration_ms=100):
    try:
        import winsound
        winsound.Beep(freq, duration_ms)
    except Exception:
        print("\a", end="", flush=True)


def main():
    print("=" * 65)
    print("🤖 DEEPSEEK OCR CLICK & INPUT AUTOMATION")
    print("=" * 65)

    if not init_ocr():
        print("Пожалуйста, установите easyocr: pip install easyocr")
        input("Нажмите Enter для выхода...")
        return

    print("\nПодготовка к авто-сканированию экрана через 3 секунды.")
    print("Переключитесь на окно браузера с открытым чатом DeepSeek!")
    for i in range(3, 0, -1):
        print(f"⏳ [{i}]...")
        time.sleep(1)

    ui_info = find_deepseek_ui_by_ocr()

    if not ui_info:
        print("\n❌ Не удалось автоматически определить элементы через OCR.")
        print("Убедитесь, что окно браузера развернуто и чат виден на экране.")
        return

    input_x, input_y = ui_info['input_coords']
    toolbar_y = ui_info['toolbar_y']
    ref_x = ui_info['ref_x']

    test_msg = "Привет! Это проверка автоматического клика и ввода через Python OCR. Ответь одним словом 'УСПЕХ'."

    # 1. Плавное движение курсора к полю ввода и вставка текста
    print(f"\n👉 [Шаг 1/4] Перемещение в поле ввода DeepSeek: ({input_x}, {input_y})...")
    pyautogui.moveTo(input_x, input_y, duration=0.8, tween=pyautogui.easeInOutQuad)
    pyautogui.click()
    time.sleep(0.2)

    print("📋 [Шаг 2/4] Вставка текста через Ctrl+V...")
    pyperclip.copy(test_msg)
    time.sleep(0.1)
    pyautogui.hotkey('ctrl', 'v')
    print(f"✓ Текст вставлен ({len(test_msg)} симв.)")

    # 2. Ждем активации синей кнопки (React меняет цвет кнопки с серого на ярко-синий)
    time.sleep(0.4)

    # 3. Теперь, когда кнопка стала ярко-синей, сканируем ее точное положение
    btn_x, btn_y = find_active_blue_send_button(toolbar_y, ref_x)

    # 4. Плавно ведем курсор к кнопке, делаем круг и жмем
    print(f"\n👉 [Шаг 3/4] Плавное движение к синей кнопке отправки: ({btn_x}, {btn_y})...")
    pyautogui.moveTo(btn_x, btn_y, duration=1.2, tween=pyautogui.easeInOutQuad)

    print("✨ [Шаг 4/4] Анимация прицеливания (вращение вокруг кнопки)...")
    animated_circle_around_point(btn_x, btn_y, radius=20, steps=20)
    pyautogui.moveTo(btn_x, btn_y, duration=0.15)
    time.sleep(0.1)

    print("💥 НАЖАТИЕ КНОПКИ ОТПРАВКИ (MouseDown + MouseUp)!")
    play_sound(1200, 80)
    pyautogui.mouseDown(button='left')
    time.sleep(0.08)
    pyautogui.mouseUp(button='left')
    play_sound(1600, 120)

    print("\n🎉 ГОТОВО! Проверьте, началась ли генерация ответа в DeepSeek.")


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\n\nПрервано пользователем.")
