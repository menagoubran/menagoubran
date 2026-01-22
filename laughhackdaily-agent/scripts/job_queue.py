"""
Job Queue System for LaughHackDaily Pipeline
Manages job states, persistence, and worker coordination.
"""

import json
import os
import time
from datetime import datetime
from pathlib import Path
from typing import Optional, List, Dict, Any
from enum import Enum
import fcntl


class JobStatus(Enum):
    NEW = "NEW"
    IN_PROGRESS = "IN_PROGRESS"
    SCRIPTED = "SCRIPTED"
    VOICED = "VOICED"
    FOOTAGE_READY = "FOOTAGE_READY"
    RENDERED = "RENDERED"
    FAILED = "FAILED"


class Job:
    """Represents a single video production job."""

    def __init__(
        self,
        job_id: str,
        topic: str,
        status: str = "NEW",
        attempts: int = 0,
        worker_id: Optional[str] = None,
        locked_at: Optional[str] = None,
        created_at: Optional[str] = None,
        updated_at: Optional[str] = None,
        error_message: Optional[str] = None,
        metadata: Optional[Dict] = None
    ):
        self.job_id = job_id
        self.topic = topic
        self.status = status
        self.attempts = attempts
        self.worker_id = worker_id
        self.locked_at = locked_at
        self.created_at = created_at or datetime.now().isoformat()
        self.updated_at = updated_at or datetime.now().isoformat()
        self.error_message = error_message
        self.metadata = metadata or {}

    def to_dict(self) -> Dict[str, Any]:
        return {
            "job_id": self.job_id,
            "topic": self.topic,
            "status": self.status,
            "attempts": self.attempts,
            "worker_id": self.worker_id,
            "locked_at": self.locked_at,
            "created_at": self.created_at,
            "updated_at": self.updated_at,
            "error_message": self.error_message,
            "metadata": self.metadata
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "Job":
        return cls(**data)

    def __repr__(self):
        return f"Job({self.job_id}, {self.topic[:30]}..., {self.status})"


class JobQueue:
    """
    Persistent job queue with file-based storage.
    Supports multiple workers with locking mechanism.
    """

    LOCK_TIMEOUT_MINUTES = 30

    def __init__(self, queue_dir: str):
        self.queue_dir = Path(queue_dir)
        self.queue_file = self.queue_dir / "jobs.jsonl"
        self.lock_file = self.queue_dir / ".queue.lock"
        self._ensure_dirs()

    def _ensure_dirs(self):
        """Create queue directory if it doesn't exist."""
        self.queue_dir.mkdir(parents=True, exist_ok=True)

    def _acquire_lock(self, timeout: int = 10) -> bool:
        """Acquire file lock for thread-safe operations."""
        start = time.time()
        while time.time() - start < timeout:
            try:
                self._lock_fd = open(self.lock_file, 'w')
                fcntl.flock(self._lock_fd.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)
                return True
            except (IOError, OSError):
                time.sleep(0.1)
        return False

    def _release_lock(self):
        """Release file lock."""
        try:
            fcntl.flock(self._lock_fd.fileno(), fcntl.LOCK_UN)
            self._lock_fd.close()
        except:
            pass

    def _read_all_jobs(self) -> List[Job]:
        """Read all jobs from queue file."""
        jobs = []
        if self.queue_file.exists():
            with open(self.queue_file, 'r') as f:
                for line in f:
                    line = line.strip()
                    if line:
                        try:
                            jobs.append(Job.from_dict(json.loads(line)))
                        except json.JSONDecodeError:
                            continue
        return jobs

    def _write_all_jobs(self, jobs: List[Job]):
        """Write all jobs to queue file."""
        with open(self.queue_file, 'w') as f:
            for job in jobs:
                f.write(json.dumps(job.to_dict()) + "\n")

    def add_job(self, topic: str, job_id: Optional[str] = None) -> Job:
        """Add a new job to the queue."""
        if not job_id:
            job_id = datetime.now().strftime("%Y%m%d_%H%M%S") + f"_{hash(topic) % 1000:03d}"

        job = Job(job_id=job_id, topic=topic)

        if self._acquire_lock():
            try:
                jobs = self._read_all_jobs()
                # Check for duplicate
                if not any(j.job_id == job_id for j in jobs):
                    jobs.append(job)
                    self._write_all_jobs(jobs)
            finally:
                self._release_lock()

        return job

    def add_jobs_batch(self, topics: List[str]) -> List[Job]:
        """Add multiple jobs at once."""
        new_jobs = []
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")

        for i, topic in enumerate(topics):
            job_id = f"{timestamp}_{i:03d}"
            new_jobs.append(Job(job_id=job_id, topic=topic))

        if self._acquire_lock():
            try:
                jobs = self._read_all_jobs()
                existing_ids = {j.job_id for j in jobs}
                for job in new_jobs:
                    if job.job_id not in existing_ids:
                        jobs.append(job)
                self._write_all_jobs(jobs)
            finally:
                self._release_lock()

        return new_jobs

    def get_next_job(self, worker_id: str, statuses: List[str] = None) -> Optional[Job]:
        """
        Get and lock the next available job.
        Returns None if no jobs available.
        """
        if statuses is None:
            statuses = [JobStatus.NEW.value]

        if self._acquire_lock():
            try:
                jobs = self._read_all_jobs()
                now = datetime.now()

                for job in jobs:
                    # Check if job matches criteria
                    if job.status not in statuses:
                        continue

                    # Check if job is locked by another worker
                    if job.status == JobStatus.IN_PROGRESS.value and job.locked_at:
                        locked_time = datetime.fromisoformat(job.locked_at)
                        minutes_locked = (now - locked_time).total_seconds() / 60
                        if minutes_locked < self.LOCK_TIMEOUT_MINUTES:
                            continue  # Still locked

                    # Claim this job
                    job.status = JobStatus.IN_PROGRESS.value
                    job.worker_id = worker_id
                    job.locked_at = now.isoformat()
                    job.updated_at = now.isoformat()
                    job.attempts += 1

                    self._write_all_jobs(jobs)
                    return job
            finally:
                self._release_lock()

        return None

    def update_job_status(
        self,
        job_id: str,
        status: str,
        error_message: Optional[str] = None,
        metadata: Optional[Dict] = None
    ) -> bool:
        """Update job status."""
        if self._acquire_lock():
            try:
                jobs = self._read_all_jobs()
                for job in jobs:
                    if job.job_id == job_id:
                        job.status = status
                        job.updated_at = datetime.now().isoformat()
                        if error_message:
                            job.error_message = error_message
                        if metadata:
                            job.metadata.update(metadata)
                        if status in [JobStatus.RENDERED.value, JobStatus.FAILED.value]:
                            job.worker_id = None
                            job.locked_at = None
                        self._write_all_jobs(jobs)
                        return True
            finally:
                self._release_lock()
        return False

    def get_job(self, job_id: str) -> Optional[Job]:
        """Get a specific job by ID."""
        jobs = self._read_all_jobs()
        for job in jobs:
            if job.job_id == job_id:
                return job
        return None

    def get_jobs_by_status(self, status: str) -> List[Job]:
        """Get all jobs with a specific status."""
        jobs = self._read_all_jobs()
        return [j for j in jobs if j.status == status]

    def get_all_jobs(self) -> List[Job]:
        """Get all jobs."""
        return self._read_all_jobs()

    def get_stats(self) -> Dict[str, int]:
        """Get job statistics."""
        jobs = self._read_all_jobs()
        stats = {status.value: 0 for status in JobStatus}
        stats["TOTAL"] = len(jobs)
        for job in jobs:
            if job.status in stats:
                stats[job.status] += 1
        return stats

    def reset_failed_jobs(self, max_attempts: int = 3) -> int:
        """Reset failed jobs that haven't exceeded max attempts."""
        count = 0
        if self._acquire_lock():
            try:
                jobs = self._read_all_jobs()
                for job in jobs:
                    if job.status == JobStatus.FAILED.value and job.attempts < max_attempts:
                        job.status = JobStatus.NEW.value
                        job.error_message = None
                        job.updated_at = datetime.now().isoformat()
                        count += 1
                self._write_all_jobs(jobs)
            finally:
                self._release_lock()
        return count

    def cleanup_stale_locks(self) -> int:
        """Release locks on jobs that have been IN_PROGRESS too long."""
        count = 0
        if self._acquire_lock():
            try:
                jobs = self._read_all_jobs()
                now = datetime.now()
                for job in jobs:
                    if job.status == JobStatus.IN_PROGRESS.value and job.locked_at:
                        locked_time = datetime.fromisoformat(job.locked_at)
                        minutes_locked = (now - locked_time).total_seconds() / 60
                        if minutes_locked >= self.LOCK_TIMEOUT_MINUTES:
                            job.status = JobStatus.NEW.value
                            job.worker_id = None
                            job.locked_at = None
                            job.updated_at = now.isoformat()
                            count += 1
                self._write_all_jobs(jobs)
            finally:
                self._release_lock()
        return count
