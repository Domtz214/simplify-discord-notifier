# Simplify Internship Discord Notifier

Posts new internship listings from [SimplifyJobs/Summer2027-Internships](https://github.com/SimplifyJobs/Summer2027-Internships) straight to a Discord channel on a schedule.

## How it works

```
cron-job.org (external clock)
        │  fires every ~15 min
        ▼
GitHub API → triggers this repo's workflow
        │
        ▼
GitHub Actions runs parse_and_notify.py
        │
        ▼
Fetches the latest listings.json from SimplifyJobs' repo
        │
        ▼
Compares it against seen_jobs.json
        │
        ▼
Any brand-new listings → posted to Discord via webhook
        │
        ▼
seen_jobs.json gets updated and committed back to this repo
```

**Why an external cron service (cron-job.org) instead of just GitHub's built-in scheduler?** Github's scheduler was unreliable, external tool does the job more consistently.

## Files

| File | Purpose |
|---|---|
| `parse_and_notify.py` | Main script — fetches, diffs, and posts new listings |
| `test_notification.py` | Sends one fake/sample listing so you can preview the Discord message design without waiting |
| `seen_jobs.json` | Auto-generated memory of listing IDs already posted |
| `requirements.txt` | Python dependencies (`requests`, `beautifulsoup4`) |
| `.github/workflows/check_jobs.yml` | Runs `parse_and_notify.py` on a schedule |
| `.github/workflows/test-notification.yml` | Manual-only workflow to run `test_notification.py` from the Actions tab |

## Setup (if you're forking/reusing this)

1. **Create a Discord webhook** in the target channel (Channel Settings → Integrations → Webhooks).
2. Add it as a repo secret named `DISCORD_WEBHOOK_URL` (Settings → Secrets and variables → Actions).
3. **Create a fine-grained GitHub Personal Access Token**, scoped to just this repo, with `Actions: Read and write` permission only.
4. Sign up for a free [cron-job.org](https://cron-job.org) account and create a job that `POST`s to:
   ```
   https://api.github.com/repos/{your-username}/{your-repo}/actions/workflows/check_jobs.yml/dispatches
   ```
   with headers `Authorization: Bearer YOUR_TOKEN`, `Accept: application/vnd.github+json`, `Content-Type: application/json`, and body `{"ref":"main"}` — scheduled every 15 minutes.
   I've already done this, we can continue to use my account if needed.
6. Push everything, trigger a manual run once to confirm it works, then let it run.

## Notes

- Not affiliated with SimplifyJobs — this just reads their public data.
