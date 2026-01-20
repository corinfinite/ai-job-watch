# HANDOFF: AI Lab Jobs Tracker

## What This Is

A newsletter/website that tracks job posting changes at major AI labs (Anthropic, OpenAI, Google DeepMind). Published monthly, showing new roles, removed roles, and changed descriptions. Data collected daily.

## Current State

**Done:**
- Directory structure established
- Data model defined (see `data/anthropic/jobs.json` for example)
- HTML template for monthly reports (`site/2026-01/index.html`) — working, styled, uses native `<details>` for collapsible job listings
- README with project overview

**Not Done:**
- Scraper scripts
- Diff generation logic
- Report generation from data
- Cron/automation setup

## Key Design Decisions

1. **Git-backed storage**: All data lives in git. Raw scrapes, parsed jobs, descriptions — everything. Git gives us history for free and text compresses well.

2. **Separate descriptions from metadata**: `jobs.json` contains structured data with a `description_hash`. Full descriptions live in `descriptions/{company}/{job-id}.md`. This keeps jobs.json diffable and small.

3. **Raw data preservation**: Store raw API responses or HTML in `raw/{company}/YYYY-MM-DD.json` (or `.html`). If parsing logic changes later, we can reprocess.

4. **Monthly reports are static HTML**: No build system needed. Generate `site/YYYY-MM/index.html` files directly.

5. **Detection logic**:
   - NEW = job ID exists at end of month but not start
   - REMOVED = job ID exists at start but not end
   - CHANGED = job ID exists in both but `description_hash` differs

## Directory Structure

```
ai-jobs-tracker/
├── data/{company}/jobs.json      # Current state, array of job objects
├── descriptions/{company}/*.md   # Full job descriptions
├── raw/{company}/YYYY-MM-DD.*    # Daily raw scrapes (JSON or HTML)
├── site/YYYY-MM/index.html       # Monthly reports
├── scripts/                      # Scraper, differ, report generator
├── README.md
└── HANDOFF.md
```

## Data Model

```json
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
```

- `id`: Slugified from title, must be unique per company, used as filename for description
- `description_hash`: First 12 chars of SHA256 of description text
- Dates are ISO format `YYYY-MM-DD`

## Scraping Notes

### Anthropic
- Uses Greenhouse
- **JSON API**: `https://api.greenhouse.io/v1/boards/anthropic/jobs` — returns job list
- **Job details**: `https://api.greenhouse.io/v1/boards/anthropic/jobs/{id}` — returns full description
- No auth required

### OpenAI
- Uses Ashby (switched from Greenhouse ~2024)
- Careers page: `https://openai.com/careers/`
- **Likely API**: Check network tab on careers page for Ashby API calls
- Format is typically `https://api.ashbyhq.com/posting-api/job-board/{board_id}`

### Google DeepMind
- Uses Google's internal careers system
- Careers page: `https://deepmind.google/careers/`
- **Probably needs HTML scraping** — inspect the page, may have embedded JSON in script tags
- Jobs link to Google Careers (`careers.google.com`)

## Next Steps (Suggested Order)

### 1. Write the Anthropic scraper first
Anthropic has the cleanest API. Get this working end-to-end:
- Fetch from Greenhouse API
- Parse into job objects
- Save raw response to `raw/anthropic/YYYY-MM-DD.json`
- Update `data/anthropic/jobs.json`
- Save/update descriptions in `descriptions/anthropic/`

### 2. Generalize to other companies
- OpenAI (Ashby API)
- DeepMind (likely HTML scraping)

### 3. Build the differ
Compare two snapshots of `jobs.json` (by git commit or by date) and output:
- List of new jobs
- List of removed jobs  
- List of changed jobs (with dates of change if possible)

### 4. Build the report generator
Take diff output + job data and generate `site/YYYY-MM/index.html` using the existing template as a base.

### 5. Automation
- GitHub Action or cron job to run scraper daily
- GitHub Action to generate monthly report on 1st of each month

## Technical Preferences

- **Language**: Python is fine, or Node/TypeScript if preferred
- **Dependencies**: Minimize. `requests` or `httpx` for HTTP, stdlib for JSON/hashing
- **No database**: Files + git only
- **Testing**: At minimum, test the differ logic with fixture data

## Questions You Might Have

**Q: What if a job ID changes but it's clearly the same role?**
A: Don't try to be clever. If the ID changes, it's a removal + addition. Keep it simple.

**Q: What about jobs that get reposted (removed then re-added)?**
A: Track by ID. If same ID reappears, `first_seen` stays the same, `last_seen` updates. If it's a new ID, it's a new job.

**Q: How to handle rate limiting?**
A: Be polite. One request per second is plenty. We're only hitting 3 sites once per day.

**Q: What timezone for dates?**
A: UTC. Keep it simple.

## Files to Look At

1. `site/2026-01/index.html` — The template. This is what the output should look like.
2. `data/anthropic/jobs.json` — Example data structure.
3. `README.md` — Project overview and structure docs.
