"""Anthropic job scraper using Greenhouse API."""

import time
from pathlib import Path
from typing import Any
from urllib.request import urlopen, Request
import json

from .base import BaseScraper, Job
from .utils import slugify, hash_description, html_to_markdown


class AnthropicScraper(BaseScraper):
    """Scraper for Anthropic jobs via Greenhouse API."""

    JOBS_LIST_URL = "https://api.greenhouse.io/v1/boards/anthropic/jobs"
    JOB_DETAIL_URL = "https://api.greenhouse.io/v1/boards/anthropic/jobs/{job_id}"

    # Rate limiting
    REQUEST_DELAY = 0.5  # seconds between requests

    def get_company_name(self) -> str:
        return "anthropic"

    def _fetch_json(self, url: str) -> dict[str, Any]:
        """Fetch JSON from URL with user agent."""
        req = Request(url, headers={"User-Agent": "AI-Jobs-Tracker/1.0"})
        with urlopen(req, timeout=30) as response:
            return json.loads(response.read().decode("utf-8"))

    def _extract_team(self, departments: list[dict[str, Any]]) -> str:
        """Extract team name from departments list."""
        if departments and len(departments) > 0:
            return departments[0].get("name", "Unknown")
        return "Unknown"

    def _extract_location(self, location: dict[str, Any]) -> str:
        """Extract location string from location object."""
        return location.get("name", "Unknown") if location else "Unknown"

    def fetch_jobs(self) -> tuple[list[Job], dict[str, Any]]:
        """Fetch all Anthropic jobs from Greenhouse API."""
        # First, get the jobs list
        jobs_list_data = self._fetch_json(self.JOBS_LIST_URL)
        jobs_list = jobs_list_data.get("jobs", [])

        # Store all raw job details for archiving
        raw_data = {
            "jobs_list": jobs_list_data,
            "job_details": {},
        }

        jobs: list[Job] = []
        seen_ids: dict[str, int] = {}  # Track ID collisions

        for i, job_summary in enumerate(jobs_list):
            gh_id = job_summary["id"]

            # Fetch full job details
            time.sleep(self.REQUEST_DELAY)
            job_detail = self._fetch_json(self.JOB_DETAIL_URL.format(job_id=gh_id))
            raw_data["job_details"][str(gh_id)] = job_detail

            # Parse job
            title = job_detail.get("title", "Unknown")
            content_html = job_detail.get("content", "")

            # Generate unique ID, handling collisions by appending greenhouse ID
            base_id = slugify(title)
            if base_id in seen_ids:
                job_id = f"{base_id}-{gh_id}"
            else:
                job_id = base_id
            seen_ids[base_id] = seen_ids.get(base_id, 0) + 1

            job = Job(
                id=job_id,
                title=title,
                team=self._extract_team(job_detail.get("departments", [])),
                location=self._extract_location(job_detail.get("location")),
                url=job_detail.get("absolute_url", ""),
                first_seen="",  # Will be set by run()
                last_seen="",  # Will be set by run()
                description_hash=hash_description(content_html),
                description=html_to_markdown(content_html),
            )
            jobs.append(job)

            # Progress indicator
            if (i + 1) % 50 == 0:
                print(f"  Fetched {i + 1}/{len(jobs_list)} jobs...")

        return jobs, raw_data
