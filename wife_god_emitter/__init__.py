"""
Wife God eMitra + Twitter Automation Agent
===========================================

A 100% locally-hosted autonomous AI agent for eMitra (Rajasthan SSO)
services and Twitter (X) operations.

Features:
- Offline OCR (EasyOCR + Tesseract) for document processing
- Local LLM via Ollama (Llama-3, Qwen, Mistral)
- Playwright + PyAutoGUI fallback for web automation
- Voice interface (pyttsx3 TTS + Whisper STT)
- SQLite for local data persistence
- 100% local execution - no cloud APIs

Author: Wife God Team
Version: 1.0.0
License: MIT
"""

__version__ = "1.0.0"
__author__ = "Wife God Team"
__email__ = "support@wifegod.local"
__license__ = "MIT"

# Core exports
from .core.config import Config
from .core.database import DatabaseManager
from .core.local_llm import LocalLLM
from .core.voice import VoiceCommunicator

# Module exports
from .modules.doc_processor import DocProcessor, DocType
from .modules.captcha_solver import CaptchaSolver, CaptchaType
from .modules.pyautogui_fallback import PyAutoGUIFallback

# Bot exports
from .bots.emitra_bot import eMitraBot, ServiceStatus
from .bots.twitter_bot import TwitterBot, TwitterAction

# Main agent
from .main import WifeGodAgent, Task, TaskType, TaskStatus

__all__ = [
    # Version info
    "__version__",
    "__author__",
    "__email__",
    "__license__",
    # Core
    "Config",
    "DatabaseManager",
    "LocalLLM",
    "VoiceCommunicator",
    # Modules
    "DocProcessor",
    "DocType",
    "CaptchaSolver",
    "CaptchaType",
    "PyAutoGUIFallback",
    # Bots
    "eMitraBot",
    "ServiceStatus",
    "TwitterBot",
    "TwitterAction",
    # Main
    "WifeGodAgent",
    "Task",
    "TaskType",
    "TaskStatus",
]