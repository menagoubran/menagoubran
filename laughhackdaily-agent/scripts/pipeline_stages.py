"""
Pipeline Stages for LaughHackDaily Video Production
Each stage is idempotent and produces persistent outputs.
"""

import json
import os
import re
import time
import requests
from pathlib import Path
from typing import Optional, Dict, Any, List
from datetime import datetime


class StageResult:
    """Result of a pipeline stage execution."""

    def __init__(self, success: bool, output_path: Optional[str] = None,
                 data: Optional[Dict] = None, error: Optional[str] = None):
        self.success = success
        self.output_path = output_path
        self.data = data or {}
        self.error = error

    def to_dict(self) -> Dict[str, Any]:
        return {
            "success": self.success,
            "output_path": self.output_path,
            "data": self.data,
            "error": self.error
        }


class PipelineConfig:
    """Configuration for the pipeline."""

    def __init__(self, base_dir: str):
        self.base_dir = Path(base_dir)
        self.scripts_dir = self.base_dir / "scripts"
        self.audio_dir = self.base_dir / "audio"
        self.footage_dir = self.base_dir / "footage"
        self.videos_dir = self.base_dir / "videos"
        self.logs_dir = self.base_dir / "logs"

        # Create all directories
        for d in [self.scripts_dir, self.audio_dir, self.footage_dir,
                  self.videos_dir, self.logs_dir]:
            d.mkdir(parents=True, exist_ok=True)

    def get_script_path(self, job_id: str) -> Path:
        return self.scripts_dir / f"{job_id}.json"

    def get_audio_path(self, job_id: str) -> Path:
        return self.audio_dir / f"{job_id}.mp3"

    def get_footage_dir(self, job_id: str) -> Path:
        return self.footage_dir / job_id

    def get_video_path(self, job_id: str) -> Path:
        return self.videos_dir / f"{job_id}.mp4"


# =============================================================================
# STAGE A: Script Generation (Claude)
# =============================================================================

# UPDATED PROMPT FOR 11-SECOND OPTIMAL FORMAT
SCRIPT_PROMPT_TEMPLATE = """Create a viral TikTok script for the topic: {topic}

CRITICAL FORMAT REQUIREMENTS:
- Target duration: 11 seconds (9-13 seconds acceptable)
- ONE powerful insight only (NOT 3 tips)
- Hook + Payoff + Loop structure
- Total voiceover: 25-40 words maximum

Return ONLY valid JSON (no markdown):
{{
    "duration_target": 11,
    "hook_text": "5-9 word hook for text overlay",
    "voiceover": "25-40 word script. Start with attention-grabbing hook. Deliver ONE insight. End with loop phrase that connects back to the hook.",
    "loop_phrase": "The final 2-3 words that loop back to the start",
    "sections": [
        {{
            "start": 0,
            "end": 4,
            "type": "hook",
            "pexels_keywords": ["keyword1", "keyword2"],
            "text_overlay": "HOOK TEXT"
        }},
        {{
            "start": 4,
            "end": 9,
            "type": "insight",
            "pexels_keywords": ["keyword1", "keyword2"],
            "text_overlay": "KEY INSIGHT"
        }},
        {{
            "start": 9,
            "end": 11,
            "type": "loop",
            "pexels_keywords": ["keyword1", "keyword2"],
            "text_overlay": ""
        }}
    ]
}}

CONTENT REQUIREMENTS:
- Psychology/self-improvement focus
- First 2 seconds must hook viewer (pattern interrupt)
- ONE insight that feels like a revelation
- Loop ending makes viewer want to rewatch
- Keywords must work for vertical video (portraits, faces, emotions)

EXAMPLE TOPICS AND STYLES:
- "mirror behavior" → "When someone copies your gestures, they're not mocking you..."
- "silence in conversations" → "The person who speaks last usually wins..."
- "eye contact" → "If they look away first, you already have the upper hand..."

DO NOT:
- Use "tip 1, tip 2, tip 3" format
- Make it longer than 40 words
- Include call-to-action (no "follow for more")
- Use generic keywords like "person" or "video"
"""


def stage_script(
    job_id: str,
    topic: str,
    config: PipelineConfig,
    claude_client,
    force: bool = False
) -> StageResult:
    """
    Stage A: Generate script using Claude.
    Idempotent: skips if output exists unless force=True.
    """
    output_path = config.get_script_path(job_id)

    # Idempotency check
    if output_path.exists() and not force:
        try:
            with open(output_path, 'r') as f:
                data = json.load(f)
            return StageResult(success=True, output_path=str(output_path), data=data)
        except:
            pass  # File corrupted, regenerate

    prompt = SCRIPT_PROMPT_TEMPLATE.format(topic=topic)

    try:
        response = claude_client.messages.create(
            model="claude-sonnet-4-20250514",
            max_tokens=1000,
            messages=[{"role": "user", "content": prompt}]
        )

        # Extract JSON from response
        text = response.content[0].text
        match = re.search(r'\{.*\}', text, re.DOTALL)
        if not match:
            return StageResult(success=False, error="No JSON found in Claude response")

        data = json.loads(match.group())

        # Validate required fields
        required = ["voiceover", "sections"]
        for field in required:
            if field not in data:
                return StageResult(success=False, error=f"Missing required field: {field}")

        # Add metadata
        data["job_id"] = job_id
        data["topic"] = topic
        data["generated_at"] = datetime.now().isoformat()

        # Save script
        with open(output_path, 'w') as f:
            json.dump(data, f, indent=2)

        return StageResult(success=True, output_path=str(output_path), data=data)

    except json.JSONDecodeError as e:
        return StageResult(success=False, error=f"JSON parse error: {e}")
    except Exception as e:
        return StageResult(success=False, error=f"Claude API error: {e}")


# =============================================================================
# STAGE B: Voice Generation (ElevenLabs)
# =============================================================================

def stage_voice(
    job_id: str,
    config: PipelineConfig,
    elevenlabs_client,
    voice_id: str = "pNInz6obpgDQGcFmaJgB",
    force: bool = False
) -> StageResult:
    """
    Stage B: Generate voiceover using ElevenLabs.
    Requires script to exist. Idempotent.
    """
    script_path = config.get_script_path(job_id)
    output_path = config.get_audio_path(job_id)

    # Check prerequisite
    if not script_path.exists():
        return StageResult(success=False, error="Script not found. Run stage_script first.")

    # Idempotency check
    if output_path.exists() and not force:
        return StageResult(success=True, output_path=str(output_path))

    # Load script
    try:
        with open(script_path, 'r') as f:
            script_data = json.load(f)
    except Exception as e:
        return StageResult(success=False, error=f"Failed to load script: {e}")

    voiceover_text = script_data.get("voiceover", "")
    if not voiceover_text:
        return StageResult(success=False, error="No voiceover text in script")

    try:
        audio_gen = elevenlabs_client.text_to_speech.convert(
            voice_id=voice_id,
            text=voiceover_text,
            model_id="eleven_multilingual_v2",
            output_format="mp3_44100_128"
        )

        with open(output_path, "wb") as f:
            for chunk in audio_gen:
                f.write(chunk)

        return StageResult(success=True, output_path=str(output_path))

    except Exception as e:
        return StageResult(success=False, error=f"ElevenLabs API error: {e}")


# =============================================================================
# STAGE C: Footage Download (Pexels)
# =============================================================================

class PexelsClient:
    """Pexels API client for video search and download."""

    def __init__(self, api_key: str):
        self.api_key = api_key
        self.base_url = "https://api.pexels.com/videos"
        self.headers = {"Authorization": api_key}

    def search_videos(self, query: str, per_page: int = 5,
                      orientation: str = "portrait", timeout: int = 10) -> List[Dict]:
        params = {
            "query": query,
            "per_page": per_page,
            "orientation": orientation,
            "size": "medium"
        }
        try:
            response = requests.get(
                f"{self.base_url}/search",
                headers=self.headers,
                params=params,
                timeout=timeout
            )
            if response.status_code == 200:
                return response.json().get("videos", [])
        except Exception:
            pass
        return []

    def download_video(self, video: Dict, output_path: str, timeout: int = 60) -> bool:
        """Download best quality video file."""
        files = video.get("video_files", [])
        if not files:
            return False

        # Sort by quality (prefer HD, then by resolution)
        files = sorted(
            files,
            key=lambda x: (x.get("quality", "") == "hd", x.get("width", 0)),
            reverse=True
        )

        url = files[0].get("link")
        if not url:
            return False

        try:
            response = requests.get(url, stream=True, timeout=timeout)
            response.raise_for_status()

            os.makedirs(os.path.dirname(output_path), exist_ok=True)
            with open(output_path, "wb") as f:
                for chunk in response.iter_content(chunk_size=8192):
                    f.write(chunk)
            return True
        except Exception:
            return False


def stage_footage(
    job_id: str,
    config: PipelineConfig,
    pexels_client: PexelsClient,
    force: bool = False,
    rate_limit_delay: float = 0.5
) -> StageResult:
    """
    Stage C: Download stock footage from Pexels.
    Requires script to exist. Idempotent per clip.
    """
    script_path = config.get_script_path(job_id)
    footage_dir = config.get_footage_dir(job_id)

    # Check prerequisite
    if not script_path.exists():
        return StageResult(success=False, error="Script not found. Run stage_script first.")

    # Load script
    try:
        with open(script_path, 'r') as f:
            script_data = json.load(f)
    except Exception as e:
        return StageResult(success=False, error=f"Failed to load script: {e}")

    sections = script_data.get("sections", [])
    if not sections:
        return StageResult(success=False, error="No sections in script")

    footage_dir.mkdir(parents=True, exist_ok=True)
    downloaded = []
    failed = []

    for i, section in enumerate(sections):
        clip_path = footage_dir / f"clip_{i:02d}.mp4"

        # Idempotency: skip if clip exists
        if clip_path.exists() and not force:
            downloaded.append({
                "index": i,
                "path": str(clip_path),
                "duration": section.get("end", 0) - section.get("start", 0)
            })
            continue

        keywords = section.get("pexels_keywords", ["person"])
        query = " ".join(keywords[:2])

        # Search for videos
        videos = pexels_client.search_videos(query, per_page=3)

        if videos and pexels_client.download_video(videos[0], str(clip_path)):
            downloaded.append({
                "index": i,
                "path": str(clip_path),
                "duration": section.get("end", 0) - section.get("start", 0),
                "query": query
            })
        else:
            failed.append({"index": i, "query": query})

        # Rate limiting
        time.sleep(rate_limit_delay)

    # Save manifest
    manifest = {
        "job_id": job_id,
        "downloaded": downloaded,
        "failed": failed,
        "total_clips": len(sections)
    }
    manifest_path = footage_dir / "manifest.json"
    with open(manifest_path, 'w') as f:
        json.dump(manifest, f, indent=2)

    if not downloaded:
        return StageResult(success=False, error="No footage downloaded")

    return StageResult(
        success=True,
        output_path=str(footage_dir),
        data=manifest
    )


# =============================================================================
# STAGE D: Video Rendering (MoviePy)
# =============================================================================

def stage_render(
    job_id: str,
    config: PipelineConfig,
    force: bool = False,
    draft_mode: bool = False
) -> StageResult:
    """
    Stage D: Render final video with MoviePy.
    Requires script, audio, and footage to exist. Idempotent.
    """
    # Lazy import for Colab compatibility
    try:
        from moviepy.editor import (
            VideoFileClip, AudioFileClip, TextClip,
            CompositeVideoClip, concatenate_videoclips
        )
    except ImportError:
        return StageResult(success=False, error="MoviePy not installed")

    script_path = config.get_script_path(job_id)
    audio_path = config.get_audio_path(job_id)
    footage_dir = config.get_footage_dir(job_id)
    output_path = config.get_video_path(job_id)

    # Check prerequisites
    if not script_path.exists():
        return StageResult(success=False, error="Script not found")
    if not audio_path.exists():
        return StageResult(success=False, error="Audio not found")
    if not footage_dir.exists():
        return StageResult(success=False, error="Footage not found")

    # Idempotency check
    if output_path.exists() and not force:
        return StageResult(success=True, output_path=str(output_path))

    # Load script and manifest
    try:
        with open(script_path, 'r') as f:
            script_data = json.load(f)
        manifest_path = footage_dir / "manifest.json"
        with open(manifest_path, 'r') as f:
            manifest = json.load(f)
    except Exception as e:
        return StageResult(success=False, error=f"Failed to load data: {e}")

    sections = script_data.get("sections", [])
    downloaded = manifest.get("downloaded", [])

    if not downloaded:
        return StageResult(success=False, error="No footage clips available")

    clips = []
    try:
        # Load audio
        audio = AudioFileClip(str(audio_path))

        # Process each clip
        for item in downloaded:
            try:
                clip = VideoFileClip(item["path"])
                duration = item.get("duration", 3)

                # Trim or loop to match duration
                if clip.duration > duration:
                    clip = clip.subclip(0, duration)
                elif clip.duration < duration:
                    clip = clip.loop(duration=duration)

                # Resize for TikTok (1080x1920)
                clip = clip.resize(height=1920)
                if clip.w > 1080:
                    clip = clip.crop(x_center=clip.w / 2, width=1080, height=1920)

                clips.append(clip)
            except Exception as e:
                print(f"Warning: Failed to process clip {item['path']}: {e}")
                continue

        if not clips:
            return StageResult(success=False, error="No clips could be processed")

        # Concatenate clips
        video = concatenate_videoclips(clips, method="compose")

        # Trim to audio length
        if video.duration > audio.duration:
            video = video.subclip(0, audio.duration)

        # Set audio
        video = video.set_audio(audio)

        # Add text overlays
        text_clips = []
        for i, section in enumerate(sections[:len(clips)]):
            overlay_text = section.get("text_overlay", "")
            if not overlay_text:
                continue

            try:
                txt = TextClip(
                    overlay_text,
                    fontsize=60 if len(overlay_text) > 20 else 70,
                    color='white',
                    font='DejaVu-Sans-Bold',
                    stroke_color='black',
                    stroke_width=2,
                    method='label'
                )
                txt = txt.set_position('center')
                txt = txt.set_start(section["start"])
                txt = txt.set_duration(section["end"] - section["start"])
                text_clips.append(txt)
            except Exception:
                # Font fallback
                try:
                    txt = TextClip(
                        overlay_text,
                        fontsize=60,
                        color='white',
                        method='label'
                    )
                    txt = txt.set_position('center')
                    txt = txt.set_start(section["start"])
                    txt = txt.set_duration(section["end"] - section["start"])
                    text_clips.append(txt)
                except:
                    pass

        if text_clips:
            video = CompositeVideoClip([video] + text_clips)

        # Export settings
        fps = 24 if draft_mode else 30
        bitrate = '2000k' if draft_mode else '5000k'
        preset = 'ultrafast' if draft_mode else 'medium'

        video.write_videofile(
            str(output_path),
            fps=fps,
            codec='libx264',
            audio_codec='aac',
            bitrate=bitrate,
            preset=preset,
            threads=4,
            verbose=False,
            logger=None
        )

        # Cleanup
        video.close()
        audio.close()
        for c in clips:
            c.close()

        return StageResult(
            success=True,
            output_path=str(output_path),
            data={"duration": video.duration, "draft_mode": draft_mode}
        )

    except Exception as e:
        # Cleanup on error
        for c in clips:
            try:
                c.close()
            except:
                pass
        return StageResult(success=False, error=f"Render error: {e}")
