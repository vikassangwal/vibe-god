#!/usr/bin/env python3
"""
Wife God eMitra + Twitter Automation - Automated Setup Script
Installs system dependencies, Python packages, and configures the environment
"""

import asyncio
import logging
import platform
import subprocess
import sys
import os
import shutil
from pathlib import Path
from typing import List, Tuple

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger("WifeGod.Setup")


class WifeGodSetup:
    """Automated setup for Wife God Agent"""

    def __init__(self, project_root: Path = None):
        self.project_root = project_root or Path(__file__).parent.parent
        self.is_windows = platform.system() == "Windows"
        self.is_linux = platform.system() == "Linux"
        self.is_macos = platform.system() == "Darwin"

    def run_command(self, cmd: List[str], check: bool = True, shell: bool = False) -> Tuple[int, str, str]:
        """Run shell command and return (returncode, stdout, stderr)"""
        logger.info(f"Running: {' '.join(cmd) if isinstance(cmd, list) else cmd}")
        try:
            result = subprocess.run(
                cmd, shell=shell, capture_output=True, text=True, timeout=300, check=check
            )
            if result.stdout:
                logger.debug(result.stdout.strip())
            if result.stderr:
                logger.warning(result.stderr.strip())
            return result.returncode, result.stdout, result.stderr
        except subprocess.CalledProcessError as e:
            logger.error(f"Command failed: {e}")
            if e.stdout:
                logger.debug(e.stdout)
            if e.stderr:
                logger.error(e.stderr)
            return e.returncode, e.stdout or "", e.stderr or ""
        except subprocess.TimeoutExpired:
            logger.error("Command timed out")
            return -1, "", "Timeout"

    def check_python_version(self) -> bool:
        """Check Python version >= 3.10"""
        version = sys.version_info
        if version.major < 3 or (version.major == 3 and version.minor < 10):
            logger.error(f"Python 3.10+ required, found {version.major}.{version.minor}")
            return False
        logger.info(f"✓ Python {version.major}.{version.minor}.{version.micro}")
        return True

    def check_command(self, cmd: str) -> bool:
        """Check if command exists"""
        return shutil.which(cmd) is not None

    def install_system_deps_linux(self) -> bool:
        """Install system dependencies on Linux"""
        logger.info("Installing system dependencies for Linux...")

        # Update package list
        self.run_command(["apt-get", "update"])

        # Install packages
        packages = [
            "tesseract-ocr",
            "tesseract-ocr-hin",
            "libgl1-mesa-glx",
            "portaudio19-dev",
            "chromium-browser",
            "python3-dev",
            "python3-pip",
            "python3-venv",
            "git",
            "curl",
            "wget",
        ]

        for pkg in packages:
            logger.info(f"Installing {pkg}...")
            ret, _, _ = self.run_command(["apt-get", "install", "-y", pkg])
            if ret != 0:
                logger.warning(f"Failed to install {pkg}")

        return True

    def install_system_deps_macos(self) -> bool:
        """Install system dependencies on macOS"""
        logger.info("Installing system dependencies for macOS...")

        if not self.check_command("brew"):
            logger.error("Homebrew not found. Install from https://brew.sh")
            return False

        packages = [
            "tesseract",
            "tesseract-lang",
            "portaudio",
            "chromium",
            "python@3.11",
        ]

        for pkg in packages:
            logger.info(f"Installing {pkg}...")
            self.run_command(["brew", "install", pkg])

        return True

    def install_system_deps_windows(self) -> bool:
        """Install system dependencies on Windows"""
        logger.info("Installing system dependencies for Windows...")

        # Check for Chocolatey
        if not self.check_command("choco"):
            logger.warning("Chocolatey not found. Install from https://chocolatey.org")
            logger.info("Manual installation required for:")
            logger.info("  - Tesseract OCR: https://github.com/UB-Mannheim/tesseract/wiki")
            logger.info("  - Chrome/Chromium")
            logger.info("  - Git")
            return True  # Don't fail, just warn

        packages = [
            "tesseract",
            "googlechrome",
            "git",
        ]

        for pkg in packages:
            logger.info(f"Installing {pkg}...")
            self.run_command(["choco", "install", "-y", pkg])

        return True

    def install_ollama(self) -> bool:
        """Install Ollama"""
        if self.check_command("ollama"):
            logger.info("✓ Ollama already installed")
            return True

        logger.info("Installing Ollama...")
        if self.is_linux or self.is_macos:
            ret, _, _ = self.run_command(
                ["sh", "-c", "curl -fsSL https://ollama.com/install.sh | sh"]
            )
            return ret == 0
        elif self.is_windows:
            logger.info("Please install Ollama manually from https://ollama.com/download")
            return True  # Don't fail on Windows
        return False

    def pull_ollama_model(self, model: str = "llama3:8b") -> bool:
        """Pull Ollama model"""
        logger.info(f"Pulling Ollama model: {model}...")
        ret, _, _ = self.run_command(["ollama", "pull", model])
        return ret == 0

    def create_venv(self, venv_path: Path) -> bool:
        """Create virtual environment"""
        if venv_path.exists():
            logger.info(f"Virtual environment exists at {venv_path}")
            return True

        logger.info(f"Creating virtual environment at {venv_path}...")
        ret, _, _ = self.run_command([sys.executable, "-m", "venv", str(venv_path)])
        return ret == 0

    def get_pip_path(self, venv_path: Path) -> Path:
        """Get pip executable path"""
        if self.is_windows:
            return venv_path / "Scripts" / "pip.exe"
        return venv_path / "bin" / "pip"

    def install_python_deps(self, venv_path: Path) -> bool:
        """Install Python dependencies"""
        pip_path = self.get_pip_path(venv_path)
        req_file = self.project_root / "requirements.txt"

        if not req_file.exists():
            logger.error(f"Requirements file not found: {req_file}")
            return False

        logger.info("Installing Python dependencies...")
        ret, _, _ = self.run_command([str(pip_path), "install", "-r", str(req_file)])
        return ret == 0

    def install_playwright(self, venv_path: Path) -> bool:
        """Install Playwright browsers"""
        pip_path = self.get_pip_path(venv_path)
        logger.info("Installing Playwright browsers...")
        ret, _, _ = self.run_command([str(pip_path), "install", "playwright"])
        if ret != 0:
            return False

        # Install browsers
        python_exe = self.get_python_path(venv_path)
        ret, _, _ = self.run_command([str(python_exe), "-m", "playwright", "install", "chromium"])
        return ret == 0

    def get_python_path(self, venv_path: Path) -> Path:
        """Get Python executable path"""
        if self.is_windows:
            return venv_path / "Scripts" / "python.exe"
        return venv_path / "bin" / "python"

    def create_directories(self) -> None:
        """Create required directories"""
        dirs = [
            self.project_root / "data",
            self.project_root / "input_documents",
            self.project_root / "output",
            self.project_root / "temp",
            self.project_root / "models",
            self.project_root / "screenshots" / "templates",
            self.project_root / "logs",
        ]

        for d in dirs:
            d.mkdir(parents=True, exist_ok=True)
            logger.info(f"Created directory: {d}")

    def create_config(self) -> None:
        """Create config.json from template"""
        config_file = self.project_root / "config.json"
        template_file = self.project_root / "config.json.example"

        if config_file.exists():
            logger.info("✓ config.json already exists")
            return

        if template_file.exists():
            shutil.copy(template_file, config_file)
        else:
            # Create default config
            import json
            default_config = {
                "app": {"input_folder": "./input_documents", "output_folder": "./output"},
                "ollama": {"url": "http://localhost:11434", "model": "llama3:8b"},
                "emitra": {"username": "", "password": ""},
                "twitter": {"username": "", "password": ""},
            }
            with open(config_file, 'w') as f:
                json.dump(default_config, f, indent=2)

        logger.info("✓ Created config.json - Please edit with your credentials!")

    def run_full_setup(self) -> bool:
        """Run complete setup"""
        logger.info("=" * 60)
        logger.info("Wife God eMitra + Twitter Automation - Setup")
        logger.info("=" * 60)

        # Check Python
        if not self.check_python_version():
            return False

        # Install system dependencies
        if self.is_linux:
            self.install_system_deps_linux()
        elif self.is_macos:
            self.install_system_deps_macos()
        elif self.is_windows:
            self.install_system_deps_windows()

        # Install Ollama
        self.install_ollama()

        # Pull model
        self.pull_ollama_model("llama3:8b")

        # Create directories
        self.create_directories()

        # Create venv
        venv_path = self.project_root / "venv"
        if not self.create_venv(venv_path):
            logger.error("Failed to create virtual environment")
            return False

        # Install Python deps
        if not self.install_python_deps(venv_path):
            logger.error("Failed to install Python dependencies")
            return False

        # Install Playwright
        if not self.install_playwright(venv_path):
            logger.warning("Playwright installation had issues")

        # Create config
        self.create_config()

        # Create config.json.example if not exists
        example_config = self.project_root / "config.json.example"
        if not example_config.exists():
            import json
            example = {
                "app": {"input_folder": "./input_documents", "output_folder": "./output"},
                "ollama": {"url": "http://localhost:11434", "model": "llama3:8b"},
                "emitra": {"username": "", "password": ""},
                "twitter": {"username": "", "password": ""},
                "voice": {"tts_engine": "pyttsx3", "whisper_model": "base"}
            }
            with open(example_config, 'w') as f:
                json.dump(example, f, indent=2)

        logger.info("=" * 60)
        logger.info("Setup Complete!")
        logger.info("=" * 60)
        logger.info("")
        logger.info("Next steps:")
        logger.info("1. Edit config.json with your credentials")
        logger.info("2. Start Ollama: ollama serve")
        logger.info("3. Run: python -m main")
        logger.info("")

        return True


def main():
    setup = WifeGodSetup()
    success = setup.run_full_setup()
    sys.exit(0 if success else 1)


if __name__ == "__main__":
    main()