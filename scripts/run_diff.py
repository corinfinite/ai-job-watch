#!/usr/bin/env python3
"""CLI for running job diffs."""

import argparse
import json
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


def main():
    parser = argparse.ArgumentParser(description="Diff job postings between snapshots")
    parser.add_argument(
        "company",
        choices=COMPANIES,
        help="Company to diff",
    )
    parser.add_argument(
        "--month",
        help="Month to diff (YYYY-MM format). Compares start to end of month.",
    )
    parser.add_argument(
        "--start",
        help="Start git commit (or 'empty' for empty snapshot)",
    )
    parser.add_argument(
        "--end",
        help="End git commit (or 'current' for current file state)",
    )
    parser.add_argument(
        "--json",
        action="store_true",
        help="Output as JSON",
    )

    args = parser.parse_args()

    if args.month:
        # Parse month
        try:
            parts = args.month.split("-")
            year = int(parts[0])
            month = int(parts[1])
        except (ValueError, IndexError):
            print(f"Invalid month format: {args.month}. Use YYYY-MM.", file=sys.stderr)
            sys.exit(1)

        # Get commits for month range
        start_commit = get_first_commit_of_month(BASE_PATH, year, month)
        end_commit = get_last_commit_of_month(BASE_PATH, year, month)

        start_date = f"{year:04d}-{month:02d}-01"
        end_date = f"{year:04d}-{month:02d}-28"  # Approximate

        if not start_commit and not end_commit:
            print(f"No commits found for {args.month}", file=sys.stderr)
            # Fall back to current state vs empty
            start_jobs = {}
            end_jobs = load_jobs_from_file(BASE_PATH / "data" / args.company / "jobs.json")
    else:
        if not args.start or not args.end:
            print("Either --month or both --start and --end required", file=sys.stderr)
            sys.exit(1)

        start_commit = args.start if args.start != "empty" else None
        end_commit = args.end if args.end != "current" else None
        start_date = args.start
        end_date = args.end

    # Load job snapshots
    file_path = f"data/{args.company}/jobs.json"

    if args.month:
        if start_commit:
            start_jobs = load_jobs_from_git(BASE_PATH, start_commit, file_path)
        else:
            start_jobs = {}

        if end_commit:
            end_jobs = load_jobs_from_git(BASE_PATH, end_commit, file_path)
        else:
            end_jobs = load_jobs_from_file(BASE_PATH / file_path)
    else:
        if start_commit:
            start_jobs = load_jobs_from_git(BASE_PATH, start_commit, file_path)
        else:
            start_jobs = {}

        if end_commit:
            end_jobs = load_jobs_from_git(BASE_PATH, end_commit, file_path)
        else:
            end_jobs = load_jobs_from_file(BASE_PATH / file_path)

    # Compute diff
    result = diff_jobs(start_jobs, end_jobs, args.company, start_date, end_date)

    # Output
    if args.json:
        print(json.dumps(result.to_dict(), indent=2))
    else:
        print(f"\n{result.company.title()} Jobs Diff")
        print(f"Period: {result.start_date} → {result.end_date}")
        print(f"Jobs: {result.start_count} → {result.end_count} ({result.delta:+d})")
        print()
        print(f"  New:     {len(result.new_jobs)}")
        print(f"  Removed: {len(result.removed_jobs)}")
        print(f"  Changed: {len(result.changed_jobs)}")

        if result.new_jobs:
            print("\n  New Jobs:")
            for job in result.new_jobs[:10]:
                print(f"    + {job['title']} ({job['team']})")
            if len(result.new_jobs) > 10:
                print(f"    ... and {len(result.new_jobs) - 10} more")

        if result.removed_jobs:
            print("\n  Removed Jobs:")
            for job in result.removed_jobs[:10]:
                print(f"    - {job['title']} ({job['team']})")
            if len(result.removed_jobs) > 10:
                print(f"    ... and {len(result.removed_jobs) - 10} more")

        if result.changed_jobs:
            print("\n  Changed Jobs:")
            for change in result.changed_jobs[:10]:
                print(f"    ~ {change.title}")
            if len(result.changed_jobs) > 10:
                print(f"    ... and {len(result.changed_jobs) - 10} more")


if __name__ == "__main__":
    main()
