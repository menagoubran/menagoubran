"""
Pipeline Controller for LaughHackDaily Video Production
Orchestrates job execution with parallel processing, resume, and batch support.
"""

import os
import time
import random
import logging
from datetime import datetime
from pathlib import Path
from typing import Optional, List, Dict, Callable
from concurrent.futures import ThreadPoolExecutor, as_completed

from .job_queue import JobQueue, JobStatus, Job
from .pipeline_stages import (
    PipelineConfig, StageResult, PexelsClient,
    stage_script, stage_voice, stage_footage, stage_render
)


class PipelineController:
    """
    Orchestrates the video production pipeline.
    Supports batch processing, parallelism, and automatic resume.
    """

    def __init__(
        self,
        base_dir: str,
        claude_client,
        elevenlabs_client,
        pexels_api_key: str,
        worker_id: Optional[str] = None,
        log_level: int = logging.INFO
    ):
        self.config = PipelineConfig(base_dir)
        self.queue = JobQueue(os.path.join(base_dir, "queue"))
        self.claude = claude_client
        self.elevenlabs = elevenlabs_client
        self.pexels = PexelsClient(pexels_api_key)
        self.worker_id = worker_id or f"worker_{datetime.now().strftime('%H%M%S')}"

        # Setup logging
        self.logger = logging.getLogger(f"Pipeline-{self.worker_id}")
        self.logger.setLevel(log_level)
        if not self.logger.handlers:
            handler = logging.StreamHandler()
            handler.setFormatter(logging.Formatter(
                '%(asctime)s [%(name)s] %(levelname)s: %(message)s'
            ))
            self.logger.addHandler(handler)

            # File handler
            log_file = self.config.logs_dir / f"{self.worker_id}.log"
            file_handler = logging.FileHandler(log_file)
            file_handler.setFormatter(logging.Formatter(
                '%(asctime)s [%(levelname)s] %(message)s'
            ))
            self.logger.addHandler(file_handler)

    # =========================================================================
    # Single Job Execution
    # =========================================================================

    def run_single_job(
        self,
        job: Job,
        force: bool = False,
        draft_mode: bool = False
    ) -> Dict:
        """
        Execute all pipeline stages for a single job.
        Automatically resumes from the last successful stage.
        """
        job_id = job.job_id
        topic = job.topic
        results = {"job_id": job_id, "topic": topic, "stages": {}}

        self.logger.info(f"Starting job: {job_id} - {topic}")

        # Determine starting stage based on existing outputs
        start_stage = self._determine_start_stage(job_id, force)
        self.logger.info(f"Starting from stage: {start_stage}")

        # Stage A: Script
        if start_stage <= 1:
            self.queue.update_job_status(job_id, JobStatus.IN_PROGRESS.value)
            result = stage_script(job_id, topic, self.config, self.claude, force)
            results["stages"]["script"] = result.to_dict()
            if not result.success:
                self._handle_stage_failure(job_id, "script", result.error)
                return results
            self.queue.update_job_status(job_id, JobStatus.SCRIPTED.value)
            self.logger.info(f"[{job_id}] Script generated")

        # Stage B: Voice
        if start_stage <= 2:
            result = stage_voice(job_id, self.config, self.elevenlabs, force=force)
            results["stages"]["voice"] = result.to_dict()
            if not result.success:
                self._handle_stage_failure(job_id, "voice", result.error)
                return results
            self.queue.update_job_status(job_id, JobStatus.VOICED.value)
            self.logger.info(f"[{job_id}] Voice generated")

        # Stage C: Footage
        if start_stage <= 3:
            result = stage_footage(job_id, self.config, self.pexels, force=force)
            results["stages"]["footage"] = result.to_dict()
            if not result.success:
                self._handle_stage_failure(job_id, "footage", result.error)
                return results
            self.queue.update_job_status(job_id, JobStatus.FOOTAGE_READY.value)
            self.logger.info(f"[{job_id}] Footage downloaded")

        # Stage D: Render
        result = stage_render(job_id, self.config, force=force, draft_mode=draft_mode)
        results["stages"]["render"] = result.to_dict()
        if not result.success:
            self._handle_stage_failure(job_id, "render", result.error)
            return results

        self.queue.update_job_status(job_id, JobStatus.RENDERED.value)
        self.logger.info(f"[{job_id}] Video rendered: {result.output_path}")

        results["success"] = True
        results["output_path"] = result.output_path
        return results

    def _determine_start_stage(self, job_id: str, force: bool) -> int:
        """Determine which stage to start from based on existing outputs."""
        if force:
            return 1

        # Check outputs in reverse order
        if self.config.get_video_path(job_id).exists():
            return 5  # Already complete
        if self.config.get_footage_dir(job_id).exists():
            return 4  # Start at render
        if self.config.get_audio_path(job_id).exists():
            return 3  # Start at footage
        if self.config.get_script_path(job_id).exists():
            return 2  # Start at voice

        return 1  # Start from beginning

    def _handle_stage_failure(self, job_id: str, stage: str, error: str):
        """Handle a stage failure."""
        self.logger.error(f"[{job_id}] Stage '{stage}' failed: {error}")
        self.queue.update_job_status(
            job_id,
            JobStatus.FAILED.value,
            error_message=f"Stage {stage}: {error}"
        )

    # =========================================================================
    # Batch Execution
    # =========================================================================

    def run_jobs(
        self,
        max_jobs: int = 10,
        start_from: str = "NEW",
        force: bool = False,
        draft_mode: bool = False,
        rate_limit_delay: tuple = (1.0, 3.0)
    ) -> Dict:
        """
        Run multiple jobs from the queue.

        Args:
            max_jobs: Maximum number of jobs to process
            start_from: Job status to start from (NEW, SCRIPTED, etc.)
            force: Force regeneration of all stages
            draft_mode: Use draft quality for faster rendering
            rate_limit_delay: (min, max) seconds to wait between jobs

        Returns:
            Summary of processed jobs
        """
        self.logger.info(f"Starting batch run: max_jobs={max_jobs}, start_from={start_from}")

        # Clean up stale locks first
        cleaned = self.queue.cleanup_stale_locks()
        if cleaned:
            self.logger.info(f"Cleaned up {cleaned} stale locks")

        # Determine which statuses to process
        status_map = {
            "NEW": [JobStatus.NEW.value],
            "SCRIPTED": [JobStatus.SCRIPTED.value],
            "VOICED": [JobStatus.VOICED.value],
            "FOOTAGE_READY": [JobStatus.FOOTAGE_READY.value],
            "ALL_INCOMPLETE": [
                JobStatus.NEW.value,
                JobStatus.SCRIPTED.value,
                JobStatus.VOICED.value,
                JobStatus.FOOTAGE_READY.value
            ]
        }
        statuses = status_map.get(start_from, [JobStatus.NEW.value])

        results = {
            "completed": [],
            "failed": [],
            "skipped": [],
            "total_processed": 0
        }

        for i in range(max_jobs):
            # Get next job
            job = self.queue.get_next_job(self.worker_id, statuses)
            if not job:
                self.logger.info("No more jobs available")
                break

            self.logger.info(f"Processing job {i + 1}/{max_jobs}: {job.job_id}")

            try:
                result = self.run_single_job(job, force=force, draft_mode=draft_mode)
                if result.get("success"):
                    results["completed"].append({
                        "job_id": job.job_id,
                        "topic": job.topic,
                        "output": result.get("output_path")
                    })
                else:
                    results["failed"].append({
                        "job_id": job.job_id,
                        "topic": job.topic,
                        "error": result.get("stages", {})
                    })
            except Exception as e:
                self.logger.exception(f"Unexpected error processing job {job.job_id}")
                self.queue.update_job_status(
                    job.job_id,
                    JobStatus.FAILED.value,
                    error_message=str(e)
                )
                results["failed"].append({
                    "job_id": job.job_id,
                    "topic": job.topic,
                    "error": str(e)
                })

            results["total_processed"] += 1

            # Rate limiting between jobs
            if i < max_jobs - 1:
                delay = random.uniform(*rate_limit_delay)
                self.logger.debug(f"Waiting {delay:.1f}s before next job")
                time.sleep(delay)

        self.logger.info(
            f"Batch complete: {len(results['completed'])} completed, "
            f"{len(results['failed'])} failed"
        )

        return results

    # =========================================================================
    # Parallel Processing (Early Stages Only)
    # =========================================================================

    def run_parallel_scripts(
        self,
        topics: List[str],
        max_workers: int = 5
    ) -> List[Dict]:
        """
        Generate scripts for multiple topics in parallel.
        Safe to parallelize as it's just API calls.
        """
        self.logger.info(f"Generating {len(topics)} scripts in parallel")

        # Add jobs to queue first
        jobs = self.queue.add_jobs_batch(topics)

        results = []
        with ThreadPoolExecutor(max_workers=max_workers) as executor:
            futures = {
                executor.submit(
                    stage_script,
                    job.job_id,
                    job.topic,
                    self.config,
                    self.claude
                ): job
                for job in jobs
            }

            for future in as_completed(futures):
                job = futures[future]
                try:
                    result = future.result()
                    if result.success:
                        self.queue.update_job_status(job.job_id, JobStatus.SCRIPTED.value)
                    results.append({
                        "job_id": job.job_id,
                        "topic": job.topic,
                        "success": result.success,
                        "error": result.error
                    })
                except Exception as e:
                    results.append({
                        "job_id": job.job_id,
                        "topic": job.topic,
                        "success": False,
                        "error": str(e)
                    })

        return results

    def run_parallel_voices(
        self,
        job_ids: Optional[List[str]] = None,
        max_workers: int = 3
    ) -> List[Dict]:
        """
        Generate voices for multiple jobs in parallel.
        If job_ids not provided, processes all SCRIPTED jobs.
        """
        if job_ids is None:
            jobs = self.queue.get_jobs_by_status(JobStatus.SCRIPTED.value)
            job_ids = [j.job_id for j in jobs]

        self.logger.info(f"Generating {len(job_ids)} voices in parallel")

        results = []
        with ThreadPoolExecutor(max_workers=max_workers) as executor:
            futures = {
                executor.submit(
                    stage_voice,
                    job_id,
                    self.config,
                    self.elevenlabs
                ): job_id
                for job_id in job_ids
            }

            for future in as_completed(futures):
                job_id = futures[future]
                try:
                    result = future.result()
                    if result.success:
                        self.queue.update_job_status(job_id, JobStatus.VOICED.value)
                    results.append({
                        "job_id": job_id,
                        "success": result.success,
                        "error": result.error
                    })
                except Exception as e:
                    results.append({
                        "job_id": job_id,
                        "success": False,
                        "error": str(e)
                    })

        return results

    def run_parallel_footage(
        self,
        job_ids: Optional[List[str]] = None,
        max_workers: int = 3
    ) -> List[Dict]:
        """
        Download footage for multiple jobs in parallel.
        If job_ids not provided, processes all VOICED jobs.
        """
        if job_ids is None:
            jobs = self.queue.get_jobs_by_status(JobStatus.VOICED.value)
            job_ids = [j.job_id for j in jobs]

        self.logger.info(f"Downloading footage for {len(job_ids)} jobs in parallel")

        results = []
        with ThreadPoolExecutor(max_workers=max_workers) as executor:
            futures = {
                executor.submit(
                    stage_footage,
                    job_id,
                    self.config,
                    self.pexels
                ): job_id
                for job_id in job_ids
            }

            for future in as_completed(futures):
                job_id = futures[future]
                try:
                    result = future.result()
                    if result.success:
                        self.queue.update_job_status(job_id, JobStatus.FOOTAGE_READY.value)
                    results.append({
                        "job_id": job_id,
                        "success": result.success,
                        "error": result.error
                    })
                except Exception as e:
                    results.append({
                        "job_id": job_id,
                        "success": False,
                        "error": str(e)
                    })

        return results

    def run_sequential_renders(
        self,
        job_ids: Optional[List[str]] = None,
        draft_mode: bool = False,
        max_concurrent: int = 1
    ) -> List[Dict]:
        """
        Render videos sequentially (or with limited concurrency).
        Rendering is CPU-heavy, so we limit parallelism.
        """
        if job_ids is None:
            jobs = self.queue.get_jobs_by_status(JobStatus.FOOTAGE_READY.value)
            job_ids = [j.job_id for j in jobs]

        self.logger.info(f"Rendering {len(job_ids)} videos (max_concurrent={max_concurrent})")

        results = []
        with ThreadPoolExecutor(max_workers=max_concurrent) as executor:
            futures = {
                executor.submit(
                    stage_render,
                    job_id,
                    self.config,
                    draft_mode=draft_mode
                ): job_id
                for job_id in job_ids
            }

            for future in as_completed(futures):
                job_id = futures[future]
                try:
                    result = future.result()
                    if result.success:
                        self.queue.update_job_status(job_id, JobStatus.RENDERED.value)
                    results.append({
                        "job_id": job_id,
                        "success": result.success,
                        "output": result.output_path,
                        "error": result.error
                    })
                except Exception as e:
                    results.append({
                        "job_id": job_id,
                        "success": False,
                        "error": str(e)
                    })

        return results

    # =========================================================================
    # Full Parallel Pipeline (Optimized)
    # =========================================================================

    def run_optimized_batch(
        self,
        topics: List[str],
        script_workers: int = 5,
        voice_workers: int = 3,
        footage_workers: int = 3,
        render_workers: int = 1,
        draft_mode: bool = False
    ) -> Dict:
        """
        Run the full pipeline with optimized parallelism:
        - Scripts: High parallelism (light API calls)
        - Voices: Medium parallelism (network bound)
        - Footage: Medium parallelism (network bound)
        - Render: Low parallelism (CPU bound)
        """
        self.logger.info(f"Starting optimized batch for {len(topics)} topics")

        results = {
            "scripts": [],
            "voices": [],
            "footage": [],
            "renders": [],
            "summary": {}
        }

        # Stage 1: Generate all scripts in parallel
        self.logger.info("=== Stage 1: Generating scripts ===")
        results["scripts"] = self.run_parallel_scripts(topics, script_workers)
        scripted_ids = [r["job_id"] for r in results["scripts"] if r["success"]]
        self.logger.info(f"Scripts generated: {len(scripted_ids)}/{len(topics)}")

        if not scripted_ids:
            self.logger.error("No scripts generated, aborting")
            return results

        # Stage 2: Generate all voices in parallel
        self.logger.info("=== Stage 2: Generating voices ===")
        results["voices"] = self.run_parallel_voices(scripted_ids, voice_workers)
        voiced_ids = [r["job_id"] for r in results["voices"] if r["success"]]
        self.logger.info(f"Voices generated: {len(voiced_ids)}/{len(scripted_ids)}")

        if not voiced_ids:
            self.logger.error("No voices generated, aborting")
            return results

        # Stage 3: Download all footage in parallel
        self.logger.info("=== Stage 3: Downloading footage ===")
        results["footage"] = self.run_parallel_footage(voiced_ids, footage_workers)
        footage_ids = [r["job_id"] for r in results["footage"] if r["success"]]
        self.logger.info(f"Footage downloaded: {len(footage_ids)}/{len(voiced_ids)}")

        if not footage_ids:
            self.logger.error("No footage downloaded, aborting")
            return results

        # Stage 4: Render videos (limited parallelism)
        self.logger.info("=== Stage 4: Rendering videos ===")
        results["renders"] = self.run_sequential_renders(
            footage_ids,
            draft_mode=draft_mode,
            max_concurrent=render_workers
        )
        rendered_ids = [r["job_id"] for r in results["renders"] if r["success"]]
        self.logger.info(f"Videos rendered: {len(rendered_ids)}/{len(footage_ids)}")

        # Summary
        results["summary"] = {
            "total_topics": len(topics),
            "scripts_generated": len(scripted_ids),
            "voices_generated": len(voiced_ids),
            "footage_downloaded": len(footage_ids),
            "videos_rendered": len(rendered_ids),
            "success_rate": f"{len(rendered_ids) / len(topics) * 100:.1f}%"
        }

        self.logger.info(f"Batch complete: {results['summary']}")
        return results

    # =========================================================================
    # Utility Methods
    # =========================================================================

    def add_topics(self, topics: List[str]) -> List[Job]:
        """Add topics to the job queue."""
        return self.queue.add_jobs_batch(topics)

    def get_status(self) -> Dict:
        """Get current queue status."""
        return self.queue.get_stats()

    def reset_failed(self, max_attempts: int = 3) -> int:
        """Reset failed jobs for retry."""
        return self.queue.reset_failed_jobs(max_attempts)

    def get_completed_videos(self) -> List[Dict]:
        """Get list of all completed videos."""
        jobs = self.queue.get_jobs_by_status(JobStatus.RENDERED.value)
        return [
            {
                "job_id": j.job_id,
                "topic": j.topic,
                "path": str(self.config.get_video_path(j.job_id))
            }
            for j in jobs
        ]

    def generate_report(self) -> str:
        """Generate a summary report of the pipeline status."""
        stats = self.queue.get_stats()
        completed = self.queue.get_jobs_by_status(JobStatus.RENDERED.value)
        failed = self.queue.get_jobs_by_status(JobStatus.FAILED.value)

        report = []
        report.append("=" * 60)
        report.append("LAUGHHACKDAILY PIPELINE REPORT")
        report.append("=" * 60)
        report.append(f"Generated: {datetime.now().isoformat()}")
        report.append(f"Worker ID: {self.worker_id}")
        report.append("")
        report.append("QUEUE STATUS:")
        for status, count in stats.items():
            report.append(f"  {status}: {count}")
        report.append("")
        report.append(f"COMPLETED VIDEOS ({len(completed)}):")
        for job in completed[-10:]:  # Last 10
            report.append(f"  - {job.topic[:40]}")
        report.append("")
        if failed:
            report.append(f"FAILED JOBS ({len(failed)}):")
            for job in failed[-5:]:  # Last 5
                report.append(f"  - {job.topic[:30]}: {job.error_message}")
        report.append("=" * 60)

        return "\n".join(report)
