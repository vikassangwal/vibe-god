import os
import io
import time
import base64
from pathlib import Path
from typing import Dict, Any, Optional, List
from PIL import Image

try:
    import mss
except ImportError:
    mss = None

try:
    import pyautogui
    pyautogui.FAILSAFE = False
except ImportError:
    pyautogui = None

try:
    import pytesseract
except ImportError:
    pytesseract = None


class ScreenVisionAI:
    def __init__(self, capture_dir: str = './data/screen_captures'):
        self.capture_dir = Path(capture_dir)
        self.capture_dir.mkdir(parents=True, exist_ok=True)
        self._setup_tesseract_path()

    def _setup_tesseract_path(self):
        if pytesseract:
            common_paths = [
                r'C:\Program Files\Tesseract-OCR\tesseract.exe',
                r'C:\Program Files (x86)\Tesseract-OCR\tesseract.exe',
                r'C:\Users\HP\AppData\Local\Tesseract-OCR\tesseract.exe'
            ]
            for p in common_paths:
                if os.path.exists(p):
                    pytesseract.pytesseract.tesseract_cmd = p
                    break

    def capture_screenshot(self, save_disk: bool = True) -> Optional[Image.Image]:
        if not mss:
            return None
        try:
            with mss.mss() as sct:
                monitor = sct.monitors[1] if len(sct.monitors) > 1 else sct.monitors[0]
                sct_img = sct.grab(monitor)
                img = Image.frombytes('RGB', sct_img.size, sct_img.bgra, 'raw', 'BGRX')
                if save_disk:
                    save_path = self.capture_dir / 'live_screen.jpg'
                    img.save(str(save_path), quality=75, optimize=True)
                return img
        except Exception as e:
            print('Screenshot error:', e)
            return None

    def get_live_screen_base64(self, max_width: int = 800) -> Dict[str, Any]:
        img = self.capture_screenshot(save_disk=False)
        if not img:
            return {'success': False, 'error': 'Could not capture screen'}

        try:
            w, h = img.size
            if w > max_width:
                new_h = int((max_width / w) * h)
                img = img.resize((max_width, new_h), Image.LANCZOS)

            buffer = io.BytesIO()
            img.save(buffer, format='JPEG', quality=65)
            b64_str = base64.b64encode(buffer.getvalue()).decode('utf-8')

            return {
                'success': True,
                'image_b64': 'data:image/jpeg;base64,' + b64_str,
                'width': w,
                'height': h,
                'timestamp': time.time()
            }
        except Exception as e:
            return {'success': False, 'error': str(e)}

    def find_and_click_text(self, target_text: str) -> Dict[str, Any]:
        if not pytesseract:
            return {'success': False, 'error': 'Tesseract OCR not configured'}

        img = self.capture_screenshot(save_disk=False)
        if not img:
            return {'success': False, 'error': 'Screen capture failed'}

        try:
            data = pytesseract.image_to_data(img, output_type=pytesseract.Output.DICT)
            n_boxes = len(data['text'])
            target_lower = target_text.strip().lower()

            matches = []
            for i in range(n_boxes):
                text_val = data['text'][i].strip().lower()
                if target_lower in text_val and int(data['conf'][i]) > 30:
                    x, y, w, h = data['left'][i], data['top'][i], data['width'][i], data['height'][i]
                    center_x = x + w // 2
                    center_y = y + h // 2
                    matches.append({'text': data['text'][i], 'x': center_x, 'y': center_y, 'conf': data['conf'][i]})

            if not matches:
                return {'success': False, 'error': 'Target text screen par nahi mila'}

            best = matches[0]
            bx, by = best['x'], best['y']
            bt = best['text']
            if pyautogui:
                pyautogui.FAILSAFE = False
                pyautogui.moveTo(bx, by, duration=0.35)
                pyautogui.click()
                return {
                    'success': True,
                    'message': f'Screen par {bt} mila aur click kar diya ({bx}, {by})!',
                    'location': best
                }
            return {'success': True, 'message': f'Found at ({bx}, {by})'}

        except Exception as e:
            return {'success': False, 'error': f'OCR Error: {str(e)}'}
