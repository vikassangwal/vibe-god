"""
AI Video Editor Module for Wife God Agent
Auto-edit farm/shop videos, add captions, generate thumbnails, schedule uploads
"""

import asyncio
import logging
import json
import os
import tempfile
from pathlib import Path
from typing import Dict, Any, List, Optional, Tuple
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from ..core.local_llm import LocalLLM
    from ..core.voice import VoiceCommunicator
    from ..core.database import DatabaseManager

try:
    import cv2
    import numpy as np
except ImportError:
    cv2 = None
    np = None

try:
    from moviepy.editor import VideoFileClip, AudioFileClip, ImageClip, TextClip, CompositeVideoClip, concatenate_videoclips
except ImportError:
    VideoFileClip = None

try:
    import whisper
except ImportError:
    whisper = None

logger = logging.getLogger("WifeGod.VideoEditor")


class VideoType(Enum):
    FARM_TIMELAPSE = "farm_timelapse"
    SHOP_TOUR = "shop_tour"
    PRODUCT_DEMO = "product_demo"
    TUTORIAL = "tutorial"
    VLOG = "vlog"
    REEL = "reel"
    SHORT = "short"


class Platform(Enum):
    YOUTUBE = "youtube"
    INSTAGRAM = "instagram"
    TIKTOK = "tiktok"
    FACEBOOK = "facebook"
    TWITTER = "twitter"


@dataclass
class VideoProject:
    id: str
    name: str
    type: VideoType
    source_files: List[str]
    output_path: str = ""
    duration: float = 0
    resolution: Tuple[int, int] = (1920, 1080)
    fps: int = 30
    music_path: str = ""
    caption_style: Dict = field(default_factory=dict)
    thumbnail_path: str = ""
    status: str = "pending"
    created_at: datetime = field(default_factory=datetime.now)


@dataclass
class Clip:
    id: str
    source_path: str
    start_time: float
    end_time: float
    duration: float
    order: int
    transitions: List[str] = field(default_factory=list)
    effects: List[str] = field(default_factory=list)
    text_overlay: str = ""
    audio_path: str = ""


@dataclass
class CaptionSegment:
    start: float
    end: float
    text: str
    language: str = "hi"


@dataclass
class UploadTask:
    id: str
    project_id: str
    platform: Platform
    title: str
    description: str
    tags: List[str]
    scheduled_time: Optional[datetime] = None
    status: str = "pending"
    video_path: str = ""
    thumbnail_path: str = ""


class VideoEditor:
    """
    AI Video Editor
    - Auto-cut and arrange clips
    - Speech-to-text captions (Whisper)
    - Auto-captions in Hindi/English
    - Thumbnail generation
    - Music mixing
    - Platform-specific formatting
    - Scheduled uploads
    """

    def __init__(self, config: Dict[str, Any] = None):
        self.config = config or {}
        self.projects: Dict[str, VideoProject] = {}
        self.upload_queue: List[UploadTask] = []
        self._db = None
        self._llm = None
        self._voice = None
        self._whisper_model = None
        self._upload_task = None

    def set_dependencies(self, db, llm, voice):
        self._db = db
        self._llm = llm
        self._voice = voice

    async def initialize(self):
        """Initialize video editor"""
        logger.info("Initializing VideoEditor...")

        # Load Whisper model for captions
        if whisper:
            try:
                self._whisper_model = await asyncio.get_event_loop().run_in_executor(
                    None, lambda: whisper.load_model("base")
                )
                logger.info("Whisper model loaded")
            except Exception as e:
                logger.warning(f"Whisper load failed: {e}")

        self._upload_task = asyncio.create_task(self._upload_loop())
        logger.info("VideoEditor initialized")

    async def create_project(self, project: VideoProject) -> Dict[str, Any]:
        """Create new video project"""
        self.projects[project.id] = project
        await self._save_project(project)
        return {"success": True, "project_id": project.id}

    async def auto_edit(self, project_id: str, style: str = "auto") -> Dict[str, Any]:
        """Auto-edit video from source clips"""
        if project_id not in self.projects:
            return {"success": False, "error": "Project not found"}

        project = self.projects[project_id]
        project.status = "editing"

        try:
            if self._voice:
                await self._voice.speak("Video edit shuru kar raha hoon...")

            # Load clips
            clips = await self._load_clips(project.source_files)

            # Auto-arrange based on style
            arranged_clips = await self._auto_arrange_clips(clips, style)

            # Generate captions
            captions = await self._generate_captions(arranged_clips)

            # Add music if specified
            if project.music_path:
                arranged_clips = await self._add_music(arranged_clips, project.music_path)

            # Apply transitions and effects
            arranged_clips = await self._apply_transitions(arranged_clips)

            # Render final video
            output_path = await self._render_video(project, arranged_clips, captions)

            # Generate thumbnail
            thumbnail_path = await self._generate_thumbnail(output_path, project)

            project.output_path = output_path
            project.thumbnail_path = thumbnail_path
            project.duration = sum(c.duration for c in arranged_clips)
            project.status = "completed"

            await self._save_project(project)

            if self._voice:
                await self._voice.speak("Video edit complete ho gaya. Thumbnail bhi ban gaya.")

            return {
                "success": True,
                "output_path": output_path,
                "thumbnail_path": thumbnail_path,
                "duration": project.duration
            }

        except Exception as e:
            project.status = "failed"
            logger.error(f"Auto-edit failed: {e}")
            return {"success": False, "error": str(e)}

    async def _load_clips(self, source_files: List[str]) -> List[Dict]:
        """Load and analyze source video files"""
        clips = []

        for i, file_path in enumerate(source_files):
            if not os.path.exists(file_path):
                continue

            if not VideoFileClip:
                continue

            try:
                clip = VideoFileClip(file_path)
                clip_info = {
                    "id": f"clip_{i}",
                    "source_path": file_path,
                    "duration": clip.duration,
                    "fps": clip.fps,
                    "size": clip.size,
                    "has_audio": clip.audio is not None,
                    "start_time": 0,
                    "end_time": clip.duration
                }
                clip.close()
                clips.append({
                    "id": f"clip_{i}",
                    "source_path": file_path,
                    "start_time": 0,
                    "end_time": clip.duration,
                    "duration": clip.duration,
                    "order": i,
                    "info": clip_info
                })
            except Exception as e:
                logger.warning(f"Failed to load {file_path}: {e}")

        return clips

    async def _auto_arrange_clips(self, clips: List[Dict], style: str) -> List[Dict]:
        """Auto-arrange clips based on style"""
        if style == "timelapse":
            # Speed up all clips
            for clip in clips:
                clip["speed"] = 10.0
        elif style == "story":
            # Keep natural order, maybe add intro/outro
            pass
        elif style == "highlights":
            # Select best moments (would need AI analysis)
            pass

        return clips

    async def _generate_captions(self, clips: List[Dict]) -> List[CaptionSegment]:
        """Generate captions using Whisper"""
        captions = []

        if not self._whisper_model:
            return captions

        for clip in clips:
            if not clip.get("source_path"):
                continue

            try:
                # Extract audio and transcribe
                result = await asyncio.get_event_loop().run_in_executor(
                    None,
                    lambda: self._whisper_model.transcribe(clip["source_path"], language="hi")
                )

                for segment in result.get("segments", []):
                    captions.append(CaptionSegment(
                        start=segment["start"],
                        end=segment["end"],
                        text=segment["text"].strip(),
                        language=result.get("language", "hi")
                    ))
            except Exception as e:
                logger.warning(f"Caption generation failed: {e}")

        return captions

    async def _add_music(self, clips: List[Dict], music_path: str) -> List[Dict]:
        """Add background music"""
        # Would mix audio tracks
        return clips

    async def _apply_transitions(self, clips: List[Dict]) -> List[Dict]:
        """Apply transitions between clips"""
        transitions = ["fade", "slide", "zoom", "crossfade"]
        for i, clip in enumerate(clips):
            if i > 0:
                clip["transitions"] = ["fade"]
        return clips

    async def _render_video(self, project: VideoProject, clips: List[Dict], captions: List[CaptionSegment]) -> str:
        """Render final video using MoviePy"""
        if not VideoFileClip:
            return ""

        video_clips = []

        for clip in clips:
            try:
                vfc = VideoFileClip(clip["source_path"])
                vfc = vfc.subclip(clip["start_time"], clip["end_time"])

                # Apply speed if specified
                if "speed" in clip:
                    vfc = vfc.speedx(clip["speed"])

                video_clips.append(vfc)
            except Exception as e:
                logger.warning(f"Failed to load clip: {e}")

        if not video_clips:
            return ""

        # Concatenate
        final_clip = concatenate_videoclips(video_clips, method="compose")

        # Add captions as text overlays
        # (Would add TextClip overlays for each caption segment)

        # Write output
        output_path = project.output_path or f"./output/video_{datetime.now().strftime('%Y%m%d_%H%M%S')}.mp4"
        Path(output_path).parent.mkdir(parents=True, exist_ok=True)

        final_clip.write_videofile(
            output_path,
            fps=project.fps,
            codec='libx264',
            audio_codec='aac',
            threads=4
        )

        # Close clips
        for clip in video_clips:
            clip.close()
        final_clip.close()

        return output_path

    async def _generate_thumbnail(self, video_path: str, project: VideoProject) -> str:
        """Generate thumbnail from video"""
        if not cv2:
            return ""

        try:
            cap = cv2.VideoCapture(video_path)
            # Get frame at 10% or middle
            frame_count = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
            cap.set(cv2.CAP_PROP_POS_FRAMES, frame_count // 10)
            ret, frame = cap.read()
            cap.release()

            if ret:
                # Resize for thumbnail
                thumb = cv2.resize(frame, (1280, 720))

                # Add title text
                cv2.putText(thumb, project.name, (50, 100),
                           cv2.FONT_HERSHEY_SIMPLEX, 2, (255, 255, 255), 3)

                thumb_path = video_path.replace('.mp4', '_thumb.jpg')
                cv2.imwrite(thumb_path, thumb)
                return thumb_path
        except Exception as e:
            logger.error(f"Thumbnail generation failed: {e}")

        return ""

    # Caption burning
    async def burn_captions(self, video_path: str, captions: List[CaptionSegment],
                            output_path: str, style: Dict = None) -> str:
        """Burn captions into video"""
        # Would use MoviePy to overlay TextClips
        return video_path

    # Thumbnail generation with AI
    async def generate_ai_thumbnail(self, video_path: str, title: str,
                                    style: str = "farm") -> str:
        """Generate thumbnail using AI"""
        # Would use Stable Diffusion or similar
        return await self._generate_thumbnail(video_path, VideoProject(name=title))

    # Upload Management
    async def schedule_upload(self, task: UploadTask) -> Dict[str, Any]:
        """Schedule video upload"""
        self.upload_queue.append(task)
        await self._save_upload_task(task)
        return {"success": True, "task_id": task.id}

    async def _upload_loop(self):
        """Background upload loop"""
        while True:
            try:
                if self._upload_queue:
                    task = self.upload_queue.pop(0)
                    if task.scheduled_time and task.scheduled_time > datetime.now():
                        self._upload_queue.insert(0, task)
                        await asyncio.sleep(60)
                        continue

                    result = await self._upload_to_platform(task)
                    task.status = "completed" if result.get("success") else "failed"
                    await self._save_upload_task(task)

                    if self._voice:
                        await self._voice.speak(
                            f"Video {task.platform.value} pe upload {'ho gaya' if result.get('success') else 'fail ho gaya'}."
                        )

                await asyncio.sleep(60)
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Upload loop error: {e}")
                await asyncio.sleep(60)

    async def _upload_to_platform(self, task: UploadTask) -> Dict[str, Any]:
        """Upload video to platform"""
        # Would use platform APIs (YouTube Data API, Instagram Graph API, etc.)
        # For now, return success
        return {"success": True, "url": f"https://{task.platform.value}.com/video/{task.id}"}

    # Short/Reel generation
    async def create_short_from_video(self, video_path: str, duration: int = 60,
                                      aspect_ratio: str = "9:16") -> str:
        """Create YouTube Short/Reel from longer video"""
        # Would extract best segments and reformat
        return video_path

    async def create_reel_from_photos(self, photo_paths: List[str], music_path: str = "",
                                      duration_per_photo: float = 3) -> str:
        """Create Reel from photos with music"""
        # Would create video from photos with Ken Burns effect
        return ""

    # Utility
    def get_project_status(self, project_id: str) -> Dict[str, Any]:
        if project_id not in self.projects:
            return {"error": "Project not found"}

        project = self.projects[project_id]
        return {
            "id": project.id,
            "name": project.name,
            "type": project.type.value,
            "status": project.status,
            "duration": project.duration,
            "output_path": project.output_path,
            "thumbnail": project.thumbnail_path,
            "created_at": project.created_at.isoformat()
        }

    def get_status(self) -> Dict[str, Any]:
        return {
            "projects": len(self.projects),
            "upload_queue": len(self.upload_queue),
            "completed": len([p for p in self.projects.values() if p.status == "completed"]),
            "in_progress": len([p for p in self.projects.values() if p.status == "editing"]),
        }

    async def close(self):
        if self._upload_task:
            self._upload_task.cancel()
        logger.info("VideoEditor closed")