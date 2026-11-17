"""
PyAutoGUI Fallback Module for Wife God Agent
System-level automation with OpenCV template matching for when Playwright fails
"""

import asyncio
import logging
import time
import os
import tempfile
from pathlib import Path
from typing import Dict, Any, List, Optional, Tuple
from dataclasses import dataclass
from datetime import datetime

try:
    import pyautogui
    import pygetwindow as gw
except ImportError:
    pyautogui = None
    gw = None

try:
    import cv2
    import numpy as np
except ImportError:
    cv2 = None
    np = None

try:
    from PIL import ImageGrab, Image
except ImportError:
    ImageGrab = None
    Image = None

logger = logging.getLogger("WifeGod.PyAutoGUIFallback")


@dataclass
class FallbackConfig:
    enabled: bool = True
    template_threshold: float = 0.8
    click_delay: float = 0.1
    type_delay: float = 0.05
    screenshot_dir: str = "./screenshots/templates"


@dataclass
class TemplateMatch:
    name: str
    confidence: float
    position: Tuple[int, int]  # (x, y) center
    size: Tuple[int, int]  # (w, h)


class PyAutoGUIFallback:
    """
    PyAutoGUI fallback for system-level automation
    - Template matching with OpenCV
    - Screen capture and analysis
    - Mouse/keyboard automation
    """

    def __init__(self, config: Dict[str, Any]):
        self.config = FallbackConfig(**config) if isinstance(config, dict) else config
        self._templates: Dict[str, np.ndarray] = {}
        self._template_dir = Path(self.config.screenshot_dir)
        self._template_dir.mkdir(parents=True, exist_ok=True)

        # PyAutoGUI settings
        if pyautogui:
            pyautogui.FAILSAFE = True
            pyautogui.PAUSE = self.config.click_delay

    async def initialize(self):
        """Initialize fallback system"""
        logger.info("Initializing PyAutoGUIFallback...")

        if not pyautogui:
            logger.warning("PyAutoGUI not available")
            return

        if not cv2:
            logger.warning("OpenCV not available, template matching disabled")

        # Load existing templates
        await self._load_templates()

        # Get screen size
        self.screen_width, self.screen_height = pyautogui.size()
        logger.info(f"Screen resolution: {self.screen_width}x{self.screen_height}")

        logger.info("PyAutoGUIFallback initialized")

    async def _load_templates(self):
        """Load template images for matching"""
        for template_file in self._template_dir.glob("*.png"):
            try:
                template = cv2.imread(str(template_file), cv2.IMREAD_GRAYSCALE)
                if template is not None:
                    self._templates[template_file.stem] = template
                    logger.info(f"Loaded template: {template_file.stem}")
            except Exception as e:
                logger.warning(f"Failed to load template {template_file}: {e}")

    def capture_screen(self, region: Optional[Tuple[int, int, int, int]] = None) -> Optional[np.ndarray]:
        """Capture screen as OpenCV image"""
        if not ImageGrab or not cv2:
            return None

        try:
            if region:
                screenshot = ImageGrab.grab(bbox=region)
            else:
                screenshot = ImageGrab.grab()

            # Convert to OpenCV format
            screenshot_np = np.array(screenshot)
            screenshot_cv = cv2.cvtColor(screenshot_np, cv2.COLOR_RGB2BGR)
            return screenshot_cv
        except Exception as e:
            logger.error(f"Screen capture failed: {e}")
            return None

    def find_template(self, template_name: str, threshold: float = None,
                      region: Optional[Tuple[int, int, int, int]] = None) -> Optional[TemplateMatch]:
        """Find template on screen"""
        if template_name not in self._templates:
            logger.warning(f"Template not found: {template_name}")
            return None

        if not cv2:
            return None

        threshold = threshold or self.config.template_threshold

        # Capture screen
        screen = self.capture_screen(region)
        if screen is None:
            return None

        screen_gray = cv2.cvtColor(screen, cv2.COLOR_BGR2GRAY)
        template = self._templates[template_name]

        # Match template
        result = cv2.matchTemplate(screen_gray, template, cv2.TM_CCOEFF_NORMED)
        min_val, max_val, min_loc, max_loc = cv2.minMaxLoc(result)

        if max_val >= threshold:
            h, w = template.shape[:2]
            center_x = max_loc[0] + w // 2
            center_y = max_loc[1] + h // 2

            return TemplateMatch(
                name=template_name,
                confidence=max_val,
                position=(center_x, center_y),
                size=(w, h)
            )

        return None

    def find_all_templates(self, threshold: float = None) -> List[TemplateMatch]:
        """Find all known templates on screen"""
        matches = []
        for name in self._templates:
            match = self.find_template(name, threshold)
            if match:
                matches.append(match)
        return matches

    def click_template(self, template_name: str, threshold: float = None,
                       button: str = 'left', clicks: int = 1) -> bool:
        """Click on template if found"""
        match = self.find_template(template_name, threshold)
        if match:
            x, y = match.position
            self.click(x, y, button, clicks)
            return True
        return False

    def click(self, x: int, y: int, button: str = 'left', clicks: int = 1):
        """Click at coordinates"""
        if pyautogui:
            pyautogui.click(x, y, button=button, clicks=clicks, interval=self.config.click_delay)

    def double_click(self, x: int, y: int):
        """Double click at coordinates"""
        self.click(x, y, clicks=2)

    def right_click(self, x: int, y: int):
        """Right click at coordinates"""
        self.click(x, y, button='right')

    def type_text(self, text: str, interval: float = None):
        """Type text"""
        if pyautogui:
            pyautogui.write(text, interval=interval or self.config.type_delay)

    def press_key(self, key: str, presses: int = 1):
        """Press key"""
        if pyautogui:
            for _ in range(presses):
                pyautogui.press(key)
                time.sleep(0.05)

    def hotkey(self, *keys):
        """Press key combination"""
        if pyautogui:
            pyautogui.hotkey(*keys)

    def scroll(self, clicks: int, x: int = None, y: int = None):
        """Scroll"""
        if pyautogui:
            pyautogui.scroll(clicks, x=x, y=y)

    def drag_to(self, x: int, y: int, duration: float = 0.5):
        """Drag to coordinates"""
        if pyautogui:
            pyautogui.dragTo(x, y, duration=duration, button='left')

    def locate_on_screen(self, image_path: str, confidence: float = 0.8) -> Optional[Tuple[int, int, int, int]]:
        """Locate image on screen (PyAutoGUI built-in)"""
        if pyautogui:
            try:
                return pyautogui.locateOnScreen(image_path, confidence=confidence)
            except:
                return None
        return None

    def click_image(self, image_path: str, confidence: float = 0.8) -> bool:
        """Click on image if found on screen"""
        if pyautogui:
            try:
                location = pyautogui.locateCenterOnScreen(image_path, confidence=confidence)
                if location:
                    pyautogui.click(location)
                    return True
            except:
                pass
        return False

    def save_template(self, name: str, region: Optional[Tuple[int, int, int, int]] = None) -> bool:
        """Save screen region as template"""
        if not cv2:
            return False

        screen = self.capture_screen(region)
        if screen is None:
            return False

        gray = cv2.cvtColor(screen, cv2.COLOR_BGR2GRAY)
        template_path = self._template_dir / f"{name}.png"

        try:
            cv2.imwrite(str(template_path), gray)
            self._templates[name] = gray
            logger.info(f"Saved template: {name}")
            return True
        except Exception as e:
            logger.error(f"Failed to save template: {e}")
            return False

    def create_template_from_coords(self, name: str, x: int, y: int, w: int, h: int) -> bool:
        """Create template from screen coordinates"""
        region = (x, y, x + w, y + h)
        return self.save_template(name, region)

    def get_mouse_position(self) -> Tuple[int, int]:
        """Get current mouse position"""
        if pyautogui:
            return pyautogui.position()
        return (0, 0)

    def wait_for_template(self, template_name: str, timeout: float = 10.0,
                          threshold: float = None, interval: float = 0.5) -> Optional[TemplateMatch]:
        """Wait for template to appear on screen"""
        start = time.time()
        while time.time() - start < timeout:
            match = self.find_template(template_name, threshold)
            if match:
                return match
            time.sleep(interval)
        return None

    def wait_and_click(self, template_name: str, timeout: float = 10.0,
                       threshold: float = None) -> bool:
        """Wait for template and click it"""
        match = self.wait_for_template(template_name, timeout, threshold)
        if match:
            self.click(match.position[0], match.position[1])
            return True
        return False

    def type_in_field(self, text: str, clear_first: bool = True):
        """Type text in currently focused field"""
        if clear_first:
            self.hotkey('ctrl', 'a')
            time.sleep(0.1)
            self.press_key('delete')
            time.sleep(0.1)
        self.type_text(text)

    def fill_form_field(self, field_label: str, value: str, tab_after: bool = True):
        """Fill form field by label (attempts to find and click label first)"""
        # Try to find label template
        label_template = f"label_{field_label.lower().replace(' ', '_')}"
        if self.click_template(label_template):
            time.sleep(0.2)
            self.type_in_field(value)
            if tab_after:
                self.press_key('tab')
            return True
        return False

    def take_screenshot(self, path: str = None, region: Tuple[int, int, int, int] = None) -> str:
        """Take screenshot and save to file"""
        if not ImageGrab:
            return ""

        if path is None:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            path = f"./screenshots/screenshot_{timestamp}.png"

        Path(path).parent.mkdir(parents=True, exist_ok=True)

        try:
            if region:
                screenshot = ImageGrab.grab(bbox=region)
            else:
                screenshot = ImageGrab.grab()

            screenshot.save(path)
            return path
        except Exception as e:
            logger.error(f"Screenshot failed: {e}")
            return ""

    def get_window_position(self, window_title: str) -> Optional[Tuple[int, int, int, int]]:
        """Get window position by title"""
        if gw:
            try:
                windows = gw.getWindowsWithTitle(window_title)
                if windows:
                    win = windows[0]
                    return (win.left, win.top, win.width, win.height)
            except:
                pass
        return None

    def activate_window(self, window_title: str) -> bool:
        """Activate window by title"""
        if gw:
            try:
                windows = gw.getWindowsWithTitle(window_title)
                if windows:
                    windows[0].activate()
                    return True
            except:
                pass
        return False

    def is_ready(self) -> bool:
        return pyautogui is not None

    async def close(self):
        """Cleanup"""
        logger.info("PyAutoGUIFallback closed")