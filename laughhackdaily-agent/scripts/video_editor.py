"""
Video Editor Module for LaughHackDaily
"""

import os
from pathlib import Path

import numpy as np
from PIL import Image, ImageDraw, ImageFont
from moviepy.editor import (
    VideoFileClip, AudioFileClip, ImageClip, CompositeVideoClip,
    concatenate_videoclips
)


class VideoEditor:
    """Video editor for TikTok content production."""

    def __init__(self, output_dir: str = "output"):
        self.output_dir = Path(output_dir)
        self.video_size = (1080, 1920)  # 9:16 vertical
        self.fps = 30
        self.font_size = 110
        self.font_color = "white"
        self.stroke_color = "black"
        self.stroke_width = 2

    def resize_clip(self, clip: VideoFileClip) -> VideoFileClip:
        """Resize and crop clip to 9:16 vertical format."""
        target_w, target_h = self.video_size
        target_ratio = target_w / target_h
        clip_w, clip_h = clip.size
        clip_ratio = clip_w / clip_h

        if clip_ratio > target_ratio:
            resized = clip.resize(height=target_h)
            new_w = int(clip_ratio * target_h)
            x1 = (new_w - target_w) // 2
            cropped = resized.crop(x1=x1, y1=0, x2=x1 + target_w, y2=target_h)
        else:
            resized = clip.resize(width=target_w)
            new_h = int(target_w / clip_ratio)
            y1 = (new_h - target_h) // 2
            cropped = resized.crop(x1=0, y1=y1, x2=target_w, y2=y1 + target_h)
        return cropped

    def concatenate_clips(self, clips: list, transition_duration: float = 0.1) -> VideoFileClip:
        """Concatenate clips with optional crossfade transitions."""
        if transition_duration > 0:
            processed = []
            for i, clip in enumerate(clips):
                if i > 0:
                    clip = clip.crossfadein(transition_duration)
                if i < len(clips) - 1:
                    clip = clip.crossfadeout(transition_duration)
                processed.append(clip)
            return concatenate_videoclips(processed, method="compose")
        return concatenate_videoclips(clips)

    def create_text_image(self, text, size=None, font_size=None,
                          font_color=None, stroke_color=None,
                          stroke_width=None, position="bottom"):
        """Create a transparent image with styled text overlay."""
        if size is None:
            size = self.video_size
        if font_size is None:
            font_size = self.font_size
        if font_color is None:
            font_color = self.font_color
        if stroke_color is None:
            stroke_color = self.stroke_color
        if stroke_width is None:
            stroke_width = self.stroke_width

        img = Image.new("RGBA", size, (0, 0, 0, 0))
        draw = ImageDraw.Draw(img)

        try:
            font = ImageFont.truetype(
                "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf", font_size
            )
        except (IOError, OSError):
            font = ImageFont.load_default()

        bbox = draw.textbbox((0, 0), text, font=font)
        text_width = bbox[2] - bbox[0]
        text_height = bbox[3] - bbox[1]

        if position == "center":
            x = (size[0] - text_width) // 2
            y = (size[1] - text_height) // 2
        elif position == "top":
            x = (size[0] - text_width) // 2
            y = size[1] // 6
        elif position == "bottom":
            x = (size[0] - text_width) // 2
            y = int(size[1] * 0.8)
        elif isinstance(position, tuple):
            x, y = position
        else:
            x, y = 50, 50

        # Draw stroke
        for dx in range(-stroke_width, stroke_width + 1):
            for dy in range(-stroke_width, stroke_width + 1):
                if dx != 0 or dy != 0:
                    draw.text((x + dx, y + dy), text, font=font, fill=stroke_color)
        draw.text((x, y), text, font=font, fill=font_color)
        return np.array(img)

    def create_text_clip(self, text, duration, start_time=0,
                         font_size=None, position="bottom",
                         fade_in=0.2, fade_out=0.2):
        """Create a text overlay clip."""
        text_img = self.create_text_image(text, font_size=font_size, position=position)
        clip = ImageClip(text_img, duration=duration).set_start(start_time)
        if fade_in > 0:
            clip = clip.crossfadein(fade_in)
        if fade_out > 0:
            clip = clip.crossfadeout(fade_out)
        return clip

    def add_text_overlays(self, video, text_configs):
        """Add multiple text overlays to a video."""
        text_clips = []
        for config in text_configs:
            duration = config["end"] - config["start"]
            if duration <= 0:
                continue
            clip = self.create_text_clip(
                config["text"],
                duration,
                config["start"],
                config.get("font_size"),
                config.get("position", "bottom")
            )
            text_clips.append(clip)
        return CompositeVideoClip([video] + text_clips)

    def apply_zoom_effect(self, clip, zoom_factor=1.05):
        """Apply a subtle zoom-in effect."""
        duration = clip.duration

        def zoom_frame(get_frame, t):
            frame = get_frame(t)
            img = Image.fromarray(frame)
            w, h = img.size

            progress = t / duration if duration > 0 else 0
            current_zoom = 1 + (zoom_factor - 1) * progress

            crop_w = int(w / current_zoom)
            crop_h = int(h / current_zoom)
            left = (w - crop_w) // 2
            top = (h - crop_h) // 2

            img = img.crop((left, top, left + crop_w, top + crop_h))
            img = img.resize((w, h), Image.LANCZOS)
            return np.array(img)

        return clip.fl(zoom_frame)

    def export_video(self, video, output_path, fps=None):
        """Export video to file."""
        if fps is None:
            fps = self.fps
        os.makedirs(os.path.dirname(output_path), exist_ok=True)
        video.write_videofile(
            output_path,
            fps=fps,
            codec="libx264",
            audio_codec="aac",
            bitrate="5000k",
            preset="medium",
            threads=4,
            verbose=False,
            logger=None
        )
        return output_path

    def create_video_synced(self, clip_paths, audio_path, text_overlays=None,
                            output_path=None, apply_zoom=True):
        """Create video with clips synced to divide audio duration equally."""
        if not os.path.exists(audio_path):
            raise ValueError(f"Audio file not found: {audio_path}")

        audio = AudioFileClip(audio_path)
        total_duration = audio.duration
        clip_duration = total_duration / len(clip_paths)
        print(f"  Syncing: {len(clip_paths)} clips to {total_duration:.2f}s audio "
              f"({clip_duration:.2f}s each)")

        clips = []
        for i, path in enumerate(clip_paths):
            try:
                clip = VideoFileClip(path)
                if clip.duration < clip_duration:
                    clip = clip.loop(duration=clip_duration)
                else:
                    clip = clip.subclip(0, clip_duration)

                clip = self.resize_clip(clip)

                if apply_zoom:
                    clip = self.apply_zoom_effect(clip)

                clips.append(clip)
            except Exception as e:
                print(f"    Warning: Could not process clip {path}: {e}")
                continue

        if not clips:
            raise ValueError("No valid clips to process")

        video = self.concatenate_clips(clips)
        video = video.set_audio(audio)

        if text_overlays:
            video = self.add_text_overlays(video, text_overlays)

        if output_path is None:
            output_path = str(self.output_dir / "videos" / "output_synced.mp4")

        result = self.export_video(video, output_path)

        # Cleanup
        audio.close()
        video.close()
        for c in clips:
            c.close()

        return result
