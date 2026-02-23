# ZONA RATED Bot

A gated Telegram Supergroup bot for sharing video content with referral-based access control, affiliate monetization, and verified redirect tracking.

Built with Python, aiogram 3.x, asyncpg, PostgreSQL, and aiohttp.

---

## Features

- **Referral-gated access** -- Users must invite a configurable number of people before they can join the supergroup
- **Bilingual UI** -- Indonesian and English; users choose on first interaction
- **Forum-based content organization** -- Categories are Telegram forum topics managed by the bot
- **Video management wizard** -- Admin 6-step flow: title, categories, description, file, thumbnail, affiliate override, confirm & post
- **Auto-thumbnail extraction** -- ffmpeg extracts JPEG frames from video URLs
- **ShrinkMe.io URL shortening** -- Video download URLs shortened automatically at add-time
- **Verified redirect tracking** -- Embedded aiohttp web server marks real browser visits and auto-delivers videos
- **Download deep links** -- `t.me/bot?start=dl_{id}` deep links in topic posts, handled in private chat
- **Dynamic admin panel** -- All config settings viewable/editable from the bot, plus statistics, user management, broadcast
- **Background scheduler** -- Detects newly qualified users every 60 seconds and notifies them
- **One-time invite links** -- Verified users get expiring invite links (Method 3 hybrid join security)
- **Clean text UI** -- No emojis or icons anywhere

---

## Tech Stack

| Component        | Technology                          |
| ---------------- | ----------------------------------- |
| Language         | Python 3.12+                        |
| Telegram SDK     | aiogram 3.x                         |
| Database         | PostgreSQL 14+                      |
| DB driver        | asyncpg                             |
| Web server       | aiohttp (embedded, same process)    |
| Thumbnails       | ffmpeg                              |
| URL shortener    | ShrinkMe.io API                     |
| Reverse proxy    | Caddy / nginx (production) or ngrok (dev) |

---

## Project Structure

```
rated-bot/
  .env                    # Environment variables (not committed)
  .env.example            # Template for .env
  run.py                  # Convenience entry point
  requirements.txt        # Python dependencies
  CHANGELOG.md            # Version history
  database/
    schema.sql            # Full DB schema + seed data
  bot/
    __init__.py
    __main__.py           # Bot + web server startup
    config.py             # Loads .env into typed Settings
    i18n.py               # Bilingual translation strings
    states.py             # FSM state definitions
    scheduler.py          # Background periodic tasks
    web.py                # aiohttp redirect tracking server
    db/
      pool.py             # asyncpg connection pool
      config_repo.py      # Config CRUD
      user_repo.py        # User CRUD
      referral_repo.py    # Referral tracking
      topic_repo.py       # Category/topic management
      video_repo.py       # Video CRUD + download sessions
    handlers/
      __init__.py         # Router registration
      start.py            # /start, deep links, onboarding
      admin.py            # /admin panel, config editor
      video.py            # /addvideo wizard, delivery, callbacks
      join.py             # Verification checks, invite links
      join_request.py     # Supergroup join request handler
      common.py           # /status, /help, /mylink, fallback
    keyboards/
      inline.py           # All inline keyboard builders
    utils/
      shortener.py        # ShrinkMe.io API integration
      thumbnail.py        # ffmpeg thumbnail extraction
```

---

## Prerequisites

1. **Python 3.12 or higher**
2. **PostgreSQL 14 or higher**
3. **ffmpeg** (for thumbnail extraction from video URLs)
4. **A Telegram Bot** created via [@BotFather](https://t.me/BotFather)
5. **A Telegram Supergroup** with forum/topics mode enabled
6. **A public URL** for the redirect tracking server (Caddy/nginx with HTTPS, or ngrok for development)

---

## Production Deployment (Step by Step)

### 1. Provision the Server

Use any Linux VPS (Ubuntu 22.04+ recommended). Minimum: 1 vCPU, 1 GB RAM, 10 GB disk.

```bash
sudo apt update && sudo apt upgrade -y
```

### 2. Install System Dependencies

```bash
# Python
sudo apt install -y python3 python3-pip python3-venv

# PostgreSQL
sudo apt install -y postgresql postgresql-contrib

# ffmpeg
sudo apt install -y ffmpeg
```

### 3. Set Up PostgreSQL

```bash
sudo -u postgres psql
```

Inside the PostgreSQL shell:

```sql
CREATE USER ratedbot WITH PASSWORD 'your_secure_password';
CREATE DATABASE rated_bot OWNER ratedbot;
GRANT ALL PRIVILEGES ON DATABASE rated_bot TO ratedbot;
\q
```

### 4. Initialize the Database Schema

```bash
sudo -u postgres psql -d rated_bot -f /path/to/rated-bot/database/schema.sql
```

This creates all tables (config, users, referrals, topics, videos, download_sessions, downloads, invite_links) and seeds default config values.

### 5. Clone the Repository

```bash
cd /opt
git clone https://github.com/ourcaldo/zonarated_bot.git rated-bot
cd rated-bot
```

### 6. Create a Virtual Environment

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install --upgrade pip
pip install -r requirements.txt
```

This installs aiogram, asyncpg, python-dotenv, and aiohttp (pulled in by aiogram).

### 7. Configure Environment Variables

```bash
cp .env.example .env
nano .env
```

Fill in the values:

```dotenv
# Telegram Bot Token (from @BotFather)
BOT_TOKEN=123456789:AABBCCDDEEFFaabbccddeeff

# Telegram Supergroup ID (negative number, e.g. -1001234567890)
SUPERGROUP_ID=-1001234567890

# PostgreSQL Connection URL
DATABASE_URL=postgresql://ratedbot:your_secure_password@localhost:5432/rated_bot
```

### 8. Set Initial Config in the Database

After starting the bot once (to verify it connects), update config values either from the bot's admin panel (`/admin` > Settings) or directly via SQL:

```sql
UPDATE config SET value = '5418740718' WHERE key = 'ADMIN_IDS';
UPDATE config SET value = '3' WHERE key = 'REQUIRED_REFERRALS';
UPDATE config SET value = 'https://your-affiliate-link.com' WHERE key = 'AFFILIATE_LINK';
UPDATE config SET value = 'your_shrinkme_api_key' WHERE key = 'SHRINKME_API_KEY';
UPDATE config SET value = 'https://yourdomain.com' WHERE key = 'REDIRECT_BASE_URL';
```

> **ADMIN_IDS** -- comma-separated Telegram user IDs who can access `/admin`
>
> **REDIRECT_BASE_URL** -- the public URL of your redirect tracking server (e.g. `https://yourdomain.com`). This is how download links are built: `{REDIRECT_BASE_URL}/{session_token}`.

### 9. Set Up HTTPS Reverse Proxy (Caddy)

The embedded web server listens on port 8080. You need a reverse proxy with HTTPS in production.

**Option A: Caddy (recommended -- auto HTTPS)**

```bash
sudo apt install -y debian-keyring debian-archive-keyring apt-transport-https curl
curl -1sLf 'https://dl.cloudsmith.io/public/caddy/stable/gpg.key' | sudo gpg --dearmor -o /usr/share/keyrings/caddy-stable-archive-keyring.gpg
curl -1sLf 'https://dl.cloudsmith.io/public/caddy/stable/debian.deb.txt' | sudo tee /etc/apt/sources.list.d/caddy-stable.list
sudo apt update
sudo apt install caddy
```

Create `/etc/caddy/Caddyfile`:

```
yourdomain.com {
    reverse_proxy localhost:8080
}
```

```bash
sudo systemctl enable caddy
sudo systemctl restart caddy
```

Caddy will automatically obtain and renew Let's Encrypt certificates.

**Option B: nginx + certbot**

```bash
sudo apt install -y nginx certbot python3-certbot-nginx
```

Create `/etc/nginx/sites-available/ratedbot`:

```nginx
server {
    server_name yourdomain.com;

    location / {
        proxy_pass http://127.0.0.1:8080;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }
}
```

```bash
sudo ln -s /etc/nginx/sites-available/ratedbot /etc/nginx/sites-enabled/
sudo certbot --nginx -d yourdomain.com
sudo systemctl enable nginx
sudo systemctl restart nginx
```

### 10. Create a systemd Service

Create `/etc/systemd/system/ratedbot.service`:

```ini
[Unit]
Description=ZONA RATED Telegram Bot
After=network.target postgresql.service

[Service]
Type=simple
User=www-data
Group=www-data
WorkingDirectory=/opt/rated-bot
ExecStart=/opt/rated-bot/.venv/bin/python run.py
Restart=always
RestartSec=5
EnvironmentFile=/opt/rated-bot/.env

[Install]
WantedBy=multi-user.target
```

> Adjust `User`, `WorkingDirectory`, and `ExecStart` paths to match your setup.

```bash
sudo systemctl daemon-reload
sudo systemctl enable ratedbot
sudo systemctl start ratedbot
```

### 11. Verify Everything is Running

```bash
# Check bot service status
sudo systemctl status ratedbot

# Check logs
sudo journalctl -u ratedbot -f

# Test redirect server
curl -I https://yourdomain.com/test-token
# Should return 404 (invalid token) -- confirms the web server is reachable
```

### 12. Configure the Bot in the Supergroup

1. Add the bot to your supergroup as an **administrator** with permissions: manage topics, invite users via link, delete messages, ban users
2. Enable **forum/topics mode** in the supergroup settings
3. Use `/admin` in a private chat with the bot to:
   - Add categories (creates forum topics automatically)
   - Set the "All Videos" topic
   - Add videos via the wizard
   - Adjust referral requirements and other settings

---

## Running Locally (Development)

```bash
git clone https://github.com/ourcaldo/zonarated_bot.git rated-bot
cd rated-bot
python -m venv .venv

# Windows
.venv\Scripts\activate

# Linux/macOS
source .venv/bin/activate

pip install -r requirements.txt
cp .env.example .env
# Edit .env with your values

python run.py
```

For the redirect tracking server to work locally, use **ngrok** to expose port 8080:

```bash
ngrok http 8080 --url=your-static-domain.ngrok-free.app
```

Then set `REDIRECT_BASE_URL` to `https://your-static-domain.ngrok-free.app` in the bot's admin settings.

---

## Admin Commands

All admin commands are available via `/admin` in a private chat with the bot (restricted to user IDs listed in `ADMIN_IDS` config).

| Menu                | Actions                                                        |
| ------------------- | -------------------------------------------------------------- |
| **Statistics**      | Total users, verified, joined, referral stats                  |
| **Settings**        | View/edit all config keys (referrals, affiliate, welcome, etc) |
| **User Management** | Approve user by ID, look up user details                       |
| **Broadcast**       | Send HTML message to all users                                 |
| **Manage Categories**   | List, add, remove categories; set "All Videos" topic               |
| **Add Video**       | Launch the 6-step video upload wizard                          |

---

## How the Download Flow Works

1. Admin posts a video via `/addvideo` wizard. The bot creates a topic post with a "Download" deep link button.
2. User clicks the deep link button, which opens a private chat with `?start=dl_{video_id}`.
3. Bot creates a 10-minute download session (UUID token) and shows the user an "Open Link" button.
4. The button URL points to `{REDIRECT_BASE_URL}/{session_token}`.
5. When the user opens the link in their browser:
   - The embedded web server validates the session (not expired, not already used).
   - Marks `visited_at` timestamp (verified visit).
   - Auto-delivers the video to the user's Telegram chat.
   - 302-redirects the browser to the affiliate URL.
6. No manual "Done" button needed. Delivery is instant and verified.

---

## Database Config Keys

| Key                    | Description                                           | Default |
| ---------------------- | ----------------------------------------------------- | ------- |
| `REQUIRED_REFERRALS`   | Number of referrals needed to join the supergroup      | `1`     |
| `INVITE_EXPIRY_SECONDS`| How long a one-time invite link stays valid (seconds)  | `300`   |
| `ADMIN_IDS`            | Comma-separated Telegram user IDs of bot admins        | (empty) |
| `AFFILIATE_LINK`       | Default affiliate URL shown before downloads           | (empty) |
| `WELCOME_MESSAGE`      | Welcome message sent on first `/start`                 | `Selamat datang di ZONA RATED!` |
| `SHRINKME_API_KEY`     | ShrinkMe.io API key for URL shortening                 | (empty) |
| `REDIRECT_BASE_URL`    | Public URL of the redirect tracking server             | (empty) |

All keys are editable at runtime from the bot's admin panel (Settings menu).

---

## Updating in Production

```bash
cd /opt/rated-bot
git pull origin main
sudo systemctl restart ratedbot
```

If `schema.sql` has new columns or tables, apply the migration:

```bash
sudo -u postgres psql -d rated_bot -f database/schema.sql
```

> The schema uses `CREATE TABLE IF NOT EXISTS` and `ON CONFLICT DO NOTHING`, so it's safe to re-run.

---

## Troubleshooting

| Issue | Solution |
| ----- | -------- |
| Bot doesn't respond | Check `sudo systemctl status ratedbot` and `journalctl -u ratedbot -f` for errors |
| Database connection refused | Verify PostgreSQL is running: `sudo systemctl status postgresql` |
| Redirect links return 502 | Ensure the bot process is running and listening on port 8080. Check reverse proxy config. |
| ffmpeg thumbnail fails | Verify ffmpeg is installed: `ffmpeg -version`. For remote URLs, ensure the server can reach them. |
| ShrinkMe shortening fails | Check if the API key is valid. The bot falls back to raw URLs automatically. |
| Users can't join supergroup | Verify the bot is an admin in the supergroup with invite link permissions. |
| `/admin` not working | Ensure your Telegram user ID is in the `ADMIN_IDS` config value. |

---

## License

Private project. All rights reserved.
