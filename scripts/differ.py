"""Job diff logic for tracking changes over time."""

import json
import subprocess
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Optional


@dataclass
class JobChange:
    """Represents a changed job."""

    job_id: str
    title: str
    team: str
    location: str
    url: str
    old_hash: str
    new_hash: str
    first_seen: str
    last_seen: str


@dataclass
class DiffResult:
    """Result of diffing two job snapshots."""

    company: str
    start_date: str
    end_date: str
    start_count: int
    end_count: int
    new_jobs: list[dict[str, Any]] = field(default_factory=list)
    removed_jobs: list[dict[str, Any]] = field(default_factory=list)
    changed_jobs: list[JobChange] = field(default_factory=list)

    @property
    def delta(self) -> int:
        return self.end_count - self.start_count

    def to_dict(self) -> dict[str, Any]:
        return {
            "company": self.company,
            "start_date": self.start_date,
            "end_date": self.end_date,
            "start_count": self.start_count,
            "end_count": self.end_count,
            "delta": self.delta,
            "summary": {
                "new": len(self.new_jobs),
                "removed": len(self.removed_jobs),
                "changed": len(self.changed_jobs),
            },
            "new_jobs": self.new_jobs,
            "removed_jobs": self.removed_jobs,
            "changed_jobs": [
                {
                    "id": c.job_id,
                    "title": c.title,
                    "team": c.team,
                    "location": c.location,
                    "url": c.url,
                    "old_hash": c.old_hash,
                    "new_hash": c.new_hash,
                    "first_seen": c.first_seen,
                    "last_seen": c.last_seen,
                }
                for c in self.changed_jobs
            ],
        }


def load_jobs_from_file(path: Path) -> dict[str, dict[str, Any]]:
    """Load jobs from a JSON file, indexed by ID."""
    if not path.exists():
        return {}

    with open(path) as f:
        jobs = json.load(f)

    return {job["id"]: job for job in jobs}


def load_jobs_from_git(repo_path: Path, commit: str, file_path: str) -> dict[str, dict[str, Any]]:
    """Load jobs from a specific git commit."""
    try:
        result = subprocess.run(
            ["git", "show", f"{commit}:{file_path}"],
            cwd=repo_path,
            capture_output=True,
            text=True,
            check=True,
        )
        jobs = json.loads(result.stdout)
        return {job["id"]: job for job in jobs}
    except subprocess.CalledProcessError:
        # File didn't exist at that commit
        return {}
    except json.JSONDecodeError:
        return {}


def get_first_commit_of_month(repo_path: Path, year: int, month: int) -> Optional[str]:
    """Get the first commit of a given month."""
    # Format: YYYY-MM-01
    start_date = f"{year:04d}-{month:02d}-01"
    # Get commits on or after start date, oldest first
    result = subprocess.run(
        [
            "git",
            "log",
            "--oneline",
            "--reverse",
            f"--since={start_date}",
            "--format=%H",
        ],
        cwd=repo_path,
        capture_output=True,
        text=True,
    )
    if result.returncode == 0 and result.stdout.strip():
        return result.stdout.strip().split("\n")[0]
    return None


def get_last_commit_of_month(repo_path: Path, year: int, month: int) -> Optional[str]:
    """Get the last commit of a given month."""
    # Calculate end date (first day of next month)
    if month == 12:
        end_date = f"{year + 1:04d}-01-01"
    else:
        end_date = f"{year:04d}-{month + 1:02d}-01"

    # Get commits before end date, newest first
    result = subprocess.run(
        [
            "git",
            "log",
            "--oneline",
            f"--until={end_date}",
            "--format=%H",
            "-1",
        ],
        cwd=repo_path,
        capture_output=True,
        text=True,
    )
    if result.returncode == 0 and result.stdout.strip():
        return result.stdout.strip()
    return None


def diff_jobs(
    start_jobs: dict[str, dict[str, Any]],
    end_jobs: dict[str, dict[str, Any]],
    company: str,
    start_date: str,
    end_date: str,
) -> DiffResult:
    """Compute diff between two job snapshots.

    Args:
        start_jobs: Jobs at start of period, indexed by ID
        end_jobs: Jobs at end of period, indexed by ID
        company: Company name
        start_date: Start date string
        end_date: End date string

    Returns:
        DiffResult with new, removed, and changed jobs
    """
    start_ids = set(start_jobs.keys())
    end_ids = set(end_jobs.keys())

    # New jobs: in end but not start
    new_ids = end_ids - start_ids
    new_jobs = [end_jobs[id] for id in sorted(new_ids)]

    # Removed jobs: in start but not end
    removed_ids = start_ids - end_ids
    removed_jobs = [start_jobs[id] for id in sorted(removed_ids)]

    # Changed jobs: in both, but different description_hash
    common_ids = start_ids & end_ids
    changed_jobs = []
    for id in sorted(common_ids):
        old_job = start_jobs[id]
        new_job = end_jobs[id]
        if old_job.get("description_hash") != new_job.get("description_hash"):
            changed_jobs.append(
                JobChange(
                    job_id=id,
                    title=new_job.get("title", ""),
                    team=new_job.get("team", ""),
                    location=new_job.get("location", ""),
                    url=new_job.get("url", ""),
                    old_hash=old_job.get("description_hash", ""),
                    new_hash=new_job.get("description_hash", ""),
                    first_seen=new_job.get("first_seen", ""),
                    last_seen=new_job.get("last_seen", ""),
                )
            )

    return DiffResult(
        company=company,
        start_date=start_date,
        end_date=end_date,
        start_count=len(start_jobs),
        end_count=len(end_jobs),
        new_jobs=new_jobs,
        removed_jobs=removed_jobs,
        changed_jobs=changed_jobs,
    )
