#!/usr/bin/env python3
"""
LaughHackDaily Agent - TikTok Video Production Pipeline

Usage:
    python main.py --help
    python main.py add-topics "topic1" "topic2" "topic3"
    python main.py run --max-jobs 10 --draft
    python main.py status
    python main.py generate-topics 20
"""

import argparse
import os
import sys
from pathlib import Path


def get_pipeline():
    """Initialize and return the pipeline controller."""
    # Check for required environment variables
    required_vars = ['ANTHROPIC_API_KEY', 'ELEVENLABS_API_KEY', 'PEXELS_API_KEY']
    missing = [v for v in required_vars if not os.environ.get(v)]
    if missing:
        print(f"Error: Missing environment variables: {', '.join(missing)}")
        print("\nSet them with:")
        for v in missing:
            print(f"  export {v}='your-key-here'")
        sys.exit(1)

    from anthropic import Anthropic
    from elevenlabs.client import ElevenLabs
    from scripts.pipeline_controller import PipelineController

    base_dir = os.environ.get('BASE_DIR', './output')

    return PipelineController(
        base_dir=base_dir,
        claude_client=Anthropic(api_key=os.environ['ANTHROPIC_API_KEY']),
        elevenlabs_client=ElevenLabs(api_key=os.environ['ELEVENLABS_API_KEY']),
        pexels_api_key=os.environ['PEXELS_API_KEY']
    )


def cmd_add_topics(args):
    """Add topics to the job queue."""
    pipeline = get_pipeline()
    jobs = pipeline.add_topics(args.topics)
    print(f"Added {len(jobs)} topics to queue:")
    for job in jobs:
        print(f"  - {job.job_id}: {job.topic[:50]}...")


def cmd_run(args):
    """Process jobs from the queue."""
    pipeline = get_pipeline()

    if args.parallel:
        # Run optimized parallel batch
        topics = [j.topic for j in pipeline.queue.get_jobs_by_status("NEW")]
        if not topics:
            print("No NEW jobs in queue")
            return
        results = pipeline.run_optimized_batch(
            topics[:args.max_jobs],
            draft_mode=args.draft
        )
    else:
        # Run sequential batch
        results = pipeline.run_jobs(
            max_jobs=args.max_jobs,
            force=args.force,
            draft_mode=args.draft
        )

    print(f"\nCompleted: {len(results.get('completed', []))}")
    print(f"Failed: {len(results.get('failed', []))}")


def cmd_status(args):
    """Show queue status."""
    pipeline = get_pipeline()
    print(pipeline.generate_report())


def cmd_generate_topics(args):
    """Generate topic ideas."""
    from scripts.topic_generator import TopicGenerator

    generator = TopicGenerator()
    topics = generator.generate_batch(args.count)

    print(f"Generated {len(topics)} topics:\n")
    for i, t in enumerate(topics, 1):
        print(f"{i:2}. {t['topic']}")
        print(f"    Theme: {t['theme']}, Angle: {t['angle']}\n")


def cmd_reset_failed(args):
    """Reset failed jobs for retry."""
    pipeline = get_pipeline()
    count = pipeline.reset_failed(args.max_attempts)
    print(f"Reset {count} failed jobs")


def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(
        description="LaughHackDaily TikTok Video Production Pipeline",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Add topics to queue
  python main.py add-topics "mirroring behavior" "eye contact tricks"

  # Run pipeline with 10 jobs
  python main.py run --max-jobs 10

  # Run with parallel processing in draft mode
  python main.py run --parallel --draft

  # Check status
  python main.py status

  # Generate topic ideas
  python main.py generate-topics 20
        """
    )

    subparsers = parser.add_subparsers(dest='command', help='Available commands')

    # add-topics
    p_add = subparsers.add_parser('add-topics', help='Add topics to queue')
    p_add.add_argument('topics', nargs='+', help='Topics to add')
    p_add.set_defaults(func=cmd_add_topics)

    # run
    p_run = subparsers.add_parser('run', help='Process jobs from queue')
    p_run.add_argument('--max-jobs', type=int, default=10, help='Max jobs to process')
    p_run.add_argument('--draft', action='store_true', help='Use draft quality for speed')
    p_run.add_argument('--force', action='store_true', help='Force regenerate all stages')
    p_run.add_argument('--parallel', action='store_true', help='Use parallel processing')
    p_run.set_defaults(func=cmd_run)

    # status
    p_status = subparsers.add_parser('status', help='Show queue status')
    p_status.set_defaults(func=cmd_status)

    # generate-topics
    p_gen = subparsers.add_parser('generate-topics', help='Generate topic ideas')
    p_gen.add_argument('count', type=int, nargs='?', default=20, help='Number of topics')
    p_gen.set_defaults(func=cmd_generate_topics)

    # reset-failed
    p_reset = subparsers.add_parser('reset-failed', help='Reset failed jobs for retry')
    p_reset.add_argument('--max-attempts', type=int, default=3, help='Max attempts before permanent failure')
    p_reset.set_defaults(func=cmd_reset_failed)

    args = parser.parse_args()

    if not args.command:
        parser.print_help()
        return

    args.func(args)


if __name__ == "__main__":
    main()
