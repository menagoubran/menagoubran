"""
Colab Auto-Produce Template
Copy each cell into a Google Colab notebook.
Uses gTTS as fallback when ElevenLabs is unavailable.
"""

# =============================================================================
# CELL 1: SETUP & INSTALL
# =============================================================================

CELL_1 = '''
# ============================================
# SETUP - Run once per session
# ============================================

import os
from google.colab import drive, userdata

# Mount Drive for persistent storage
drive.mount('/content/drive')

# Create output directories
OUTPUT_DIR = '/content/drive/MyDrive/TikTok_Videos'
for d in ['audio', 'footage', 'videos', 'scripts']:
    os.makedirs(f"{OUTPUT_DIR}/{d}", exist_ok=True)

# Load API keys from Colab Secrets
os.environ['ANTHROPIC_API_KEY'] = userdata.get('ANTHROPIC_API_KEY')
os.environ['PEXELS_API_KEY'] = userdata.get('PEXELS_API_KEY')

# ElevenLabs is optional - gTTS will be used as fallback
try:
    os.environ['ELEVENLABS_API_KEY'] = userdata.get('ELEVEN_LABS_API_KEY')
    print("ElevenLabs key loaded")
except Exception:
    print("No ElevenLabs key - will use gTTS for voice")

os.environ['OUTPUT_DIR'] = OUTPUT_DIR

# Install dependencies
!pip install -q anthropic elevenlabs requests moviepy pillow numpy gTTS

print("\\nSetup complete!")
print(f"Output: {OUTPUT_DIR}")
'''

# =============================================================================
# CELL 2: PRODUCTION CODE
# =============================================================================

CELL_2 = '''
# ============================================
# PRODUCTION CODE - Run once per session
# ============================================

import os
import re
import json
import time
import numpy as np
from pathlib import Path

import requests
from PIL import Image, ImageDraw, ImageFont
from anthropic import Anthropic
from moviepy.editor import (
    VideoFileClip, AudioFileClip, ImageClip, CompositeVideoClip,
    CompositeAudioClip, concatenate_videoclips, concatenate_audioclips
)
from gtts import gTTS


class VideoEditor:
    """Video editor for TikTok 9:16 content."""

    def __init__(self, output_dir="output"):
        self.output_dir = Path(output_dir)
        self.video_size = (1080, 1920)
        self.fps = 30
        self.font_size = 110
        self.font_color = "white"
        self.stroke_color = "black"
        self.stroke_width = 2

    def resize_clip(self, clip):
        target_w, target_h = self.video_size
        target_ratio = target_w / target_h
        clip_w, clip_h = clip.size
        clip_ratio = clip_w / clip_h

        if clip_ratio > target_ratio:
            resized = clip.resize(height=target_h)
            new_w = int(clip_ratio * target_h)
            x1 = (new_w - target_w) // 2
            return resized.crop(x1=x1, y1=0, x2=x1 + target_w, y2=target_h)
        else:
            resized = clip.resize(width=target_w)
            new_h = int(target_w / clip_ratio)
            y1 = (new_h - target_h) // 2
            return resized.crop(x1=0, y1=y1, x2=target_w, y2=y1 + target_h)

    def create_text_image(self, text, position="bottom"):
        size = self.video_size
        img = Image.new("RGBA", size, (0, 0, 0, 0))
        draw = ImageDraw.Draw(img)

        try:
            font = ImageFont.truetype(
                "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf",
                self.font_size
            )
        except (IOError, OSError):
            font = ImageFont.load_default()

        bbox = draw.textbbox((0, 0), text, font=font)
        tw, th = bbox[2] - bbox[0], bbox[3] - bbox[1]

        if position == "center":
            x, y = (size[0] - tw) // 2, (size[1] - th) // 2
        elif position == "top":
            x, y = (size[0] - tw) // 2, size[1] // 6
        else:  # bottom
            x, y = (size[0] - tw) // 2, int(size[1] * 0.8)

        for dx in range(-self.stroke_width, self.stroke_width + 1):
            for dy in range(-self.stroke_width, self.stroke_width + 1):
                if dx != 0 or dy != 0:
                    draw.text((x+dx, y+dy), text, font=font, fill=self.stroke_color)
        draw.text((x, y), text, font=font, fill=self.font_color)
        return np.array(img)

    def add_text_overlays(self, video, overlays):
        clips = []
        for cfg in overlays:
            dur = cfg["end"] - cfg["start"]
            if dur <= 0 or not cfg.get("text"):
                continue
            img = self.create_text_image(cfg["text"], cfg.get("position", "bottom"))
            clip = (ImageClip(img, duration=dur)
                    .set_start(cfg["start"])
                    .crossfadein(0.2)
                    .crossfadeout(0.2))
            clips.append(clip)
        if clips:
            return CompositeVideoClip([video] + clips)
        return video

    def apply_zoom_effect(self, clip, zoom_factor=1.05):
        duration = clip.duration
        def zoom_frame(get_frame, t):
            frame = get_frame(t)
            img = Image.fromarray(frame)
            w, h = img.size
            progress = t / duration if duration > 0 else 0
            z = 1 + (zoom_factor - 1) * progress
            cw, ch = int(w / z), int(h / z)
            left, top = (w - cw) // 2, (h - ch) // 2
            img = img.crop((left, top, left+cw, top+ch)).resize((w, h), Image.LANCZOS)
            return np.array(img)
        return clip.fl(zoom_frame)

    def create_video_synced(self, clip_paths, audio_path, text_overlays=None,
                            output_path=None, apply_zoom=True):
        audio = AudioFileClip(audio_path)
        total_dur = audio.duration
        clip_dur = total_dur / len(clip_paths)

        clips = []
        for path in clip_paths:
            try:
                clip = VideoFileClip(path)
                if clip.duration < clip_dur:
                    clip = clip.loop(duration=clip_dur)
                else:
                    clip = clip.subclip(0, clip_dur)
                clip = self.resize_clip(clip)
                if apply_zoom:
                    clip = self.apply_zoom_effect(clip)
                clips.append(clip)
            except Exception as e:
                print(f"  Clip error ({path}): {e}")

        if not clips:
            raise ValueError("No clips processed")

        video = concatenate_videoclips(clips, method="compose")
        video = video.set_audio(audio)

        if text_overlays:
            video = self.add_text_overlays(video, text_overlays)

        if output_path is None:
            output_path = str(self.output_dir / "videos" / "output.mp4")

        os.makedirs(os.path.dirname(output_path), exist_ok=True)
        video.write_videofile(output_path, fps=self.fps, codec="libx264",
                              audio_codec="aac", bitrate="5000k", preset="medium",
                              threads=4, verbose=False, logger=None)
        audio.close()
        video.close()
        for c in clips:
            c.close()
        return output_path


class PexelsClient:
    def __init__(self, api_key):
        self.headers = {"Authorization": api_key}

    def search(self, query, per_page=5):
        try:
            r = requests.get("https://api.pexels.com/videos/search",
                             headers=self.headers,
                             params={"query": query, "per_page": per_page,
                                     "orientation": "portrait", "size": "medium"},
                             timeout=10)
            return r.json().get("videos", []) if r.ok else []
        except:
            return []

    def download(self, video, path):
        files = sorted(video.get("video_files", []),
                       key=lambda x: (x.get("quality") == "hd", x.get("width", 0)),
                       reverse=True)
        if not files:
            return False
        try:
            r = requests.get(files[0]["link"], stream=True, timeout=30)
            r.raise_for_status()
            os.makedirs(os.path.dirname(path), exist_ok=True)
            with open(path, "wb") as f:
                for chunk in r.iter_content(8192):
                    f.write(chunk)
            return True
        except:
            return False


class AutoProducer:
    def __init__(self):
        self.output_dir = Path(os.environ.get('OUTPUT_DIR', 'output'))
        for d in ['audio', 'footage', 'videos', 'scripts']:
            (self.output_dir / d).mkdir(parents=True, exist_ok=True)

        self.claude = Anthropic(api_key=os.environ['ANTHROPIC_API_KEY'])
        self.pexels = PexelsClient(os.environ['PEXELS_API_KEY'])
        self.editor = VideoEditor(str(self.output_dir))

        # ElevenLabs optional
        self.elevenlabs = None
        el_key = os.environ.get('ELEVENLABS_API_KEY')
        if el_key:
            try:
                from elevenlabs import ElevenLabs
                self.elevenlabs = ElevenLabs(api_key=el_key)
            except:
                pass

    def generate_script(self, topic):
        prompt = f"""You are a Viral Content Strategist. Create a TikTok script for: {topic}

Return ONLY valid JSON:
{{
    "script": "Full voiceover (under 140 words). Use [PAUSE] for pauses.",
    "sections": [
        {{"start": 0, "end": 5, "pexels_keywords": ["kw1", "kw2"], "text_overlay": "HOOK TEXT"}},
        {{"start": 5, "end": 12, "pexels_keywords": ["kw1", "kw2"], "text_overlay": "POINT 1"}},
        {{"start": 12, "end": 20, "pexels_keywords": ["kw1", "kw2"], "text_overlay": "POINT 2"}},
        {{"start": 20, "end": 28, "pexels_keywords": ["kw1", "kw2"], "text_overlay": "CTA"}}
    ]
}}

Requirements: Hook in first 3s, psychology/self-improvement focus, loopable ending."""

        try:
            resp = self.claude.messages.create(
                model="claude-sonnet-4-20250514", max_tokens=1500,
                messages=[{"role": "user", "content": prompt}])
            match = re.search(r'\\{.*\\}', resp.content[0].text, re.DOTALL)
            if match:
                return json.loads(match.group())
        except Exception as e:
            print(f"  Script error: {e}")

        return {
            "script": f"Here's what most people get wrong about {topic}. "
                      f"The truth will surprise you. Follow for more insights.",
            "sections": [
                {"start": 0, "end": 5, "pexels_keywords": [topic, "person"], "text_overlay": "DID YOU KNOW?"},
                {"start": 5, "end": 12, "pexels_keywords": ["thinking", "idea"], "text_overlay": "THE TRUTH"},
                {"start": 12, "end": 20, "pexels_keywords": ["success", "confidence"], "text_overlay": "KEY INSIGHT"},
                {"start": 20, "end": 25, "pexels_keywords": ["follow", "subscribe"], "text_overlay": "FOLLOW"}
            ]
        }

    def generate_voiceover(self, text, path):
        clean = text.replace("[PAUSE]", "...")
        if self.elevenlabs:
            try:
                gen = self.elevenlabs.text_to_speech.convert(
                    voice_id="pNInz6obpgDQGcFmaJgB", text=clean,
                    model_id="eleven_multilingual_v2")
                with open(path, "wb") as f:
                    for chunk in gen:
                        f.write(chunk)
                print("  Voice: ElevenLabs")
                return path
            except Exception as e:
                print(f"  ElevenLabs failed: {e}")

        # gTTS fallback
        try:
            tts = gTTS(text=clean, lang='en', slow=False)
            tts.save(path)
            print("  Voice: gTTS")
            return path
        except Exception as e:
            print(f"  gTTS failed: {e}")
            return None

    def mix_audio(self, voice_path, music_path, out_path):
        try:
            voice = AudioFileClip(voice_path)
            music = AudioFileClip(music_path)
            if music.duration < voice.duration:
                loops = int(voice.duration / music.duration) + 1
                music = concatenate_audioclips([music] * loops)
            music = music.subclip(0, voice.duration).volumex(0.15)
            final = CompositeAudioClip([voice, music])
            final.write_audiofile(out_path, fps=44100, verbose=False, logger=None)
            voice.close(); music.close(); final.close()
            return out_path
        except Exception as e:
            print(f"  Mix failed: {e}")
            return voice_path

    def produce(self, topic, fast_mode=False):
        print(f"\\n{'='*60}")
        print(f"  PRODUCING: {topic} (fast={fast_mode})")
        print(f"{'='*60}")
        slug = re.sub(r'[^\\w]', '_', topic.lower())[:40]

        # 1. Script
        print("\\n[1/5] Script...")
        script = self.generate_script(topic)
        with open(self.output_dir / "scripts" / f"{slug}.json", "w") as f:
            json.dump(script, f, indent=2)
        print(f"  Generated: {len(script['script'])} chars")

        # 2. Voice
        print("\\n[2/5] Voiceover...")
        voice_path = str(self.output_dir / "audio" / f"{slug}_raw.mp3")
        if not self.generate_voiceover(script["script"], voice_path):
            print("  FAILED"); return None

        # 3. Music mix
        print("\\n[3/5] Audio mix...")
        music_path = str(self.output_dir / "audio" / "bg_music.mp3")
        final_audio = str(self.output_dir / "audio" / f"{slug}_final.mp3")
        if not os.path.exists(music_path):
            try:
                url = "https://files.freemusicarchive.org/storage-freemusicarchive-org/music/ccCommunity/Kai_Engel/Satin/Kai_Engel_-_04_-_Sentinel.mp3"
                r = requests.get(url, stream=True, timeout=30)
                if r.ok:
                    with open(music_path, "wb") as f:
                        for chunk in r.iter_content(8192): f.write(chunk)
            except:
                pass
        if os.path.exists(music_path):
            final_audio = self.mix_audio(voice_path, music_path, final_audio)
        else:
            final_audio = voice_path

        # 4. Footage
        print("\\n[4/5] Footage...")
        clips = []
        for i, sec in enumerate(script["sections"]):
            q = " ".join(sec["pexels_keywords"][:2])
            print(f"  [{i+1}] {q}")
            vids = self.pexels.search(q)
            if vids:
                p = str(self.output_dir / "footage" / f"{slug}_{i}.mp4")
                if self.pexels.download(vids[0], p):
                    clips.append(p)
            time.sleep(0.5)

        if not clips:
            print("  FAILED: No footage"); return None

        # 5. Render
        print(f"\\n[5/5] Rendering ({len(clips)} clips)...")
        try:
            audio = AudioFileClip(final_audio)
            dur = audio.duration; audio.close()
            cdur = dur / len(clips)
            overlays = [{"text": s.get("text_overlay", ""),
                         "start": i*cdur, "end": (i+1)*cdur}
                        for i, s in enumerate(script["sections"][:len(clips)])]
            out = str(self.output_dir / "videos" / f"{slug}.mp4")
            self.editor.create_video_synced(clips, final_audio, overlays, out, not fast_mode)
            print(f"\\n  SUCCESS: {out}")
            return out
        except Exception as e:
            print(f"  FAILED: {e}")
            import traceback; traceback.print_exc()
            return None


# Ready!
producer = AutoProducer()
print("\\nAutoProducer ready!")
print("Usage: producer.produce('Your Topic', fast_mode=True)")
'''

# =============================================================================
# CELL 3: PRODUCE VIDEO
# =============================================================================

CELL_3 = '''
# ============================================
# PRODUCE A VIDEO
# Change the topic and run this cell
# ============================================

topic = "Public Speaking"  # <-- CHANGE THIS

producer.produce(topic, fast_mode=True)
'''

# =============================================================================
# CELL 4: BATCH PRODUCE
# =============================================================================

CELL_4 = '''
# ============================================
# BATCH PRODUCE - Multiple videos
# ============================================

topics = [
    "Public Speaking",
    "Body Language Secrets",
    "The Psychology of Eye Contact",
    "How to Read People Instantly",
    "Confidence Tricks That Work",
]

import time

for i, topic in enumerate(topics):
    print(f"\\n\\n{'#'*60}")
    print(f"# VIDEO {i+1}/{len(topics)}")
    print(f"{'#'*60}")
    producer.produce(topic, fast_mode=True)
    time.sleep(2)  # Rate limiting
'''

# =============================================================================
# CELL 5: DOWNLOAD
# =============================================================================

CELL_5 = '''
# ============================================
# DOWNLOAD VIDEO
# ============================================

import os, re
from google.colab import files

topic = "Public Speaking"  # <-- MUST MATCH CELL 3
slug = re.sub(r'[^\\w]', '_', topic.lower())[:40]
video_path = f"{os.environ['OUTPUT_DIR']}/videos/{slug}.mp4"

if os.path.exists(video_path):
    size_mb = os.path.getsize(video_path) / (1024*1024)
    print(f"Downloading: {video_path} ({size_mb:.1f} MB)")
    files.download(video_path)
else:
    print(f"Not found: {video_path}")
    print("Available videos:")
    vdir = f"{os.environ['OUTPUT_DIR']}/videos"
    if os.path.exists(vdir):
        for f in os.listdir(vdir):
            if f.endswith('.mp4'):
                print(f"  {f}")
'''


if __name__ == "__main__":
    print("=" * 60)
    print("COLAB AUTO-PRODUCE TEMPLATE")
    print("=" * 60)
    print("\\nCopy these cells into a Google Colab notebook:")
    print("  Cell 1: Setup & Install")
    print("  Cell 2: Production Code (VideoEditor + AutoProducer)")
    print("  Cell 3: Produce Single Video")
    print("  Cell 4: Batch Produce Multiple Videos")
    print("  Cell 5: Download Video")
