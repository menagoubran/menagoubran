# LaughHackDaily Agent

A scalable TikTok video production pipeline optimized for Google Colab.

## Features

- **4-Stage Pipeline**: Script → Voice → Footage → Render
- **Job Queue System**: Persistent queue with status tracking
- **Parallel Processing**: Concurrent script/voice/footage generation
- **Idempotent Operations**: Resume from any stage after disconnection
- **Batch Mode**: Process 10-50 videos in one session
- **Multi-Worker Support**: Run multiple Colab tabs pulling from same queue
- **Optimized Format**: 11-second videos with hook + insight + loop structure

## Project Structure

```
laughhackdaily-agent/
├── scripts/
│   ├── __init__.py
│   ├── job_queue.py          # Job queue with status tracking
│   ├── pipeline_stages.py    # 4-stage pipeline functions
│   ├── pipeline_controller.py # Orchestration & parallelism
│   └── topic_generator.py    # Viral topic generation
├── templates/
│   └── colab_notebook.py     # Ready-to-use Colab cells
├── output/                   # Generated files (local)
├── logs/                     # Execution logs
├── main.py                   # CLI entry point
└── requirements.txt
```

## Quick Start (Google Colab)

1. Open Google Colab
2. Copy cells from `templates/colab_notebook.py`
3. Set API keys in Colab Secrets:
   - `ANTHROPIC_API_KEY`
   - `ELEVEN_LABS_API_KEY`
   - `PEXELS_API_KEY`
4. Run Cell 1 (Setup) then Cell 2 (Pipeline Code)
5. Add topics and process!

## Pipeline Stages

| Stage | Output | Parallelizable |
|-------|--------|----------------|
| A: Script (Claude) | `/scripts/{job_id}.json` | Yes (5 workers) |
| B: Voice (ElevenLabs) | `/audio/{job_id}.mp3` | Yes (3 workers) |
| C: Footage (Pexels) | `/footage/{job_id}/` | Yes (3 workers) |
| D: Render (MoviePy) | `/videos/{job_id}.mp4` | Limited (1-2) |

## Job Status Flow

```
NEW → IN_PROGRESS → SCRIPTED → VOICED → FOOTAGE_READY → RENDERED
                                                        ↓
                                                     FAILED
```

## CLI Usage (Local)

```bash
# Set environment variables
export ANTHROPIC_API_KEY='your-key'
export ELEVENLABS_API_KEY='your-key'
export PEXELS_API_KEY='your-key'
export BASE_DIR='./output'

# Add topics to queue
python main.py add-topics "mirroring behavior" "eye contact tricks"

# Process queue
python main.py run --max-jobs 10

# Use parallel processing
python main.py run --parallel --draft

# Check status
python main.py status

# Generate topic ideas
python main.py generate-topics 20

# Reset failed jobs
python main.py reset-failed
```

## Optimized Video Format

The pipeline generates 11-second videos optimized for TikTok retention:

- **Duration**: 9-13 seconds (target: 11s)
- **Structure**: Hook (0-4s) → Insight (4-9s) → Loop (9-11s)
- **Voiceover**: 25-40 words maximum
- **Content**: ONE powerful insight (not 3 tips)
- **Loop Ending**: Final phrase connects back to hook

## Key Improvements Over Original

1. **Idempotency**: Each stage checks for existing outputs before running
2. **Resume**: If Colab disconnects, rerun and it continues from last stage
3. **Parallelism**: Early stages run concurrently, rendering is sequential
4. **Queue System**: Jobs persist in Google Drive, multiple workers supported
5. **Optimized Prompt**: 11-second format instead of 30-second 3-tip format

## Multi-Worker Mode (Scaling)

Open 2-4 Colab tabs, each running:
```python
# Each worker gets a unique ID
results = pipeline.run_batch(max_jobs=5)
```

Workers automatically coordinate via the shared queue file in Google Drive.

## Troubleshooting

**Colab Disconnects**: Just rerun - it resumes from the last completed stage.

**Rate Limits**: Built-in delays between API calls. Adjust `rate_limit_delay`.

**Font Errors**: The pipeline uses DejaVu-Sans-Bold with fallback.

**Memory Errors**: Use `draft=True` for rendering, or process fewer jobs.

## API Requirements

- **Claude API**: Script generation
- **ElevenLabs API**: Voice synthesis
- **Pexels API**: Stock footage (free tier works)

## License

MIT
