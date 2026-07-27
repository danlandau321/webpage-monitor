# webpage-monitor

Check a web page (or an API endpoint) once a day, and get an email **only when
its content changes** — or on every run if you want a daily "all clear." No
server to run: it uses GitHub Actions' free scheduler.

This is the generic, shareable version of a "watch this page and tell me when it
updates" automation. It ships with no URLs, emails, or secrets — you supply all
of that as configuration, so the repo is safe to make public.

## How it works

Every scheduled run, `monitor.py`:

1. **Fetches** `MONITOR_URL`.
2. **Extracts** the part you care about (the whole body, one JSON field, or the
   text inside a CSS selector).
3. **Fingerprints** it (SHA-256) and compares against the last run's fingerprint,
   stored in `state.json` (committed back to the repo so it persists).
4. **Emails** you if it changed (or on the first run, or every run if
   `ALWAYS_EMAIL=true`).

## Setup (about 10 minutes)

1. **Fork / create** a repo from these files and push them to GitHub.
2. **Add email secrets.** In the repo: Settings → Secrets and variables →
   Actions → *Secrets* tab. Add `SMTP_HOST`, `SMTP_PORT`, `SMTP_USER`,
   `SMTP_PASS`, `EMAIL_FROM`, `EMAIL_TO`. If you use Gmail, `SMTP_PASS` must be an
   **App Password** (myaccount.google.com/apppasswords), not your login password.
3. **Add what-to-watch variables.** Same screen, *Variables* tab. At minimum set
   `MONITOR_URL` and `MONITOR_MODE`. Add `MONITOR_FIELD`, `MONITOR_SELECTOR`,
   `MONITOR_HEADERS`, `MONITOR_LABEL`, `ALWAYS_EMAIL` as needed.
4. **Pick a time.** Edit the `cron` line in `.github/workflows/monitor.yml`
   (it's in UTC).
5. **Test it now.** Actions tab → *webpage-monitor* → *Run workflow*. The first
   run emails you a baseline confirmation.

## Choosing an extraction mode

- `raw` — watch the entire response. Simple, but noisy if the page has anything
  that changes on every load (timestamps, tokens, ads).
- `json` — best when the page is backed by an API that returns JSON. Point
  `MONITOR_FIELD` at the exact field (dot path, e.g. `data.items.0.title`). This
  is the most robust option when it's available.
- `selector` — watch just one element of an HTML page via a CSS selector in
  `MONITOR_SELECTOR` (e.g. `#notice`, `.alert-banner`). Needs `beautifulsoup4`.

Tip: many "web pages" load their real content from a JSON API in the background.
If `raw` mode sees an almost-empty page, open your browser's Network tab, find
the request that returns the data, and point the monitor at that URL in `json`
mode with any headers it needs (`MONITOR_HEADERS`). That's usually more reliable
than scraping the rendered HTML.

## Local test

```bash
cp .env.example .env      # fill in real values (do NOT commit this file)
set -a; . ./.env; set +a
pip install -r requirements.txt
python monitor.py
```

## Honest limitations

- **Scheduled runs can be late.** GitHub Actions cron is best-effort and may lag
  a few minutes at busy times.
- **Schedules pause after 60 days** of no repo activity; any push re-enables them.
- **State lives in the repo.** The committed `state.json` reveals the last content
  seen — fine for public info, but don't monitor anything private in a public repo.
- **UTC only.** The cron doesn't follow daylight saving; a fixed UTC time drifts
  by an hour across DST changes.

## License

MIT — do whatever you like.
