#!/usr/bin/env python3
"""
Wife God - 100% Local eMitra (Rajasthan SSO) + Twitter (X) Automation Agent
=============================================================================
Fully autonomous, no external cloud APIs. Runs entirely on local hardware.

Architecture:
- Local OCR: EasyOCR/Tesseract
- Local LLM: Ollama (Llama-3/Qwen/Mistral)
- Web Automation: Playwright + PyAutoGUI fallback
- Voice: pyttsx3 (TTS) + Whisper-local (STT)
- Database: SQLite
- Document Processing: Pillow + img2pdf

Author: Wife God System
"""

import asyncio
import logging
import sys
import os
import signal
import json
from pathlib import Path
from typing import Dict, Any, Optional, List
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent))

# Core modules
from core.config import Config
from core.database import DatabaseManager
from core.local_llm import LocalLLM
from core.voice import VoiceCommunicator
from modules.doc_processor import DocProcessor
from modules.captcha_solver import CaptchaSolver
from modules.pyautogui_fallback import PyAutoGUIFallback
from bots.emitra_bot import eMitraBot
from bots.twitter_bot import TwitterBot

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('wife_god.log'),
        logging.StreamHandler(sys.stdout)
    ]
)
logger = logging.getLogger("WifeGod")


class TaskType(Enum):
    EMITRA_SERVICE = "emitra_service"
    TWITTER_POST = "twitter_post"
    TWITTER_SCRAPE = "twitter_scrape"
    TWITTER_DM = "twitter_dm"
    DOC_PROCESS = "doc_process"
    VOICE_INTERACTION = "voice_interaction"


class TaskStatus(Enum):
    PENDING = "pending"
    RUNNING = "running"
    WAITING_INPUT = "waiting_input"
    COMPLETED = "completed"
    FAILED = "failed"


@dataclass
class Task:
    id: str
    type: TaskType
    status: TaskStatus = TaskStatus.PENDING
    params: Dict[str, Any] = field(default_factory=dict)
    result: Dict[str, Any] = field(default_factory=dict)
    created_at: datetime = field(default_factory=datetime.now)
    updated_at: datetime = field(default_factory=datetime.now)
    error: Optional[str] = None


class WifeGodAgent:
    """
    Central controller for Wife God - The Sovereign Local AI Agent
    Orchestrates all modules for eMitra + Twitter automation
    """

    def __init__(self, config_path: str = "config.json"):
        self.config = Config(config_path)
        self.db = DatabaseManager(self.config.db_path)
        self.llm = LocalLLM(self.config.ollama_url, self.config.ollama_model)
        self.voice = VoiceCommunicator(self.config.voice_config)
        self.doc_processor = DocProcessor(self.config.doc_config)
        self.captcha_solver = CaptchaSolver(self.config.captcha_config)
        self.pyautogui_fallback = PyAutoGUIFallback(self.config.fallback_config)

        # Bots
        self.emitra_bot = eMitraBot(
            config=self.config.emitra_config,
            llm=self.llm,
            voice=self.voice,
            doc_processor=self.doc_processor,
            captcha_solver=self.captcha_solver,
            pyautogui_fallback=self.pyautogui_fallback,
            db=self.db
        )
        self.twitter_bot = TwitterBot(
            config=self.config.twitter_config,
            llm=self.llm,
            voice=self.voice,
            doc_processor=self.doc_processor,
            pyautogui_fallback=self.pyautogui_fallback,
            db=self.db
        )

        # State
        self.running = False
        self.current_task: Optional[Task] = None
        self.task_queue: asyncio.Queue = asyncio.Queue()
        self._shutdown_event = asyncio.Event()

        # Setup signal handlers
        signal.signal(signal.SIGINT, self._signal_handler)
        signal.signal(signal.SIGTERM, self._signal_handler)

    def _signal_handler(self, signum, frame):
        logger.info(f"Received signal {signum}, initiating graceful shutdown...")
        asyncio.create_task(self.shutdown())

    async def initialize(self):
        """Initialize all components"""
        logger.info("=" * 60)
        logger.info("Initializing Wife God - Sovereign Local AI Agent")
        logger.info("=" * 60)

        # Initialize database
        await self.db.initialize()
        logger.info("✓ Database initialized")

        # Test Ollama connection
        if await self.llm.health_check():
            logger.info(f"✓ Ollama connected: {self.config.ollama_model}")
        else:
            logger.warning("⚠ Ollama not available - some features limited")

        # Initialize voice
        await self.voice.initialize()
        logger.info("✓ Voice system initialized")

        # Initialize document processor
        await self.doc_processor.initialize()
        logger.info("✓ Document processor initialized")

        # Initialize captcha solver
        await self.captcha_solver.initialize()
        logger.info("✓ Captcha solver initialized")

        # Initialize bots
        await self.emitra_bot.initialize()
        logger.info("✓ eMitra bot initialized")

        await self.twitter_bot.initialize()
        logger.info("✓ Twitter bot initialized")

        # Start background tasks
        self.running = True
        asyncio.create_task(self._task_processor())
        asyncio.create_task(self._watch_input_folder())
        asyncio.create_task(self._health_monitor())

        logger.info("=" * 60)
        logger.info("Wife God fully initialized and ready!")
        logger.info("=" * 60)

        # Announce readiness
        await self.voice.speak("Wife God system ready. Awaiting commands.")

    async def shutdown(self):
        """Graceful shutdown"""
        logger.info("Shutting down Wife God...")
        self.running = False

        # Wait for current task
        if self.current_task and self.current_task.status == TaskStatus.RUNNING:
            logger.info("Waiting for current task to complete...")
            await asyncio.sleep(2)

        # Close bots
        await self.emitra_bot.close()
        await self.twitter_bot.close()

        # Close voice
        await self.voice.close()

        # Close database
        await self.db.close()

        self._shutdown_event.set()
        logger.info("Wife God shutdown complete")

    async def _task_processor(self):
        """Process tasks from queue"""
        while self.running:
            try:
                task = await asyncio.wait_for(self.task_queue.get(), timeout=1.0)
                await self._execute_task(task)
            except asyncio.TimeoutError:
                continue
            except Exception as e:
                logger.error(f"Task processor error: {e}")

    async def _execute_task(self, task: Task):
        """Execute a single task"""
        self.current_task = task
        task.status = TaskStatus.RUNNING
        task.updated_at = datetime.now()
        await self.db.log_task(task)

        try:
            logger.info(f"Executing task: {task.id} ({task.type.value})")

            if task.type == TaskType.EMITRA_SERVICE:
                result = await self.emitra_bot.execute_service(task.params)
            elif task.type == TaskType.TWITTER_POST:
                result = await self.twitter_bot.post_tweet(task.params)
            elif task.type == TaskType.TWITTER_SCRAPE:
                result = await self.twitter_bot.scrape_hashtag(task.params)
            elif task.type == TaskType.TWITTER_DM:
                result = await self.twitter_bot.handle_dm(task.params)
            elif task.type == TaskType.DOC_PROCESS:
                result = await self.doc_processor.process_batch(task.params)
            elif task.type == TaskType.VOICE_INTERACTION:
                result = await self.voice.handle_interaction(task.params)
            else:
                raise ValueError(f"Unknown task type: {task.type}")

            task.result = result
            task.status = TaskStatus.COMPLETED
            logger.info(f"Task completed: {task.id}")

        except Exception as e:
            logger.error(f"Task failed: {task.id} - {e}")
            task.status = TaskStatus.FAILED
            task.error = str(e)

            # Notify via voice
            await self.voice.speak(f"Task failed: {str(e)[:100]}")

        finally:
            task.updated_at = datetime.now()
            await self.db.log_task(task)
            self.current_task = None

    async def _watch_input_folder(self):
        """Watch input folder for new documents"""
        input_folder = Path(self.config.input_folder)
        input_folder.mkdir(parents=True, exist_ok=True)

        processed = set()

        while self.running:
            try:
                for file_path in input_folder.glob("*"):
                    if file_path.is_file() and file_path not in processed:
                        if file_path.suffix.lower() in ['.jpg', '.jpeg', '.png', '.pdf', '.tiff']:
                            logger.info(f"New document detected: {file_path.name}")
                            processed.add(file_path)

                            # Auto-process document
                            await self.task_queue.put(Task(
                                id=f"doc_{datetime.now().timestamp()}",
                                type=TaskType.DOC_PROCESS,
                                params={"file_path": str(file_path), "auto": True}
                            ))

                await asyncio.sleep(5)
            except Exception as e:
                logger.error(f"Input folder watcher error: {e}")

    async def _health_monitor(self):
        """Monitor system health"""
        while self.running:
            try:
                await asyncio.sleep(60)  # Check every minute

                # Check Ollama
                if not await self.llm.health_check():
                    logger.warning("Ollama health check failed")

                # Check disk space
                import shutil
                disk = shutil.disk_usage("/")
                if disk.free / disk.total < 0.1:
                    await self.voice.speak("Warning: Low disk space")

            except Exception as e:
                logger.error(f"Health monitor error: {e}")

    # Public API methods

    async def request_emitra_service(self, service_name: str, documents: List[str],
                                     user_data: Dict[str, Any]) -> Dict[str, Any]:
        """Request eMitra service execution"""
        task = Task(
            id=f"emitra_{datetime.now().timestamp()}",
            type=TaskType.EMITRA_SERVICE,
            params={
                "service": service_name,
                "documents": documents,
                "user_data": user_data
            }
        )
        await self.task_queue.put(task)

        # Wait for completion (with timeout)
        for _ in range(300):  # 5 min timeout
            await asyncio.sleep(1)
            if task.status in [TaskStatus.COMPLETED, TaskStatus.FAILED]:
                break

        return task.result if task.status == TaskStatus.COMPLETED else {"error": task.error}

    async def post_tweet(self, text: str, media_paths: List[str] = None,
                         reply_to: str = None) -> Dict[str, Any]:
        """Post a tweet"""
        task = Task(
            id=f"tweet_{datetime.now().timestamp()}",
            type=TaskType.TWITTER_POST,
            params={
                "text": text,
                "media_paths": media_paths or [],
                "reply_to": reply_to
            }
        )
        await self.task_queue.put(task)

        for _ in range(60):
            await asyncio.sleep(1)
            if task.status in [TaskStatus.COMPLETED, TaskStatus.FAILED]:
                break

        return task.result if task.status == TaskStatus.COMPLETED else {"error": task.error}

    async def scrape_hashtag(self, hashtag: str, limit: int = 50) -> Dict[str, Any]:
        """Scrape tweets by hashtag"""
        task = Task(
            id=f"scrape_{datetime.now().timestamp()}",
            type=TaskType.TWITTER_SCRAPE,
            params={"hashtag": hashtag, "limit": limit}
        )
        await self.task_queue.put(task)

        for _ in range(60):
            await asyncio.sleep(1)
            if task.status in [TaskStatus.COMPLETED, TaskStatus.FAILED]:
                break

        return task.result if task.status == TaskStatus.COMPLETED else {"error": task.error}

    async def process_documents(self, file_paths: List[str]) -> Dict[str, Any]:
        """Process documents through OCR and structuring"""
        task = Task(
            id=f"doc_{datetime.now().timestamp()}",
            type=TaskType.DOC_PROCESS,
            params={"file_paths": file_paths}
        )
        await self.task_queue.put(task)

        for _ in range(120):
            await asyncio.sleep(1)
            if task.status in [TaskStatus.COMPLETED, TaskStatus.FAILED]:
                break

        return task.result if task.status == TaskStatus.COMPLETED else {"error": task.error}

    async def voice_command(self, command: str) -> Dict[str, Any]:
        """Process voice command"""
        return await self.voice.process_command(command, self)

    def get_status(self) -> Dict[str, Any]:
        """Get system status"""
        return {
            "running": self.running,
            "current_task": self.current_task.id if self.current_task else None,
            "queue_size": self.task_queue.qsize(),
            "emitra_ready": self.emitra_bot.is_ready(),
            "twitter_ready": self.twitter_bot.is_ready(),
            "ollama_healthy": asyncio.run(self.llm.health_check()) if self.running else False,
            "voice_ready": self.voice.is_ready(),
        }


async def main():
    """Main entry point"""
    # Set encoding for Windows console
    if sys.platform == "win32":
        try:
            sys.stdout.reconfigure(encoding="utf-8", errors="replace")
            sys.stderr.reconfigure(encoding="utf-8", errors="replace")
        except AttributeError:
            pass

    # Print banner
    print("""
    ================================================================
                         WIFE GOD - SOVEREIGN AI
              100% Local eMitra + Twitter Automation Agent
    ================================================================
    """)

    # Create agent
    agent = WifeGodAgent("config.json")

    try:
        await agent.initialize()

        # Keep running
        print("\nWife God is running. Press Ctrl+C to stop.")
        print("Commands available via voice or API.")
        print("-" * 50)

        # Wait for shutdown
        await agent._shutdown_event.wait()

    except KeyboardInterrupt:
        print("\nShutdown requested...")
    except Exception as e:
        logger.error(f"Fatal error: {e}")
        import traceback
        traceback.print_exc()
    finally:
        await agent.shutdown()
        print("Wife God shutdown complete.")


if __name__ == "__main__":
    asyncio.run(main())