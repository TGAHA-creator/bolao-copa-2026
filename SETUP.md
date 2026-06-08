# Daily Bolão Copa 2026 email — setup

This makes the daily email run **on its own** in GitHub's cloud. No Claude plan
feature, no send-capable Gmail connector, and your Mac does not need to be on.

How it works: a GitHub Actions cron triggers once a day → `scripts/send_daily_email.py`
reads your routine spec from the repo, asks the Anthropic API to write today's
email, and sends it via SMTP to `tiagosa@yahoo.com.br`.

## Files to add to the repo `TGAHA-creator/bolao-copa-2026`

```
.github/workflows/daily-bolao-email.yml
scripts/send_daily_email.py
bolao-copa-2026-routine.md      <- your existing routine spec (the source of truth)
data/                            <- optional: any data files the email should use
```

## One-time setup (≈10 minutes)

### 1. Get an email app password
An app password is a special password just for apps — separate from your login.

- **Yahoo:** Account Security → "Generate app password" (requires 2-step verification on).
  SMTP host `smtp.mail.yahoo.com`, port `465`.
- **Gmail (alternative):** myaccount.google.com → Security → App passwords (requires 2-step verification).
  SMTP host `smtp.gmail.com`, port `465`. If you use Gmail to send, set the `SMTP_HOST` variable accordingly.

The "from" address is just whatever mailbox the app password belongs to — the
recipient is always `tiagosa@yahoo.com.br`, so the origin doesn't matter.

### 2. Get an Anthropic API key
console.anthropic.com → API Keys → Create Key. Note: this uses pay-as-you-go API
credits (a few cents/month for one short email a day), separate from any Claude
subscription.

### 3. Add the secrets to GitHub
In the repo: **Settings → Secrets and variables → Actions → New repository secret.**
Add these three secrets:

| Secret name         | Value                                  |
|---------------------|----------------------------------------|
| `ANTHROPIC_API_KEY` | your Anthropic API key                 |
| `SMTP_USER`         | the full sending address (e.g. `you@yahoo.com.br`) |
| `SMTP_PASS`         | the app password from step 1           |

Optional **Variables** (same screen, "Variables" tab) if you want to override
defaults: `SMTP_HOST`, `SMTP_PORT`, `EMAIL_TO`, `EMAIL_FROM`, `ANTHROPIC_MODEL`.

### 4. Timezone (already set to Dubai)
The workflow is set to **09:05 Asia/Dubai (UTC+4)** = `5 5 * * *` in UTC. To change
it, edit the `cron` line in `.github/workflows/daily-bolao-email.yml`.

### 5. Test it before trusting the schedule
Repo → **Actions** tab → "Daily Bolão Copa 2026 Email" → **Run workflow**
(this is the manual `workflow_dispatch` trigger). Check that the email arrives and
the run is green. Fix any secret typos, then leave it — the cron takes over.

## Good to know

- **Reliability:** GitHub's scheduled triggers are usually on time but can be
  delayed a few minutes under load. Fine for a daily digest.
- **60-day rule:** GitHub auto-disables scheduled workflows after 60 days with **no
  commits** to the repo. A keepalive step is already built in — each run writes a
  timestamp to `.github/last-run.txt` and commits it with `[skip ci]`, so the repo
  never goes idle. (This needs the `contents: write` permission, already set.)
- **Changing the email content:** edit `bolao-copa-2026-routine.md` (and/or files
  in `data/`) and commit. The script always reads the latest version — no code change needed.
- **Cost control:** the model defaults to `claude-sonnet-4-6`. Switch the
  `ANTHROPIC_MODEL` variable to `claude-haiku-4-5-20251001` for a cheaper run.
