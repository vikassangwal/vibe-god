"""
Digi Mitra Video & Media Automation Engine
- Video Trimming / Cutting
- Converting Image to Video / Reel
- Audio extraction / Subtitle prep
"""

import os
from pathlib import Path
from typing import Dict, Any, Optional

try:
    from moviepy.editor import VideoFileClip, ImageClip, AudioFileClip
except Exception:
    VideoFileClip = None
    ImageClip = None


class VideoAutomationEngine:
    def __init__(self, output_dir: str = './output/videos'):
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(parents=True, exist_ok=True)

    def trim_video(self, input_path: str, start_sec: float, end_sec: float, output_filename: str = 'trimmed.mp4') -> Dict[str, Any]:
        """Trim video between start_sec and end_sec"""
        if not VideoFileClip:
            return {'success': False, 'error': 'MoviePy not fully initialized'}

        try:
            in_file = Path(input_path)
            if not in_file.exists():
                return {'success': False, 'error': f'Video file nahi mili: {input_path}'}

            out_path = self.output_dir / output_filename
            clip = VideoFileClip(str(in_file)).subclip(start_sec, end_sec)
            clip.write_videofile(str(out_path), codec='libx264', audio_codec='aac')
            clip.close()

            return {
                'success': True,
                'output_file': str(out_path),
                'message': f'Video safaltapoorvak trim ho gayi: {out_path}'
            }
        except Exception as e:
            return {'success': False, 'error': str(e)}

    def create_reel_from_image(self, image_path: str, duration_sec: int = 5, output_filename: str = 'reel.mp4') -> Dict[str, Any]:
        """Create quick video from image for social media reels"""
        if not ImageClip:
            return {'success': False, 'error': 'MoviePy not available'}

        try:
            out_path = self.output_dir / output_filename
            clip = ImageClip(image_path).set_duration(duration_sec)
            clip.write_videofile(str(out_path), fps=24)
            clip.close()
            return {'success': True, 'output_file': str(out_path)}
        except Exception as e:
            return {'success': False, 'error': str(e)}

