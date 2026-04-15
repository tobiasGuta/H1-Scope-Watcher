# H1 Scope Watcher

> Automatically monitor HackerOne program scope changes and get instant notifications on Discord, Telegram, or Slack.

Never miss a new in-scope target again. H1 Scope Watcher polls the HackerOne API on a schedule, diffs scope entries against the last known state, and fires a rich notification the moment something changes — new domains added, targets removed, bounty eligibility updated, severity ceiling changed.

---

## Features

- **Multi-program support** — watch as many HackerOne programs as you want
- **Smart diffing** — detects added targets, removed targets, and attribute changes (bounty, severity, submission eligibility)
- **Three notification channels** — Discord, Telegram, Slack; only configured ones are used
- **Zero-database design** — snapshots are plain JSON files, no DB setup required
- **First-run safe** — saves a baseline on the first run, notifies from the second run onwards
- **Multiple deployment options** — local cron, Docker (free, no server needed)
 - **Multiple deployment options** — local cron or Docker
- **Environment variable overrides** — keep secrets out of your config file

---

## Prerequisites

| Requirement | Version |
|---|---|
| Python | 3.10+ |
| pip | Latest |
| HackerOne account | With API token |

---

## Quick Start (Local)

### 1. Clone the repository

```bash
git clone https://github.com/yourhandle/h1-scope-watcher.git
cd h1-scope-watcher
```

### 2. Install dependencies

```bash
pip install -r requirements.txt
```

### 3. Create your config file

```bash
cp config.example.yaml config.yaml
```

Open `config.yaml` and fill in:

- Your HackerOne username and API token
- The program handles you want to watch
- At least one notifier (Discord, Telegram, or Slack)

### 4. Run a single check

```bash
python main.py --run-once
```

The first run saves a baseline snapshot. Run it again to test that diffing and notifications work.

### 5. Run continuously (scheduled loop)

```bash
python main.py
```

The watcher will poll on the interval set in `config.yaml` (default: 30 minutes).

---

## Configuration

### `config.yaml` reference

```yaml
hackerone:
  username: "your_h1_username"      # HackerOne username (not email)
  api_token: "your_api_token"       # Settings → API Token (Programs: read)

programs:
  - security                         # HackerOne's own program
  - shopify
  - google

scheduler:
  interval_minutes: 30               # How often to poll (minutes)

storage:
  path: "snapshots"                  # Where to store JSON snapshots

log_level: "INFO"                    # DEBUG | INFO | WARNING | ERROR

notifiers:
  discord:
    webhook_url: "https://discord.com/api/webhooks/..."
    username: "H1 Scope Watcher"     # Optional display name

  telegram:
    bot_token: "123456:ABCDEF..."
    chat_id: "987654321"

  slack:
    webhook_url: "https://hooks.slack.com/services/..."
```

> **Security tip:** Keep `config.yaml` in `.gitignore` (it already is). Use environment variables for secrets when possible.

### Getting a HackerOne API Token

1. Log in to HackerOne
2. Go to **Settings → API Token** → [Direct link](https://hackerone.com/settings/api_token/edit)
3. Create a token with **Programs** read permission
4. Copy the token — it will only be shown once

### Setting up notifiers

<details>
<summary><strong>Discord</strong></summary>

1. Open your Discord server settings
2. Go to **Integrations → Webhooks → New Webhook**
3. Choose a channel, give it a name, click **Copy Webhook URL**
4. Paste the URL into `config.yaml` under `notifiers.discord.webhook_url`

</details>

<details>
<summary><strong>Telegram</strong></summary>

1. Open Telegram and message **@BotFather**
2. Send `/newbot` and follow the prompts → copy the **token**
3. Start a conversation with your new bot (send it any message)
4. Get your `chat_id` by visiting:
   ```
   https://api.telegram.org/bot<YOUR_TOKEN>/getUpdates
   ```
   Look for `"chat": {"id": 123456789}` in the response
5. Fill in both `bot_token` and `chat_id` in `config.yaml`

To use a **group chat**, add the bot to the group and use the group's chat ID (it will be a negative number starting with `-100`).

</details>

<details>
<summary><strong>Slack</strong></summary>

1. Go to [https://api.slack.com/apps](https://api.slack.com/apps) → **Create New App → From scratch**
2. Under **Features**, click **Incoming Webhooks** and toggle it on
3. Click **Add New Webhook to Workspace**, choose a channel, and click **Allow**
4. Copy the Webhook URL and paste it into `config.yaml`

</details>

---

## Using Environment Variables (Recommended)

All sensitive config values can be set via environment variables. They always override `config.yaml`.

```bash
cp .env.example .env
# Edit .env with your values, then:
source .env
python main.py --run-once
```

| Environment Variable | Config equivalent |
|---|---|
| `H1_USERNAME` | `hackerone.username` |
| `H1_API_TOKEN` | `hackerone.api_token` |
| `DISCORD_WEBHOOK_URL` | `notifiers.discord.webhook_url` |
| `TELEGRAM_BOT_TOKEN` | `notifiers.telegram.bot_token` |
| `TELEGRAM_CHAT_ID` | `notifiers.telegram.chat_id` |
| `SLACK_WEBHOOK_URL` | `notifiers.slack.webhook_url` |
| `CHECK_INTERVAL_MINUTES` | `scheduler.interval_minutes` |
| `LOG_LEVEL` | `log_level` |
| `STORAGE_PATH` | `storage.path` |

---

## Docker Deployment

The cleanest way to run the watcher persistently on any server.

### Build and run with Docker Compose

```bash
# 1. Fill in your config
cp config.example.yaml config.yaml
# edit config.yaml...

# 2. Start the container (runs in background)
docker compose up -d

# 3. View live logs
docker compose logs -f

# 4. Stop
docker compose down
```

Snapshots are persisted in a named Docker volume (`snapshots`) so they survive container restarts.

### Run with plain Docker

```bash
docker build -t h1-scope-watcher .

docker run -d \
  --name h1-scope-watcher \
  --restart unless-stopped \
  -v $(pwd)/config.yaml:/app/config.yaml:ro \
  -v h1-snapshots:/app/snapshots \
  -e H1_API_TOKEN="your_token" \
  h1-scope-watcher
```

---

## CLI Reference

```
usage: main.py [-h] [--config CONFIG] [--run-once] [--log-level {DEBUG,INFO,WARNING,ERROR}]

H1 Scope Watcher — Monitor HackerOne program scope changes

options:
  -h, --help            Show this help message and exit
  --config CONFIG       Path to config file (default: config.yaml)
  --run-once            Run a single check then exit
  --log-level LEVEL     Override log level from config
```

### Examples

```bash
# Single check with default config
python main.py --run-once

# Continuous loop with a custom config file
python main.py --config /etc/h1watcher/config.yaml

# Debug a single check
python main.py --run-once --log-level DEBUG
```

---

## Project Structure

```
h1-scope-watcher/
├── main.py                        # Entry point
├── config.example.yaml            # Config template
├── requirements.txt
├── Dockerfile
├── docker-compose.yml
├── .env.example                   # Environment variable template
├── .gitignore
|
├── core/
│   ├── config_loader.py           # YAML + env var config loading
│   ├── fetcher.py                 # HackerOne API client
│   ├── differ.py                  # Scope diff logic
│   ├── storage.py                 # JSON snapshot persistence
│   ├── watcher.py                 # Main orchestrator
│   └── logger.py                  # Logging setup
|
├── notifiers/
│   ├── base.py                    # Abstract base + shared formatting
│   ├── discord.py                 # Discord webhook notifier
│   ├── telegram.py                # Telegram Bot API notifier
│   ├── slack.py                   # Slack incoming webhook notifier
│   └── dispatcher.py              # Fires all configured notifiers

```

---

## Notification Format

All three notifiers produce the same information:

```
HackerOne scope changed!
https://hackerone.com/security
Summary: +2 added, -1 removed

Added (2)
  • `api.example.com` [URL] — Bounty | Critical
  • `*.staging.example.com` [WILDCARD] — No bounty | Medium

Removed (1)
  • `legacy.example.com` [URL] — Bounty | High
```

## Examples:

<img width="1068" height="293" alt="Screenshot From 2026-04-14 21-47-31" src="https://github.com/user-attachments/assets/d018ecd3-8d71-4dac-bf66-39d0ddbcc6a1" />

<img width="297" height="46" alt="Screenshot From 2026-04-14 21-48-11" src="https://github.com/user-attachments/assets/1fab5ae9-dcb7-4927-9c20-49ebb22d08c8" />

<img width="1063" height="936" alt="Screenshot From 2026-04-14 21-48-23" src="https://github.com/user-attachments/assets/18e08901-f806-4fd2-90c4-35712a329aeb" />

---

## Contributing

Pull requests are welcome! Areas where contributions are especially appreciated:

- Additional notifiers (email, PagerDuty, ntfy.sh, Pushover…)
- Web dashboard / history viewer
- Tests and CI improvements
- Support for other bug bounty platforms (Bugcrowd, Intigriti…)

Please open an issue first to discuss significant changes.

---

## Disclaimer

This tool uses the official HackerOne public API with authenticated requests. It does not scrape the website. Please be respectful of HackerOne's API rate limits and terms of service. The author is not responsible for any misuse of this tool.

---

## License

MIT License see [LICENSE](LICENSE) for details.

---

*Built for the bug bounty community. Happy hunting!*
