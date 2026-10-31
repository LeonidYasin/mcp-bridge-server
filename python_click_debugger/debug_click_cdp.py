"""
DeepSeek Browser CDP Click Debugger (Python + WebSocket / Chrome DevTools Protocol)
==================================================================================
Этот скрипт подключается к вашему запущенному Chrome через порт отладки 9222,
внедряет на страницу chat.deepseek.com яркий неоновый курсор-лазер,
плавно ведет его по экрану к кнопке отправки и выполняет клик с эффектом ударной волны.

Подготовка Chrome (запустить один раз):
    Закройте все окна Chrome и запустите его в командной строке с флагом отладки:
    chrome.exe --remote-debugging-port=9222

Установка зависимостей Python:
    pip install requests websockets
"""

import sys
import time
import json
import asyncio

try:
    import requests
    import websockets
except ImportError:
    print("\n❌ Установите зависимости: pip install requests websockets\n")
    sys.exit(1)

CDP_HTTP_URL = "http://127.0.0.1:9222"


def find_deepseek_tab():
    """Находит открытую вкладку chat.deepseek.com через HTTP API отладки Chrome."""
    try:
        res = requests.get(f"{CDP_HTTP_URL}/json", timeout=3)
        tabs = res.json()
    except Exception as e:
        print(f"\n❌ Не удалось подключиться к Chrome на {CDP_HTTP_URL}: {e}")
        print("\nУбедитесь, что Chrome запущен с флагом отладки:")
        print('  chrome.exe --remote-debugging-port=9222\n')
        return None

    for t in tabs:
        if t.get("type") == "page" and "chat.deepseek.com" in t.get("url", ""):
            print(f"✓ Найдена вкладка DeepSeek: {t.get('title')} ({t.get('url')})")
            return t

    print("⚠ Вкладка chat.deepseek.com не найдена среди открытых вкладок Chrome.")
    # Предлагаем любую страницу, если DeepSeek не найден
    pages = [t for t in tabs if t.get("type") == "page"]
    if pages:
        print(f"Используем первую доступную страницу: {pages[0].get('url')}")
        return pages[0]
    return None


# JavaScript код анимации виртуального лазерного курсора прямо внутри DOM
OVERLAY_JS_CODE = """
(function() {
    let pointer = document.getElementById('py-debug-laser-cursor');
    if (!pointer) {
        pointer = document.createElement('div');
        pointer.id = 'py-debug-laser-cursor';
        pointer.style.cssText = `
            position: fixed;
            left: 0;
            top: 0;
            width: 24px;
            height: 24px;
            margin-left: -12px;
            margin-top: -12px;
            border-radius: 50%;
            background: radial-gradient(circle, #ef4444 0%, #dc2626 50%, rgba(239, 68, 68, 0) 80%);
            border: 2px solid #ffffff;
            box-shadow: 0 0 15px #ef4444, 0 0 30px #ef4444;
            pointer-events: none;
            z-index: 2147483647;
            transform: translate(-100px, -100px);
            transition: transform 0.05s linear;
        `;
        document.documentElement.appendChild(pointer);
    }

    window.__pyMoveCursor = function(x, y) {
        pointer.style.transform = `translate(${Math.round(x)}px, ${Math.round(y)}px)`;
    };

    window.__pyShockwave = function(x, y) {
        const ring = document.createElement('div');
        ring.style.cssText = `
            position: fixed;
            left: ${Math.round(x)}px;
            top: ${Math.round(y)}px;
            width: 60px;
            height: 60px;
            margin-left: -30px;
            margin-top: -30px;
            border-radius: 50%;
            border: 4px solid #38bdf8;
            box-shadow: 0 0 25px #0284c7;
            pointer-events: none;
            z-index: 2147483647;
            transform: scale(0.2);
            opacity: 1;
            transition: transform 0.5s cubic-bezier(0.1, 0.9, 0.2, 1), opacity 0.5s ease-out;
        `;
        document.documentElement.appendChild(ring);
        requestAnimationFrame(() => {
            ring.style.transform = 'scale(2.5)';
            ring.style.opacity = '0';
        });
        setTimeout(() => ring.remove(), 600);
    };

    // Поиск кнопки отправки
    const btn = document.querySelector('button[type="submit"]') ||
                document.querySelector('div[role="button"][class*="send"]') ||
                document.querySelector('button:has(svg path)') ||
                document.querySelector('button[aria-label*="send"]') ||
                document.querySelector('button[aria-label*="отправ"]');

    if (btn) {
        const r = btn.getBoundingClientRect();
        return {
            found: true,
            x: Math.round(r.left + r.width / 2),
            y: Math.round(r.top + r.height / 2),
            width: Math.round(r.width),
            height: Math.round(r.height)
        };
    }
    return { found: false, x: window.innerWidth - 60, y: window.innerHeight - 80 };
})();
"""


async def run_cdp_animated_click(tab):
    ws_url = tab.get("webSocketDebuggerUrl")
    if not ws_url:
        print("❌ Отсутствует webSocketDebuggerUrl у вкладки.")
        return

    print(f"\n🔌 Подключение к WebSocket CDP: {ws_url}...")
    async with websockets.connect(ws_url) as ws:
        msg_id = 0

        async def send_cmd(method, params=None):
            nonlocal msg_id
            msg_id += 1
            payload = {"id": msg_id, "method": method, "params": params or {}}
            await ws.send(json.dumps(payload))
            while True:
                resp = await ws.recv()
                data = json.loads(resp)
                if data.get("id") == msg_id:
                    return data.get("result", {})

        print("✓ Соединение установлено! Активация страницы...")
        await send_cmd("Page.bringToFront")

        # Внедряем оверлей и определяем координаты кнопки
        print("🔍 Определение координат кнопки отправки в DOM...")
        eval_res = await send_cmd("Runtime.evaluate", {
            "expression": OVERLAY_JS_CODE,
            "returnByValue": True
        })
        val = eval_res.get("result", {}).get("value", {})
        target_x = val.get("x", 800)
        target_y = val.get("y", 600)
        found = val.get("found", False)

        print(f"🎯 Координаты кнопки в браузере: x={target_x}, y={target_y} (найдена: {found})")

        # Анимация движения лазерного курсора из центра экрана к кнопке
        start_x, start_y = target_x - 300, target_y - 200
        steps = 35
        print(f"\n✨ Анимация плавного ведения курсора ({steps} шагов)...")

        for i in range(steps + 1):
            t = i / steps
            # Плавная функция замедления ease-out
            ease_t = 1 - (1 - t) ** 3
            cx = start_x + (target_x - start_x) * ease_t
            cy = start_y + (target_y - start_y) * ease_t

            # Двигаем видимый маркер на странице
            await send_cmd("Runtime.evaluate", {
                "expression": f"window.__pyMoveCursor({cx}, {cy});"
            })
            # Посылаем аппаратное событие перемещения мыши Chrome
            await send_cmd("Input.dispatchMouseEvent", {
                "type": "mouseMoved",
                "x": round(cx),
                "y": round(cy)
            })
            await asyncio.sleep(0.02)

        print("💥 Вызов ударной волны и воспроизведение клика...")
        await send_cmd("Runtime.evaluate", {
            "expression": f"window.__pyShockwave({target_x}, {target_y});"
        })

        # Аппаратный клик мыши
        await send_cmd("Input.dispatchMouseEvent", {
            "type": "mousePressed",
            "x": target_x,
            "y": target_y,
            "button": "left",
            "clickCount": 1
        })
        await asyncio.sleep(0.08)
        await send_cmd("Input.dispatchMouseEvent", {
            "type": "mouseReleased",
            "x": target_x,
            "y": target_y,
            "button": "left"
        })

        # Дополнительно: нажать клавишу Enter
        print("⌨️ Посылка аппаратного нажатия клавиши Enter...")
        await send_cmd("Input.dispatchKeyEvent", {
            "type": "rawKeyDown",
            "windowsVirtualKeyCode": 13,
            "key": "Enter",
            "code": "Enter"
        })
        await asyncio.sleep(0.04)
        await send_cmd("Input.dispatchKeyEvent", {
            "type": "keyUp",
            "windowsVirtualKeyCode": 13,
            "key": "Enter",
            "code": "Enter"
        })

        print("\n🎉 ГОТОВО! Проверьте, началась ли генерация в DeepSeek.")


def main():
    print("=" * 60)
    print("🤖 DEEPSEEK CDP ANIMATED CLICK DEBUGGER")
    print("=" * 60)
    tab = find_deepseek_tab()
    if not tab:
        return

    asyncio.run(run_cdp_animated_click(tab))


if __name__ == "__main__":
    main()
