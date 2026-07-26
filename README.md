# freelance-job-finder

AI-powered tool to automatically search for freelance **MuleSoft / TIBCO / TIBCO AMX BPM / Integration** projects across German freelance platforms, rank them by relevance, and deliver a daily digest via **Telegram** and **Email**.

## Architecture

```
                    GitHub Copilot Agent
                             │
                 Executes on GitHub Actions
                             │
                    Python / Playwright
                             │
        ┌──────────────┬──────────────┬──────────────┬─────────────┐
        │              │              │              │             │
 freelancermap.de  freelance.de    gulp.de      jobserve.com
        │              │              │              │
        └──────────────┴──────────────┴──────────────┘
                             │
                   Normalize Results
                             │
              Remove duplicates & rank
                             │
                 AI summarises relevance
                             │
         Email / Telegram
                             │
                      Daily at 08:00 CET
```

## Technology Stack

| Component | Technology |
|---|---|
| Language | Python 3.12 |
| Browser Automation | Playwright |
| HTML Parsing | BeautifulSoup4 |
| Data Model | Pydantic v2 |
| Scheduling | GitHub Actions Cron |
| Notifications | Telegram Bot API + SMTP Email |
| Database | SQLite (dedup / history tracking) |
| Configuration | YAML |

## Repository Structure

```
freelance-job-finder/
├── .github/workflows/
│   ├── daily_search.yml     # scheduled + manual run
│   └── tests.yml            # pytest on push/PR
├── src/
│   ├── scrapers/
│   │   ├── base.py
│   │   ├── freelancermap.py
│   │   ├── freelance_de.py
│   │   ├── gulp.py
│   │   └── jobserve.py
│   ├── notifiers/
│   │   ├── base.py
│   │   ├── telegram_notifier.py
│   │   └── email_notifier.py
│   ├── models.py
│   ├── normalizer.py
│   ├── deduplicator.py
│   ├── ranker.py
│   ├── storage.py
│   ├── config.py
│   └── main.py
├── config/
│   └── config.yaml          # user-editable search/notification settings
├── tests/
│   ├── test_models.py
│   ├── test_normalizer.py
│   ├── test_deduplicator.py
│   └── test_ranker.py
├── requirements.txt
├── pyproject.toml
├── .env.example
└── README.md
```

## Setup (Local)

### 1. Clone & create a virtual environment

```bash
git clone https://github.com/sili2017/freelance-job-finder.git
cd freelance-job-finder
python -m venv .venv
source .venv/bin/activate   # Windows: .venv\Scripts\activate
```

### 2. Install dependencies

```bash
pip install -r requirements.txt
playwright install --with-deps chromium
```

### 3. Configure credentials

Copy `.env.example` to `.env` and fill in your credentials:

```bash
cp .env.example .env
# Edit .env with your Telegram token, chat ID, and SMTP settings
```

### 4. Configure search settings

Edit `config/config.yaml` to adjust:
- `search.keywords` – what to search for
- `search.locations` – where to search
- `sites` – enable/disable individual scrapers
- `notifications` – enable/disable Telegram/email
- `ranking.weights` – adjust keyword importance

### 5. Run locally

```bash
python -m src.main
```
### .venv/bin/python -m src.main

## Running Tests

```bash
pytest --tb=short -v
```

No network access or secrets are required for tests — everything uses fixtures/mocks.

## GitHub Actions Secrets

Configure the following secrets in your repository's **Settings → Secrets and variables → Actions**:

| Secret | Description |
|---|---|
| `TELEGRAM_BOT_TOKEN` | Telegram Bot API token (from @BotFather) |
| `TELEGRAM_CHAT_ID` | Telegram chat/channel ID to send messages to |
| `SMTP_HOST` | SMTP server hostname (e.g. `smtp.gmail.com`) |
| `SMTP_PORT` | SMTP port (usually `587` for STARTTLS) |
| `SMTP_USERNAME` | SMTP login username |
| `SMTP_PASSWORD` | SMTP account password |
| `SMTP_FROM` | Sender email address |
| `SMTP_TO` | Recipient email address |

## Scheduling

The GitHub Actions workflow (`daily_search.yml`) runs at **07:00 UTC** every day.

- CET (UTC+1, winter): that's 08:00 CET ✓
- CEST (UTC+2, summer): that's 09:00 CEST (one hour later)

If you need a strictly fixed 08:00 CET in both seasons, you would need two separate cron expressions or use a different approach. The current single-cron solution is a pragmatic tradeoff.

## SQLite History / Deduplication

The SQLite database (`data/seen_postings.db`) persists across daily runs using GitHub Actions cache (key: `seen-postings-db-<os>-<run_id>`). Older cache keys are used as restore fallbacks so deduplication history is maintained across runs. The database is **not committed** to the repository.

## Disclaimer & Legal

> ⚠️ **Important**: This tool scrapes publicly accessible pages on freelancermap.de, freelance.de, gulp.de, and jobserve.com. Before using it, you must:
>
> 1. Read and comply with each site's **Terms of Service** and **robots.txt**.
> 2. The CSS selectors in the scrapers are **best-effort placeholders** written without live site access and **must be validated** against the actual live sites before relying on them.
> 3. Rate limiting (2–5 second delays) is implemented by default; respect site operators and do not increase request rates.
> 4. **You are solely responsible** for ensuring your use of this tool complies with applicable laws and the terms of each service.
> 5. The authors of this tool accept no liability for misuse.
