# Changelog

All notable changes to the ZONA RATED Bot project are documented here.

---

## [v4.0] - 2026-02-21

### Added
- **Bilingual support (Indonesian / English)**: New `bot/i18n.py` module with ~40 translation keys covering all user-facing messages. Users choose their language on first `/start`.
- **Language selection flow**: First-time users see an inline keyboard to pick Indonesia or English. Choice is stored in the `language` column (`VARCHAR(2)`) added to the users table.
- **Share button with `switch_inline_query`**: The "Bagikan Link" / "Share Link" button opens Telegram's native share picker pre-filled with the user's referral link and message.
- **Background scheduler** (`bot/scheduler.py`): Runs every 60 seconds alongside polling. Detects users who now meet the referral requirement (e.g. after a DB change or config update) and sends them a congratulations message with a join button.
- **Fallback message handler**: Any unrecognized text message now gets a reply. Registered users see their referral link + progress + inline buttons (Share, Status, Help). Unregistered users see a "Start" button linking to the bot.
- **Fallback callback buttons**: `fb_status` and `fb_help` callbacks provide quick Status and Help responses without typing commands.
- **`UserOnboarding` FSM state**: `choosing_language` state used during first-time `/start` to wait for language selection.
- **Admin panel notification on approve**: When admin approves a user via the admin panel, the approved user receives a notification in their chosen language.

### Changed
- **All emojis/icons removed**: Every bot message, button label, admin panel text, and database seed value is now clean text with no emojis or icons.
- **"Supergroup" renamed to "ZONA RATED"**: All user-facing strings now say "ZONA RATED" instead of "supergroup" (e.g. "Join ZONA RATED", "Selamat datang di ZONA RATED!").
- **`/start` flow redesigned**: No longer sends the invite link immediately. New flow: language picker (first time) -> welcome message with referral link + Share button + Check Requirements button.
- **Check Requirements handler**: Renamed from `join_group` callback to `check_req`. All `edit_text` calls wrapped in `try/except TelegramBadRequest` to prevent "message is not modified" errors.
- **Admin panel**: All emoji prefixes removed from menu text, statistics, settings display, user lookup, broadcast messages. Admin commands (settings, approve, lookup) unchanged functionally.
- **Welcome message in DB**: Updated from "Selamat datang di Rated Bot! (corrupted emoji)" to clean "Selamat datang di ZONA RATED!".
- **`config_repo.py` default fallback**: Changed from "Selamat datang di Zona Rated!" to "Selamat datang di ZONA RATED!".
- **`schema.sql` seed data**: WELCOME_MESSAGE seed updated to "Selamat datang di ZONA RATED!" with no emoji.
- **`__main__.py`**: Now starts the scheduler as an `asyncio.create_task` alongside polling, and cancels it on shutdown.
- **`keyboards/inline.py`**: Added `language_keyboard()`, `fallback_keyboard()`, `start_keyboard()`. Reworked `welcome_keyboard()` to accept i18n params and use `switch_inline_query`. All button builders now take text as parameter for i18n.
- **`common.py`**: Added imports for `F`, `fallback_keyboard`, `start_keyboard`. Added `cb_fb_status`, `cb_fb_help` callback handlers and `fallback()` catch-all message handler.
- **`project-documentation.md`**: Updated to v4.0 — reflects new onboarding flow, language selection, no-emoji policy, scheduler, fallback handler, admin panel design, and current tech stack.

### Fixed
- **TelegramBadRequest "message is not modified"**: Previously crashed when user clicked "Check Requirements" and the message content was unchanged. Now caught and silently ignored.
- **Corrupted emoji in DB welcome message**: The stored value had garbled UTF-8 bytes from a previous emoji. Cleaned via direct SQL update.

---

## [v3.0] - 2026-02-21

### Added
- **Interactive admin panel**: `/admin` command opens an inline keyboard dashboard with sub-menus for Statistics, Settings, User Management, and Broadcast. All protected by admin ID check from `config` table.
- **FSM-based admin input**: `AdminInput` states (waiting_referrals, waiting_affiliate, waiting_welcome, waiting_expiry, waiting_approve_id, waiting_lookup_id, waiting_broadcast) for collecting typed input during admin operations.
- **Admin sub-menus**: Statistics (user counts, config summary), Settings (set referrals/affiliate/welcome/expiry), User Management (approve user by ID, lookup user by ID), Broadcast (send message to all users).
- **User lookup**: Admin can look up any user by Telegram ID and see full details (name, username, referral count, verification status, join status, timestamps).
- **Broadcast system**: Admin can send an HTML message to all users with delivery count reporting.

### Changed
- Admin commands replaced from text-based (`/setrequirement`, `/approve`) to fully interactive inline keyboard navigation.
- All admin settings now stored in and read from the `config` database table.

---

## [v2.0] - 2026-02-21

### Added
- **Full bot implementation**: Python + aiogram 3.x + asyncpg + PostgreSQL.
- **Project structure**: `bot/` package with `config.py`, `handlers/`, `keyboards/`, `db/`, `states.py`, `__main__.py`.
- **Database layer**: `schema.sql` with config, users, referrals, videos, download_sessions tables. Repository modules for config, users, and referrals.
- **`/start` command**: Handles deep link referral parameters, creates users, credits referrers, sends notifications.
- **Referral system**: Unique deep links per user, automatic counting, referrer notifications, completion detection.
- **Verification flow**: "Gabung Grup" button checks referral count vs. configurable requirement.
- **Method 3 (Hybrid Join)**: One-time expiring invite links + join request double verification.
- **Join request handler**: Re-verifies user status when they click the invite link and request to join the supergroup.
- **User commands**: `/status` (verification progress), `/help` (command list), `/mylink` (referral link).
- **`.env` configuration**: BOT_TOKEN, SUPERGROUP_ID, DATABASE_URL.
- **`requirements.txt`**: aiogram, asyncpg, python-dotenv.

---

## [v1.0] - 2026-02-21

### Added
- **Project documentation** (`project-documentation.md`): Complete 2300-line specification covering architecture, user journey, verification system, Method 3 security, download process, referral deep dive, implementation roadmap, and best practices.
