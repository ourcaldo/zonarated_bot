# Feature Specification v2 — Five New Features

> **Status:** Feasibility confirmed — all 5 features are implementable  
> **Date:** 2026-02-24  
> **Scope:** Maintenance mode, duplicate video check, scheduling, auto get & run, admin message differentiation

---

## Overview & Feasibility Summary

| # | Feature | Feasibility | Complexity | New Tables | New Config Keys |
|---|---------|-------------|------------|------------|-----------------|
| 1 | Maintenance Mode | ✅ Very feasible | Low | 0 | 3 |
| 2 | Duplicate Video Check | ✅ Very feasible | Low | 0 | 0 |
| 3 | Scheduling Mode | ✅ Feasible | Medium | 1 | 0 |
| 4 | Auto Get & Run | ✅ Feasible | High | 0 | 3 |
| 5 | Admin vs User Message | ✅ Very feasible | Low | 0 | 0 |

---

## Feature 1: Maintenance Mode

### What It Does
When enabled, the bot responds to **all non-admin users** with a maintenance message instead of processing any command or callback. Admins remain fully functional. Optionally, admin can set a time window (start → end) so the mode auto-activates and auto-deactivates.

### How It Works

**New config keys** (stored in `config` table):

| Key | Default | Description |
|-----|---------|-------------|
| `MAINTENANCE_MODE` | `false` | Master toggle (`true`/`false`) |
| `MAINTENANCE_START` | _(empty)_ | Optional ISO 8601 datetime for auto-enable (e.g. `2026-02-25T02:00:00+07:00`) |
| `MAINTENANCE_END` | _(empty)_ | Optional ISO 8601 datetime for auto-disable |

**Middleware (aiogram outer middleware):**
- A new `MaintenanceMiddleware` class registered on the Dispatcher level
- On every incoming `Update` (message, callback_query, etc.):
  1. Check if sender is admin → if yes, **pass through** (no blocking)
  2. Read `MAINTENANCE_MODE` from DB (with a short in-memory cache, e.g. 30s TTL, to avoid hammering DB)
  3. If `MAINTENANCE_MODE == true`:
     - Check optional time window: if `MAINTENANCE_START`/`MAINTENANCE_END` are set, only block if current time is within the window
     - Reply with a maintenance message (bilingual) and **stop processing**
  4. If `false` or outside time window → pass through normally

**Admin panel integration:**
- New button in admin settings: **"🔧 Maintenance Mode"**
- Toggle callback `adm_toggle_MAINTENANCE_MODE` (already supported by the generic toggle pattern in `admin.py`)
- When toggling ON, ask: "Set time window?" → two options:
  - **"Yes, set schedule"** → prompt for start datetime, then end datetime (FSM states)
  - **"No, enable now indefinitely"** → just set `MAINTENANCE_MODE=true`, clear start/end
- When toggling OFF, clear `MAINTENANCE_START` and `MAINTENANCE_END`

**Scheduler hook:**
- In `scheduler.py`, add a check: if `MAINTENANCE_END` has passed and mode is still `true`, auto-set `MAINTENANCE_MODE=false` and clear the time fields

**i18n keys needed:**
- `maintenance_message` → "⚙️ Bot is under maintenance. Please try again later." / Indonesian equivalent
- `maintenance_schedule_message` → "⚙️ Bot is under maintenance until {end_time}. Please try again later."

### Files to Modify
| File | Changes |
|------|---------|
| `bot/middleware.py` | **NEW FILE** — `MaintenanceMiddleware` class |
| `bot/__main__.py` | Register middleware on Dispatcher |
| `bot/handlers/admin.py` | Add maintenance toggle + optional time window FSM flow |
| `bot/states.py` | Add `AdminInput.waiting_maintenance_start`, `AdminInput.waiting_maintenance_end` |
| `bot/i18n.py` | Add maintenance message strings |
| `bot/scheduler.py` | Add auto-disable check |
| `database/schema.sql` | Add 3 new seed `INSERT` rows in config |

---

## Feature 2: Duplicate Video Link Check

### What It Does
During the "Add Video" wizard, after the admin provides a video link/file, the bot queries the database to check if that exact `file_url` already exists. If it does, the bot shows info about the existing video and presents 3 buttons:
1. **"🔄 Change Video"** — go back to the file input step
2. **"▶️ Continue Anyway"** — proceed with the duplicate URL (allow re-posting)
3. **"❌ Cancel"** — abort the wizard

### How It Works

**In `bot/handlers/video.py`, `waiting_file` state handler:**

After receiving the video URL or file_id:
1. Query `videos` table: `SELECT * FROM videos WHERE file_url = $1 LIMIT 1`
2. If **no match** → proceed as normal (current behavior)
3. If **match found**:
   - Show message: "⚠️ This video has been posted before:\n\n**{title}** ({code})\nCategory: {category}\nPosted: {post_date}"
   - Show inline keyboard with 3 buttons:
     - `vid_dup_change` → clear file from state data, re-prompt for file
     - `vid_dup_continue` → store file in state data, move to next step (thumbnail)
     - `vid_dup_cancel` → clear state, abort wizard

**New DB function** in `video_repo.py`:
```python
async def get_video_by_url(pool, file_url: str) -> Record | None:
    return await pool.fetchrow(
        "SELECT * FROM videos WHERE file_url = $1 LIMIT 1", file_url
    )
```

### Files to Modify
| File | Changes |
|------|---------|
| `bot/handlers/video.py` | Add duplicate check after file input, add 3 callback handlers |
| `bot/db/video_repo.py` | Add `get_video_by_url()` function |
| `bot/keyboards/inline.py` | Add `duplicate_video_keyboard()` function |
| `bot/i18n.py` | Add duplicate warning message strings |

---

## Feature 3: Scheduling Mode

### What It Does
Same as the "Add Video" wizard, but instead of posting immediately after confirmation, the admin picks a date/time and the video is queued. A background scheduler task picks up due items and posts them automatically.

### How It Works

**New table: `scheduled_videos`**

```sql
CREATE TABLE IF NOT EXISTS scheduled_videos (
    schedule_id     BIGSERIAL    PRIMARY KEY,
    title           VARCHAR(255) NOT NULL,
    category        VARCHAR(100),
    description     TEXT,
    file_url        TEXT         NOT NULL,
    thumbnail_data  BYTEA,                          -- thumbnail bytes (if extracted)
    thumbnail_file_id TEXT,                          -- or Telegram file_id
    affiliate_link  TEXT,
    topic_ids       TEXT,                            -- comma-separated topic IDs
    scheduled_at    TIMESTAMPTZ  NOT NULL,           -- when to post
    status          VARCHAR(20)  DEFAULT 'pending',  -- pending | posted | failed | cancelled
    created_by      BIGINT       NOT NULL,           -- admin user_id
    created_at      TIMESTAMPTZ  DEFAULT NOW(),
    posted_at       TIMESTAMPTZ,                     -- actual post timestamp
    error_message   TEXT                             -- if posting failed
);

CREATE INDEX IF NOT EXISTS idx_sv_status ON scheduled_videos(status);
CREATE INDEX IF NOT EXISTS idx_sv_scheduled ON scheduled_videos(scheduled_at);
```

**Admin flow:**

Two entry points from admin panel:
- Existing **"Add Video"** → posts immediately (unchanged)
- New **"Schedule Video"** → same wizard steps, but final step asks for schedule time instead of posting

At the confirmation step:
- Show **"📅 Schedule"** button instead of / in addition to **"✅ Confirm & Post"**
- If "Schedule" chosen → enter `AdminVideo.waiting_schedule_time` state
- Admin inputs date/time (e.g. `2026-02-25 14:00` or offset like `+2h`)
- Bot parses, confirms: "Video will be posted at {datetime}. Confirm?"
- On confirm → insert into `scheduled_videos` with `status=pending`

**Scheduler task** (in `scheduler.py`):
- New periodic check every 60s: `_process_scheduled_videos()`
- Query: `SELECT * FROM scheduled_videos WHERE status = 'pending' AND scheduled_at <= NOW() ORDER BY scheduled_at ASC LIMIT 5`
- For each due video:
  1. Set `status = 'posting'` (lock)
  2. Run the same posting logic as `on_video_confirm` (extract into a shared `post_video()` function)
  3. On success: set `status = 'posted'`, record `posted_at`
  4. On failure: set `status = 'failed'`, record `error_message`

**Admin panel additions:**
- New button: **"📋 Scheduled Queue"** — shows upcoming scheduled posts
- Ability to cancel a pending scheduled video

### New DB module: `bot/db/schedule_repo.py`
- `create_scheduled_video(...)` — insert
- `get_pending_videos(limit)` — fetch due items
- `update_schedule_status(schedule_id, status, error=None)` — update
- `get_upcoming_schedules(limit)` — for admin view
- `cancel_schedule(schedule_id)` — set status to cancelled
- `get_scheduled_by_url(file_url)` — for Feature 4 exclusion check

### Files to Modify/Create
| File | Changes |
|------|---------|
| `bot/db/schedule_repo.py` | **NEW FILE** — schedule CRUD |
| `bot/handlers/video.py` | Add schedule branch at confirmation step, extract shared `post_video()` |
| `bot/handlers/admin.py` | Add "Schedule Video" entry point + "Scheduled Queue" view |
| `bot/states.py` | Add `AdminVideo.waiting_schedule_time` |
| `bot/keyboards/inline.py` | Add schedule-related keyboards |
| `bot/scheduler.py` | Add `_process_scheduled_videos()` task |
| `bot/i18n.py` | Add schedule-related strings |
| `database/schema.sql` | Add `scheduled_videos` table |

---

## Feature 4: Auto Get & Run (Bunny Storage Scanner)

### What It Does
Connects to Bunny Storage via their FTP/HTTP API, lists all video files in each category folder (Asia, Solo, Western, etc.), cross-references with the database to find unposted and unscheduled files, and auto-posts them with a configurable delay between each post.

### Prerequisites
- Bunny Storage API credentials (Storage Zone name + API key)
- Folder structure in Bunny: each category folder name matches a topic name in the DB

### How It Works

**New config keys:**

| Key | Default | Description |
|-----|---------|-------------|
| `BUNNY_STORAGE_API_KEY` | _(empty)_ | Bunny Edge Storage API key |
| `BUNNY_STORAGE_ZONE` | _(empty)_ | Storage zone name |
| `BUNNY_STORAGE_REGION` | _(empty)_ | Region endpoint (e.g. `sg`, `de`, empty for default Falkenstein) |

**Bunny Storage HTTP API** (not FTP — HTTP is simpler and async-friendly):
```
GET https://{region}.storage.bunnycdn.com/{zone_name}/{path}/
Headers: AccessKey: {api_key}
```
Returns JSON array of file objects: `{ "ObjectName": "video.mp4", "Path": "/zone/Asia/", "Length": 12345, "IsDirectory": false, ... }`

**New utility: `bot/utils/bunny_storage.py`**
- `list_folder(path: str) -> list[dict]` — list files/subfolders
- `list_video_files(path: str) -> list[dict]` — filter to video extensions (`.mp4`, `.mkv`, `.avi`, `.mov`, `.webm`, `.wmv`)
- `get_file_url(path: str) -> str` — construct CDN URL from file path

**Auto Get & Run flow (admin-triggered):**

1. Admin clicks **"🔄 Auto Get & Run"** in admin panel
2. Bot shows category list (from DB topics) + "All Categories" option
3. Admin selects category/categories
4. Admin sets **delay** between posts (preset buttons: 15m, 30m, 1h, 2h, custom)
5. Bot scans Bunny Storage for the selected category folder(s)
6. For each video file found:
   - Build CDN URL: `https://{cdn_hostname}/{category}/{filename}`
   - Check `videos` table: does a record with this `file_url` already exist? → **skip**
   - Check `scheduled_videos` table: is this URL already scheduled? → **skip**
   - Remaining files = **new, unposted videos**
7. Bot shows summary: "Found {X} new videos in {category}. Post with {delay} delay?"
8. On confirm → create entries in `scheduled_videos` with staggered `scheduled_at` times:
   - Video 1: NOW + delay
   - Video 2: NOW + 2×delay
   - Video N: NOW + N×delay
9. The scheduler (Feature 3) picks them up and posts them on time

**Title auto-generation:** File name → title (strip extension, replace `_`/`-` with spaces, title-case)

**Why this design?** Instead of a long-running blocking process, we convert Auto Get & Run into scheduled video entries. This means:
- Progress survives bot restarts
- Admin can cancel individual items from the schedule queue
- No need for a separate long-running background task
- Reuses the scheduler from Feature 3

### Files to Modify/Create
| File | Changes |
|------|---------|
| `bot/utils/bunny_storage.py` | **NEW FILE** — Bunny Storage API client |
| `bot/handlers/admin.py` | Add Auto Get & Run flow (category select, delay input, scan, confirm) |
| `bot/states.py` | Add `AdminAutoRun.waiting_categories`, `waiting_delay`, `confirming` |
| `bot/keyboards/inline.py` | Add delay picker keyboard, auto-run confirmation keyboard |
| `bot/db/schedule_repo.py` | Add `get_scheduled_by_url()` for exclusion check |
| `bot/db/video_repo.py` | Add `get_all_file_urls()` for bulk exclusion check |
| `bot/i18n.py` | Add auto-run related strings |
| `database/schema.sql` | Add 3 new config seed rows |

---

## Feature 5: Admin vs User Fallback Message

### What It Does
Currently, when an admin sends a random message to the bot, they get the same generic user fallback (referral link, share button, etc.). Instead:
- **Admin** → show admin panel button (same as `/admin`)
- **Regular user** → keep current behavior (referral info + share/status/help buttons)

### How It Works

**In `bot/handlers/common.py`, modify `fallback()` handler:**

```python
@router.message(F.chat.type == "private")
async def fallback(message: types.Message) -> None:
    pool = await get_pool()
    user_id = message.from_user.id

    # Check if admin
    admin_ids = await config_repo.get_admin_ids(pool)
    if user_id in admin_ids:
        await message.reply(
            "👋 Admin panel:",
            reply_markup=admin_quick_panel_keyboard()
        )
        return

    # ... existing user fallback logic unchanged ...
```

**New keyboard: `admin_quick_panel_keyboard()`**
- **"📊 Open Panel"** → callback `adm_main`
- **"➕ Add Video"** → callback `adm_add_video`
- **"📅 Schedule Video"** → callback (from Feature 3)
- **"🔄 Auto Get & Run"** → callback (from Feature 4)

### Files to Modify
| File | Changes |
|------|---------|
| `bot/handlers/common.py` | Add admin check in `fallback()` |
| `bot/keyboards/inline.py` | Add `admin_quick_panel_keyboard()` |

---

## Implementation Order (Recommended)

The features have dependencies, so the recommended build order is:

```
5 → 1 → 2 → 3 → 4
```

| Step | Feature | Reason |
|------|---------|--------|
| 1st | **#5 Admin Message** | Simplest, zero dependencies, immediate UX fix |
| 2nd | **#1 Maintenance Mode** | Self-contained, introduces middleware pattern |
| 3rd | **#2 Duplicate Check** | Self-contained, small change in video wizard |
| 4th | **#3 Scheduling** | Needed before #4, introduces `scheduled_videos` table and scheduler logic |
| 5th | **#4 Auto Get & Run** | Depends on #3 (scheduling infrastructure), most complex |

---

## New Files Summary

| File | Purpose |
|------|---------|
| `bot/middleware.py` | Maintenance mode middleware |
| `bot/db/schedule_repo.py` | Scheduled videos CRUD |
| `bot/utils/bunny_storage.py` | Bunny Storage API client |

## Modified Files Summary

| File | Features |
|------|----------|
| `bot/__main__.py` | #1 (register middleware) |
| `bot/handlers/admin.py` | #1, #3, #4 (new admin flows) |
| `bot/handlers/video.py` | #2, #3 (duplicate check, schedule branch, extract shared posting function) |
| `bot/handlers/common.py` | #5 (admin fallback differentiation) |
| `bot/keyboards/inline.py` | #1, #2, #3, #4, #5 (new keyboards) |
| `bot/states.py` | #1, #3, #4 (new FSM states) |
| `bot/scheduler.py` | #1, #3 (maintenance auto-disable, scheduled video posting) |
| `bot/i18n.py` | #1, #2, #3, #4 (new translation strings) |
| `bot/db/video_repo.py` | #2, #4 (URL lookup, bulk URL fetch) |
| `database/schema.sql` | #1, #3, #4 (new config seeds, scheduled_videos table) |
| `bot/config.py` | #4 (optional: new Bunny Storage settings) |

---

## What I Need From You

1. **Feature 4 (Auto Get & Run):**
   - Bunny Storage Zone name
   - Bunny Storage API key (the Storage-level key, not the Account key)
   - Region (or if default Falkenstein)
   - Confirm: do folder names exactly match your topic/category names in the DB?

2. **Feature 1 (Maintenance Mode):**
   - Should the timezone for scheduling maintenance be fixed (e.g. WIB/UTC+7) or configurable?

3. **Feature 3 (Scheduling):**
   - Same timezone question — what's the default timezone for scheduled posts?
   - Should scheduled videos support the thumbnail extraction flow, or just auto-extract from the URL?

4. **General:**
   - Confirm the implementation order (5 → 1 → 2 → 3 → 4) works for you, or if you want a different priority
