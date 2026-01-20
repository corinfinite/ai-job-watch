"""Base scraper interface and Job data model."""

from abc import ABC, abstractmethod
from dataclasses import dataclass, asdict, field
from pathlib import Path
from typing import Any
import json


@dataclass
class Job:
    """Represents a job posting."""

    id: str
    title: str
    team: str
    location: str
    url: str
    first_seen: str
    last_seen: str
    description_hash: str
    description: str = field(default="", repr=False)

    def to_dict(self, include_description: bool = False) -> dict[str, Any]:
        """Convert to dictionary for JSON serialization."""
        data = asdict(self)
        if not include_description:
            del data["description"]
        return data

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "Job":
        """Create Job from dictionary."""
        return cls(**data)


class BaseScraper(ABC):
    """Abstract base class for job scrapers."""

    def __init__(self, base_path: Path):
        """Initialize scraper with base data path.

        Args:
            base_path: Base path for data storage (e.g., /path/to/ai-jobs-tracker)
        """
        self.base_path = Path(base_path)
        self.company_name = self.get_company_name()

        # Set up paths
        self.data_dir = self.base_path / "data" / self.company_name
        self.raw_dir = self.base_path / "raw" / self.company_name
        self.descriptions_dir = self.base_path / "descriptions" / self.company_name

        # Ensure directories exist
        self.data_dir.mkdir(parents=True, exist_ok=True)
        self.raw_dir.mkdir(parents=True, exist_ok=True)
        self.descriptions_dir.mkdir(parents=True, exist_ok=True)

    @abstractmethod
    def get_company_name(self) -> str:
        """Return the company name (used for directory names)."""
        pass

    @abstractmethod
    def fetch_jobs(self) -> tuple[list[Job], dict[str, Any]]:
        """Fetch jobs from the careers API/page.

        Returns:
            Tuple of (list of Job objects, raw API response for archiving)
        """
        pass

    def load_existing_jobs(self) -> dict[str, Job]:
        """Load existing jobs from jobs.json."""
        jobs_file = self.data_dir / "jobs.json"
        if not jobs_file.exists():
            return {}

        with open(jobs_file) as f:
            jobs_data = json.load(f)

        return {job["id"]: Job.from_dict({**job, "description": ""}) for job in jobs_data}

    def save_jobs(self, jobs: list[Job]) -> None:
        """Save jobs to jobs.json."""
        jobs_file = self.data_dir / "jobs.json"

        # Sort by ID for consistent ordering
        sorted_jobs = sorted(jobs, key=lambda j: j.id)

        with open(jobs_file, "w") as f:
            json.dump([j.to_dict() for j in sorted_jobs], f, indent=2)
            f.write("\n")

    def save_raw(self, data: Any, date_str: str) -> Path:
        """Save raw API response."""
        raw_file = self.raw_dir / f"{date_str}.json"

        with open(raw_file, "w") as f:
            json.dump(data, f, indent=2)
            f.write("\n")

        return raw_file

    def save_description(self, job_id: str, description_md: str) -> Path:
        """Save job description as markdown."""
        desc_file = self.descriptions_dir / f"{job_id}.md"

        with open(desc_file, "w") as f:
            f.write(description_md)

        return desc_file

    def run(self, today: str) -> dict[str, Any]:
        """Run the scraper.

        Args:
            today: Today's date in YYYY-MM-DD format

        Returns:
            Summary of changes
        """
        # Fetch fresh data
        new_jobs, raw_data = self.fetch_jobs()

        # Save raw data
        self.save_raw(raw_data, today)

        # Load existing jobs
        existing_jobs = self.load_existing_jobs()

        # Build updated job list
        updated_jobs: list[Job] = []
        new_count = 0
        updated_count = 0

        new_jobs_by_id = {job.id: job for job in new_jobs}

        for job in new_jobs:
            if job.id in existing_jobs:
                # Existing job - preserve first_seen, update last_seen
                existing = existing_jobs[job.id]
                job.first_seen = existing.first_seen
                job.last_seen = today

                # Check if description changed
                if job.description_hash != existing.description_hash:
                    updated_count += 1
            else:
                # New job
                job.first_seen = today
                job.last_seen = today
                new_count += 1

            # Save description
            if job.description:
                self.save_description(job.id, job.description)

            updated_jobs.append(job)

        # Count removed jobs (in existing but not in new)
        removed_count = len(set(existing_jobs.keys()) - set(new_jobs_by_id.keys()))

        # Save updated jobs
        self.save_jobs(updated_jobs)

        return {
            "company": self.company_name,
            "date": today,
            "total_jobs": len(updated_jobs),
            "new": new_count,
            "updated": updated_count,
            "removed": removed_count,
        }
