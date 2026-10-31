"""
DeepSeek Template Matching Clicker (Python + Image Samples) v2.0
================================================================
Этот скрипт использует ТОЧНЫЕ вырезанные образцы (шаблоны) кнопок из вашего скриншота:
  - templates/send_button.png      (круглая кнопка отправки со стрелкой)
  - templates/arrow_icon.png       (белая стрелка внутри кнопки)
  - templates/paperclip.png        (иконка скрепки рядом с кнопкой)
  - templates/deepthink_button.png (кнопка «Глубокое мышление»)
  - templates/websearch_button.png (кнопка «Умный поиск»)

Что исправлено в v2.0:
  1. Точная вертикальная координата поля ввода (Y = Button_Y - 82px), попадающая
     ровно в центр строки ввода «Сообщение для DeepSeek», а не в пустой отступ ниже.
  2. Аппаратный Ctrl+V через Win32 API (VK_CONTROL + VK_V) — работает при ЛЮБОЙ
     раскладке клавиатуры (РУС / ENG), не теряя клавиши.
  3. Двойной клик по полю ввода: 1-й клик активирует окно браузера, 2-й ставит курсор в textarea.
  4. Авто-контроль активации кнопки: проверка, загорелась ли кнопка ярко-синим цветом после вставки текста.
  5. Дублирующая отправка через клавишу Enter (VK_RETURN) + клик по синей кнопке.

Установка библиотек:
    pip install pyautogui pyperclip pillow
"""

import os
import sys
import time
import math
import ctypes
from PIL import Image

try:
    import pyautogui
    import pyperclip
except ImportError:
    print("\n❌ Установите библиотеки: pip install pyautogui pyperclip pillow\n")
    sys.exit(1)

pyautogui.FAILSAFE = True
pyautogui.PAUSE = 0.05

TEMPLATES_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "templates")


def play_sound(freq=1200, duration_ms=100):
    """Воспроизведение системного звукового сигнала."""
    try:
        import winsound
        winsound.Beep(freq, duration_ms)
    except Exception:
        print("\a", end="", flush=True)


def win32_paste():
    """
    Аппаратная эмуляция Ctrl+V через Win32 API.
    VK_CONTROL = 0x11
    VK_V = 0x56 (физическая клавиша V, работает независимо от раскладки RU/EN).
    """
    try:
        user32 = ctypes.windll.user32
        VK_CONTROL = 0x11
        VK_V = 0x56
        KEYEVENTF_KEYUP = 0x0002

        # Ctrl DOWN
        user32.keybd_event(VK_CONTROL, 0, 0, 0)
        time.sleep(0.04)
        # V DOWN
        user32.keybd_event(VK_V, 0, 0, 0)
        time.sleep(0.04)
        # V UP
        user32.keybd_event(VK_V, 0, KEYEVENTF_KEYUP, 0)
        time.sleep(0.04)
        # Ctrl UP
        user32.keybd_event(VK_CONTROL, 0, KEYEVENTF_KEYUP, 0)
        time.sleep(0.08)
        return True
    except Exception:
        pyautogui.hotkey('ctrl', 'v')
        return True


def win32_press_enter():
    """Аппаратная эмуляция нажатия клавиши Enter (VK_RETURN = 0x0D)."""
    try:
        user32 = ctypes.windll.user32
        VK_RETURN = 0x0D
        KEYEVENTF_KEYUP = 0x0002
        user32.keybd_event(VK_RETURN, 0, 0, 0)
        time.sleep(0.04)
        user32.keybd_event(VK_RETURN, 0, KEYEVENTF_KEYUP, 0)
        time.sleep(0.05)
        return True
    except Exception:
        pyautogui.press('enter')
        return True


def animated_circle_around_point(center_x, center_y, radius=20, steps=20):
    """Анимация вращения курсора вокруг цели для визуальной индикации."""
    for i in range(steps + 1):
        angle = (2 * math.pi / steps) * i
        x = center_x + int(radius * math.cos(angle))
        y = center_y + int(radius * math.sin(angle))
        pyautogui.moveTo(x, y, duration=0.015)


def locate_template(filename, confidence=0.75):
    """
    Ищет изображение-шаблон на экране.
    Возвращает центр совпадения (x, y) или None.
    """
    path = os.path.join(TEMPLATES_DIR, filename)
    if not os.path.exists(path):
        return None

    # Попытка поиска с confidence (требует opencv)
    try:
        box = pyautogui.locateOnScreen(path, confidence=confidence)
        if box:
            center = pyautogui.center(box)
            return int(center.x), int(center.y)
    except Exception:
        pass

    # Попытка попиксельного поиска без confidence
    try:
        box = pyautogui.locateOnScreen(path)
        if box:
            center = pyautogui.center(box)
            return int(center.x), int(center.y)
    except Exception:
        pass

    return None


def is_button_active_blue(send_x, send_y):
    """
    Проверяет, стала ли кнопка отправки насыщенно-синей (активной).
    Когда текста нет — кнопка темно-серо-синяя.
    Когда текст вставлен — кнопка становится ярко-синей (#2b7fff / #1d4ed8 / #2563eb).
    """
    try:
        box = (max(0, send_x - 10), max(0, send_y - 10), 20, 20)
        img = pyautogui.screenshot(region=box)
        w, h = img.size
        blue_count = 0
        total = w * h
        for y in range(h):
            for x in range(w):
                r, g, b = img.getpixel((x, y))[:3]
                # Ярко-синий: высокий B, и B заметно превосходит R
                if b > 165 and (b - r) > 55:
                    blue_count += 1
        return (blue_count / total) >= 0.15
    except Exception:
        return False


def find_deepseek_buttons_by_template():
    """
    Ищет кнопки DeepSeek по образцам изображений.
    Возвращает координаты поля ввода и кнопки отправки.
    """
    print("\n🔍 Поиск элементов DeepSeek по образцам изображений (Template Matching)...")

    send_btn_pos = None
    deepthink_pos = None
    paperclip_pos = None

    # 1. Поиск кнопки отправки со стрелкой ↑
    print("  [1/4] Поиск кнопки отправки (send_button.png)...")
    send_btn_pos = locate_template("send_button.png", confidence=0.75)
    
    if not send_btn_pos:
        print("  [2/4] Резервный поиск по белой стрелке (arrow_icon.png)...")
        send_btn_pos = locate_template("arrow_icon.png", confidence=0.7)

    # 2. Поиск иконки скрепки 📎 (ровно в 46px левее кнопки отправки)
    print("  [3/4] Поиск иконки скрепки (paperclip.png)...")
    paperclip_pos = locate_template("paperclip.png", confidence=0.75)

    if paperclip_pos and not send_btn_pos:
        send_btn_pos = (paperclip_pos[0] + 46, paperclip_pos[1])
        print(f"  ✓ Кнопка отправки вычислена от иконки скрепки: ({send_btn_pos[0]}, {send_btn_pos[1]})")

    # 3. Поиск кнопки «Глубокое мышление» или «Умный поиск»
    print("  [4/4] Поиск кнопок режимов («Глубокое мышление» / «Умный поиск»)...")
    deepthink_pos = locate_template("deepthink_button.png", confidence=0.75)
    if not deepthink_pos:
        deepthink_pos = locate_template("websearch_button.png", confidence=0.75)

    if not send_btn_pos and not deepthink_pos:
        print("\n❌ Ни один шаблон не найден на экране.")
        print("Убедитесь, что окно с чатом DeepSeek открыто и не перекрыто другими окнами.")
        return None

    # Определение базовой линии кнопок (Y)
    if send_btn_pos and deepthink_pos:
        base_y = int((send_btn_pos[1] + deepthink_pos[1]) / 2)
    elif send_btn_pos:
        base_y = send_btn_pos[1]
    else:
        base_y = deepthink_pos[1]

    # Защита от попадания на панель задач Windows (taskbar)
    screen_w, screen_h = pyautogui.size()
    if base_y > screen_h - 45:
        base_y = screen_h - 75

    if not send_btn_pos and deepthink_pos:
        send_btn_pos = (min(screen_w - 70, deepthink_pos[0] + 650), base_y)

    # Точный расчет позиции textarea:
    # По высоте: ровно на 82px ВЫШЕ базовой линии кнопок (центр строки ввода)
    # По ширине: берем отступ от левой границы кнопок или правее центра
    input_x = deepthink_pos[0] + 50 if deepthink_pos else max(150, send_btn_pos[0] - 400)
    input_y = base_y - 82

    print(f"\n🎯 НАЙДЕНЫ ЭЛЕМЕНТЫ DEEPSEEK:")
    print(f"   Базовая линия кнопок (Y): {base_y}")
    print(f"   Поле ввода (Textarea):    x={input_x}, y={input_y} (на 82px выше кнопок)")
    print(f"   Кнопка отправки (Send):   x={send_btn_pos[0]}, y={send_btn_pos[1]}")

    return {
        'input': (input_x, input_y),
        'send': send_btn_pos,
        'base_y': base_y
    }


def focus_and_paste_text(input_x, input_y, text, send_x, send_y, base_y):
    """
    Надежно фокусирует поле ввода и вставляет текст.
    Если кнопка не активировалась сразу — пробует микро-смещение по вертикали.
    """
    # Список кандидатов по вертикали:
    # -82px (точный центр), -72px (чуть ниже), -92px (чуть выше), -65px
    y_offsets = [-82, -72, -92, -65]
    
    # Помещаем текст в буфер заранее
    pyperclip.copy(text)
    time.sleep(0.05)

    for attempt, off in enumerate(y_offsets, 1):
        target_y = base_y + off
        print(f"\n👉 [Попытка {attempt}/4] Фокус в textarea: x={input_x}, y={target_y} (offset={off}px)...")
        
        # Плавное движение к полю ввода
        pyautogui.moveTo(input_x, target_y, duration=0.5, tween=pyautogui.easeInOutQuad)
        
        # ДВОЙНОЙ КЛИК: 1-й активирует окно Chrome, 2-й ставит курсор в textarea
        print("   🖱️ Двойной клик (активация окна Chrome + установка каретки)...")
        pyautogui.click()
        time.sleep(0.12)
        pyautogui.click()
        time.sleep(0.15)

        # Аппаратный Ctrl+V
        print("   📋 Вставка текста через аппаратный Ctrl+V (Win32 keybd_event)...")
        win32_paste()
        play_sound(1000, 60)
        time.sleep(0.35)

        # Проверка: загорелась ли кнопка отправки синим цветом?
        if is_button_active_blue(send_x, send_y):
            print("   🎉 УСПЕХ: Кнопка отправки стала ярко-синей! Текст распознан DeepSeek.")
            return True
        else:
            print("   ⚠ Кнопка отправки пока не стала ярко-синей. Проверяем следующую точку...")

    print("   ℹ Завершено тестирование точек фокуса. Переходим к отправке.")
    return True


def execute_cycle(coords_dict, text):
    input_coords = coords_dict['input']
    send_coords = coords_dict['send']
    base_y = coords_dict['base_y']

    input_x, input_y = input_coords
    send_x, send_y = send_coords

    print("\n" + "=" * 60)
    print("🚀 ВЫПОЛНЕНИЕ: ПЛАВНЫЙ ВВОД ТЕКСТА И ОТПРАВКА")
    print("=" * 60)

    # 1. Фокусировка и вставка текста с авто-проверкой
    focus_and_paste_text(input_x, input_y, text, send_x, send_y, base_y)
    time.sleep(0.2)

    # 2. Плавное перемещение к найденной кнопке отправки
    print(f"\n👉 Плавное скольжение курсора к кнопке отправки: ({send_x}, {send_y})...")
    pyautogui.moveTo(send_x, send_y, duration=1.0, tween=pyautogui.easeInOutQuad)

    # 3. Анимация прицеливания (круг вокруг кнопки)
    print("✨ Анимация прицеливания: вращение курсора вокруг кнопки отправки...")
    animated_circle_around_point(send_x, send_y, radius=18, steps=20)
    pyautogui.moveTo(send_x, send_y, duration=0.15)
    time.sleep(0.1)

    # 4. Аппаратный клик по кнопке
    print("💥 НАЖАТИЕ КНОПКИ ОТПРАВКИ МЫШЬЮ!")
    play_sound(1200, 80)
    pyautogui.mouseDown(button='left')
    time.sleep(0.08)
    pyautogui.mouseUp(button='left')
    play_sound(1600, 100)
    time.sleep(0.2)

    # 5. Дублирующая отправка через клавишу Enter (для 100% гарантии)
    print("⌨️ Нажатие Enter (гарантия отправки сообщения в DeepSeek)...")
    win32_press_enter()

    print("\n🎉 ВСЕ ДЕЙСТВИЯ ВЫПОЛНЕНЫ! Проверьте чат DeepSeek на экране.")


def main():
    print("=" * 60)
    print("🤖 DEEPSEEK TEMPLATE MATCHING CLICKER v2.0")
    print("=" * 60)
    print("Убедитесь, что окно браузера с DeepSeek открыто на экране.")
    print("Сканирование начнется через 3 секунды...")
    for i in range(3, 0, -1):
        print(f"⏳ [{i}]...")
        time.sleep(1)

    coords = find_deepseek_buttons_by_template()
    if not coords:
        return

    test_msg = "Привет! Это проверка автоматического клика по образцу изображения v2.0. Ответь одним словом 'УСПЕХ'."
    execute_cycle(coords, test_msg)


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\n\nПрервано пользователем.")
