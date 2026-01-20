# AI Lab Jobs Tracker

Monthly changelog of job postings at major AI research labs.

## Directory Structure

```
ai-jobs-tracker/
├── data/                    # Current state (committed to git)
│   ├── anthropic/
│   │   └── jobs.json        # Array of job objects
│   ├── openai/
│   │   └── jobs.json
│   └── deepmind/
│       └── jobs.json
│
├── descriptions/            # Full job descriptions (markdown)
│   ├── anthropic/
│   │   └── {job-id}.md
│   ├── openai/
│   └── deepmind/
│
├── raw/                     # Raw scrape archives (committed to git)
│   ├── anthropic/
│   │   └── 2026-01-19.json  # or .html depending on source
│   ├── openai/
│   └── deepmind/
│
├── scripts/                 # Scraper, differ, report generator
│
└── site/                    # Generated monthly reports
    ├── 2026-01/
    │   └── index.html
    └── 2026-02/
        └── index.html
```

## Data Model

### jobs.json

```json
[
  {
    "id": "engineering-manager-claude",
    "title": "Engineering Manager, Claude",
    "team": "Product Engineering",
    "location": "San Francisco, CA",
    "url": "https://boards.greenhouse.io/anthropic/jobs/1234567",
    "first_seen": "2025-11-14",
    "last_seen": "2026-01-19",
    "description_hash": "a1b2c3d4e5f6"
  }
]
```

- `id`: Slug derived from title, used for description filenames
- `description_hash`: SHA256 of description text (first 12 chars), used to detect changes
- `first_seen` / `last_seen`: Date strings (YYYY-MM-DD)

### Raw Data Strategy

Store one file per company per day in `raw/`:
- Prefer JSON if the careers page has an API endpoint (Greenhouse, Lever, Ashby all do)
- Fall back to HTML if scraping is required
- Filename format: `YYYY-MM-DD.json` or `YYYY-MM-DD.html`

Git handles text compression well. Expected sizes:
- ~100KB per company per day (JSON)
- ~300KB per company per day (HTML)
- ~9-27 MB/month total
- Repo stays manageable for years

### Generating Diffs

To generate a monthly report:
1. Load `jobs.json` from the first commit of the month
2. Load `jobs.json` from the last commit of the month
3. Diff by `id`:
   - IDs in new but not old → NEW
   - IDs in old but not new → REMOVED
   - IDs in both but `description_hash` differs → CHANGED

## Scraping Notes

### Anthropic
- Uses Greenhouse
- API: `https://boards.greenhouse.io/anthropic/jobs` (returns HTML, but structured)
- Better: `https://api.greenhouse.io/v1/boards/anthropic/jobs` (returns JSON)

### OpenAI
- Uses Ashby (since ~2024)
- Careers page: `https://openai.com/careers/`
- May need to inspect network tab for API endpoint

### Google DeepMind
- Uses Google's internal system
- Careers page: `https://deepmind.google/careers/`
- Likely requires HTML scraping

## TODO

- [ ] Write scraper scripts
- [ ] Set up daily cron job
- [ ] Automate monthly report generation
- [ ] Add more labs (xAI, Meta FAIR, Mistral, etc.)
