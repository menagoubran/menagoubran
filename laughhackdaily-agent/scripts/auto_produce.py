"""
Auto Producer for LaughHackDaily
Generates TikTok videos end-to-end using Claude, ElevenLabs/gTTS, Pexels, and MoviePy.
"""

import os
import sys
import re
import json
import time
from pathlib import Path

import requests
from anthropic import Anthropic
from moviepy.editor import AudioFileClip, CompositeAudioClip, concatenate_audioclips
from gtts import gTTS

from .video_editor import VideoEditor


class PexelsClient:
    """Pexels API client for stock video search and download."""

    def __init__(self, api_key):
        self.api_key = api_key
        self.base_url = "https://api.pexels.com/videos"
        self.headers = {"Authorization": api_key}

    def search_videos(self, query, per_page=5):
        params = {
            "query": query,
            "per_page": per_page,
            "orientation": "portrait",
            "size": "medium"
        }
        try:
            response = requests.get(
                f"{self.base_url}/search",
                headers=self.headers,
                params=params,
                timeout=10
            )
            if response.status_code == 200:
                return response.json().get("videos", [])
        except Exception as e:
            print(f"  Pexels search error: {e}")
        return []

    def download_video(self, video, output_path):
        files = sorted(
            video.get("video_files", []),
            key=lambda x: (x.get("quality", "") == "hd", x.get("width", 0)),
            reverse=True
        )
        if not files:
            return None
        url = files[0].get("link")
        if not url:
            return None
        try:
            r = requests.get(url, stream=True, timeout=30)
            r.raise_for_status()
            os.makedirs(os.path.dirname(output_path), exist_ok=True)
            with open(output_path, "wb") as f:
                for chunk in r.iter_content(chunk_size=8192):
                    f.write(chunk)
            return output_path
        except Exception as e:
            print(f"  Download error: {e}")
            return None


class AutoProducer:
    """End-to-end TikTok video producer."""

    def __init__(self, output_dir: str = "output"):
        self.output_dir = Path(output_dir)
        for d in ["audio", "footage", "videos", "scripts"]:
            (self.output_dir / d).mkdir(parents=True, exist_ok=True)

        # Initialize API clients
        anthropic_key = os.environ.get("ANTHROPIC_API_KEY")
        elevenlabs_key = os.environ.get("ELEVENLABS_API_KEY")
        pexels_key = os.environ.get("PEXELS_API_KEY")

        if not anthropic_key:
            raise ValueError("ANTHROPIC_API_KEY environment variable not set")
        if not pexels_key:
            raise ValueError("PEXELS_API_KEY environment variable not set")

        self.claude = Anthropic(api_key=anthropic_key)
        self.pexels = PexelsClient(pexels_key)
        self.editor = VideoEditor(str(self.output_dir))

        # ElevenLabs is optional (gTTS fallback available)
        self.elevenlabs = None
        if elevenlabs_key:
            try:
                from elevenlabs import ElevenLabs
                self.elevenlabs = ElevenLabs(api_key=elevenlabs_key)
            except ImportError:
                print("  ElevenLabs package not installed, using gTTS")

    def generate_script(self, topic, source_material=None):
        """Generate a viral TikTok script using Claude."""
        ref_text = f"\n\nReference Material:\n{source_material}" if source_material else ""
        prompt = f"""You are a Viral Content Strategist for TikTok. Create a highly engaging, retention-optimized script for the topic: {topic}{ref_text}

Structure the video for maximum retention:
1. **Hook (0-3s)**: Visually striking, controversial statement or question.
2. **Re-engagement (3-10s)**: Why they should care, "The Problem".
3. **Value (10-25s)**: The core insight, fast-paced.
4. **CTA (25-30s)**: Loopable ending or strong call to action.

Return ONLY valid JSON in this format:
{{
    "script": "Full voiceover text with natural pauses marked as [PAUSE]. Keep it under 140 words.",
    "sections": [
        {{
            "start": 0, "end": 5,
            "pexels_keywords": ["visual keyword 1", "visual keyword 2"],
            "text_overlay": "Big Bold Text",
            "visual_cues": "Description of what is happening"
        }}
    ]
}}

Create 4-6 sections covering approximately 30 seconds total."""

        try:
            resp = self.claude.messages.create(
                model="claude-sonnet-4-20250514",
                max_tokens=1500,
                messages=[{"role": "user", "content": prompt}]
            )
            txt = resp.content[0].text
            match = re.search(r'\{.*\}', txt, re.DOTALL)
            if match:
                data = json.loads(match.group())
                if "script" in data and "sections" in data:
                    print(f"  Script generated: {len(data['script'])} chars, "
                          f"{len(data['sections'])} sections")
                    return data
        except Exception as e:
            print(f"  Script generation error: {e}")

        return self._fallback_script(topic)

    def _fallback_script(self, topic):
        """Fallback script if Claude API fails."""
        return {
            "script": (
                f"Here is a mind-blowing fact about {topic}. "
                f"Most people don't know this secret. "
                f"It changes everything. Follow for more."
            ),
            "sections": [
                {"start": 0, "end": 5, "pexels_keywords": [topic, "person"],
                 "text_overlay": "DID YOU KNOW?"},
                {"start": 5, "end": 12, "pexels_keywords": ["thinking", "idea"],
                 "text_overlay": "THE SECRET"},
                {"start": 12, "end": 20, "pexels_keywords": ["reveal", "insight"],
                 "text_overlay": "THE TRUTH"},
                {"start": 20, "end": 25, "pexels_keywords": ["success", "confidence"],
                 "text_overlay": "FOLLOW FOR MORE"}
            ]
        }

    def generate_voiceover(self, script_text, output_path):
        """Generate voiceover audio. Tries ElevenLabs first, falls back to gTTS."""
        clean_text = script_text.replace("[PAUSE]", "...")

        # Try ElevenLabs first
        if self.elevenlabs:
            try:
                gen = self.elevenlabs.text_to_speech.convert(
                    voice_id="pNInz6obpgDQGcFmaJgB",
                    text=clean_text,
                    model_id="eleven_multilingual_v2"
                )
                with open(output_path, "wb") as f:
                    for chunk in gen:
                        f.write(chunk)
                print("  Voiceover generated (ElevenLabs)")
                return output_path
            except Exception as e:
                print(f"  ElevenLabs error: {e}")
                print("  Falling back to gTTS...")

        # gTTS fallback
        try:
            tts = gTTS(text=clean_text, lang='en', slow=False)
            tts.save(output_path)
            print("  Voiceover generated (gTTS)")
            return output_path
        except Exception as e:
            print(f"  gTTS error: {e}")
            return None

    def download_background_music(self, output_path):
        """Download royalty-free background music."""
        url = ("https://files.freemusicarchive.org/storage-freemusicarchive-org/"
               "music/ccCommunity/Kai_Engel/Satin/"
               "Kai_Engel_-_04_-_Sentinel.mp3")
        try:
            r = requests.get(url, stream=True, timeout=30)
            if r.status_code == 200:
                with open(output_path, "wb") as f:
                    for chunk in r.iter_content(chunk_size=8192):
                        f.write(chunk)
                return output_path
        except Exception as e:
            print(f"  Music download failed: {e}")
        return None

    def mix_audio(self, voice_path, music_path, final_path):
        """Mix voiceover with background music."""
        try:
            voice = AudioFileClip(voice_path)
            music = AudioFileClip(music_path)

            # Loop music if shorter than voice
            if music.duration < voice.duration:
                loops = int(voice.duration / music.duration) + 1
                music = concatenate_audioclips([music] * loops)

            music = music.subclip(0, voice.duration).volumex(0.15)
            final = CompositeAudioClip([voice, music])
            final.write_audiofile(final_path, fps=44100, verbose=False, logger=None)

            voice.close()
            music.close()
            final.close()
            return final_path
        except Exception as e:
            print(f"  Audio mixing failed: {e}, using voice only")
            return voice_path

    def produce(self, topic, source_material=None, fast_mode=False):
        """Produce a complete TikTok video for the given topic."""
        print(f"\n{'='*60}")
        print(f"  PRODUCING: {topic}")
        print(f"  Fast mode: {fast_mode}")
        print(f"{'='*60}")

        slug = re.sub(r'[^\w]', '_', topic.lower())[:40]

        # Stage 1: Script
        print("\n[1/5] Generating script...")
        script_data = self.generate_script(topic, source_material)
        script_path = self.output_dir / "scripts" / f"{slug}.json"
        with open(script_path, "w") as f:
            json.dump(script_data, f, indent=2)

        # Stage 2: Voiceover
        print("\n[2/5] Generating voiceover...")
        raw_voice_path = str(self.output_dir / "audio" / f"{slug}_raw.mp3")
        if not self.generate_voiceover(script_data["script"], raw_voice_path):
            print("  FAILED: Could not generate audio")
            return None

        # Stage 3: Background music & mixing
        print("\n[3/5] Mixing audio...")
        music_path = str(self.output_dir / "audio" / "bg_music.mp3")
        final_audio_path = str(self.output_dir / "audio" / f"{slug}_final.mp3")

        if not os.path.exists(music_path):
            print("  Downloading background music...")
            self.download_background_music(music_path)

        if os.path.exists(music_path):
            final_audio_path = self.mix_audio(raw_voice_path, music_path, final_audio_path)
        else:
            print("  No background music available, using voice only")
            final_audio_path = raw_voice_path

        # Stage 4: Download footage
        print("\n[4/5] Downloading footage...")
        footage_paths = []
        for i, sec in enumerate(script_data["sections"]):
            query = " ".join(sec["pexels_keywords"][:2])
            print(f"  [{i+1}/{len(script_data['sections'])}] Searching: {query}")
            videos = self.pexels.search_videos(query)
            if videos:
                clip_path = str(self.output_dir / "footage" / f"{slug}_clip_{i}.mp4")
                if self.pexels.download_video(videos[0], clip_path):
                    footage_paths.append(clip_path)
                    print(f"    Downloaded")
                else:
                    print(f"    Download failed")
            else:
                print(f"    No results")
            time.sleep(0.5)

        if not footage_paths:
            print("  FAILED: No footage downloaded")
            return None

        # Stage 5: Assemble video
        print(f"\n[5/5] Assembling video ({len(footage_paths)} clips)...")
        try:
            # Calculate synced text overlays
            audio = AudioFileClip(final_audio_path)
            duration = audio.duration
            audio.close()
            clip_dur = duration / len(footage_paths)

            synced_overlays = []
            for i, sec in enumerate(script_data["sections"][:len(footage_paths)]):
                overlay_text = sec.get("text_overlay", "")
                if overlay_text:
                    synced_overlays.append({
                        "text": overlay_text,
                        "start": i * clip_dur,
                        "end": (i + 1) * clip_dur
                    })

            output_path = str(self.output_dir / "videos" / f"{slug}.mp4")
            result = self.editor.create_video_synced(
                clip_paths=footage_paths,
                audio_path=final_audio_path,
                text_overlays=synced_overlays,
                output_path=output_path,
                apply_zoom=not fast_mode
            )

            print(f"\n{'='*60}")
            print(f"  SUCCESS: {result}")
            print(f"{'='*60}")
            return result

        except Exception as e:
            print(f"  FAILED: Video assembly error: {e}")
            import traceback
            traceback.print_exc()
            return None


def main():
    """CLI entry point for auto_produce."""
    topic = " ".join(sys.argv[1:]) if len(sys.argv) > 1 else "Public Speaking"
    fast_mode = "--fast" in sys.argv

    # Remove flag from topic if present
    topic = topic.replace("--fast", "").strip()

    producer = AutoProducer()
    producer.produce(topic, fast_mode=fast_mode)


if __name__ == "__main__":
    main()
