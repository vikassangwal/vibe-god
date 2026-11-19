"""
Digi Mitra Automated Short Video & Reels Generator (ऑटोमैटिक रील्स मेकर)
Generates high-definition (720x1280, 9:16 vertical) MP4 short videos/reels:
- Category templates: Trading Strategy, eMitra & Sarkari Yojna, Earning Motivation
- Animated gradient backdrops & progress bar
- Dynamic text layout using PIL & OpenCV
"""

import os
import cv2
import numpy as np
from pathlib import Path
from typing import Dict, Any, List, Optional
from datetime import datetime
from PIL import Image, ImageDraw, ImageFont

OUTPUT_DIR = Path(__file__).parent.parent / "output" / "reels"


class ReelsGenerator:
    def __init__(self, output_dir: Optional[Path] = None):
        self.output_dir = output_dir or OUTPUT_DIR
        self.output_dir.mkdir(parents=True, exist_ok=True)
        self.width = 720
        self.height = 1280
        self.fps = 24

    def generate_reel(self, category: str = "trading", title: str = "", points: Optional[List[str]] = None) -> Dict[str, Any]:
        """
        Renders a full 6-second vertical reel video (720x1280)
        """
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"reel_{category}_{timestamp}.mp4"
        filepath = self.output_dir / filename

        # Default content if none provided
        if not title:
            if category == "trading":
                title = "NIFTY BREAKOUT SECRET"
                points = [
                    "1. RSI 35 ke neeche bounce dekhein",
                    "2. 20 SMA ke upar green candle",
                    "3. Stop loss: Support ke 1% neeche",
                    "Follow Digi Mitra for Daily Calls!"
                ]
            elif category == "emitra":
                title = "JAN AADHAAR UPDATE 2026"
                points = [
                    "1. Mahila Mukhiya ki bank passbook",
                    "2. Sabhi members ka active mobile",
                    "3. eMitra se free KYC verification",
                    "Turant banwayein aur labh lein!"
                ]
            else:
                title = "1 LAKH MONTHLY BLUEPRINT"
                points = [
                    "1. eMitra online citizen services",
                    "2. B2B Client outreach automation",
                    "3. Daily market swing execution",
                    "Consistency is the true superpower!"
                ]

        total_frames = self.fps * 6  # 6 seconds

        fourcc = cv2.VideoWriter_fourcc(*'mp4v')
        out = cv2.VideoWriter(str(filepath), fourcc, self.fps, (self.width, self.height))

        # Color schemes based on category
        theme_colors = {
            "trading": ((15, 23, 42), (56, 189, 248), (52, 211, 153)),  # Dark blue, sky, emerald
            "emitra": ((20, 30, 45), (245, 158, 11), (56, 189, 248)),   # Navy, amber, cyan
            "business": ((24, 24, 27), (168, 85, 247), (236, 72, 153))  # Charcoal, purple, pink
        }
        bg_col, acc_col, high_col = theme_colors.get(category, theme_colors["trading"])

        for f in range(total_frames):
            # 1. Base frame with subtle gradient pulse
            shift = int(15 * np.sin(2 * np.pi * f / total_frames))
            frame_rgb = np.zeros((self.height, self.width, 3), dtype=np.uint8)
            for y in range(self.height):
                alpha = y / self.height
                r = int(bg_col[0] + (35 + shift) * alpha)
                g = int(bg_col[1] + (45 + shift) * alpha)
                b = int(bg_col[2] + (65 + shift) * alpha)
                frame_rgb[y, :] = (min(255, r), min(255, g), min(255, b))

            # 2. Draw Text and Elements using PIL for crisp typography
            pil_img = Image.fromarray(frame_rgb)
            draw = ImageDraw.Draw(pil_img)

            # Top branding pill
            draw.rounded_rectangle([200, 70, 520, 120], radius=25, fill=(acc_col[0], acc_col[1], acc_col[2], 180))
            draw.text((250, 82), "👑 DIGI MITRA 2.0", fill=(15, 23, 42))

            # Title Box
            draw.rounded_rectangle([50, 180, 670, 320], radius=20, fill=(30, 41, 59), outline=acc_col, width=3)
            draw.text((80, 235), title, fill=(248, 250, 252))

            # Multi-point reveals over time
            visible_points_count = min(len(points), int((f / total_frames) * (len(points) + 1)) + 1)
            y_offset = 380
            for i in range(visible_points_count):
                pt = points[i]
                is_last = (i == len(points) - 1)
                box_bg = (16, 185, 129, 220) if is_last else (40, 50, 75, 200)
                txt_col = (255, 255, 255) if is_last else (226, 232, 240)

                draw.rounded_rectangle([60, y_offset, 660, y_offset + 95], radius=15, fill=box_bg)
                draw.text((90, y_offset + 32), pt, fill=txt_col)
                y_offset += 125

            # Bottom progress bar (Animated)
            prog_width = int(self.width * (f / total_frames))
            draw.rectangle([0, self.height - 12, prog_width, self.height], fill=acc_col)

            # Convert back to OpenCV BGR
            cv_frame = cv2.cvtColor(np.array(pil_img), cv2.COLOR_RGB2BGR)
            out.write(cv_frame)

        out.release()

        return {
            "success": True,
            "filename": filename,
            "filepath": str(filepath),
            "download_url": f"/api/reels/download/{filename}",
            "message": f"🎬 Reel Video generate ho gaya: {filename}"
        }
