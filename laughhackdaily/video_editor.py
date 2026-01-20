"""
Video Editor Module for LaughHackDaily

Handles video editing operations:
- Clip trimming and concatenation
- Audio overlay
- Text overlay generation
- Video effects and transitions
"""

import os
from pathlib import Path
from PIL import Image, ImageDraw, ImageFont
import numpy as np

# MoviePy imports
from moviepy import (
    VideoFileClip,
    AudioFileClip,
    ImageClip,
    CompositeVideoClip,
    concatenate_videoclips,
    vfx
)


class VideoEditor:
    """Main video editor class for TikTok content production."""

    def __init__(self, output_dir: str = "output"):
        self.output_dir = Path(output_dir)
        self.video_size = (1080, 1920)  # 9:16 vertical
        self.fps = 30

        # Text styling defaults
        self.font_size = 60
        self.font_color = "white"
        self.stroke_color = "black"
        self.stroke_width = 3

    def trim_clip(self, clip_path: str, start: float, end: float) -> VideoFileClip:
        """Trim a video clip to specified start and end times."""
        clip = VideoFileClip(clip_path)
        trimmed = clip.subclipped(start, min(end, clip.duration))
        return trimmed

    def resize_clip(self, clip: VideoFileClip) -> VideoFileClip:
        """Resize clip to 9:16 vertical format with center crop."""
        target_w, target_h = self.video_size
        target_ratio = target_w / target_h

        clip_w, clip_h = clip.size
        clip_ratio = clip_w / clip_h

        if clip_ratio > target_ratio:
            # Clip is wider - scale by height, crop width
            new_h = target_h
            new_w = int(clip_ratio * target_h)
            resized = clip.resized(height=new_h)
            x_center = new_w // 2
            x1 = x_center - target_w // 2
            cropped = resized.cropped(x1=x1, y1=0, x2=x1+target_w, y2=target_h)
        else:
            # Clip is taller - scale by width, crop height
            new_w = target_w
            new_h = int(target_w / clip_ratio)
            resized = clip.resized(width=new_w)
            y_center = new_h // 2
            y1 = y_center - target_h // 2
            cropped = resized.cropped(x1=0, y1=y1, x2=target_w, y2=y1+target_h)

        return cropped

    def concatenate_clips(self, clips: list, transition_duration: float = 0.1) -> VideoFileClip:
        """Concatenate multiple clips with optional crossfade transitions."""
        if transition_duration > 0:
            # Add crossfade between clips
            processed_clips = []
            for i, clip in enumerate(clips):
                if i > 0:
                    clip = clip.with_effects([vfx.CrossFadeIn(transition_duration)])
                if i < len(clips) - 1:
                    clip = clip.with_effects([vfx.CrossFadeOut(transition_duration)])
                processed_clips.append(clip)
            return concatenate_videoclips(processed_clips, method="compose")
        else:
            return concatenate_videoclips(clips)

    def create_text_image(
        self,
        text: str,
        size: tuple = None,
        font_size: int = None,
        font_color: str = None,
        stroke_color: str = None,
        stroke_width: int = None,
        position: str = "center"
    ) -> np.ndarray:
        """Create a text overlay image using Pillow."""
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

        # Create transparent image
        img = Image.new("RGBA", size, (0, 0, 0, 0))
        draw = ImageDraw.Draw(img)

        # Try to load a bold font, fallback to default
        try:
            font = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf", font_size)
        except OSError:
            try:
                font = ImageFont.truetype("/usr/share/fonts/truetype/liberation/LiberationSans-Bold.ttf", font_size)
            except OSError:
                font = ImageFont.load_default()

        # Get text bounding box
        bbox = draw.textbbox((0, 0), text, font=font)
        text_width = bbox[2] - bbox[0]
        text_height = bbox[3] - bbox[1]

        # Calculate position
        if position == "center":
            x = (size[0] - text_width) // 2
            y = (size[1] - text_height) // 2
        elif position == "top":
            x = (size[0] - text_width) // 2
            y = size[1] // 6
        elif position == "bottom":
            x = (size[0] - text_width) // 2
            y = size[1] * 3 // 4
        else:
            x, y = position if isinstance(position, tuple) else (50, 50)

        # Draw text with stroke
        for dx in range(-stroke_width, stroke_width + 1):
            for dy in range(-stroke_width, stroke_width + 1):
                if dx != 0 or dy != 0:
                    draw.text((x + dx, y + dy), text, font=font, fill=stroke_color)
        draw.text((x, y), text, font=font, fill=font_color)

        return np.array(img)

    def create_text_clip(
        self,
        text: str,
        duration: float,
        start_time: float = 0,
        font_size: int = None,
        position: str = "center",
        fade_in: float = 0.2,
        fade_out: float = 0.2
    ) -> ImageClip:
        """Create an animated text overlay clip."""
        text_img = self.create_text_image(
            text,
            font_size=font_size,
            position=position
        )

        clip = ImageClip(text_img, duration=duration)
        clip = clip.with_start(start_time)

        # Add fade effects
        if fade_in > 0:
            clip = clip.with_effects([vfx.CrossFadeIn(fade_in)])
        if fade_out > 0:
            clip = clip.with_effects([vfx.CrossFadeOut(fade_out)])

        return clip

    def add_text_overlays(
        self,
        video: VideoFileClip,
        text_configs: list
    ) -> CompositeVideoClip:
        """
        Add multiple text overlays to a video.

        text_configs: list of dicts with keys:
            - text: str
            - start: float (seconds)
            - end: float (seconds)
            - position: str ("center", "top", "bottom")
            - font_size: int (optional)
        """
        text_clips = []

        for config in text_configs:
            duration = config["end"] - config["start"]
            clip = self.create_text_clip(
                text=config["text"],
                duration=duration,
                start_time=config["start"],
                font_size=config.get("font_size", self.font_size),
                position=config.get("position", "center")
            )
            text_clips.append(clip)

        return CompositeVideoClip([video] + text_clips)

    def add_audio(
        self,
        video: VideoFileClip,
        audio_path: str,
        volume: float = 1.0
    ) -> VideoFileClip:
        """Add audio track to video."""
        audio = AudioFileClip(audio_path)

        # Adjust audio duration to match video
        if audio.duration > video.duration:
            audio = audio.subclipped(0, video.duration)

        # Set volume
        audio = audio.with_volume_scaled(volume)

        return video.with_audio(audio)

    def add_background_music(
        self,
        video: VideoFileClip,
        music_path: str,
        volume: float = 0.15
    ) -> VideoFileClip:
        """Add background music at low volume."""
        if not os.path.exists(music_path):
            return video

        music = AudioFileClip(music_path)

        # Loop music if shorter than video
        if music.duration < video.duration:
            loops_needed = int(video.duration / music.duration) + 1
            music = concatenate_videoclips([music] * loops_needed).subclipped(0, video.duration)
        else:
            music = music.subclipped(0, video.duration)

        music = music.with_volume_scaled(volume)

        # Mix with existing audio
        if video.audio:
            from moviepy import CompositeAudioClip
            mixed = CompositeAudioClip([video.audio, music])
            return video.with_audio(mixed)
        else:
            return video.with_audio(music)

    def apply_zoom_effect(
        self,
        clip: VideoFileClip,
        zoom_factor: float = 1.1,
        direction: str = "in"
    ) -> VideoFileClip:
        """Apply slow zoom in or out effect."""
        def zoom(get_frame, t):
            frame = get_frame(t)
            h, w = frame.shape[:2]

            progress = t / clip.duration
            if direction == "in":
                current_zoom = 1 + (zoom_factor - 1) * progress
            else:
                current_zoom = zoom_factor - (zoom_factor - 1) * progress

            # Calculate new dimensions
            new_h = int(h * current_zoom)
            new_w = int(w * current_zoom)

            # Resize frame
            from PIL import Image
            img = Image.fromarray(frame)
            img = img.resize((new_w, new_h), Image.Resampling.LANCZOS)

            # Crop to original size from center
            left = (new_w - w) // 2
            top = (new_h - h) // 2
            img = img.crop((left, top, left + w, top + h))

            return np.array(img)

        return clip.transform(zoom)

    def export_video(
        self,
        video: VideoFileClip,
        output_path: str,
        fps: int = None,
        codec: str = "libx264",
        audio_codec: str = "aac",
        bitrate: str = "8000k"
    ) -> str:
        """Export final video to file."""
        if fps is None:
            fps = self.fps

        # Ensure output directory exists
        os.makedirs(os.path.dirname(output_path), exist_ok=True)

        video.write_videofile(
            output_path,
            fps=fps,
            codec=codec,
            audio_codec=audio_codec,
            bitrate=bitrate,
            preset="medium",
            threads=4
        )

        return output_path

    def create_video_from_clips(
        self,
        clip_paths: list,
        clip_durations: list,
        audio_path: str = None,
        text_overlays: list = None,
        output_path: str = None
    ) -> str:
        """
        Main method to create a complete video from clips.

        Args:
            clip_paths: List of paths to video clips
            clip_durations: List of durations for each clip (seconds)
            audio_path: Path to voiceover audio
            text_overlays: List of text overlay configs
            output_path: Output file path

        Returns:
            Path to exported video
        """
        print("  Loading and processing clips...")
        clips = []

        for i, (path, duration) in enumerate(zip(clip_paths, clip_durations)):
            print(f"    Processing clip {i+1}/{len(clip_paths)}: {path}")

            try:
                clip = VideoFileClip(path)

                # Trim to desired duration
                clip_duration = min(duration, clip.duration)
                clip = clip.subclipped(0, clip_duration)

                # Resize to vertical format
                clip = self.resize_clip(clip)

                # Apply subtle zoom effect
                clip = self.apply_zoom_effect(clip, zoom_factor=1.05)

                clips.append(clip)
            except Exception as e:
                print(f"    Warning: Could not process clip {path}: {e}")
                continue

        if not clips:
            raise ValueError("No valid clips to process")

        print("  Concatenating clips...")
        video = self.concatenate_clips(clips, transition_duration=0.1)

        # Add audio
        if audio_path and os.path.exists(audio_path):
            print("  Adding voiceover audio...")
            video = self.add_audio(video, audio_path)

        # Add text overlays
        if text_overlays:
            print("  Adding text overlays...")
            video = self.add_text_overlays(video, text_overlays)

        # Export
        if output_path is None:
            output_path = str(self.output_dir / "videos" / "output.mp4")

        print(f"  Exporting to {output_path}...")
        return self.export_video(video, output_path)


def test_editor():
    """Test the video editor with sample content."""
    editor = VideoEditor()

    # Create a simple test text image
    text_img = editor.create_text_image(
        "TEST OVERLAY",
        font_size=80,
        position="center"
    )

    print(f"Created text image with shape: {text_img.shape}")
    print("Video editor module loaded successfully!")


if __name__ == "__main__":
    test_editor()
