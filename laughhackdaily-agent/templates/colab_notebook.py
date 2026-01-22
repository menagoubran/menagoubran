"""
LAUGHHACKDAILY - MASTER PRODUCTION SYSTEM v2.0
=============================================
Optimized Pipeline Factory with:
- 4-stage pipeline (Script → Voice → Footage → Render)
- Job queue with resume capability
- Parallel processing for early stages
- Idempotent operations
- Batch mode support
- Multi-worker support

Copy this code into Google Colab cells.
"""

# =============================================================================
# CELL 1: SETUP (Run once per session)
# =============================================================================

CELL_1_SETUP = '''
# ============================================
# 🎬 LAUGHHACKDAILY v2.0 - SETUP
# Run this cell once when you open the notebook
# ============================================

print("🔧 SETUP - Initializing Pipeline Factory")
print("=" * 60)

# Imports
from google.colab import drive, userdata
import os
import sys

# Mount Google Drive
print("\\n[1/5] 📁 Mounting Google Drive...")
drive.mount('/content/drive')

# Create directory structure
print("\\n[2/5] 📂 Creating directory structure...")
BASE_DIR = '/content/drive/MyDrive/TikTok_Videos'
DIRS = ['queue', 'scripts', 'audio', 'footage', 'videos', 'logs']
for d in DIRS:
    os.makedirs(f"{BASE_DIR}/{d}", exist_ok=True)
print(f"✅ Base directory: {BASE_DIR}")

# Load API keys
print("\\n[3/5] 🔑 Loading API keys...")
os.environ['ANTHROPIC_API_KEY'] = userdata.get('ANTHROPIC_API_KEY')
os.environ['ELEVENLABS_API_KEY'] = userdata.get('ELEVEN_LABS_API_KEY')
os.environ['PEXELS_API_KEY'] = userdata.get('PEXELS_API_KEY')
os.environ['BASE_DIR'] = BASE_DIR
print("✅ API keys loaded from Colab Secrets")

# Install dependencies
print("\\n[4/5] 📦 Installing dependencies...")
!pip install -q anthropic elevenlabs requests moviepy pillow numpy

# Set worker ID for this session
import random
WORKER_ID = f"worker_{random.randint(1000, 9999)}"
os.environ['WORKER_ID'] = WORKER_ID
print(f"\\n[5/5] 🤖 Worker ID: {WORKER_ID}")

print("\\n" + "=" * 60)
print("✅ SETUP COMPLETE!")
print("=" * 60)
print("👉 Now run Cell 2 to load the pipeline code")
'''

# =============================================================================
# CELL 2: PIPELINE CODE (Run once per session)
# =============================================================================

CELL_2_PIPELINE = '''
# ============================================
# 🎬 PIPELINE FACTORY CODE
# Run this cell once after setup
# ============================================

import json
import os
import re
import time
import random
import requests
from pathlib import Path
from datetime import datetime
from typing import Optional, List, Dict, Any
from concurrent.futures import ThreadPoolExecutor, as_completed
from anthropic import Anthropic
from elevenlabs.client import ElevenLabs

print("📝 Loading Pipeline Factory v2.0...")

# =============================================================================
# JOB QUEUE SYSTEM
# =============================================================================

class JobStatus:
    NEW = "NEW"
    IN_PROGRESS = "IN_PROGRESS"
    SCRIPTED = "SCRIPTED"
    VOICED = "VOICED"
    FOOTAGE_READY = "FOOTAGE_READY"
    RENDERED = "RENDERED"
    FAILED = "FAILED"


class Job:
    def __init__(self, job_id: str, topic: str, status: str = "NEW",
                 attempts: int = 0, error_message: str = None):
        self.job_id = job_id
        self.topic = topic
        self.status = status
        self.attempts = attempts
        self.error_message = error_message
        self.created_at = datetime.now().isoformat()

    def to_dict(self):
        return vars(self)

    @classmethod
    def from_dict(cls, data):
        job = cls(data["job_id"], data["topic"])
        job.__dict__.update(data)
        return job


class JobQueue:
    def __init__(self, queue_dir: str):
        self.queue_file = Path(queue_dir) / "jobs.jsonl"
        Path(queue_dir).mkdir(parents=True, exist_ok=True)

    def _read_jobs(self) -> List[Job]:
        jobs = []
        if self.queue_file.exists():
            with open(self.queue_file, 'r') as f:
                for line in f:
                    if line.strip():
                        jobs.append(Job.from_dict(json.loads(line)))
        return jobs

    def _write_jobs(self, jobs: List[Job]):
        with open(self.queue_file, 'w') as f:
            for job in jobs:
                f.write(json.dumps(job.to_dict()) + "\\n")

    def add_topics(self, topics: List[str]) -> List[Job]:
        jobs = self._read_jobs()
        existing_ids = {j.job_id for j in jobs}
        new_jobs = []
        ts = datetime.now().strftime("%Y%m%d_%H%M%S")
        for i, topic in enumerate(topics):
            job_id = f"{ts}_{i:03d}"
            if job_id not in existing_ids:
                job = Job(job_id, topic)
                jobs.append(job)
                new_jobs.append(job)
        self._write_jobs(jobs)
        return new_jobs

    def get_next(self, statuses=None) -> Optional[Job]:
        if statuses is None:
            statuses = [JobStatus.NEW]
        jobs = self._read_jobs()
        for job in jobs:
            if job.status in statuses:
                job.status = JobStatus.IN_PROGRESS
                job.attempts += 1
                self._write_jobs(jobs)
                return job
        return None

    def update_status(self, job_id: str, status: str, error: str = None):
        jobs = self._read_jobs()
        for job in jobs:
            if job.job_id == job_id:
                job.status = status
                if error:
                    job.error_message = error
                break
        self._write_jobs(jobs)

    def get_stats(self) -> Dict[str, int]:
        jobs = self._read_jobs()
        stats = {"TOTAL": len(jobs)}
        for status in [JobStatus.NEW, JobStatus.SCRIPTED, JobStatus.VOICED,
                       JobStatus.FOOTAGE_READY, JobStatus.RENDERED, JobStatus.FAILED]:
            stats[status] = sum(1 for j in jobs if j.status == status)
        return stats

    def reset_failed(self, max_attempts: int = 3) -> int:
        jobs = self._read_jobs()
        count = 0
        for job in jobs:
            if job.status == JobStatus.FAILED and job.attempts < max_attempts:
                job.status = JobStatus.NEW
                count += 1
        self._write_jobs(jobs)
        return count


# =============================================================================
# PEXELS CLIENT
# =============================================================================

class PexelsClient:
    def __init__(self, api_key: str):
        self.api_key = api_key
        self.headers = {"Authorization": api_key}

    def search(self, query: str, per_page: int = 3) -> List[Dict]:
        try:
            resp = requests.get(
                "https://api.pexels.com/videos/search",
                headers=self.headers,
                params={"query": query, "per_page": per_page,
                        "orientation": "portrait", "size": "medium"},
                timeout=10
            )
            return resp.json().get("videos", []) if resp.ok else []
        except:
            return []

    def download(self, video: Dict, path: str) -> bool:
        files = sorted(video.get("video_files", []),
                       key=lambda x: (x.get("quality") == "hd", x.get("width", 0)),
                       reverse=True)
        if not files:
            return False
        try:
            resp = requests.get(files[0]["link"], stream=True, timeout=60)
            resp.raise_for_status()
            os.makedirs(os.path.dirname(path), exist_ok=True)
            with open(path, "wb") as f:
                for chunk in resp.iter_content(8192):
                    f.write(chunk)
            return True
        except:
            return False


# =============================================================================
# OPTIMIZED CLAUDE PROMPT (11 seconds, 1 insight, loop ending)
# =============================================================================

SCRIPT_PROMPT = """Create a viral TikTok script for: {topic}

CRITICAL REQUIREMENTS:
- Duration: 11 seconds (9-13 acceptable)
- ONE powerful insight only (NOT 3 tips)
- Hook + Payoff + Loop structure
- Voiceover: 25-40 words maximum

Return ONLY valid JSON:
{{
    "duration_target": 11,
    "hook_text": "5-9 word hook for overlay",
    "voiceover": "25-40 word script with hook, one insight, loop ending",
    "loop_phrase": "Final 2-3 words that loop back",
    "sections": [
        {{"start": 0, "end": 4, "type": "hook", "pexels_keywords": ["keyword1", "keyword2"], "text_overlay": "HOOK"}},
        {{"start": 4, "end": 9, "type": "insight", "pexels_keywords": ["keyword1", "keyword2"], "text_overlay": "INSIGHT"}},
        {{"start": 9, "end": 11, "type": "loop", "pexels_keywords": ["keyword1", "keyword2"], "text_overlay": ""}}
    ]
}}

Focus: Psychology/self-improvement
Hook must grab attention in 2 seconds
Loop ending makes viewers rewatch
Keywords must work for vertical video"""


# =============================================================================
# PIPELINE STAGES (Idempotent)
# =============================================================================

class Pipeline:
    def __init__(self, base_dir: str):
        self.base_dir = Path(base_dir)
        self.claude = Anthropic(api_key=os.environ['ANTHROPIC_API_KEY'])
        self.elevenlabs = ElevenLabs(api_key=os.environ['ELEVENLABS_API_KEY'])
        self.pexels = PexelsClient(os.environ['PEXELS_API_KEY'])
        self.queue = JobQueue(base_dir + "/queue")

    def _path(self, subdir: str, job_id: str, ext: str) -> Path:
        return self.base_dir / subdir / f"{job_id}{ext}"

    # Stage A: Script Generation
    def stage_script(self, job_id: str, topic: str, force: bool = False) -> bool:
        path = self._path("scripts", job_id, ".json")
        if path.exists() and not force:
            print(f"  [Script] ✓ Already exists")
            return True

        print(f"  [Script] Generating with Claude...")
        try:
            resp = self.claude.messages.create(
                model="claude-sonnet-4-20250514",
                max_tokens=1000,
                messages=[{"role": "user", "content": SCRIPT_PROMPT.format(topic=topic)}]
            )
            match = re.search(r'\\{.*\\}', resp.content[0].text, re.DOTALL)
            if not match:
                return False
            data = json.loads(match.group())
            data["job_id"] = job_id
            data["topic"] = topic
            with open(path, 'w') as f:
                json.dump(data, f, indent=2)
            print(f"  [Script] ✓ Generated ({len(data.get('voiceover', ''))} chars)")
            return True
        except Exception as e:
            print(f"  [Script] ✗ Error: {e}")
            return False

    # Stage B: Voice Generation
    def stage_voice(self, job_id: str, force: bool = False) -> bool:
        script_path = self._path("scripts", job_id, ".json")
        audio_path = self._path("audio", job_id, ".mp3")

        if audio_path.exists() and not force:
            print(f"  [Voice] ✓ Already exists")
            return True

        if not script_path.exists():
            print(f"  [Voice] ✗ No script found")
            return False

        print(f"  [Voice] Generating with ElevenLabs...")
        try:
            with open(script_path) as f:
                script = json.load(f)
            audio = self.elevenlabs.text_to_speech.convert(
                voice_id="pNInz6obpgDQGcFmaJgB",
                text=script["voiceover"],
                model_id="eleven_multilingual_v2",
                output_format="mp3_44100_128"
            )
            with open(audio_path, "wb") as f:
                for chunk in audio:
                    f.write(chunk)
            print(f"  [Voice] ✓ Generated")
            return True
        except Exception as e:
            print(f"  [Voice] ✗ Error: {e}")
            return False

    # Stage C: Footage Download
    def stage_footage(self, job_id: str, force: bool = False) -> bool:
        script_path = self._path("scripts", job_id, ".json")
        footage_dir = self.base_dir / "footage" / job_id

        manifest_path = footage_dir / "manifest.json"
        if manifest_path.exists() and not force:
            print(f"  [Footage] ✓ Already downloaded")
            return True

        if not script_path.exists():
            print(f"  [Footage] ✗ No script found")
            return False

        print(f"  [Footage] Downloading from Pexels...")
        footage_dir.mkdir(parents=True, exist_ok=True)

        with open(script_path) as f:
            script = json.load(f)

        downloaded = []
        for i, sec in enumerate(script.get("sections", [])):
            clip_path = footage_dir / f"clip_{i:02d}.mp4"
            if clip_path.exists() and not force:
                downloaded.append({"index": i, "path": str(clip_path),
                                   "duration": sec["end"] - sec["start"]})
                continue

            query = " ".join(sec.get("pexels_keywords", ["person"])[:2])
            videos = self.pexels.search(query)
            if videos and self.pexels.download(videos[0], str(clip_path)):
                downloaded.append({"index": i, "path": str(clip_path),
                                   "duration": sec["end"] - sec["start"]})
            time.sleep(0.5)  # Rate limit

        with open(manifest_path, 'w') as f:
            json.dump({"job_id": job_id, "downloaded": downloaded}, f)

        print(f"  [Footage] ✓ Downloaded {len(downloaded)}/{len(script.get('sections', []))} clips")
        return len(downloaded) > 0

    # Stage D: Video Render
    def stage_render(self, job_id: str, force: bool = False, draft: bool = False) -> bool:
        from moviepy.editor import (VideoFileClip, AudioFileClip, TextClip,
                                    CompositeVideoClip, concatenate_videoclips)

        video_path = self._path("videos", job_id, ".mp4")
        if video_path.exists() and not force:
            print(f"  [Render] ✓ Already rendered")
            return True

        script_path = self._path("scripts", job_id, ".json")
        audio_path = self._path("audio", job_id, ".mp3")
        manifest_path = self.base_dir / "footage" / job_id / "manifest.json"

        for p, name in [(script_path, "script"), (audio_path, "audio"), (manifest_path, "footage")]:
            if not p.exists():
                print(f"  [Render] ✗ Missing {name}")
                return False

        print(f"  [Render] Assembling video...")
        try:
            with open(script_path) as f:
                script = json.load(f)
            with open(manifest_path) as f:
                manifest = json.load(f)

            audio = AudioFileClip(str(audio_path))
            clips = []

            for item in manifest["downloaded"]:
                clip = VideoFileClip(item["path"])
                dur = item["duration"]
                clip = clip.subclip(0, min(dur, clip.duration)) if clip.duration > dur else clip.loop(duration=dur)
                clip = clip.resize(height=1920)
                if clip.w > 1080:
                    clip = clip.crop(x_center=clip.w/2, width=1080, height=1920)
                clips.append(clip)

            video = concatenate_videoclips(clips, method="compose")
            if video.duration > audio.duration:
                video = video.subclip(0, audio.duration)
            video = video.set_audio(audio)

            # Add text overlays
            texts = []
            sections = script.get("sections", [])
            for i, sec in enumerate(sections[:len(clips)]):
                text = sec.get("text_overlay", "")
                if text:
                    try:
                        txt = TextClip(text, fontsize=60, color='white',
                                       font='DejaVu-Sans-Bold', stroke_color='black',
                                       stroke_width=2, method='label')
                        txt = txt.set_position('center').set_start(sec["start"]).set_duration(sec["end"]-sec["start"])
                        texts.append(txt)
                    except:
                        pass

            if texts:
                video = CompositeVideoClip([video] + texts)

            fps = 24 if draft else 30
            bitrate = '2000k' if draft else '5000k'
            preset = 'ultrafast' if draft else 'medium'

            video.write_videofile(str(video_path), fps=fps, codec='libx264',
                                  audio_codec='aac', bitrate=bitrate, preset=preset,
                                  threads=4, verbose=False, logger=None)

            video.close()
            audio.close()
            for c in clips:
                c.close()

            print(f"  [Render] ✓ Complete ({video.duration:.1f}s)")
            return True

        except Exception as e:
            print(f"  [Render] ✗ Error: {e}")
            import traceback
            traceback.print_exc()
            return False

    # Full pipeline for single job
    def run_job(self, job: Job, force: bool = False, draft: bool = False) -> bool:
        print(f"\\n{'='*60}")
        print(f"🎬 JOB: {job.job_id}")
        print(f"📝 Topic: {job.topic}")
        print('='*60)

        stages = [
            ("script", lambda: self.stage_script(job.job_id, job.topic, force), JobStatus.SCRIPTED),
            ("voice", lambda: self.stage_voice(job.job_id, force), JobStatus.VOICED),
            ("footage", lambda: self.stage_footage(job.job_id, force), JobStatus.FOOTAGE_READY),
            ("render", lambda: self.stage_render(job.job_id, force, draft), JobStatus.RENDERED),
        ]

        for name, func, next_status in stages:
            if not func():
                self.queue.update_status(job.job_id, JobStatus.FAILED, f"Failed at {name}")
                print(f"\\n❌ Job failed at stage: {name}")
                return False
            self.queue.update_status(job.job_id, next_status)

        print(f"\\n✅ Job complete: {self._path('videos', job.job_id, '.mp4')}")
        return True

    # Batch processing
    def run_batch(self, max_jobs: int = 10, force: bool = False, draft: bool = False) -> Dict:
        print(f"\\n🚀 Starting batch run (max {max_jobs} jobs)")
        results = {"completed": [], "failed": []}

        for i in range(max_jobs):
            job = self.queue.get_next([JobStatus.NEW])
            if not job:
                print("\\nNo more jobs in queue")
                break

            success = self.run_job(job, force, draft)
            if success:
                results["completed"].append(job.job_id)
            else:
                results["failed"].append(job.job_id)

            # Random delay between jobs
            if i < max_jobs - 1:
                delay = random.uniform(1, 3)
                time.sleep(delay)

        print(f"\\n{'='*60}")
        print(f"📊 BATCH COMPLETE")
        print(f"  ✅ Completed: {len(results['completed'])}")
        print(f"  ❌ Failed: {len(results['failed'])}")
        print('='*60)
        return results

    # Parallel script generation
    def parallel_scripts(self, topics: List[str], workers: int = 5) -> List[str]:
        print(f"\\n⚡ Generating {len(topics)} scripts in parallel...")
        jobs = self.queue.add_topics(topics)

        with ThreadPoolExecutor(max_workers=workers) as ex:
            futures = {ex.submit(self.stage_script, j.job_id, j.topic): j for j in jobs}
            for future in as_completed(futures):
                job = futures[future]
                if future.result():
                    self.queue.update_status(job.job_id, JobStatus.SCRIPTED)
                    print(f"  ✓ {job.job_id}")

        return [j.job_id for j in jobs]


# Initialize pipeline
pipeline = Pipeline(os.environ['BASE_DIR'])

print("=" * 60)
print("✅ PIPELINE FACTORY LOADED!")
print("=" * 60)
print("\\nAvailable commands:")
print("  pipeline.queue.add_topics(['topic1', 'topic2', ...])  # Add topics")
print("  pipeline.queue.get_stats()                            # View queue status")
print("  pipeline.run_batch(max_jobs=10)                       # Process queue")
print("  pipeline.parallel_scripts(['t1', 't2', ...])          # Parallel scripts")
print("\\n👉 Run Cell 3 to add topics, or Cell 4 for quick single video")
'''

# =============================================================================
# CELL 3: BATCH MODE (Add topics and process)
# =============================================================================

CELL_3_BATCH = '''
# ============================================
# 📋 BATCH MODE - Add topics and process
# ============================================

# ✏️ ADD YOUR TOPICS HERE ✏️
topics = [
    "the psychology of mirroring behavior",
    "why silence makes you more powerful",
    "the eye contact trick that changes everything",
    "what your body language reveals about you",
    "the first impression hack nobody talks about",
    "how to read people instantly",
    "the confidence signal that can't be faked",
    "why charismatic people never do this",
    "the subtle sign someone is manipulating you",
    "what high-status people do differently",
]

# Add topics to queue
print(f"\\n📋 Adding {len(topics)} topics to queue...")
jobs = pipeline.queue.add_topics(topics)
print(f"✅ Added {len(jobs)} new topics")

# Show queue status
stats = pipeline.queue.get_stats()
print(f"\\n📊 Queue Status:")
for status, count in stats.items():
    print(f"  {status}: {count}")

print("\\n" + "="*60)
print("👉 Run the next cell to process the queue")
print("="*60)
'''

# =============================================================================
# CELL 4: PROCESS QUEUE
# =============================================================================

CELL_4_PROCESS = '''
# ============================================
# 🎬 PROCESS QUEUE
# ============================================

# Configuration
MAX_JOBS = 10        # How many videos to generate
DRAFT_MODE = False   # True = faster but lower quality
FORCE = False        # True = regenerate even if exists

print(f"\\n🚀 Processing up to {MAX_JOBS} jobs...")
print(f"   Draft mode: {DRAFT_MODE}")
print(f"   Force regenerate: {FORCE}")

# Process!
results = pipeline.run_batch(
    max_jobs=MAX_JOBS,
    force=FORCE,
    draft=DRAFT_MODE
)

# Final report
print(f"\\n{'='*60}")
print("📊 FINAL REPORT")
print('='*60)
stats = pipeline.queue.get_stats()
for status, count in stats.items():
    print(f"  {status}: {count}")
'''

# =============================================================================
# CELL 5: QUICK SINGLE VIDEO
# =============================================================================

CELL_5_SINGLE = '''
# ============================================
# 🎬 QUICK SINGLE VIDEO
# For when you just want one video fast
# ============================================

# ✏️ CHANGE THIS TOPIC ✏️
topic = "why silence makes you more powerful"

# Generate
print(f"\\n🎬 Generating video for: {topic}")
jobs = pipeline.queue.add_topics([topic])
if jobs:
    pipeline.run_job(jobs[0], draft=True)  # draft=True for speed
'''

# =============================================================================
# CELL 6: PARALLEL GENERATION (Advanced)
# =============================================================================

CELL_6_PARALLEL = '''
# ============================================
# ⚡ PARALLEL GENERATION (Advanced)
# Generate scripts and voices in parallel, then render sequentially
# ============================================

topics = [
    "the psychology of mirroring",
    "power of strategic silence",
    "eye contact dominance tricks",
    "reading body language secrets",
    "first impression psychology",
]

print(f"\\n⚡ PARALLEL PIPELINE for {len(topics)} topics")
print("="*60)

# Stage 1: Parallel script generation
print("\\n[1/4] 📝 Generating scripts in parallel...")
job_ids = pipeline.parallel_scripts(topics, workers=5)
time.sleep(1)

# Stage 2: Parallel voice generation
print("\\n[2/4] 🎤 Generating voices in parallel...")
with ThreadPoolExecutor(max_workers=3) as ex:
    futures = {ex.submit(pipeline.stage_voice, jid): jid for jid in job_ids}
    for future in as_completed(futures):
        jid = futures[future]
        if future.result():
            pipeline.queue.update_status(jid, JobStatus.VOICED)
            print(f"  ✓ {jid}")

# Stage 3: Parallel footage download
print("\\n[3/4] 🎬 Downloading footage in parallel...")
with ThreadPoolExecutor(max_workers=3) as ex:
    futures = {ex.submit(pipeline.stage_footage, jid): jid for jid in job_ids}
    for future in as_completed(futures):
        jid = futures[future]
        if future.result():
            pipeline.queue.update_status(jid, JobStatus.FOOTAGE_READY)
            print(f"  ✓ {jid}")

# Stage 4: Sequential rendering (CPU heavy)
print("\\n[4/4] ✂️ Rendering videos sequentially...")
for jid in job_ids:
    if pipeline.stage_render(jid, draft=True):
        pipeline.queue.update_status(jid, JobStatus.RENDERED)

print("\\n" + "="*60)
print("✅ PARALLEL PIPELINE COMPLETE!")
stats = pipeline.queue.get_stats()
print(f"  Rendered: {stats.get('RENDERED', 0)} videos")
print("="*60)
'''

# =============================================================================
# CELL 7: TOPIC GENERATOR
# =============================================================================

CELL_7_TOPICS = '''
# ============================================
# 🎯 TOPIC GENERATOR
# Auto-generate viral topic ideas
# ============================================

import random

THEMES = [
    "mirroring behavior", "silence in conversations", "eye contact",
    "body language", "first impressions", "status signals",
    "confidence tricks", "charisma secrets", "manipulation detection",
    "social dominance", "likability hacks", "persuasion techniques",
    "reading people", "emotional intelligence", "power dynamics",
]

HOOKS = [
    "Most people don't realize {theme}",
    "The real reason behind {theme}",
    "What {theme} reveals about you",
    "The {theme} trick that changes everything",
    "Why {theme} makes you instantly more powerful",
    "What high-status people know about {theme}",
]

def generate_topics(count: int = 20) -> list:
    topics = []
    used_themes = set()
    while len(topics) < count and len(used_themes) < len(THEMES):
        theme = random.choice(THEMES)
        if theme in used_themes:
            continue
        used_themes.add(theme)
        hook = random.choice(HOOKS).format(theme=theme)
        topics.append(hook)
    return topics

# Generate 20 topics
topics = generate_topics(20)
print("🎯 GENERATED TOPICS:")
print("="*60)
for i, t in enumerate(topics, 1):
    print(f"{i:2}. {t}")

print("\\n" + "="*60)
print("To add these to the queue, run:")
print("  pipeline.queue.add_topics(topics)")
'''

# =============================================================================
# CELL 8: STATUS & DOWNLOADS
# =============================================================================

CELL_8_STATUS = '''
# ============================================
# 📊 STATUS & DOWNLOADS
# ============================================

import os
from google.colab import files

# Show queue status
print("📊 QUEUE STATUS:")
print("="*60)
stats = pipeline.queue.get_stats()
for status, count in stats.items():
    print(f"  {status}: {count}")

# List completed videos
print("\\n📁 COMPLETED VIDEOS:")
print("="*60)
videos_dir = f"{os.environ['BASE_DIR']}/videos"
if os.path.exists(videos_dir):
    videos = [f for f in os.listdir(videos_dir) if f.endswith('.mp4')]
    for v in sorted(videos)[-10:]:  # Last 10
        path = f"{videos_dir}/{v}"
        size_mb = os.path.getsize(path) / (1024*1024)
        print(f"  {v} ({size_mb:.1f} MB)")

    # Download option
    if videos:
        print("\\n📥 To download a video, run:")
        print(f'  files.download("{videos_dir}/[filename].mp4")')
'''


# =============================================================================
# Print all cells for easy copying
# =============================================================================

if __name__ == "__main__":
    print("=" * 70)
    print("LAUGHHACKDAILY COLAB NOTEBOOK - COPY THESE CELLS")
    print("=" * 70)

    cells = [
        ("CELL 1: SETUP", CELL_1_SETUP),
        ("CELL 2: PIPELINE CODE", CELL_2_PIPELINE),
        ("CELL 3: BATCH MODE", CELL_3_BATCH),
        ("CELL 4: PROCESS QUEUE", CELL_4_PROCESS),
        ("CELL 5: QUICK SINGLE VIDEO", CELL_5_SINGLE),
        ("CELL 6: PARALLEL GENERATION", CELL_6_PARALLEL),
        ("CELL 7: TOPIC GENERATOR", CELL_7_TOPICS),
        ("CELL 8: STATUS & DOWNLOADS", CELL_8_STATUS),
    ]

    for name, code in cells:
        print(f"\n{'#' * 70}")
        print(f"# {name}")
        print('#' * 70)
        print(code)
