"""
DeepSeek Click Debugger (PyAutoGUI) — Интерактивная отладка клика мышью с анимацией v2.0
========================================================================================
Этот скрипт запускается на вашем компьютере (Windows) в терминале / VS Code.
Он наглядно демонстрирует движение реального курсора мыши, привлекает внимание
круговой анимацией вокруг кнопки отправки DeepSeek и выполняет аппаратный клик + Enter.

Установка зависимостей:
    pip install pyautogui pyperclip pillow
"""

import sys
import time
import math
import ctypes

try:
    import pyautogui
    import pyperclip
except ImportError:
    print("\n❌ Ошибка: Не установлены необходимые библиотеки.")
    print("Установите их командой:")
    print("    pip install pyautogui pyperclip pillow\n")
    sys.exit(1)

# Защита от потери контроля: резкое движение мыши в любой угол экрана прерывает скрипт
pyautogui.FAILSAFE = True
pyautogui.PAUSE = 0.05


def animated_circle_around_point(center_x, center_y, radius=24, steps=20):
    """Рисует курсором мыши заметный плавный круг вокруг кнопки перед кликом."""
    for i in range(steps + 1):
        angle = (2 * math.pi / steps) * i
        x = center_x + int(radius * math.cos(angle))
        y = center_y + int(radius * math.sin(angle))
        pyautogui.moveTo(x, y, duration=0.015)


def play_sound(freq=1200, duration_ms=120):
    """Воспроизводит системный звуковой сигнал клика на Windows."""
    try:
        import winsound
        winsound.Beep(freq, duration_ms)
    except Exception:
        print("\a", end="", flush=True)


def win32_paste():
    """Аппаратная эмуляция Ctrl+V через Win32 API (работает при любой раскладке клавиатуры)."""
    try:
        user32 = ctypes.windll.user32
        VK_CONTROL = 0x11
        VK_V = 0x56
        KEYEVENTF_KEYUP = 0x0002
        user32.keybd_event(VK_CONTROL, 0, 0, 0)
        time.sleep(0.04)
        user32.keybd_event(VK_V, 0, 0, 0)
        time.sleep(0.04)
        user32.keybd_event(VK_V, 0, KEYEVENTF_KEYUP, 0)
        time.sleep(0.04)
        user32.keybd_event(VK_CONTROL, 0, KEYEVENTF_KEYUP, 0)
        time.sleep(0.08)
        return True
    except Exception:
        pyautogui.hotkey('ctrl', 'v')
        return True


def win32_press_enter():
    """Аппаратная эмуляция Enter."""
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


def execute_visual_click(target_x, target_y, test_text=None):
    """
    Выполняет полный цикл отладки клика с хорошо заметной анимацией курсора.
    """
    screen_w, screen_h = pyautogui.size()
    print(f"\n🖥️ Разрешение экрана: {screen_w}x{screen_h}")
    print(f"🎯 Точка кнопки отправки: ({target_x}, {target_y})")

    # Если передан текст, вставляем его перед кликом
    if test_text:
        print(f"\n📝 Подготовка текста: «{test_text[:40]}...»")
        pyperclip.copy(test_text)
        print("⏳ У вас есть 3 секунды, чтобы переключиться на окно браузера DeepSeek...")
        for i in range(3, 0, -1):
            print(f"   [{i}]...")
            time.sleep(1)

        # Точный расчет позиции поля ввода: ровно на 82px выше кнопки отправки!
        input_x = max(150, target_x - 300)
        input_y = target_y - 82
        print(f"👉 Двойной клик в поле ввода (textarea ровно на 82px выше): ({input_x}, {input_y})...")
        pyautogui.moveTo(input_x, input_y, duration=0.6, tween=pyautogui.easeInOutQuad)
        
        # Двойной клик: окно + фокус
        pyautogui.click()
        time.sleep(0.12)
        pyautogui.click()
        time.sleep(0.2)

        print("📋 Вставка текста (Win32 аппаратный Ctrl+V, независимый от раскладки)...")
        win32_paste()
        play_sound(1000, 70)
        time.sleep(0.5)

    current_x, current_y = pyautogui.position()
    print(f"\n🚀 [Фаза 1/3] Плавное движение курсора из ({current_x}, {current_y}) к кнопке ({target_x}, {target_y})...")
    pyautogui.moveTo(target_x, target_y, duration=1.2, tween=pyautogui.easeInOutQuad)

    print("✨ [Фаза 2/3] Анимация прицеливания: вращение курсора вокруг кнопки...")
    animated_circle_around_point(target_x, target_y, radius=20, steps=20)

    pyautogui.moveTo(target_x, target_y, duration=0.15)
    time.sleep(0.15)

    print("🖱️ [Фаза 3/3] НАЖАТИЕ КНОПКИ МЫШИ!")
    play_sound(1100, 80)
    
    pyautogui.mouseDown(button='left')
    time.sleep(0.08)
    pyautogui.mouseUp(button='left')
    
    play_sound(1600, 100)
    time.sleep(0.2)

    # Дублирование через Enter для надежности
    win32_press_enter()
    print("✅ Клик и отправка успешно завершены!\n")


def calibrate_coordinates():
    """Интерактивный помощник для определения точных координат кнопки."""
    print("\n" + "=" * 60)
    print("🎯 РЕЖИМ КАЛИБРОВКИ КООРДИНАТ")
    print("=" * 60)
    print("1. Откройте окно браузера с DeepSeek на экране.")
    print("2. Наведите курсор мыши ТОЧНО на круглую синюю кнопку отправки (со стрелкой ↑).")
    print("3. Подождите 5 секунд, не двигая мышь...\n")

    for i in range(5, 0, -1):
        x, y = pyautogui.position()
        print(f"⏳ Замер через {i} сек... Текущее положение: x={x}, y={y}")
        time.sleep(1)

    final_x, final_y = pyautogui.position()
    play_sound(1400, 200)
    print(f"\n🎉 КООРДИНАТЫ ЗАФИКСИРОВАНЫ: x={final_x}, y={final_y}")
    return final_x, final_y


def main():
    print("=" * 60)
    print("🤖 DEEPSEEK CLICK DEBUGGER (PYTHON + ANIMATED CURSOR) v2.0")
    print("=" * 60)
    print("Выберите режим отладки:")
    print("  [1] Интерактивная калибровка кнопки (навести мышь на кнопку отправки)")
    print("  [2] Ввести координаты (X, Y) вручную")
    print("  [3] Быстрый тест: текущие координаты мыши")
    print("=" * 60)

    choice = input("Введите номер (1-3) [по умолчанию 1]: ").strip() or "1"

    target_x, target_y = None, None

    if choice == "1":
        target_x, target_y = calibrate_coordinates()
    elif choice == "2":
        try:
            target_x = int(input("Введите X: ").strip())
            target_y = int(input("Введите Y: ").strip())
        except ValueError:
            print("Некорректные числа. Запуск калибровки...")
            target_x, target_y = calibrate_coordinates()
    else:
        target_x, target_y = pyautogui.position()
        print(f"Используем текущие координаты: ({target_x}, {target_y})")

    test_input = input("\nВставить тестовый текст перед кликом? (y/N): ").strip().lower()
    text = None
    if test_input == 'y':
        text = "Тестовый вопрос от Python отладчика клика v2.0: напиши одно слово 'РАБОТАЕТ'."

    print("\n🚀 Запуск теста клика через 2 секунды! Смотрите на экран...")
    time.sleep(2)
    execute_visual_click(target_x, target_y, test_text=text)


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\n\nПрервано пользователем.")
