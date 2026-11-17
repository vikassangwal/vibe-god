#!/usr/bin/env python3
"""
Setup script for Wife God eMitra + Twitter Automation Agent
"""

from setuptools import setup, find_packages
from pathlib import Path

this_directory = Path(__file__).parent
long_description = (this_directory / "README.md").read_text(encoding="utf-8") if (this_directory / "README.md").exists() else ""

setup(
    name="wife-god-emitter",
    version="1.0.0",
    author="Wife God Team",
    author_email="support@wifegod.local",
    description="100% Local eMitra (Rajasthan SSO) + Twitter (X) Automation Agent",
    long_description=long_description,
    long_description_content_type="text/markdown",
    url="https://github.com/wifegod/wife-god-emitter",
    packages=find_packages(where=".", include=["wife_god_emitter*"]),
    package_dir={"": "."},
    classifiers=[
        "Development Status :: 4 - Beta",
        "Intended Audience :: Developers",
        "License :: OSI Approved :: MIT License",
        "Programming Language :: Python :: 3.10",
        "Programming Language :: Python :: 3.11",
        "Programming Language :: Python :: 3.12",
        "Topic :: Office/Business :: Financial",
        "Topic :: Internet :: WWW/HTTP :: Dynamic Content",
        "Topic :: Software Development :: Libraries :: Python Modules",
    ],
    python_requires=">=3.10",
    install_requires=[
        "asyncio-mqtt==0.16.1",
        "aiofiles==23.2.1",
        "aiohttp==3.14.4",
        "pydantic==2.5.3",
        "pydantic-settings==2.1.0",
        "python-dotenv==1.2.2",
        "pyyaml==6.0.1",
        "aiosqlite==0.19.0",
        "playwright==1.40.0",
        "pyautogui==0.9.54",
        "pygetwindow==0.0.9",
        "pillow==10.1.0",
        "easyocr==1.7.1",
        "pytesseract==0.3.10",
        "opencv-python-headless==4.9.0.80",
        "numpy==1.26.2",
        "img2pdf==0.4.4",
        "pdfplumber==0.10.3",
        "fitz==0.0.1.dev2",
        "pyttsx3==2.90",
        "faster-whisper==1.0.3",
        "sounddevice==0.4.6",
        "soundfile==0.12.1",
        "ollama==0.2.0",
        "tqdm==4.66.1",
        "rich==13.7.0",
        "click==8.1.7",
        "python-dateutil==2.8.2",
        "python-magic==0.4.27",
    ],
    extras_require={
        "gpu": [
            "torch==2.1.2",
            "torchvision==0.16.2",
        ],
        "dev": [
            "pytest==7.4.4",
            "pytest-asyncio==0.23.3",
            "black==23.12.1",
            "ruff==0.1.15",
            "mypy==1.7.1",
        ],
    },
    entry_points={
        "console_scripts": [
            "wife-god=main:main",
            "wife-god-cli=main:main",
        ],
    },
    include_package_data=True,
    package_data={
        "wife_god_emitter": ["config.json", "models/*"],
    },
    zip_safe=False,
)