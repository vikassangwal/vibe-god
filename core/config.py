"""
Configuration management for Wife God Agent
"""

import json
from pathlib import Path
from typing import Any, Dict, Optional
from dataclasses import dataclass, field


@dataclass
class AppConfig:
    name: str = "Wife God"
    version: str = "1.0.0"
    mode: str = "production"
    input_folder: str = "./input_documents"
    output_folder: str = "./output"
    temp_folder: str = "./temp"
    log_level: str = "INFO"


@dataclass
class DatabaseConfig:
    path: str = "./data/wife_god.db"


@dataclass
class OllamaConfig:
    url: str = "http://localhost:11434"
    model: str = "llama3:8b"
    timeout: int = 120
    temperature: float = 0.1
    max_tokens: int = 4096


@dataclass
class VoiceConfig:
    tts_engine: str = "pyttsx3"
    tts_rate: int = 150
    tts_volume: float = 0.9
    tts_voice: str = "hindi"
    stt_engine: str = "whisper"
    whisper_model: str = "base"
    language: str = "hi"
    vad_threshold: float = 0.5
    sample_rate: int = 16000


@dataclass
class DocConfig:
    ocr_engine: str = "easyocr"
    easyocr_languages: list = field(default_factory=lambda: ["en", "hi"])
    tesseract_path: str = "tesseract"
    max_file_size_mb: int = 10
    compression_quality: int = 85
    output_dpi: int = 200
    size_limits: Dict[str, int] = field(default_factory=lambda: {
        "signature_kb": 50,
        "photo_kb": 100,
        "document_kb": 500,
        "aadhaar_kb": 200
    })
    supported_formats: list = field(default_factory=lambda: [
        ".jpg", ".jpeg", ".png", ".pdf", ".tiff", ".bmp"
    ])


@dataclass
class CaptchaConfig:
    solver: str = "opencv"
    model_path: str = "./models/captcha_model.onnx"
    fallback_to_human: bool = True
    human_timeout: int = 60


@dataclass
class FallbackConfig:
    enabled: bool = True
    template_threshold: float = 0.8
    click_delay: float = 0.1
    type_delay: float = 0.05
    screenshot_dir: str = "./screenshots/templates"


@dataclass
class EmiteServiceConfig:
    url: str = ""
    documents: list = field(default_factory=list)


@dataclass
class EmiteConfig:
    sso_url: str = "https://sso.rajasthan.gov.in"
    portal_url: str = "https://emitra.rajasthan.gov.in"
    username: str = ""
    password: str = ""
    headless: bool = False
    browser: str = "chromium"
    viewport: Dict[str, int] = field(default_factory=lambda: {"width": 1920, "height": 1080})
    timeout: int = 30000
    services: Dict[str, EmiteServiceConfig] = field(default_factory=dict)


@dataclass
class TwitterConfig:
    username: str = ""
    password: str = ""
    headless: bool = False
    browser: str = "chromium"
    viewport: Dict[str, int] = field(default_factory=lambda: {"width": 1920, "height": 1080})
    timeout: int = 30000
    session_file: str = "./data/twitter_session.json"
    rate_limits: Dict[str, int] = field(default_factory=lambda: {
        "tweets_per_hour": 50,
        "dms_per_hour": 100,
        "follows_per_hour": 50
    })


class Config:
    """Configuration manager for Wife God Agent"""

    def __init__(self, config_path: str = "config.json"):
        self.config_path = Path(config_path)
        self._config: Dict[str, Any] = {}

        # Parsed configs
        self.app = AppConfig()
        self.db = DatabaseConfig()
        self.ollama = OllamaConfig()
        self.voice = VoiceConfig()
        self.doc = DocConfig()
        self.captcha = CaptchaConfig()
        self.fallback = FallbackConfig()
        self.emitra = EmiteConfig()
        self.twitter = TwitterConfig()

        self.load()

    def load(self):
        """Load configuration from file"""
        if self.config_path.exists():
            with open(self.config_path, 'r') as f:
                self._config = json.load(f)
        else:
            # Create default config
            self._config = self._default_config()
            self.save()

        self._parse_config()

    def _default_config(self) -> Dict[str, Any]:
        """Return default configuration"""
        return {
            "app": {
                "name": "Wife God",
                "version": "1.0.0",
                "mode": "production",
                "input_folder": "./input_documents",
                "output_folder": "./output",
                "temp_folder": "./temp",
                "log_level": "INFO"
            },
            "database": {
                "path": "./data/wife_god.db"
            },
            "ollama": {
                "url": "http://localhost:11434",
                "model": "llama3:8b",
                "timeout": 120,
                "temperature": 0.1,
                "max_tokens": 4096
            },
            "voice": {
                "tts_engine": "pyttsx3",
                "tts_rate": 150,
                "tts_volume": 0.9,
                "tts_voice": "hindi",
                "stt_engine": "whisper",
                "whisper_model": "base",
                "language": "hi",
                "vad_threshold": 0.5,
                "sample_rate": 16000
            },
            "doc": {
                "ocr_engine": "easyocr",
                "easyocr_languages": ["en", "hi"],
                "tesseract_path": "tesseract",
                "max_file_size_mb": 10,
                "compression_quality": 85,
                "output_dpi": 200,
                "size_limits": {
                    "signature_kb": 50,
                    "photo_kb": 100,
                    "document_kb": 500,
                    "aadhaar_kb": 200
                },
                "supported_formats": [".jpg", ".jpeg", ".png", ".pdf", ".tiff", ".bmp"]
            },
            "captcha": {
                "solver": "opencv",
                "model_path": "./models/captcha_model.onnx",
                "fallback_to_human": True,
                "human_timeout": 60
            },
            "fallback": {
                "enabled": True,
                "template_threshold": 0.8,
                "click_delay": 0.1,
                "type_delay": 0.05
            },
            "emitra": {
                "sso_url": "https://sso.rajasthan.gov.in",
                "portal_url": "https://emitra.rajasthan.gov.in",
                "username": "",
                "password": "",
                "headless": False,
                "browser": "chromium",
                "viewport": {"width": 1920, "height": 1080},
                "timeout": 30000,
                "services": {}
            },
            "twitter": {
                "username": "",
                "password": "",
                "headless": False,
                "browser": "chromium",
                "viewport": {"width": 1920, "height": 1080},
                "timeout": 30000,
                "session_file": "./data/twitter_session.json",
                "rate_limits": {
                    "tweets_per_hour": 50,
                    "dms_per_hour": 100,
                    "follows_per_hour": 50
                }
            }
        }

    def _parse_config(self):
        """Parse config into typed objects"""
        c = self._config

        # App
        app_data = c.get("app", {})
        self.app = AppConfig(
            name=app_data.get("name", "Wife God"),
            version=app_data.get("version", "1.0.0"),
            mode=app_data.get("mode", "production"),
            input_folder=app_data.get("input_folder", "./input_documents"),
            output_folder=app_data.get("output_folder", "./output"),
            temp_folder=app_data.get("temp_folder", "./temp"),
            log_level=app_data.get("log_level", "INFO")
        )

        # Database
        db_data = c.get("database", {})
        self.db = DatabaseConfig(path=db_data.get("path", "./data/wife_god.db"))

        # Ollama
        ollama_data = c.get("ollama", {})
        self.ollama = OllamaConfig(
            url=ollama_data.get("url", "http://localhost:11434"),
            model=ollama_data.get("model", "llama3:8b"),
            timeout=ollama_data.get("timeout", 120),
            temperature=ollama_data.get("temperature", 0.1),
            max_tokens=ollama_data.get("max_tokens", 4096)
        )

        # Voice
        voice_data = c.get("voice", {})
        self.voice = VoiceConfig(
            tts_engine=voice_data.get("tts_engine", "pyttsx3"),
            tts_rate=voice_data.get("tts_rate", 150),
            tts_volume=voice_data.get("tts_volume", 0.9),
            tts_voice=voice_data.get("tts_voice", "hindi"),
            stt_engine=voice_data.get("stt_engine", "whisper"),
            whisper_model=voice_data.get("whisper_model", "base"),
            language=voice_data.get("language", "hi"),
            vad_threshold=voice_data.get("vad_threshold", 0.5),
            sample_rate=voice_data.get("sample_rate", 16000)
        )

        # Document
        doc_data = c.get("doc", {})
        self.doc = DocConfig(
            ocr_engine=doc_data.get("ocr_engine", "easyocr"),
            easyocr_languages=doc_data.get("easyocr_languages", ["en", "hi"]),
            tesseract_path=doc_data.get("tesseract_path", "tesseract"),
            max_file_size_mb=doc_data.get("max_file_size_mb", 10),
            compression_quality=doc_data.get("compression_quality", 85),
            output_dpi=doc_data.get("output_dpi", 200),
            size_limits=doc_data.get("size_limits", {
                "signature_kb": 50,
                "photo_kb": 100,
                "document_kb": 500,
                "aadhaar_kb": 200
            }),
            supported_formats=doc_data.get("supported_formats", [".jpg", ".jpeg", ".png", ".pdf", ".tiff", ".bmp"])
        )

        # Captcha
        captcha_data = c.get("captcha", {})
        self.captcha = CaptchaConfig(
            solver=captcha_data.get("solver", "opencv"),
            model_path=captcha_data.get("model_path", "./models/captcha_model.onnx"),
            fallback_to_human=captcha_data.get("fallback_to_human", True),
            human_timeout=captcha_data.get("human_timeout", 60)
        )

        # Fallback
        fallback_data = c.get("fallback", {})
        self.fallback = FallbackConfig(
            enabled=fallback_data.get("enabled", True),
            template_threshold=fallback_data.get("template_threshold", 0.8),
            click_delay=fallback_data.get("click_delay", 0.1),
            type_delay=fallback_data.get("type_delay", 0.05)
        )

        # eMitra
        emitra_data = c.get("emitra", {})
        services = {}
        for key, val in emitra_data.get("services", {}).items():
            if isinstance(val, dict):
                services[key] = EmiteServiceConfig(
                    url=val.get("url", ""),
                    documents=val.get("documents", [])
                )
            else:
                services[key] = EmiteServiceConfig(documents=val if isinstance(val, list) else [])

        self.emitra = EmiteConfig(
            sso_url=emitra_data.get("sso_url", "https://sso.rajasthan.gov.in"),
            portal_url=emitra_data.get("portal_url", "https://emitra.rajasthan.gov.in"),
            username=emitra_data.get("username", ""),
            password=emitra_data.get("password", ""),
            headless=emitra_data.get("headless", False),
            browser=emitra_data.get("browser", "chromium"),
            viewport=emitra_data.get("viewport", {"width": 1920, "height": 1080}),
            timeout=emitra_data.get("timeout", 30000),
            services=services
        )

        # Twitter
        twitter_data = c.get("twitter", {})
        self.twitter = TwitterConfig(
            username=twitter_data.get("username", ""),
            password=twitter_data.get("password", ""),
            headless=twitter_data.get("headless", False),
            browser=twitter_data.get("browser", "chromium"),
            viewport=twitter_data.get("viewport", {"width": 1920, "height": 1080}),
            timeout=twitter_data.get("timeout", 30000),
            session_file=twitter_data.get("session_file", "./data/twitter_session.json"),
            rate_limits=twitter_data.get("rate_limits", {
                "tweets_per_hour": 50,
                "dms_per_hour": 100,
                "follows_per_hour": 50
            })
        )

    def save(self):
        """Save configuration to file"""
        # Ensure parent directory exists
        self.config_path.parent.mkdir(parents=True, exist_ok=True)

        with open(self.config_path, 'w') as f:
            json.dump(self._config, f, indent=2)

    @property
    def db_path(self) -> str:
        return self.db.path

    @property
    def ollama_url(self) -> str:
        return self.ollama.url

    @property
    def ollama_model(self) -> str:
        return self.ollama.model

    @property
    def voice_config(self) -> VoiceConfig:
        return self.voice

    @property
    def doc_config(self) -> DocConfig:
        return self.doc

    @property
    def captcha_config(self) -> CaptchaConfig:
        return self.captcha

    @property
    def fallback_config(self) -> FallbackConfig:
        return self.fallback

    @property
    def emitra_config(self) -> EmiteConfig:
        return self.emitra

    @property
    def twitter_config(self) -> TwitterConfig:
        return self.twitter

    @property
    def input_folder(self) -> str:
        return self.app.input_folder

    @property
    def output_folder(self) -> str:
        return self.app.output_folder

    @property
    def temp_folder(self) -> str:
        return self.app.temp_folder