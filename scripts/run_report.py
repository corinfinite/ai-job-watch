#!/usr/bin/env python3
"""CLI for generating monthly reports."""

import argparse
import sys
from pathlib import Path

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent))

from config import BASE_PATH, COMPANIES
from differ import (
    diff_jobs,
    load_jobs_from_file,
    load_jobs_from_git,
    get_first_commit_of_month,
    get_last_commit_of_month,
)
from report import generate_report, save_report


def main():
    parser = argparse.ArgumentParser(description="Generate monthly job report")
    parser.add_argument(
        "--month",
        required=True,
        help="Month to generate report for (YYYY-MM format)",
    )
    parser.add_argument(
        "--companies",
        nargs="+",
        default=COMPANIES,
        help=f"Companies to include (default: {COMPANIES})",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Print HTML to stdout instead of saving",
    )

    args = parser.parse_args()

    # Parse month
    try:
        parts = args.month.split("-")
        year = int(parts[0])
        month = int(parts[1])
    except (ValueError, IndexError):
        print(f"Invalid month format: {args.month}. Use YYYY-MM.", file=sys.stderr)
        sys.exit(1)

    print(f"Generating report for {args.month}")
    print("=" * 40)

    # Get diffs for each company
    diffs = []

    for company in args.companies:
        print(f"\nProcessing {company}...")

        file_path = f"data/{company}/jobs.json"

        # Try to get commits for the month
        start_commit = get_first_commit_of_month(BASE_PATH, year, month)
        end_commit = get_last_commit_of_month(BASE_PATH, year, month)

        # Load job snapshots
        if start_commit:
            start_jobs = load_jobs_from_git(BASE_PATH, start_commit, file_path)
            start_date = f"{year:04d}-{month:02d}-01"
        else:
            # No start commit - use empty
            start_jobs = {}
            start_date = f"{year:04d}-{month:02d}-01"
            print(f"  No commits found at start of month, using empty snapshot")

        if end_commit:
            end_jobs = load_jobs_from_git(BASE_PATH, end_commit, file_path)
            end_date = f"{year:04d}-{month:02d}-28"
        else:
            # No end commit yet - use current file
            end_jobs = load_jobs_from_file(BASE_PATH / file_path)
            end_date = "current"
            print(f"  Using current file state for end snapshot")

        # Compute diff
        diff = diff_jobs(start_jobs, end_jobs, company, start_date, end_date)
        diffs.append(diff)

        print(f"  Jobs: {diff.start_count} -> {diff.end_count} ({diff.delta:+d})")
        print(f"  New: {len(diff.new_jobs)}, Removed: {len(diff.removed_jobs)}, Changed: {len(diff.changed_jobs)}")

    # Generate report
    print("\nGenerating HTML report...")
    html = generate_report(diffs, BASE_PATH, args.month)

    if args.dry_run:
        print("\n" + "=" * 40)
        print("DRY RUN - HTML output:")
        print("=" * 40)
        print(html)
    else:
        output_path = save_report(html, BASE_PATH, args.month)
        print(f"\nReport saved to: {output_path}")


if __name__ == "__main__":
    main()
