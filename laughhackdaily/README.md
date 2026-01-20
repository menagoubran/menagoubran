# LaughHackDaily TikTok Automation System

Fully automated TikTok video production system for the faceless psychology channel "LaughHackDaily."

## Features

- **Script Generation** - AI-powered script creation with Claude
- **Voice Synthesis** - Natural voiceovers with ElevenLabs
- **Stock Footage** - Automatic footage download from Pexels
- **Video Editing** - Automated editing with MoviePy
- **Text Overlays** - Dynamic text overlay generation

---

## Quick Start

```bash
# 1. Install dependencies
pip install -r requirements.txt

# 2. Configure API keys (create .env file)
cp .env.example .env
# Edit .env with your API keys

# 3. Run auto-production
python auto_produce.py "body language secrets"
```

---

## Setup Instructions

### 1. Install Dependencies

```bash
cd laughhackdaily
pip install -r requirements.txt
```

Or install manually:
```bash
pip install anthropic elevenlabs python-dotenv moviepy Pillow numpy requests pexels-api
```

### 2. Configure API Keys

Create a `.env` file in the `laughhackdaily/` directory:

```env
ANTHROPIC_API_KEY=sk-ant-api03-...
ELEVENLABS_API_KEY=sk_...
PEXELS_API_KEY=...
```

**Get API Keys:**
- **Anthropic (Claude):** https://console.anthropic.com/
- **ElevenLabs:** https://elevenlabs.io/
- **Pexels:** https://www.pexels.com/api/

### 3. Verify Installation

```bash
python -c "from video_editor import VideoEditor; print('✓ Video editor loaded')"
python -c "from dotenv import load_dotenv; print('✓ Dotenv loaded')"
```

---

## Usage

### Full Auto-Production (Recommended)

```bash
python auto_produce.py "topic here"
```

**Examples:**
```bash
python auto_produce.py "body language secrets"
python auto_produce.py "confidence hacks"
python auto_produce.py "first impression tips"
python auto_produce.py "eye contact techniques"
```

### Script-Only Generation

```bash
python main.py "topic here"
```

This generates a production package (script + instructions) without creating the video.

---

## Output Structure

```
output/
├── audio/
│   └── [topic].mp3              # ElevenLabs voiceover
├── footage/
│   └── [topic]/
│       ├── clip_1.mp4           # Pexels footage
│       ├── clip_2.mp4
│       ├── clip_3.mp4
│       ├── clip_4.mp4
│       └── clip_5.mp4
├── videos/
│   └── [topic].mp4              # FINAL VIDEO
├── [topic]_script.json          # Script data
└── [topic]_results.json         # Production results
```

---

## Directory Structure

```
laughhackdaily/
├── auto_produce.py          # Full auto-production pipeline
├── main.py                  # Script-only generation
├── video_editor.py          # Video editing module
├── requirements.txt         # Python dependencies
├── .env                     # API keys (not in git)
├── AGENT_CONFIG.md          # Agent configuration
├── README.md                # This file
├── templates/               # Script templates
├── docs/                    # Documentation
└── output/                  # Generated content
```

---

## Production Pipeline

The auto-producer runs these phases:

### Phase 1: Script Generation
- Uses Claude API to generate TikTok script
- Creates 5 sections with Pexels keywords
- Outputs JSON with timing information

### Phase 2: Voiceover Generation
- Sends script to ElevenLabs API
- Uses "Adam" voice by default
- Saves MP3 to `output/audio/`

### Phase 3: Footage Download
- Searches Pexels for each section's keywords
- Downloads HD vertical videos
- Saves to `output/footage/[topic]/`

### Phase 4: Video Production
- Combines clips with MoviePy
- Adds voiceover audio
- Overlays text at timestamps
- Applies zoom effects and transitions
- Exports final MP4 to `output/videos/`

---

## Content Guidelines

### The 4 Masks (Content Framing)

| Mask | Usage | Structure |
|------|-------|-----------|
| OBSERVATION | 50% | "Have you noticed how..." |
| SELF-REFLECTION | 30% | "If this keeps happening to you..." |
| SOCIAL PATTERN | 15% | "People tend to do this when..." |
| WARNING | 5% | "Be careful when..." |

### Video Structure

```
0:00-0:05 → Hook (instant scroll-stop)
0:05-0:12 → Point 1 (core value)
0:12-0:20 → Point 2 (elaboration)
0:20-0:27 → Point 3 (key insight)
0:27-0:32 → CTA + Loop trigger
```

### Compliance Rules

**Always:**
- Observation framing
- Self-improvement focus
- Second-person ("you")

**Never:**
- Direct quotes from sources
- Manipulation framing
- Over 35 seconds

---

## Troubleshooting

### "ANTHROPIC_API_KEY not found"
Make sure your `.env` file exists and contains the key:
```bash
cat .env | grep ANTHROPIC
```

### "Failed to download video"
- Check Pexels API key is valid
- Try different search keywords
- Check internet connection

### "No valid clips to process"
- Pexels may not have footage for your keywords
- Try more generic keywords
- Manual clip selection may be needed

### Video export is slow
- MoviePy uses FFmpeg which can be CPU-intensive
- Reduce video quality/bitrate for faster exports
- Consider using GPU acceleration if available

### ElevenLabs rate limit
- Free tier has limited characters/month
- Wait and retry, or upgrade your plan
- Use shorter scripts

---

## API Costs

| Service | Free Tier | Notes |
|---------|-----------|-------|
| Claude | $5 credit | ~100 scripts |
| ElevenLabs | 10k chars/mo | ~10 videos |
| Pexels | Unlimited | Free API |

---

## Success Metrics

Target performance:
- Completion rate > 80%
- Rewatch rate > 10%
- Views > 200 in first 2 hours
- Saves > likes

---

## Commands Reference

| Command | Description |
|---------|-------------|
| `python auto_produce.py "topic"` | Full video production |
| `python main.py "topic"` | Script generation only |
| `python video_editor.py` | Test video editor |

---

## License

For personal use only. Content created is original and does not quote source material directly.
