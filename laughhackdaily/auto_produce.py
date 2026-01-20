#!/usr/bin/env python3
"""
LaughHackDaily Auto-Production System

Fully automated TikTok video production:
1. Generate script with Claude API
2. Create voiceover with ElevenLabs
3. Download footage from Pexels
4. Edit and export final video

Usage:
    python auto_produce.py "body language secrets"
"""

import os
import sys
import re
import json
import time
import asyncio
import requests
from pathlib import Path
from typing import Optional
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# API clients
from anthropic import Anthropic
from elevenlabs import ElevenLabs

# Local modules
from video_editor import VideoEditor


class ProgressIndicator:
    """Simple progress indicator for long-running operations."""

    def __init__(self, message: str):
        self.message = message
        self.symbols = ["⠋", "⠙", "⠹", "⠸", "⠼", "⠴", "⠦", "⠧", "⠇", "⠏"]
        self.idx = 0

    def __enter__(self):
        print(f"\n{self.symbols[0]} {self.message}...", end="", flush=True)
        return self

    def __exit__(self, *args):
        print(" ✓")

    def update(self, suffix: str = ""):
        self.idx = (self.idx + 1) % len(self.symbols)
        print(f"\r{self.symbols[self.idx]} {self.message}... {suffix}", end="", flush=True)


class PexelsClient:
    """Client for Pexels API to download stock footage."""

    def __init__(self, api_key: str):
        self.api_key = api_key
        self.base_url = "https://api.pexels.com/videos"
        self.headers = {"Authorization": api_key}

    def search_videos(self, query: str, per_page: int = 5, orientation: str = "portrait") -> list:
        """Search for videos on Pexels."""
        params = {
            "query": query,
            "per_page": per_page,
            "orientation": orientation,
            "size": "medium"
        }

        response = requests.get(
            f"{self.base_url}/search",
            headers=self.headers,
            params=params
        )

        if response.status_code != 200:
            print(f"    Warning: Pexels search failed for '{query}': {response.status_code}")
            return []

        data = response.json()
        return data.get("videos", [])

    def download_video(self, video: dict, output_path: str) -> Optional[str]:
        """Download a video from Pexels."""
        # Find the best quality video file (HD preferred)
        video_files = video.get("video_files", [])
        if not video_files:
            return None

        # Sort by quality (prefer HD)
        video_files = sorted(
            video_files,
            key=lambda x: (x.get("quality", "") == "hd", x.get("width", 0)),
            reverse=True
        )

        video_url = video_files[0].get("link")
        if not video_url:
            return None

        try:
            response = requests.get(video_url, stream=True)
            response.raise_for_status()

            os.makedirs(os.path.dirname(output_path), exist_ok=True)

            with open(output_path, "wb") as f:
                for chunk in response.iter_content(chunk_size=8192):
                    f.write(chunk)

            return output_path
        except Exception as e:
            print(f"    Warning: Failed to download video: {e}")
            return None


class AutoProducer:
    """Main auto-production class for TikTok videos."""

    def __init__(self):
        # Load API keys
        self.anthropic_key = os.getenv("ANTHROPIC_API_KEY")
        self.elevenlabs_key = os.getenv("ELEVENLABS_API_KEY")
        self.pexels_key = os.getenv("PEXELS_API_KEY")

        # Validate keys
        if not self.anthropic_key:
            raise ValueError("ANTHROPIC_API_KEY not found in environment")
        if not self.elevenlabs_key:
            raise ValueError("ELEVENLABS_API_KEY not found in environment")
        if not self.pexels_key:
            raise ValueError("PEXELS_API_KEY not found in environment")

        # Initialize clients
        self.claude = Anthropic(api_key=self.anthropic_key)
        self.elevenlabs = ElevenLabs(api_key=self.elevenlabs_key)
        self.pexels = PexelsClient(self.pexels_key)
        self.editor = VideoEditor()

        # Output directories
        self.output_dir = Path("output")
        self.audio_dir = self.output_dir / "audio"
        self.footage_dir = self.output_dir / "footage"
        self.video_dir = self.output_dir / "videos"

        # Create directories
        for d in [self.audio_dir, self.footage_dir, self.video_dir]:
            d.mkdir(parents=True, exist_ok=True)

    def sanitize_filename(self, name: str) -> str:
        """Convert topic to safe filename."""
        return re.sub(r'[^\w\-]', '_', name.lower().strip())[:50]

    def generate_script(self, topic: str) -> dict:
        """Generate script and production details using Claude."""
        with ProgressIndicator("Generating script with Claude"):
            prompt = f"""Create a TikTok production package for topic: {topic}

You must respond with ONLY valid JSON, no other text. Use this exact structure:

{{
    "title": "Video title",
    "script": "Full voiceover script with natural pauses marked as [PAUSE]",
    "duration_estimate": 30,
    "sections": [
        {{
            "name": "Hook",
            "start": 0,
            "end": 5,
            "pexels_keywords": ["keyword1", "keyword2"],
            "text_overlay": "Text to show"
        }},
        {{
            "name": "Point 1",
            "start": 5,
            "end": 12,
            "pexels_keywords": ["keyword1", "keyword2"],
            "text_overlay": "Text to show"
        }},
        {{
            "name": "Point 2",
            "start": 12,
            "end": 20,
            "pexels_keywords": ["keyword1", "keyword2"],
            "text_overlay": "Text to show"
        }},
        {{
            "name": "Point 3",
            "start": 20,
            "end": 27,
            "pexels_keywords": ["keyword1", "keyword2"],
            "text_overlay": "Text to show"
        }},
        {{
            "name": "CTA",
            "start": 27,
            "end": 32,
            "pexels_keywords": ["keyword1", "keyword2"],
            "text_overlay": "Follow for more"
        }}
    ],
    "hashtags": ["#LaughHackDaily", "#FYP", "#ViralHack", "#ComedyHacks"]
}}

Requirements:
- Script should be 25-35 seconds when read naturally
- Include 5 sections with Pexels search keywords
- Keywords should find vertical-friendly footage
- Text overlays should be short (3-6 words)
- Focus on self-improvement psychology"""

            response = self.claude.messages.create(
                model="claude-sonnet-4-20250514",
                max_tokens=2000,
                messages=[{"role": "user", "content": prompt}]
            )

            content = response.content[0].text

            # Extract JSON from response
            try:
                # Try to find JSON in the response
                json_match = re.search(r'\{[\s\S]*\}', content)
                if json_match:
                    return json.loads(json_match.group())
                else:
                    raise ValueError("No JSON found in response")
            except json.JSONDecodeError as e:
                print(f"\n    Warning: Failed to parse JSON, using fallback structure")
                return self._create_fallback_script(topic, content)

    def _create_fallback_script(self, topic: str, raw_content: str) -> dict:
        """Create a fallback script structure if JSON parsing fails."""
        return {
            "title": topic,
            "script": raw_content[:500] if raw_content else f"Learn about {topic} in 30 seconds.",
            "duration_estimate": 30,
            "sections": [
                {"name": "Hook", "start": 0, "end": 5, "pexels_keywords": ["confident person", "eye contact"], "text_overlay": topic.upper()},
                {"name": "Point 1", "start": 5, "end": 12, "pexels_keywords": ["professional speaking", "communication"], "text_overlay": "POINT 1"},
                {"name": "Point 2", "start": 12, "end": 20, "pexels_keywords": ["body language", "gestures"], "text_overlay": "POINT 2"},
                {"name": "Point 3", "start": 20, "end": 27, "pexels_keywords": ["success mindset", "confidence"], "text_overlay": "POINT 3"},
                {"name": "CTA", "start": 27, "end": 32, "pexels_keywords": ["follow subscribe", "thumbs up"], "text_overlay": "FOLLOW FOR MORE"},
            ],
            "hashtags": ["#LaughHackDaily", "#FYP", "#ViralHack", "#ComedyHacks"]
        }

    def generate_voiceover(self, script: str, output_path: str) -> str:
        """Generate voiceover using ElevenLabs."""
        with ProgressIndicator("Generating voiceover with ElevenLabs"):
            # Clean script for TTS
            clean_script = script.replace("[PAUSE]", "...").replace("[pause]", "...")

            try:
                # Generate audio
                audio_generator = self.elevenlabs.text_to_speech.convert(
                    voice_id="pNInz6obpgDQGcFmaJgB",  # Adam voice
                    text=clean_script,
                    model_id="eleven_monolingual_v1",
                    output_format="mp3_44100_128"
                )

                # Save audio
                os.makedirs(os.path.dirname(output_path), exist_ok=True)

                with open(output_path, "wb") as f:
                    for chunk in audio_generator:
                        f.write(chunk)

                return output_path

            except Exception as e:
                print(f"\n    Error generating voiceover: {e}")
                raise

    def download_footage(self, sections: list, topic_slug: str) -> list:
        """Download footage for each section from Pexels."""
        footage_paths = []
        topic_footage_dir = self.footage_dir / topic_slug
        topic_footage_dir.mkdir(parents=True, exist_ok=True)

        print(f"\n📥 Downloading footage from Pexels...")

        for i, section in enumerate(sections):
            keywords = section.get("pexels_keywords", ["professional person"])
            query = " ".join(keywords[:2])  # Use first 2 keywords

            print(f"  Section {i+1}/{len(sections)}: {section['name']} - Searching '{query}'")

            videos = self.pexels.search_videos(query, per_page=3)

            if videos:
                # Download first suitable video
                output_path = str(topic_footage_dir / f"clip_{i+1}.mp4")
                downloaded = self.pexels.download_video(videos[0], output_path)

                if downloaded:
                    footage_paths.append({
                        "path": downloaded,
                        "duration": section["end"] - section["start"],
                        "section": section
                    })
                    print(f"    ✓ Downloaded clip {i+1}")
                else:
                    print(f"    ✗ Failed to download clip {i+1}")
            else:
                print(f"    ✗ No videos found for '{query}'")

            # Rate limiting
            time.sleep(0.5)

        return footage_paths

    def create_video(
        self,
        footage: list,
        audio_path: str,
        sections: list,
        output_path: str
    ) -> str:
        """Create final video with footage, audio, and text overlays."""
        print(f"\n🎬 Creating video...")

        # Prepare clip paths and durations
        clip_paths = [f["path"] for f in footage]
        clip_durations = [f["duration"] for f in footage]

        # Prepare text overlays
        text_overlays = []
        for section in sections:
            if section.get("text_overlay"):
                text_overlays.append({
                    "text": section["text_overlay"],
                    "start": section["start"],
                    "end": section["end"],
                    "position": "top"
                })

        # Create video
        return self.editor.create_video_from_clips(
            clip_paths=clip_paths,
            clip_durations=clip_durations,
            audio_path=audio_path,
            text_overlays=text_overlays,
            output_path=output_path
        )

    def produce(self, topic: str) -> dict:
        """
        Main production method - orchestrates the full pipeline.

        Args:
            topic: Content topic (e.g., "body language secrets")

        Returns:
            dict with paths to all generated assets
        """
        print("\n" + "=" * 60)
        print(f"🎬 LAUGHHACKDAILY AUTO-PRODUCER")
        print(f"📌 Topic: {topic}")
        print("=" * 60)

        topic_slug = self.sanitize_filename(topic)
        results = {"topic": topic, "slug": topic_slug}

        # Phase 1: Generate script
        print("\n📝 PHASE 1: Script Generation")
        script_data = self.generate_script(topic)
        results["script"] = script_data

        # Save script JSON
        script_path = self.output_dir / f"{topic_slug}_script.json"
        with open(script_path, "w") as f:
            json.dump(script_data, f, indent=2)
        results["script_path"] = str(script_path)
        print(f"  Script saved to: {script_path}")

        # Phase 2: Generate voiceover
        print("\n🎙️ PHASE 2: Voiceover Generation")
        audio_path = str(self.audio_dir / f"{topic_slug}.mp3")
        try:
            self.generate_voiceover(script_data["script"], audio_path)
            results["audio_path"] = audio_path
            print(f"  Audio saved to: {audio_path}")
        except Exception as e:
            print(f"  ⚠️ Voiceover generation failed: {e}")
            results["audio_path"] = None

        # Phase 3: Download footage
        print("\n🎥 PHASE 3: Footage Download")
        footage = self.download_footage(script_data["sections"], topic_slug)
        results["footage"] = [f["path"] for f in footage]
        print(f"  Downloaded {len(footage)} clips")

        # Phase 4: Create video
        if len(footage) >= 3 and results.get("audio_path"):
            print("\n🎞️ PHASE 4: Video Production")
            video_path = str(self.video_dir / f"{topic_slug}.mp4")
            try:
                self.create_video(
                    footage=footage,
                    audio_path=results["audio_path"],
                    sections=script_data["sections"],
                    output_path=video_path
                )
                results["video_path"] = video_path
                print(f"\n✅ Final video saved to: {video_path}")
            except Exception as e:
                print(f"\n⚠️ Video creation failed: {e}")
                results["video_path"] = None
        else:
            print("\n⚠️ Skipping video creation (insufficient footage or missing audio)")
            results["video_path"] = None

        # Summary
        print("\n" + "=" * 60)
        print("📊 PRODUCTION SUMMARY")
        print("=" * 60)
        print(f"  Topic: {topic}")
        print(f"  Script: {results.get('script_path', 'N/A')}")
        print(f"  Audio: {results.get('audio_path', 'N/A')}")
        print(f"  Footage: {len(results.get('footage', []))} clips")
        print(f"  Video: {results.get('video_path', 'N/A')}")
        print("=" * 60 + "\n")

        return results


async def main():
    """Main entry point."""
    if len(sys.argv) < 2:
        print("Usage: python auto_produce.py \"topic here\"")
        print("Example: python auto_produce.py \"body language secrets\"")
        sys.exit(1)

    topic = " ".join(sys.argv[1:])

    try:
        producer = AutoProducer()
        results = producer.produce(topic)

        # Save results
        results_path = Path("output") / f"{producer.sanitize_filename(topic)}_results.json"
        with open(results_path, "w") as f:
            json.dump(results, f, indent=2, default=str)

        print(f"Results saved to: {results_path}")

    except ValueError as e:
        print(f"\n❌ Configuration error: {e}")
        print("\nMake sure your .env file contains:")
        print("  ANTHROPIC_API_KEY=...")
        print("  ELEVENLABS_API_KEY=...")
        print("  PEXELS_API_KEY=...")
        sys.exit(1)
    except Exception as e:
        print(f"\n❌ Production failed: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    asyncio.run(main())
