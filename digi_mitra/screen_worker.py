"""
Digi Mitra Autonomous Screen Worker Engine (ऑटो स्क्रीन वर्कर)
Provides high-reliability system-level GUI and screen automation:
1. Mouse Movement, Clicks & Multi-click
2. Keyboard typing & Shortcut hotkeys (Enter, Alt+Tab, Win, Ctrl+S)
3. Safe Chart / Trendline / Shape drawing on desktop
4. Screen Dimension & Resolution analysis
5. Scroll, Focus, & Window control
"""

import sys
import os
import time
import asyncio
from pathlib import Path
from typing import Dict, Any, List, Optional, Tuple

try:
    import pyautogui
    pyautogui.FAILSAFE = False
    pyautogui.PAUSE = 0.05
except ImportError:
    pyautogui = None

try:
    import pygetwindow as gw
except ImportError:
    gw = None


class AutoScreenWorker:
    def __init__(self, screenshot_dir: str = "./screenshots"):
        self.screenshot_dir = Path(screenshot_dir)
        self.screenshot_dir.mkdir(parents=True, exist_ok=True)
        self.is_active = True

    def get_screen_status(self) -> Dict[str, Any]:
        """Returns screen resolution and active window info"""
        if not pyautogui:
            return {"available": False, "error": "PyAutoGUI not installed"}

        try:
            w, h = pyautogui.size()
            cur = pyautogui.position()
            cur_pos = {"x": cur.x, "y": cur.y}
        except Exception:
            w, h = 1920, 1080
            cur_pos = {"x": 0, "y": 0}

        active_title = "Desktop"
        try:
            if gw:
                win = gw.getActiveWindow()
                if win:
                    active_title = win.title or "Active Window"
        except Exception:
            pass

        return {
            "available": True,
            "width": w,
            "height": h,
            "cursor": cur_pos,
            "active_window": active_title,
            "worker_status": "ONLINE & READY"
        }

    def safe_draw(self, pattern: str = "trendline") -> Dict[str, Any]:
        """Draws visual shapes or trendlines without crashing"""
        if not pyautogui:
            return {"success": False, "error": "PyAutoGUI unavailable"}

        try:
            pyautogui.FAILSAFE = False
            w, h = pyautogui.size()
            mid_x, mid_y = w // 2, h // 2

            # Clamp coordinates safely inside screen bounds
            def clamp_x(x): return max(40, min(w - 40, int(x)))
            def clamp_y(y): return max(40, min(h - 40, int(y)))

            if pattern in ["trendline", "chart"]:
                # Draw a clear ascending trendline
                x1, y1 = clamp_x(mid_x - 160), clamp_y(mid_y + 90)
                x2, y2 = clamp_x(mid_x + 160), clamp_y(mid_y - 90)

                pyautogui.moveTo(x1, y1, duration=0.25)
                pyautogui.mouseDown()
                pyautogui.moveTo(x2, y2, duration=0.45)
                pyautogui.mouseUp()
                msg = f"📈 Screen par Trendline ({x1},{y1}) se ({x2},{y2}) draw kar di gayi!"

            elif pattern in ["box", "rectangle"]:
                # Draw a support/resistance box
                bx1, by1 = clamp_x(mid_x - 120), clamp_y(mid_y - 80)
                bx2, by2 = clamp_x(mid_x + 120), clamp_y(mid_y + 80)

                pyautogui.moveTo(bx1, by1, duration=0.2)
                pyautogui.mouseDown()
                pyautogui.moveTo(bx2, by1, duration=0.2)
                pyautogui.moveTo(bx2, by2, duration=0.2)
                pyautogui.moveTo(bx1, by2, duration=0.2)
                pyautogui.moveTo(bx1, by1, duration=0.2)
                pyautogui.mouseUp()
                msg = "⏹️ Screen par Support/Resistance Box draw ho gaya!"

            elif pattern in ["circle", "highlight"]:
                import math
                radius = 60
                steps = 16
                pts = [
                    (clamp_x(mid_x + radius * math.cos(2 * math.pi * i / steps)),
                     clamp_y(mid_y + radius * math.sin(2 * math.pi * i / steps)))
                    for i in range(steps + 1)
                ]
                pyautogui.moveTo(pts[0][0], pts[0][1], duration=0.2)
                pyautogui.mouseDown()
                for pt in pts[1:]:
                    pyautogui.moveTo(pt[0], pt[1], duration=0.03)
                pyautogui.mouseUp()
                msg = "⭕ Screen center par Focus Circle highlight draw ho gaya!"

            else:
                x1, y1 = clamp_x(mid_x - 100), clamp_y(mid_y)
                x2, y2 = clamp_x(mid_x + 100), clamp_y(mid_y)
                pyautogui.moveTo(x1, y1, duration=0.2)
                pyautogui.mouseDown()
                pyautogui.moveTo(x2, y2, duration=0.3)
                pyautogui.mouseUp()
                msg = "➖ Screen par guide line draw ho gayi!"

            return {"success": True, "message": msg}
        except Exception as e:
            return {"success": False, "error": f"Screen draw error: {str(e)}"}

    def safe_click(self, x: Optional[int] = None, y: Optional[int] = None, clicks: int = 1) -> Dict[str, Any]:
        """Safely clicks mouse at given coordinates or current position"""
        if not pyautogui:
            return {"success": False, "error": "PyAutoGUI unavailable"}

        try:
            pyautogui.FAILSAFE = False
            w, h = pyautogui.size()
            target_x = max(20, min(w - 20, x)) if x is not None else w // 2
            target_y = max(20, min(h - 20, y)) if y is not None else h // 2

            pyautogui.moveTo(target_x, target_y, duration=0.2)
            pyautogui.click(clicks=clicks)
            return {
                "success": True,
                "message": f"🖱️ Mouse click executed at ({target_x}, {target_y}) [{clicks} clicks]"
            }
        except Exception as e:
            return {"success": False, "error": str(e)}

    def safe_type(self, text: str, press_enter: bool = False) -> Dict[str, Any]:
        """Types text smoothly into the active screen element"""
        if not pyautogui:
            return {"success": False, "error": "PyAutoGUI unavailable"}

        try:
            pyautogui.FAILSAFE = False
            # Use clipboard paste if non-ascii / Hindi text to avoid encoding drops
            import pyperclip
            pyperclip.copy(text)
            pyautogui.hotkey('ctrl', 'v')
            if press_enter:
                time.sleep(0.1)
                pyautogui.press('enter')
            return {"success": True, "message": f"⌨️ Text '{text[:50]}' screen par type ho gaya!"}
        except Exception:
            # Fallback direct typewrite
            try:
                pyautogui.typewrite(text, interval=0.03)
                if press_enter:
                    pyautogui.press('enter')
                return {"success": True, "message": f"⌨️ Direct typed '{text[:50]}'"}
            except Exception as e:
                return {"success": False, "error": str(e)}

    def safe_scroll(self, direction: str = "down", amount: int = 400) -> Dict[str, Any]:
        """Scrolls the active window"""
        if not pyautogui:
            return {"success": False, "error": "PyAutoGUI unavailable"}

        try:
            pyautogui.FAILSAFE = False
            clicks = -amount if direction == "down" else amount
            pyautogui.scroll(clicks)
            return {"success": True, "message": f"📜 Screen {direction} scroll ki gayi ({amount} units)"}
        except Exception as e:
            return {"success": False, "error": str(e)}

    def safe_hotkey(self, keys: List[str]) -> Dict[str, Any]:
        """Presses keyboard shortcut like Alt+Tab, Win, Ctrl+S"""
        if not pyautogui:
            return {"success": False, "error": "PyAutoGUI unavailable"}

        try:
            pyautogui.FAILSAFE = False
            pyautogui.hotkey(*keys)
            return {"success": True, "message": f"⚡ Hotkey [{'+'.join(keys)}] press kiya gaya!"}
        except Exception as e:
            return {"success": False, "error": str(e)}

    def execute_natural_command(self, query: str) -> Optional[Dict[str, Any]]:
        """Parses and executes natural language screen worker tasks"""
        q = query.lower()

        # 1. Screen Drawing / Chart Pattern
        if any(w in q for w in ["screen draw", "chart draw", "draw karo", "pattern draw", "line kheencho", "trendline"]):
            pattern = "box" if "box" in q or "dabba" in q else "circle" if "circle" in q or "gola" in q else "trendline"
            return self.safe_draw(pattern)

        # 2. Scrolling
        if any(w in q for w in ["scroll down", "neeche karo", "neeche scroll", "scroll karo", "scroll up", "upar karo"]):
            direction = "up" if any(w in q for w in ["up", "upar"]) else "down"
            return self.safe_scroll(direction=direction)

        # 3. Mouse Clicks
        if any(w in q for w in ["click karo", "screen par click", "mouse click", "double click"]):
            clicks = 2 if "double" in q else 1
            return self.safe_click(clicks=clicks)

        # 4. Window Switches / Hotkeys
        if any(w in q for w in ["window badlo", "switch window", "alt tab", "app badlo"]):
            return self.safe_hotkey(["alt", "tab"])

        if any(w in q for w in ["start menu", "win key", "windows dabao"]):
            return self.safe_hotkey(["win"])

        # 5. General Screen Worker status check
        if any(w in q for w in ["screen worker", "auto screen", "screen status", "screen control"]):
            status = self.get_screen_status()
            return {
                "success": True,
                "message": (
                    f"🖥️ <b>Auto Screen Worker Active Hai:</b><br>"
                    f"• Resolution: <b>{status['width']} x {status['height']} px</b><br>"
                    f"• Cursor Position: ({status['cursor']['x']}, {status['cursor']['y']})<br>"
                    f"• Active Window: <i>{status['active_window']}</i><br>"
                    f"• Controls: <i>Chart Drawing, Mouse Click, Auto Typing, Window Switch & Scroll ready!</i>"
                )
            }

        return None
