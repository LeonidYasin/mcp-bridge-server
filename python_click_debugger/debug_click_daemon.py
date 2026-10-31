"""
DeepSeek MCP Python Bridge Daemon (v2.0)
========================================
Этот скрипт запускает локальный HTTP-сервер на порту 8765.
Когда расширение DeepSeek MCP Lite в Chrome получает ответ от MCP-сервера,
оно отправляет запрос на http://127.0.0.1:8765/send.

Этот скрипт мгновенно:
  1. Находит поле ввода и кнопку отправки по проверенным образцам (Template Matching).
  2. Переводит фокус окна и ставит курсор в textarea (двойной клик на высоте -82px).
  3. Вставляет текст через аппаратный Win32 Ctrl+V (устойчив к русской раскладке).
  4. Плавно перемещает курсор к кнопке с круговой анимацией прицеливания.
  5. Производит аппаратный клик мыши и нажимает Enter.

Запуск:
    python debug_click_daemon.py
"""

import os
import sys
import time
import json
import math
import ctypes
from http.server import HTTPServer, BaseHTTPRequestHandler
from threading import Thread

try:
    import pyautogui
    import pyperclip
    from PIL import Image
except ImportError:
    print("\n❌ Установите зависимости: pip install pyautogui pyperclip pillow\n")
    sys.exit(1)

pyautogui.FAILSAFE = True
pyautogui.PAUSE = 0.05

TEMPLATES_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "templates")
PORT = 8765


def play_sound(freq=1200, duration_ms=100):
    try:
        import winsound
        winsound.Beep(freq, duration_ms)
    except Exception:
        print("\a", end="", flush=True)


def win32_paste():
    """Аппаратная эмуляция Ctrl+V через Win32 API (работает при ЛЮБОЙ раскладке)."""
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
    """Аппаратная эмуляция Enter (VK_RETURN = 0x0D)."""
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


def animated_circle_around_point(center_x, center_y, radius=18, steps=20):
    """Анимация прицеливания курсора."""
    for i in range(steps + 1):
        angle = (2 * math.pi / steps) * i
        x = center_x + int(radius * math.cos(angle))
        y = center_y + int(radius * math.sin(angle))
        pyautogui.moveTo(x, y, duration=0.015)


def locate_template(filename, confidence=0.75):
    path = os.path.join(TEMPLATES_DIR, filename)
    if not os.path.exists(path):
        return None
    try:
        box = pyautogui.locateOnScreen(path, confidence=confidence)
        if box:
            center = pyautogui.center(box)
            return int(center.x), int(center.y)
    except Exception:
        pass
    try:
        box = pyautogui.locateOnScreen(path)
        if box:
            center = pyautogui.center(box)
            return int(center.x), int(center.y)
    except Exception:
        pass
    return None


def is_button_active_blue(send_x, send_y):
    try:
        box = (max(0, send_x - 10), max(0, send_y - 10), 20, 20)
        img = pyautogui.screenshot(region=box)
        w, h = img.size
        blue_count = 0
        total = w * h
        for y in range(h):
            for x in range(w):
                r, g, b = img.getpixel((x, y))[:3]
                if b > 165 and (b - r) > 55:
                    blue_count += 1
        return (blue_count / total) >= 0.15
    except Exception:
        return False


def find_deepseek_coordinates():
    send_btn_pos = locate_template("send_button.png", confidence=0.75)
    if not send_btn_pos:
        send_btn_pos = locate_template("arrow_icon.png", confidence=0.7)

    paperclip_pos = locate_template("paperclip.png", confidence=0.75)
    if paperclip_pos and not send_btn_pos:
        send_btn_pos = (paperclip_pos[0] + 46, paperclip_pos[1])

    deepthink_pos = locate_template("deepthink_button.png", confidence=0.75)
    if not deepthink_pos:
        deepthink_pos = locate_template("websearch_button.png", confidence=0.75)

    if not send_btn_pos and not deepthink_pos:
        return None

    if send_btn_pos and deepthink_pos:
        base_y = int((send_btn_pos[1] + deepthink_pos[1]) / 2)
    elif send_btn_pos:
        base_y = send_btn_pos[1]
    else:
        base_y = deepthink_pos[1]

    screen_w, screen_h = pyautogui.size()
    if base_y > screen_h - 45:
        base_y = screen_h - 75

    if not send_btn_pos and deepthink_pos:
        send_btn_pos = (min(screen_w - 70, deepthink_pos[0] + 650), base_y)

    input_x = deepthink_pos[0] + 50 if deepthink_pos else max(150, send_btn_pos[0] - 400)
    input_y = base_y - 82

    return {
        'input': (input_x, input_y),
        'send': send_btn_pos,
        'base_y': base_y
    }


def perform_hardware_send(text):
    print(f"\n📩 Получен сигнал отправки ({len(text)} симв.): «{text[:50]}...»")
    coords = find_deepseek_coordinates()
    if not coords:
        print("⚠ Элементы DeepSeek не найдены на экране. Убедитесь, что окно открыто.")
        return False

    input_x, input_y = coords['input']
    send_x, send_y = coords['send']
    base_y = coords['base_y']

    # 1. Фокус и вставка текста
    pyperclip.copy(text)
    time.sleep(0.05)

    y_offsets = [-82, -72, -92]
    for off in y_offsets:
        target_y = base_y + off
        pyautogui.moveTo(input_x, target_y, duration=0.4, tween=pyautogui.easeInOutQuad)
        pyautogui.click()
        time.sleep(0.1)
        pyautogui.click()
        time.sleep(0.15)
        win32_paste()
        play_sound(1000, 50)
        time.sleep(0.25)
        if is_button_active_blue(send_x, send_y):
            break

    # 2. Плавное скольжение к кнопке отправки
    pyautogui.moveTo(send_x, send_y, duration=0.8, tween=pyautogui.easeInOutQuad)
    animated_circle_around_point(send_x, send_y, radius=18, steps=16)
    pyautogui.moveTo(send_x, send_y, duration=0.1)
    time.sleep(0.1)

    # 3. Аппаратный клик
    play_sound(1200, 80)
    pyautogui.mouseDown(button='left')
    time.sleep(0.08)
    pyautogui.mouseUp(button='left')
    play_sound(1600, 100)
    time.sleep(0.15)

    # 4. Нажатие Enter
    win32_press_enter()
    print("✅ Отправка успешно завершена!\n")
    return True


class BridgeRequestHandler(BaseHTTPRequestHandler):
    def _set_cors_headers(self):
        self.send_header('Access-Control-Allow-Origin', '*')
        self.send_header('Access-Control-Allow-Methods', 'POST, GET, OPTIONS')
        self.send_header('Access-Control-Allow-Headers', 'Content-Type')

    def do_OPTIONS(self):
        self.send_response(200)
        self._set_cors_headers()
        self.end_headers()

    def do_GET(self):
        self.send_response(200)
        self._set_cors_headers()
        self.send_header('Content-Type', 'application/json')
        self.end_headers()
        res = json.dumps({'status': 'ok', 'service': 'DeepSeek MCP Python Bridge v2.0'})
        self.wfile.write(res.encode('utf-8'))

    def do_POST(self):
        if self.path == '/send':
            content_length = int(self.headers.get('Content-Length', 0))
            post_data = self.rfile.read(content_length)
            try:
                data = json.loads(post_data.decode('utf-8'))
                text = data.get('text', '')
                if text:
                    # Выполняем в отдельном потоке, чтобы не блокировать HTTP-ответ
                    Thread(target=perform_hardware_send, args=(text,)).start()
                    self.send_response(200)
                    self._set_cors_headers()
                    self.send_header('Content-Type', 'application/json')
                    self.end_headers()
                    self.wfile.write(json.dumps({'ok': True, 'status': 'executing'}).encode('utf-8'))
                    return
            except Exception as e:
                print("Ошибка обработки запроса:", e)

        self.send_response(400)
        self._set_cors_headers()
        self.end_headers()

    def log_message(self, format, *args):
        # Отключаем лишний спам в консоль
        pass


def run_daemon():
    server = HTTPServer(('127.0.0.1', PORT), BridgeRequestHandler)
    print("=" * 65)
    print(f"🤖 DEEPSEEK MCP PYTHON BRIDGE DAEMON (v2.0) ЗАПУЩЕН")
    print("=" * 65)
    print(f"📡 Локальный сервер слушает порт: http://127.0.0.1:{PORT}")
    print("✨ Когда расширение DeepSeek MCP Lite в Chrome выполнит команду,")
    print("   оно автоматически передаст сигнал сюда, и бот нажмет отправку.")
    print("\nДля остановки нажмите Ctrl+C в этом окне.")
    print("=" * 65 + "\n")
    play_sound(1400, 150)
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\nОстановка сервера...")
        server.server_close()


if __name__ == '__main__':
    run_daemon()
