#!/usr/bin/env python3
"""CLI for running job scrapers."""

import argparse
import sys
from pathlib import Path

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent))

from config import BASE_PATH, COMPANIES
from scraper import AnthropicScraper
from scraper.utils import get_today_utc


SCRAPERS = {
    "anthropic": AnthropicScraper,
}


def main():
    parser = argparse.ArgumentParser(description="Scrape job postings from AI labs")
    parser.add_argument(
        "company",
        nargs="?",
        choices=COMPANIES + ["all"],
        default="all",
        help="Company to scrape (default: all)",
    )
    parser.add_argument(
        "--date",
        help="Override date (YYYY-MM-DD format, default: today UTC)",
    )

    args = parser.parse_args()
    today = args.date or get_today_utc()

    companies = COMPANIES if args.company == "all" else [args.company]

    print(f"Scraping jobs for {today}")
    print("=" * 40)

    for company in companies:
        if company not in SCRAPERS:
            print(f"Skipping {company}: no scraper implemented")
            continue

        print(f"\n{company.title()}")
        print("-" * 20)

        scraper_cls = SCRAPERS[company]
        scraper = scraper_cls(BASE_PATH)

        try:
            result = scraper.run(today)
            print(f"  Total jobs: {result['total_jobs']}")
            print(f"  New: {result['new']}")
            print(f"  Updated: {result['updated']}")
            print(f"  Removed: {result['removed']}")
        except Exception as e:
            print(f"  Error: {e}")
            raise

    print("\nDone!")


if __name__ == "__main__":
    main()
