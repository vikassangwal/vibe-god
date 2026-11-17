"""
Voice Communication Module for Wife God Agent
TTS: pyttsx3 (offline)
STT: Whisper-local (faster-whisper)
"""

import asyncio
import logging
import tempfile
import os
import threading
import queue
import time
import uuid
from pathlib import Path
from typing import Dict, Any, Optional, Callable, List
from dataclasses import dataclass
from datetime import datetime
from enum import Enum

try:
    import pyttsx3
except ImportError:
    pyttsx3 = None

try:
    from faster_whisper import WhisperModel
except ImportError:
    WhisperModel = None

try:
    import sounddevice as sd
    import soundfile as sf
    import numpy as np
except ImportError:
    sd = None
    sf = None
    np = None

logger = logging.getLogger("WifeGod.Voice")


class VoiceState(Enum):
    IDLE = "idle"
    LISTENING = "listening"
    PROCESSING = "processing"
    SPEAKING = "speaking"


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
    vad_silence_duration: float = 2.0


@dataclass
class VoiceInteraction:
    id: str
    task_id: Optional[str]
    direction: str  # "input" or "output"
    text: str
    audio_path: Optional[str]
    timestamp: datetime


class VoiceCommunicator:
    """
    Voice communication module with offline TTS and STT
    TTS: pyttsx3 (offline, supports Hindi/English)
    STT: faster-whisper (local Whisper)
    """

    def __init__(self, config: Dict[str, Any]):
        self.config = VoiceConfig(**config) if isinstance(config, dict) else config
        self.state = VoiceState.IDLE
        self._tts_engine = None
        self._stt_model = None
        self._audio_queue = queue.Queue()
        self._recording = False
        self._audio_stream = None
        self._interaction_log: List = []
        self._waiting_for_input = False
        self._input_future: Optional[asyncio.Future] = None
        self._callbacks: Dict[str, Callable] = {}

    async def initialize(self):
        """Initialize voice components"""
        logger.info("Initializing VoiceCommunicator...")

        # Initialize TTS
        await self._init_tts()

        # Initialize STT
        await self._init_stt()

        logger.info("VoiceCommunicator initialized")

    async def _init_tts(self):
        """Initialize TTS engine"""
        if not pyttsx3:
            logger.warning("pyttsx3 not available, TTS disabled")
            return

        try:
            self._tts_engine = pyttsx3.init()

            # Configure voice
            voices = self._tts_engine.getProperty('voices')
            for voice in voices:
                if 'hindi' in voice.name.lower() or 'india' in voice.name.lower():
                    self._tts_engine.setProperty('voice', voice.id)
                    break

            self._tts_engine.setProperty('rate', self.config.tts_rate)
            self._tts_engine.setProperty('volume', self.config.tts_volume)

            logger.info("TTS engine initialized")
        except Exception as e:
            logger.error(f"TTS initialization failed: {e}")

    async def _init_stt(self):
        """Initialize STT model"""
        if not WhisperModel:
            logger.warning("faster-whisper not available, STT disabled")
            return

        try:
            # Load model in thread to avoid blocking
            loop = asyncio.get_event_loop()
            self._stt_model = await loop.run_in_executor(
                None,
                lambda: WhisperModel(
                    self.config.whisper_model,
                    device="cpu",
                    compute_type="int8"
                )
            )
            logger.info(f"STT model loaded: {self.config.whisper_model}")
        except Exception as e:
            logger.error(f"STT initialization failed: {e}")

    async def speak(self, text: str, language: str = "hi") -> bool:
        """Speak text using TTS"""
        if not self._tts_engine:
            logger.warning("TTS not available")
            return False

        self.state = VoiceState.SPEAKING

        try:
            # Log interaction
            interaction = VoiceInteraction(
                id=str(uuid.uuid4()),
                task_id=None,
                direction="output",
                text=text,
                audio_path=None,
                timestamp=datetime.now()
            )
            self._interaction_log.append(interaction)

            # Use thread for TTS to avoid blocking
            loop = asyncio.get_event_loop()
            await loop.run_in_executor(
                None,
                lambda: self._tts_engine.say(text) or self._tts_engine.runAndWait()
            )

            self.state = VoiceState.IDLE
            return True
        except Exception as e:
            logger.error(f"TTS error: {e}")
            self.state = VoiceState.IDLE
            return False

    async def speak_async(self, text: str, callback: Callable = None):
        """Speak asynchronously with callback"""
        asyncio.create_task(self._speak_with_callback(text, callback))

    async def _speak_with_callback(self, text: str, callback: Callable):
        await self.speak(text)
        if callback:
            callback()

    async def listen(self, timeout: float = 10.0, language: str = "hi") -> Optional[str]:
        """Listen for voice input and return transcribed text"""
        if not self._stt_model:
            logger.warning("STT not available")
            return None

        self.state = VoiceState.LISTENING
        logger.info("Listening...")

        try:
            # Record audio
            audio_path = await self._record_audio(timeout)
            if not audio_path:
                return None

            self.state = VoiceState.PROCESSING

            # Transcribe
            text = await self._transcribe_audio(audio_path, language)

            # Clean up temp file
            try:
                os.unlink(audio_path)
            except:
                pass

            # Log interaction
            interaction = VoiceInteraction(
                id=str(uuid.uuid4()),
                task_id=None,
                direction="input",
                text=text or "",
                audio_path=audio_path,
                timestamp=datetime.now()
            )
            self._interaction_log.append(interaction)

            self.state = VoiceState.IDLE
            return text

        except Exception as e:
            logger.error(f"Listen error: {e}")
            self.state = VoiceState.IDLE
            return None

    async def _record_audio(self, timeout: float) -> Optional[str]:
        """Record audio from microphone"""
        if not sd:
            logger.warning("sounddevice not available")
            return None

        # Create temp file
        temp_file = tempfile.NamedTemporaryFile(suffix='.wav', delete=False)
        temp_path = temp_file.name
        temp_file.close()

        try:
            # Record with VAD
            duration = 0
            silence_duration = 0
            recording = []

            def callback(indata, frames, time_info, status):
                nonlocal duration, silence_duration, recording
                recording.append(indata.copy())
                duration += frames / self.config.sample_rate

                # Simple VAD
                volume_norm = np.linalg.norm(indata) * 10
                if volume_norm < self.config.vad_threshold:
                    silence_duration += frames / self.config.sample_rate
                else:
                    silence_duration = 0

            # Start recording
            with sd.InputStream(
                samplerate=self.config.sample_rate,
                channels=1,
                callback=callback,
                dtype='float32'
            ):
                start_time = time.time()
                while duration < timeout and silence_duration < self.config.vad_silence_duration:
                    await asyncio.sleep(0.1)
                    if time.time() - start_time > timeout:
                        break

            # Save recording
            if recording:
                audio_data = np.concatenate(recording, axis=0)
                sf.write(temp_path, audio_data, self.config.sample_rate)
                return temp_path

            return None

        except Exception as e:
            logger.error(f"Recording error: {e}")
            return None

    async def _transcribe_audio(self, audio_path: str, language: str) -> Optional[str]:
        """Transcribe audio file using Whisper"""
        if not self._stt_model:
            return None

        try:
            loop = asyncio.get_event_loop()
            segments, info = await loop.run_in_executor(
                None,
                lambda: self._stt_model.transcribe(
                    audio_path,
                    language=language if language != "auto" else None,
                    vad_filter=True,
                    vad_parameters=dict(min_silence_duration_ms=500)
                )
            )

            text = " ".join([seg.text for seg in segments])
            return text.strip() if text.strip() else None

        except Exception as e:
            logger.error(f"Transcription error: {e}")
            return None

    async def wait_for_input(self, prompt: str, timeout: float = 60.0,
                             task_id: str = None) -> Optional[str]:
        """Wait for voice input with prompt"""
        self._waiting_for_input = True

        # Speak prompt
        await self.speak(prompt)

        # Create future for input
        self._input_future = asyncio.Future()

        try:
            # Wait for input with timeout
            result = await asyncio.wait_for(self._input_future, timeout=timeout)
            return result
        except asyncio.TimeoutError:
            await self.speak("Time out. No input received.")
            return None
        finally:
            self._waiting_for_input = False
            self._input_future = None

    async def provide_input(self, text: str):
        """Provide input to waiting future (for programmatic input)"""
        if self._input_future and not self._input_future.done():
            self._input_future.set_result(text)

    async def ask_for_document(self, doc_type: str, task_id: str = None) -> Optional[str]:
        """Ask user for specific document"""
        prompts = {
            "aadhaar": "Aadhaar card ka photo ya PDF dein.",
            "photo": "Apna photo dein.",
            "signature": "Signature ka photo dein.",
            "marksheet": "Marksheet ka photo dein.",
            "income_certificate": "Income certificate ka photo dein.",
            "caste_certificate": "Caste certificate ka photo dein.",
            "domicile": "Domicile certificate ka photo dein.",
            "birth_certificate": "Birth certificate ka photo dein.",
            "death_certificate": "Death certificate ka photo dein.",
            "marriage_certificate": "Marriage certificate ka photo dein.",
            "pension": "Pension documents dein.",
            "ration_card": "Ration card ka photo dein.",
            "land_record": "Land record (khatauni/khasra) ka photo dein.",
            "address_proof": "Address proof ka photo dein.",
            "bank_passbook": "Bank passbook ka photo dein.",
        }

        prompt = prompts.get(doc_type, f"{doc_type} ka document dein.")
        full_prompt = f"Mujhe {prompt} Please provide the document."

        await self.speak(full_prompt)

        # Wait for file in input folder
        input_folder = Path("./input_documents")
        start_time = time.time()
        timeout = 60

        while time.time() - start_time < timeout:
            for ext in ['.jpg', '.jpeg', '.png', '.pdf', '.tiff']:
                files = list(Path("./input_documents").glob(f"*{ext}"))
                if files:
                    # Return newest file
                    newest = max(files, key=lambda f: f.stat().st_mtime)
                    return str(newest)
            await asyncio.sleep(2)

        await self.speak("Document nahi mila. Timeout.")
        return None

    async def ask_for_otp(self, otp_type: str = "Aadhaar", task_id: str = None) -> Optional[str]:
        """Ask user for OTP"""
        prompts = {
            "aadhaar": "Aadhaar OTP bataiye.",
            "mobile": "Mobile OTP bataiye.",
            "email": "Email OTP bataiye.",
        }

        prompt = prompts.get(otp_type, f"{otp_type} OTP bataiye.")
        await self.speak(f"Kripya {prompt}")

        # Wait for voice input
        return await self.wait_for_input("", timeout=60)

    async def process_command(self, command: str, agent) -> Dict[str, Any]:
        """Process voice command through LLM"""
        from core.local_llm import LocalLLM

        # Parse command through LLM
        parsed = await agent.llm.parse_voice_command(command)

        intent = parsed.get("intent", "unknown")
        params = parsed.get("params", {})
        confidence = parsed.get("confidence", 0.0)

        logger.info(f"Voice command parsed: {intent} (confidence: {confidence})")

        if confidence < 0.5:
            await self.speak("Samajh nahi aaya. Phir se bolo.")
            return {"error": "Low confidence"}

        # Execute based on intent
        if intent == "emitra_service":
            return await agent.request_emitra_service(
                params.get("service", ""),
                params.get("documents", []),
                params.get("user_data", {})
            )
        elif intent == "twitter_post":
            return await agent.post_tweet(
                params.get("text", ""),
                params.get("media_paths", [])
            )
        elif intent == "twitter_scrape":
            return await agent.scrape_hashtag(params.get("hashtag", ""))
        elif intent == "doc_process":
            return await agent.process_documents(params.get("file_paths", []))
        elif intent == "status":
            return agent.get_status()
        else:
            await self.speak("Ye command main nahi samjha.")
            return {"error": "Unknown intent"}

    async def register_callback(self, event: str, callback: Callable):
        """Register callback for voice events"""
        self._callbacks[event] = callback

    def is_ready(self) -> bool:
        return self._tts_engine is not None or self._stt_model is not None

    async def close(self):
        """Close voice components"""
        if self._tts_engine:
            self._tts_engine.stop()
        logger.info("VoiceCommunicator closed")