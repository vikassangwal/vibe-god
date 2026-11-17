#!/usr/bin/env python3
"""
Wife God - Installation Verification Script
Verifies all components are properly installed and working.
"""

import asyncio
import sys
import subprocess
import importlib
import os
import json
import platform
from pathlib import Path
from typing import Dict, List, Tuple, Any

class Colors:
    RED = '\033[91m'
    GREEN = '\033[92m'
    YELLOW = '\033[93m'
    BLUE = '\033[94m'
    MAGENTA = '\033[95m'
    CYAN = '\033[96m'
    WHITE = '\033[97m'
    RESET = '\033[0m'
    BOLD = '\033[1m'

def print_banner():
    print(f"""
{Colors.CYAN}{'='*70}{Colors.RESET}
{Colors.BOLD}{Colors.MAGENTA}    Wife God - Installation Verification{Colors.RESET}
{Colors.CYAN}{'='*70}{Colors.RESET}
""")

def print_result(name: str, passed: bool, details: str = ""):
    status = f"{Colors.GREEN}✓ PASS{Colors.RESET}" if passed else f"{Colors.RED}✗ FAIL{Colors.RESET}"
    print(f"  {status} {name}")
    if details:
        color = Colors.GREEN if "PASS" in details or "OK" in details else Colors.YELLOW
        print(f"    {Colors.CYAN}→{Colors.RESET} {details}")

def check_python_version() -> Tuple[bool, str]:
    """Check Python version >= 3.10"""
    version = sys.version_info
    if version.major >= 3 and version.minor >= 10:
        return True, f"Python {version.major}.{version.minor}.{version.micro}"
    return False, f"Python {version.major}.{version.minor} (need 3.10+)"

def check_command(cmd: str, version_flag: str = "--version") -> Tuple[bool, str]:
    """Check if command exists and get version"""
    try:
        result = subprocess.run([cmd, version_flag], capture_output=True, text=True, timeout=10)
        if result.returncode == 0:
            version = result.stdout.strip().split('\n')[0]
            return True, version
        return False, f"Exit code: {result.returncode}"
    except FileNotFoundError:
        return False, "Not found in PATH"
    except Exception as e:
        return False, str(e)

def check_python_import(module: str, attr: str = None) -> Tuple[bool, str]:
    """Check if Python module can be imported"""
    try:
        module_obj = importlib.import_module(module)
        if attr and hasattr(module_obj, attr):
            version = getattr(module_obj, attr)
            return True, f"{module} {version}"
        return True, module
    except ImportError as e:
        return False, str(e)
    except Exception as e:
        return False, str(e)

def check_ollama() -> Tuple[bool, str]:
    """Check Ollama service"""
    try:
        # Check if ollama command exists
        result = subprocess.run(["ollama", "list"], capture_output=True, text=True, timeout=10)
        if result.returncode == 0:
            lines = result.stdout.strip().split('\n')
            models = [l.split()[0] for l in lines[1:] if l.strip()]
            return True, f"Models: {', '.join(models[:5])}{'...' if len(models) > 5 else ''}"
        return False, "Ollama not responding"
    except FileNotFoundError:
        return False, "Ollama not installed"
    except Exception as e:
        return False, str(e)

def check_ollama_model(model: str = "llama3:8b") -> Tuple[bool, str]:
    """Check if specific model is available"""
    try:
        result = subprocess.run(["ollama", "list"], capture_output=True, text=True, timeout=10)
        if model in result.stdout:
            return True, f"Model {model} available"
        return False, f"Model {model} not found"
    except Exception as e:
        return False, str(e)

def check_directories(base_path: Path) -> Tuple[bool, str]:
    """Check required directories exist"""
    required = ["data", "input_documents", "output", "temp", "models", "logs", "data_products"]
    missing = []
    for d in required:
        if not (base_path / d).exists():
            missing.append(d)
    if missing:
        return False, f"Missing: {', '.join(missing)}"
    return True, "All directories present"

def check_config(config_path: Path) -> Tuple[bool, str]:
    """Check config file exists and is valid JSON"""
    if not config_path.exists():
        return False, "config.json not found"
    try:
        with open(config_path) as f:
            config = json.load(f)
        required_keys = ["ollama", "emitra", "twitter", "voice", "doc"]
        missing = [k for k in required_keys if k not in config]
        if missing:
            return False, f"Missing config keys: {missing}"
        return True, "Valid configuration"
    except json.JSONDecodeError as e:
        return False, f"Invalid JSON: {e}"

def check_ollama_service() -> Tuple[bool, str]:
    """Check if Ollama service is running"""
    try:
        import requests
        resp = requests.get("http://localhost:11434/api/tags", timeout=5)
        if resp.status_code == 200:
            data = resp.json()
            models = [m['name'] for m in data.get('models', [])]
            return True, f"Ollama running with {len(models)} models"
        return False, f"Ollama returned {resp.status_code}"
    except requests.exceptions.ConnectionError:
        return False, "Ollama service not running (port 11434)"
    except Exception as e:
        return False, str(e)

def check_file_permissions(base_path: Path) -> Tuple[bool, str]:
    """Check write permissions on key directories"""
    test_dirs = ["data", "output", "temp", "logs"]
    for d in test_dirs:
        test_file = base_path / d / ".write_test"
        try:
            test_file.write_text("test")
            test_file.unlink()
        except Exception as e:
            return False, f"No write permission on {d}: {e}"
    return True, "Write permissions OK"

async def check_ollama_generation() -> Tuple[bool, str]:
    """Test Ollama text generation"""
    try:
        import ollama
        resp = ollama.chat(
            model="llama3:8b",
            messages=[{"role": "user", "content": "Say OK"}],
            options={"temperature": 0, "num_predict": 10}
        )
        if "OK" in resp['message']['content'].upper():
            return True, "Generation working"
        return True, f"Response: {resp['message']['content'][:50]}"
    except Exception as e:
        return False, str(e)

async def check_easyocr() -> Tuple[bool, str]:
    """Test EasyOCR initialization"""
    try:
        import easyocr
        reader = easyocr.Reader(['en', 'hi'], gpu=False)
        return True, "EasyOCR initialized"
    except Exception as e:
        return False, str(e)

async def check_playwright() -> Tuple[bool, str]:
    """Check Playwright installation"""
    try:
        from playwright.async_api import async_playwright
        async with async_playwright() as p:
            browser = await p.chromium.launch(headless=True)
            await browser.close()
        return True, "Playwright + Chromium working"
    except Exception as e:
        return False, str(e)

async def check_tesseract() -> Tuple[bool, str]:
    """Check Tesseract OCR"""
    try:
        import pytesseract
        version = pytesseract.get_tesseract_version()
        return True, f"Tesseract {version}"
    except Exception as e:
        return False, str(e)

async def check_pyttsx3() -> Tuple[bool, str]:
    """Check pyttsx3 TTS"""
    try:
        import pyttsx3
        engine = pyttsx3.init()
        voices = engine.getProperty('voices')
        return True, f"pyttsx3 with {len(voices)} voices"
    except Exception as e:
        return False, str(e)

async def check_whisper() -> Tuple[bool, str]:
    """Check Whisper STT"""
    try:
        from faster_whisper import WhisperModel
        model = WhisperModel("tiny", device="cpu", compute_type="int8")
        return True, "faster-whisper loaded"
    except Exception as e:
        return False, str(e)

async def check_opencv() -> Tuple[bool, str]:
    """Check OpenCV"""
    try:
        import cv2
        return True, f"OpenCV {cv2.__version__}"
    except Exception as e:
        return False, str(e)

async def check_pyautogui() -> Tuple[bool, str]:
    """Check PyAutoGUI"""
    try:
        import pyautogui
        size = pyautogui.size()
        return True, f"PyAutoGUI (screen: {size.width}x{size.height})"
    except Exception as e:
        return False, str(e)

async def run_all_checks() -> Dict[str, Any]:
    """Run all verification checks"""
    base_path = Path.cwd()
    results = {
        "system": [],
        "python_packages": [],
        "external_tools": [],
        "services": [],
        "config": [],
        "async_checks": [],
        "summary": {"passed": 0, "failed": 0, "warnings": 0}
    }

    print(f"\n{Colors.BOLD}{Colors.BLUE}1. System Checks{Colors.RESET}")
    checks = [
        ("Python Version", check_python_version()),
        ("OS Platform", (True, f"{platform.system()} {platform.release()}")),
        ("Architecture", (True, platform.machine())),
    ]
    for name, (passed, details) in checks:
        print_result(name, passed, details)
        results["system"].append({"name": name, "passed": passed, "details": details})
        if passed: results["summary"]["passed"] += 1
        else: results["summary"]["failed"] += 1

    print(f"\n{Colors.BOLD}{Colors.BLUE}2. External Tools{Colors.RESET}")
    tools = [
        ("Ollama CLI", check_ollama()),
        ("Ollama Model (llama3:8b)", check_ollama_model("llama3:8b")),
        ("Tesseract OCR", check_command("tesseract", "--version")),
        ("Playwright", check_command("playwright", "--version")),
        ("Git", check_command("git", "--version")),
        ("Curl", check_command("curl", "--version")),
    ]
    for name, (passed, details) in tools:
        print_result(name, passed, details)
        results["external_tools"].append({"name": name, "passed": passed, "details": details})
        if passed: results["summary"]["passed"] += 1
        else: results["summary"]["failed"] += 1

    print(f"\n{Colors.BOLD}{Colors.BLUE}3. Python Packages{Colors.RESET}")
    packages = [
        ("easyocr", check_python_import("easyocr", "__version__")),
        ("playwright", check_python_import("playwright", "__version__")),
        ("pytesseract", check_python_import("pytesseract", "__version__")),
        ("cv2 (OpenCV)", check_python_import("cv2", "__version__")),
        ("numpy", check_python_import("numpy", "__version__")),
        ("pandas", check_python_import("pandas", "__version__")),
        ("PIL/Pillow", check_python_import("PIL", "__version__")),
        ("pytesseract", check_python_import("pytesseract", "__version__")),
        ("whisper", check_python_import("whisper", "__version__")),
        ("faster_whisper", check_python_import("faster_whisper", "__version__")),
        ("pyttsx3", check_python_import("pyttsx3", "__version__")),
        ("ollama", check_python_import("ollama", "__version__")),
        ("playwright", check_python_import("playwright", "__version__")),
        ("cv2", check_python_import("cv2", "__version__")),
        ("pytz", check_python_import("pytz", "__version__")),
        ("aiohttp", check_python_import("aiohttp", "__version__")),
        ("pydantic", check_python_import("pydantic", "__version__")),
        ("aiosqlite", check_python_import("aiosqlite", "__version__")),
        ("pyyaml", check_python_import("yaml", "__version__")),
        ("python-dotenv", check_python_import("dotenv", "__version__")),
        ("croniter", check_python_import("croniter", "__version__")),
        ("psutil", check_python_import("psutil", "__version__")),
        ("GPUtil", check_python_import("GPUtil", "__version__")),
        ("reportlab", check_python_import("reportlab", "__version__")),
        ("openpyxl", check_python_import("openpyxl", "__version__")),
        ("paho-mqtt", check_python_import("paho.mqtt", "__version__")),
        ("sounddevice", check_python_import("sounddevice", "__version__")),
        ("soundfile", check_python_import("soundfile", "__version__")),
        ("paho.mqtt.client", check_python_import("paho.mqtt.client", "__version__")),
        ("pyautogui", check_python_import("pyautogui", "__version__")),
        ("pygetwindow", check_python_import("pygetwindow", "__version__")),
    ]
    for name, (passed, details) in packages:
        print_result(name, passed, details)
        results["python_packages"].append({"name": name, "passed": passed, "details": details})
        if passed: results["summary"]["passed"] += 1
        else: results["summary"]["failed"] += 1

    print(f"\n{Colors.BOLD}{Colors.BLUE}4. Configuration & Directories{Colors.RESET}")
    config_checks = [
        ("Config File", check_config(Path("config.json"))),
        ("Directories", check_directories(Path("."))),
        ("File Permissions", check_file_permissions(Path("."))),
    ]
    for name, (passed, details) in config_checks:
        print_result(name, passed, details)
        results["config"].append({"name": name, "passed": passed, "details": details})
        if passed: results["summary"]["passed"] += 1
        else: results["summary"]["failed"] += 1

    print(f"\n{Colors.BOLD}{Colors.BLUE}5. Services{Colors.RESET}")
    service_checks = [
        ("Ollama Service", check_ollama_service()),
    ]
    for name, (passed, details) in service_checks:
        print_result(name, passed, details)
        results["services"].append({"name": name, "passed": passed, "details": details})
        if passed: results["summary"]["passed"] += 1
        else: results["summary"]["failed"] += 1

    print(f"\n{Colors.BOLD}{Colors.BLUE}6. Async Component Tests{Colors.RESET}")
    async_checks = [
        ("Ollama Generation", check_ollama_generation()),
        ("EasyOCR", check_easyocr()),
        ("Playwright", check_playwright()),
        ("Tesseract OCR", check_tesseract()),
        ("pyttsx3 TTS", check_pyttsx3()),
        ("Whisper STT", check_whisper()),
        ("OpenCV", check_opencv()),
        ("PyAutoGUI", check_pyautogui()),
    ]
    for name, coro in async_checks:
        try:
            passed, details = await coro
            print_result(name, passed, details)
            results["async_checks"].append({"name": name, "passed": passed, "details": details})
            if passed: results["summary"]["passed"] += 1
            else: results["summary"]["failed"] += 1
        except Exception as e:
            print_result(name, False, str(e))
            results["async_checks"].append({"name": name, "passed": False, "details": str(e)})
            results["summary"]["failed"] += 1

    return results

def print_summary(results: Dict[str, Any]):
    """Print final summary"""
    s = results["summary"]
    total = s["passed"] + s["failed"] + s["warnings"]

    print(f"\n{Colors.CYAN}{'='*70}{Colors.RESET}")
    print(f"{Colors.BOLD}VERIFICATION SUMMARY{Colors.RESET}")
    print(f"{Colors.CYAN}{'='*70}{Colors.RESET}")
    print(f"  {Colors.GREEN}Passed:{Colors.RESET}  {s['passed']}")
    print(f"  {Colors.RED}Failed:{Colors.RESET}  {s['failed']}")
    print(f"  {Colors.YELLOW}Warnings:{Colors.RESET} {s['warnings']}")
    print(f"  {Colors.WHITE}Total:{Colors.RESET}   {total}")

    if s["failed"] == 0:
        print(f"\n{Colors.GREEN}{Colors.BOLD}✓ ALL CHECKS PASSED - System Ready!{Colors.RESET}")
        return 0
    else:
        print(f"\n{Colors.RED}{Colors.BOLD}✗ {s['failed']} CHECKS FAILED - Fix Required{Colors.RESET}")

        # Show failed items
        print(f"\n{Colors.BOLD}Failed Items:{Colors.RESET}")
        for category in ["system", "python_packages", "external_tools", "services", "config", "async_checks"]:
            for item in results[category]:
                if not item["passed"]:
                    print(f"  {Colors.RED}✗{Colors.RESET} {item['name']}: {item['details']}")

        print(f"\n{Colors.YELLOW}Common Fixes:{Colors.RESET}")
        print("  • Ollama not running:    ollama serve")
        print("  • Missing Python package: pip install <package>")
        print("  • Missing system tool:    Install via package manager")
        print("  • Config missing:        cp config.json.example config.json")
        print("  • Permissions:           chmod -R 755 ./data ./output ./temp")
        return 1

async def main():
    print_banner()

    # Change to script directory
    script_dir = Path(__file__).parent
    os.chdir(script_dir.parent)

    results = await run_all_checks()
    exit_code = print_summary(results)
    sys.exit(exit_code)

if __name__ == "__main__":
    asyncio.run(main())