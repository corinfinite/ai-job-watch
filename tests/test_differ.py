"""Tests for the differ module."""

import sys
from pathlib import Path

# Add scripts directory to path
sys.path.insert(0, str(Path(__file__).parent.parent / "scripts"))

from differ import diff_jobs, DiffResult, JobChange


class TestDiffJobs:
    """Tests for the diff_jobs function."""

    def test_empty_to_empty(self):
        """Diffing two empty snapshots returns no changes."""
        result = diff_jobs({}, {}, "test", "2026-01-01", "2026-01-31")

        assert result.company == "test"
        assert result.start_count == 0
        assert result.end_count == 0
        assert result.delta == 0
        assert len(result.new_jobs) == 0
        assert len(result.removed_jobs) == 0
        assert len(result.changed_jobs) == 0

    def test_new_jobs_detected(self):
        """Jobs in end but not start are detected as new."""
        start_jobs = {}
        end_jobs = {
            "job-1": {
                "id": "job-1",
                "title": "Software Engineer",
                "team": "Engineering",
                "location": "San Francisco",
                "url": "https://example.com/job-1",
                "first_seen": "2026-01-15",
                "last_seen": "2026-01-31",
                "description_hash": "abc123",
            },
            "job-2": {
                "id": "job-2",
                "title": "Product Manager",
                "team": "Product",
                "location": "Remote",
                "url": "https://example.com/job-2",
                "first_seen": "2026-01-20",
                "last_seen": "2026-01-31",
                "description_hash": "def456",
            },
        }

        result = diff_jobs(start_jobs, end_jobs, "test", "2026-01-01", "2026-01-31")

        assert result.start_count == 0
        assert result.end_count == 2
        assert result.delta == 2
        assert len(result.new_jobs) == 2
        assert len(result.removed_jobs) == 0
        assert len(result.changed_jobs) == 0

        # Check new jobs are sorted by ID
        assert result.new_jobs[0]["id"] == "job-1"
        assert result.new_jobs[1]["id"] == "job-2"

    def test_removed_jobs_detected(self):
        """Jobs in start but not end are detected as removed."""
        start_jobs = {
            "job-1": {
                "id": "job-1",
                "title": "Software Engineer",
                "team": "Engineering",
                "location": "San Francisco",
                "url": "https://example.com/job-1",
                "first_seen": "2025-12-01",
                "last_seen": "2026-01-01",
                "description_hash": "abc123",
            },
        }
        end_jobs = {}

        result = diff_jobs(start_jobs, end_jobs, "test", "2026-01-01", "2026-01-31")

        assert result.start_count == 1
        assert result.end_count == 0
        assert result.delta == -1
        assert len(result.new_jobs) == 0
        assert len(result.removed_jobs) == 1
        assert len(result.changed_jobs) == 0

        assert result.removed_jobs[0]["id"] == "job-1"

    def test_changed_jobs_detected(self):
        """Jobs with different description_hash are detected as changed."""
        start_jobs = {
            "job-1": {
                "id": "job-1",
                "title": "Software Engineer",
                "team": "Engineering",
                "location": "San Francisco",
                "url": "https://example.com/job-1",
                "first_seen": "2025-12-01",
                "last_seen": "2026-01-01",
                "description_hash": "abc123",
            },
        }
        end_jobs = {
            "job-1": {
                "id": "job-1",
                "title": "Software Engineer",
                "team": "Engineering",
                "location": "San Francisco | Remote",  # Location changed
                "url": "https://example.com/job-1",
                "first_seen": "2025-12-01",
                "last_seen": "2026-01-31",
                "description_hash": "xyz789",  # Hash changed
            },
        }

        result = diff_jobs(start_jobs, end_jobs, "test", "2026-01-01", "2026-01-31")

        assert result.start_count == 1
        assert result.end_count == 1
        assert result.delta == 0
        assert len(result.new_jobs) == 0
        assert len(result.removed_jobs) == 0
        assert len(result.changed_jobs) == 1

        change = result.changed_jobs[0]
        assert change.job_id == "job-1"
        assert change.old_hash == "abc123"
        assert change.new_hash == "xyz789"
        assert change.location == "San Francisco | Remote"

    def test_unchanged_jobs_not_reported(self):
        """Jobs with same description_hash are not reported as changed."""
        job_data = {
            "id": "job-1",
            "title": "Software Engineer",
            "team": "Engineering",
            "location": "San Francisco",
            "url": "https://example.com/job-1",
            "first_seen": "2025-12-01",
            "last_seen": "2026-01-31",
            "description_hash": "abc123",
        }
        start_jobs = {"job-1": job_data.copy()}
        end_jobs = {"job-1": job_data.copy()}

        result = diff_jobs(start_jobs, end_jobs, "test", "2026-01-01", "2026-01-31")

        assert len(result.new_jobs) == 0
        assert len(result.removed_jobs) == 0
        assert len(result.changed_jobs) == 0

    def test_mixed_changes(self):
        """Complex scenario with new, removed, and changed jobs."""
        start_jobs = {
            "job-1": {
                "id": "job-1",
                "title": "Engineer A",
                "team": "Team A",
                "location": "Location A",
                "url": "https://example.com/job-1",
                "first_seen": "2025-11-01",
                "last_seen": "2026-01-01",
                "description_hash": "hash1",
            },
            "job-2": {
                "id": "job-2",
                "title": "Engineer B",
                "team": "Team B",
                "location": "Location B",
                "url": "https://example.com/job-2",
                "first_seen": "2025-11-15",
                "last_seen": "2026-01-01",
                "description_hash": "hash2",
            },
            "job-3": {
                "id": "job-3",
                "title": "Engineer C",
                "team": "Team C",
                "location": "Location C",
                "url": "https://example.com/job-3",
                "first_seen": "2025-12-01",
                "last_seen": "2026-01-01",
                "description_hash": "hash3",
            },
        }
        end_jobs = {
            # job-1 removed
            "job-2": {
                "id": "job-2",
                "title": "Engineer B",
                "team": "Team B",
                "location": "Location B",
                "url": "https://example.com/job-2",
                "first_seen": "2025-11-15",
                "last_seen": "2026-01-31",
                "description_hash": "hash2-updated",  # Changed
            },
            "job-3": {
                "id": "job-3",
                "title": "Engineer C",
                "team": "Team C",
                "location": "Location C",
                "url": "https://example.com/job-3",
                "first_seen": "2025-12-01",
                "last_seen": "2026-01-31",
                "description_hash": "hash3",  # Unchanged
            },
            "job-4": {
                "id": "job-4",
                "title": "Engineer D",
                "team": "Team D",
                "location": "Location D",
                "url": "https://example.com/job-4",
                "first_seen": "2026-01-15",
                "last_seen": "2026-01-31",
                "description_hash": "hash4",  # New
            },
        }

        result = diff_jobs(start_jobs, end_jobs, "test", "2026-01-01", "2026-01-31")

        assert result.start_count == 3
        assert result.end_count == 3
        assert result.delta == 0
        assert len(result.new_jobs) == 1
        assert len(result.removed_jobs) == 1
        assert len(result.changed_jobs) == 1

        assert result.new_jobs[0]["id"] == "job-4"
        assert result.removed_jobs[0]["id"] == "job-1"
        assert result.changed_jobs[0].job_id == "job-2"


class TestDiffResultToDict:
    """Tests for DiffResult.to_dict() method."""

    def test_to_dict_structure(self):
        """to_dict returns expected structure."""
        result = DiffResult(
            company="anthropic",
            start_date="2026-01-01",
            end_date="2026-01-31",
            start_count=100,
            end_count=110,
            new_jobs=[{"id": "job-1", "title": "Test Job"}],
            removed_jobs=[],
            changed_jobs=[
                JobChange(
                    job_id="job-2",
                    title="Changed Job",
                    team="Team",
                    location="Location",
                    url="https://example.com",
                    old_hash="old",
                    new_hash="new",
                    first_seen="2025-12-01",
                    last_seen="2026-01-31",
                )
            ],
        )

        d = result.to_dict()

        assert d["company"] == "anthropic"
        assert d["start_date"] == "2026-01-01"
        assert d["end_date"] == "2026-01-31"
        assert d["start_count"] == 100
        assert d["end_count"] == 110
        assert d["delta"] == 10
        assert d["summary"]["new"] == 1
        assert d["summary"]["removed"] == 0
        assert d["summary"]["changed"] == 1
        assert len(d["new_jobs"]) == 1
        assert len(d["removed_jobs"]) == 0
        assert len(d["changed_jobs"]) == 1
        assert d["changed_jobs"][0]["id"] == "job-2"
        assert d["changed_jobs"][0]["old_hash"] == "old"
        assert d["changed_jobs"][0]["new_hash"] == "new"
