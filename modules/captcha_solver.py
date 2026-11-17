"""
Captcha Solver Module for Wife God Agent
OpenCV-based captcha solver with human-in-the-loop fallback
"""

import asyncio
import logging
import base64
import tempfile
import os
from pathlib import Path
from typing import Dict, Any, Optional, Tuple
from dataclasses import dataclass
from datetime import datetime
from enum import Enum

try:
    import cv2
    import numpy as np
except ImportError:
    cv2 = None
    np = None

try:
    from PIL import Image
except ImportError:
    Image = None

logger = logging.getLogger("WifeGod.CaptchaSolver")


class CaptchaType(Enum):
    TEXT = "text"
    MATH = "math"
    SLIDER = "slider"
    IMAGE_SELECT = "image_select"
    UNKNOWN = "unknown"


@dataclass
class CaptchaConfig:
    solver: str = "opencv"
    model_path: str = "./models/captcha_model.onnx"
    fallback_to_human: bool = True
    human_timeout: int = 60


@dataclass
class CaptchaResult:
    success: bool
    answer: str
    captcha_type: CaptchaType
    confidence: float
    method: str
    error: Optional[str] = None


class CaptchaSolver:
    """
    CAPTCHA solver for Indian government portals
    - OpenCV-based text/math captcha solving
    - Human-in-the-loop fallback
    """

    def __init__(self, config: Dict[str, Any]):
        self.config = CaptchaConfig(**config) if isinstance(config, dict) else config
        self._model = None

    async def initialize(self):
        """Initialize captcha solver"""
        logger.info("Initializing CaptchaSolver...")

        if self.config.solver == "opencv" and cv2:
            logger.info("OpenCV captcha solver ready")
        else:
            logger.warning("OpenCV not available, using human fallback only")

        logger.info("CaptchaSolver initialized")

    async def solve(self, image_path: str, captcha_type: CaptchaType = CaptchaType.UNKNOWN) -> CaptchaResult:
        """Solve captcha from image"""
        logger.info(f"Solving captcha: {image_path}")

        # Detect captcha type if unknown
        if captcha_type == CaptchaType.UNKNOWN:
            captcha_type = await self._detect_captcha_type(image_path)

        # Try OpenCV solver
        if self.config.solver == "opencv" and cv2:
            result = await self._solve_opencv(image_path, captcha_type)
            if result.success:
                return result

        # Fallback to human
        if self.config.fallback_to_human:
            return await self._human_fallback(image_path)

        return CaptchaResult(
            success=False,
            answer="",
            captcha_type=captcha_type,
            confidence=0.0,
            method="none",
            error="No solver available"
        )

    async def _detect_captcha_type(self, image_path: str) -> CaptchaType:
        """Detect captcha type from image"""
        if not cv2:
            return CaptchaType.UNKNOWN

        try:
            img = cv2.imread(image_path)
            if img is None:
                return CaptchaType.UNKNOWN

            # Convert to grayscale
            gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)

            # Check for math operators
            text = await self._extract_text_simple(gray)
            if any(op in text for op in ['+', '-', '×', '÷', '=', 'plus', 'minus']):
                return CaptchaType.MATH

            # Check for slider (long horizontal image)
            h, w = gray.shape[:2]
            if w > h * 3:
                return CaptchaType.SLIDER

            # Check for image select (grid of images)
            if w > 300 and h > 300:
                return CaptchaType.IMAGE_SELECT

            return CaptchaType.TEXT

        except Exception as e:
            logger.warning(f"Captcha type detection failed: {e}")
            return CaptchaType.UNKNOWN

    async def _solve_opencv(self, image_path: str, captcha_type: CaptchaType) -> CaptchaResult:
        """Solve using OpenCV"""
        try:
            img = cv2.imread(image_path)
            if img is None:
                return CaptchaResult(False, "", captcha_type, 0.0, "opencv", "Failed to load image")

            gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)

            if captcha_type == CaptchaType.MATH:
                return await self._solve_math(gray)
            elif captcha_type == CaptchaType.TEXT:
                return await self._solve_text(gray)
            elif captcha_type == CaptchaType.SLIDER:
                return await self._solve_slider(gray)

            return CaptchaResult(False, "", captcha_type, 0.0, "opencv", "Unsupported type")

        except Exception as e:
            logger.error(f"OpenCV solve error: {e}")
            return CaptchaResult(False, "", captcha_type, 0.0, "opencv", str(e))

    async def _solve_math(self, gray) -> CaptchaResult:
        """Solve math captcha"""
        try:
            # Extract text
            text = await self._extract_text_simple(gray)

            # Clean text
            text = text.replace('×', '*').replace('÷', '/').replace('x', '*')

            # Find math expression
            import re
            math_expr = re.search(r'[\d\s\+\-\*\/\(\)\=]+', text)
            if not math_expr:
                return CaptchaResult(False, "", CaptchaType.MATH, 0.0, "opencv", "No math expression found")

            expr = math_expr.group().replace('=', '').strip()

            # Safely evaluate
            try:
                # Only allow safe characters
                allowed = set('0123456789+-*/(). ')
                if all(c in allowed for c in expr):
                    result = eval(expr)
                    answer = str(int(result)) if result == int(result) else str(result)
                    return CaptchaResult(True, answer, CaptchaType.MATH, 0.9, "opencv")
            except:
                pass

            return CaptchaResult(False, "", CaptchaType.MATH, 0.0, "opencv", "Failed to evaluate")

        except Exception as e:
            return CaptchaResult(False, "", CaptchaType.MATH, 0.0, "opencv", str(e))

    async def _solve_text(self, gray) -> CaptchaResult:
        """Solve text captcha using OCR"""
        try:
            # Preprocess for better OCR
            processed = self._preprocess_for_ocr(gray)

            # Try Tesseract
            text = await self._extract_text_tesseract(processed)

            if text and len(text.strip()) >= 3:
                # Clean text
                import re
                clean_text = re.sub(r'[^a-zA-Z0-9]', '', text.strip())
                if len(clean_text) >= 3:
                    return CaptchaResult(True, clean_text, CaptchaType.TEXT, 0.7, "opencv")

            return CaptchaResult(False, "", CaptchaType.TEXT, 0.0, "opencv", "OCR failed")

        except Exception as e:
            return CaptchaResult(False, "", CaptchaType.TEXT, 0.0, "opencv", str(e))

    async def _solve_slider(self, gray) -> CaptchaResult:
        """Solve slider captcha (find gap position)"""
        try:
            # This would need template matching or edge detection
            # For now, return failure to trigger human fallback
            return CaptchaResult(False, "", CaptchaType.SLIDER, 0.0, "opencv", "Slider solving not implemented")
        except Exception as e:
            return CaptchaResult(False, "", CaptchaType.SLIDER, 0.0, "opencv", str(e))

    def _preprocess_for_ocr(self, gray) -> np.ndarray:
        """Preprocess image for better OCR"""
        # Resize for better OCR
        h, w = gray.shape
        scale = max(1, 100 / h) if h < 100 else 1
        if scale > 1:
            gray = cv2.resize(gray, None, fx=scale, fy=scale, interpolation=cv2.INTER_CUBIC)

        # Denoise
        gray = cv2.fastNlMeansDenoising(gray)

        # Threshold
        _, gray = cv2.threshold(gray, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)

        # Morphological operations
        kernel = np.ones((2, 2), np.uint8)
        gray = cv2.morphologyEx(gray, cv2.MORPH_CLOSE, kernel)

        return gray

    async def _extract_text_simple(self, gray) -> str:
        """Simple text extraction"""
        if cv2:
            # Use Tesseract if available
            try:
                import pytesseract
                return pytesseract.image_to_string(gray, config='--psm 7')
            except:
                pass
        return ""

    async def _extract_text_tesseract(self, gray) -> str:
        """Extract text using Tesseract"""
        try:
            import pytesseract
            return pytesseract.image_to_string(gray, config='--psm 7 -c tessedit_char_whitelist=ABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789')
        except:
            return ""

    async def _human_fallback(self, image_path: str) -> CaptchaResult:
        """Human-in-the-loop captcha solving"""
        logger.info("Falling back to human captcha solving")

        # Convert image to base64 for display
        with open(image_path, 'rb') as f:
            img_data = base64.b64encode(f.read()).decode()

        # In a real implementation, this would:
        # 1. Display image to user via GUI/Telegram/web interface
        # 2. Wait for user input
        # 3. Return user's answer

        # For now, simulate waiting for human input
        logger.info(f"CAPTCHA image ready for human: data:image/png;base64,{img_data[:100]}...")

        # This would be replaced with actual human input mechanism
        # For now, return failure to indicate human needed
        return CaptchaResult(
            success=False,
            answer="",
            captcha_type=CaptchaType.UNKNOWN,
            confidence=0.0,
            method="human_required",
            error="Human intervention required - implement GUI/Telegram notification"
        )

    async def solve_from_bytes(self, image_bytes: bytes, captcha_type: CaptchaType = CaptchaType.UNKNOWN) -> CaptchaResult:
        """Solve captcha from bytes"""
        with tempfile.NamedTemporaryFile(suffix='.png', delete=False) as tmp:
            tmp.write(image_bytes)
            tmp_path = tmp.name

        try:
            return await self.solve(tmp_path, captcha_type)
        finally:
            try:
                os.unlink(tmp_path)
            except:
                pass