"""Report generation for AI job tracker."""

import re
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Any

# Use string.Template as a fallback if Jinja2 is not available
try:
    from jinja2 import Environment, FileSystemLoader

    HAS_JINJA2 = True
except ImportError:
    HAS_JINJA2 = False

from differ import DiffResult


@dataclass
class CompanyReport:
    """Report data for a single company."""

    name: str
    start_count: int
    end_count: int
    delta: int
    new_jobs: list[dict[str, Any]]
    removed_jobs: list[dict[str, Any]]
    changed_jobs: list[dict[str, Any]]


def format_date_display(date_str: str) -> str:
    """Format a date string for display (e.g., 'Jan 5, 2026')."""
    try:
        dt = datetime.strptime(date_str, "%Y-%m-%d")
        return dt.strftime("%b %-d, %Y")
    except ValueError:
        return date_str


def truncate_location(location: str) -> str:
    """Truncate location to first city/region."""
    # Take first part before | or ,
    parts = re.split(r"[|,]", location)
    return parts[0].strip() if parts else location


def truncate_url(url: str) -> str:
    """Truncate URL for display."""
    # Remove protocol
    url = re.sub(r"^https?://", "", url)
    # Truncate if too long
    if len(url) > 40:
        return url[:37] + "..."
    return url


def load_description(descriptions_dir: Path, job_id: str) -> str:
    """Load job description from HTML file."""
    desc_file = descriptions_dir / f"{job_id}.html"
    if desc_file.exists():
        return desc_file.read_text()
    return ""


def generate_report(
    diffs: list[DiffResult],
    base_path: Path,
    date_str: str,
) -> str:
    """Generate HTML report from diff results.

    Args:
        diffs: List of DiffResult objects, one per company
        base_path: Base path for the project
        date_str: Date string (YYYY-MM-DD)

    Returns:
        Generated HTML string
    """
    if not HAS_JINJA2:
        raise ImportError("Jinja2 is required for report generation. Install with: pip install jinja2")

    # Parse date for display
    report_date = datetime.strptime(date_str, "%Y-%m-%d")
    date_display = report_date.strftime("%B %-d, %Y")

    # Build company reports
    companies = []
    total_new = 0
    total_removed = 0
    total_changed = 0

    for diff in diffs:
        company_name = diff.company.title()
        if diff.company == "deepmind":
            company_name = "Google DeepMind"

        # Load descriptions for new and changed jobs
        descriptions_dir = base_path / "descriptions" / diff.company

        new_jobs = []
        for job in diff.new_jobs:
            job_copy = dict(job)
            desc = load_description(descriptions_dir, job["id"])
            job_copy["description_html"] = desc if desc else "<p>No description available.</p>"
            new_jobs.append(job_copy)

        changed_jobs = []
        for change in diff.changed_jobs:
            job_data = {
                "id": change.job_id,
                "title": change.title,
                "team": change.team,
                "location": change.location,
                "url": change.url,
                "first_seen": change.first_seen,
                "last_seen": change.last_seen,
            }
            desc = load_description(descriptions_dir, change.job_id)
            job_data["description_html"] = desc if desc else "<p>No description available.</p>"
            changed_jobs.append(job_data)

        company_report = CompanyReport(
            name=company_name,
            start_count=diff.start_count,
            end_count=diff.end_count,
            delta=diff.delta,
            new_jobs=new_jobs,
            removed_jobs=diff.removed_jobs,
            changed_jobs=changed_jobs,
        )
        companies.append(company_report)

        total_new += len(diff.new_jobs)
        total_removed += len(diff.removed_jobs)
        total_changed += len(diff.changed_jobs)

    # Set up Jinja2
    templates_dir = base_path / "templates"
    env = Environment(loader=FileSystemLoader(templates_dir))

    # Add custom filters
    env.filters["format_date_display"] = format_date_display
    env.filters["truncate_location"] = truncate_location
    env.filters["truncate_url"] = truncate_url

    template = env.get_template("report.html")

    # Render
    html = template.render(
        date_display=date_display,
        total_new=total_new,
        total_removed=total_removed,
        total_changed=total_changed,
        companies=companies,
        last_updated=datetime.now().strftime("%b %-d, %Y"),
    )

    return html


def save_report(html: str, base_path: Path, date_str: str) -> Path:
    """Save generated HTML report to site directory."""
    site_dir = base_path / "site" / date_str
    site_dir.mkdir(parents=True, exist_ok=True)

    output_path = site_dir / "index.html"
    output_path.write_text(html)

    return output_path
