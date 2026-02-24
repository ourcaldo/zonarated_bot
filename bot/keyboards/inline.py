"""Inline keyboard builders used across handlers."""

from __future__ import annotations

from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup


# ──────────────────────────────────────────────
# Language selection
# ──────────────────────────────────────────────

def language_keyboard() -> InlineKeyboardMarkup:
    """Language picker shown on first /start."""
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(text="Indonesia", callback_data="lang_id"),
                InlineKeyboardButton(text="English", callback_data="lang_en"),
            ]
        ]
    )


# ──────────────────────────────────────────────
# Onboarding / Join flow
# ──────────────────────────────────────────────

def welcome_keyboard(ref_link: str, share_text: str, btn_share: str, btn_check: str) -> InlineKeyboardMarkup:
    """After language is chosen: share link + check requirements."""
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(
                text=btn_share,
                switch_inline_query=share_text,
            )],
            [InlineKeyboardButton(text=btn_check, callback_data="check_req")],
        ]
    )


def welcome_auto_keyboard(btn_join: str) -> InlineKeyboardMarkup:
    """When required referrals = 0, show direct join button."""
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text=btn_join, callback_data="check_req")]
        ]
    )


def check_again_keyboard(
    ref_link: str,
    share_text: str,
    btn_share: str,
    btn_check: str,
) -> InlineKeyboardMarkup:
    """Shown when user hasn't met requirements: share + check again."""
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(
                text=btn_share,
                switch_inline_query=share_text,
            )],
            [InlineKeyboardButton(text=btn_check, callback_data="check_req")],
        ]
    )


def join_supergroup_keyboard(invite_link: str, btn_text: str) -> InlineKeyboardMarkup:
    """Shown when user is verified — contains the one-time invite link."""
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text=btn_text, url=invite_link)]
        ]
    )


def gabung_grup_keyboard(btn_text: str) -> InlineKeyboardMarkup:
    """Generic join prompt (e.g. after completing referrals)."""
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text=btn_text, callback_data="check_req")]
        ]
    )


def fallback_keyboard(
    ref_link: str,
    share_text: str,
    btn_share: str,
    btn_status: str,
    btn_help: str,
) -> InlineKeyboardMarkup:
    """Shown on unrecognized messages for registered users."""
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(
                text=btn_share,
                switch_inline_query=share_text,
            )],
            [
                InlineKeyboardButton(text=btn_status, callback_data="fb_status"),
                InlineKeyboardButton(text=btn_help, callback_data="fb_help"),
            ],
        ]
    )


def start_keyboard() -> InlineKeyboardMarkup:
    """Shown on unrecognized messages for unregistered users."""
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="Start", url="https://t.me/zonarated_bot?start=start")]
        ]
    )


# ──────────────────────────────────────────────
# Download flow
# ──────────────────────────────────────────────

def download_button(video_id: int) -> InlineKeyboardMarkup:
    """Attach to video posts in the supergroup — deep link to bot."""
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(
                text="Download Video",
                url=f"https://t.me/zonarated_bot?start=dl_{video_id}",
            )]
        ]
    )


def video_download_button(url: str) -> InlineKeyboardMarkup:
    """Button sent to user's private chat to open/download the video URL."""
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="Download Video", url=url)]
        ]
    )


def affiliate_button(url: str) -> InlineKeyboardMarkup:
    """Affiliate link sent to user's private chat before download."""
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="Buka Link", url=url)],
            [InlineKeyboardButton(text="Sudah Dikunjungi", callback_data="aff_visited")],
        ]
    )


# ──────────────────────────────────────────────
# Category management (admin)
# ──────────────────────────────────────────────

def admin_category_menu() -> InlineKeyboardMarkup:
    """Sub-menu for category/topic management."""
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(text="List", callback_data="adm_cat_list"),
                InlineKeyboardButton(text="Add", callback_data="adm_cat_add"),
            ],
            [
                InlineKeyboardButton(text="Remove", callback_data="adm_cat_remove"),
                InlineKeyboardButton(text="Set 'All' Topic", callback_data="adm_cat_set_all"),
            ],
            [InlineKeyboardButton(text="< Back", callback_data="adm_main")],
        ]
    )


def category_remove_keyboard(categories: list) -> InlineKeyboardMarkup:
    """List categories as buttons for removal. Each category is a callback."""
    rows = []
    for g in categories:
        label = f"{'[ALL] ' if g['is_all'] else ''}{g['name']}"
        rows.append(
            [InlineKeyboardButton(text=label, callback_data=f"adm_cat_del_{g['topic_id']}")]
        )
    rows.append([InlineKeyboardButton(text="< Back", callback_data="adm_categories")])
    return InlineKeyboardMarkup(inline_keyboard=rows)


def category_set_all_keyboard(categories: list) -> InlineKeyboardMarkup:
    """Pick a category to mark as the 'All Videos' topic."""
    rows = []
    for g in categories:
        label = f"{'>> ' if g['is_all'] else ''}{g['name']}"
        rows.append(
            [InlineKeyboardButton(text=label, callback_data=f"adm_cat_all_{g['topic_id']}")]
        )
    rows.append([InlineKeyboardButton(text="< Back", callback_data="adm_categories")])
    return InlineKeyboardMarkup(inline_keyboard=rows)


def category_picker_keyboard(categories: list, selected_ids: list | None = None) -> InlineKeyboardMarkup:
    """Category picker for the add-video wizard (multi-select toggle).

    Selected categories are prefixed with >> to indicate selection.
    """
    selected_ids = selected_ids or []
    rows = []
    for g in categories:
        if not g["is_all"]:
            is_sel = g["topic_id"] in selected_ids
            label = f">> {g['name']}" if is_sel else g["name"]
            rows.append(
                [InlineKeyboardButton(text=label, callback_data=f"vid_cat_{g['topic_id']}")]
            )
    bottom = []
    if selected_ids:
        bottom.append(InlineKeyboardButton(text="Done", callback_data="vid_cat_done"))
    bottom.append(InlineKeyboardButton(text="Cancel", callback_data="vid_cancel"))
    rows.append(bottom)
    return InlineKeyboardMarkup(inline_keyboard=rows)


def thumbnail_preview_keyboard() -> InlineKeyboardMarkup:
    """Shown after auto-extracting a thumbnail from video URL."""
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="Use This", callback_data="vid_thumb_ok")],
            [InlineKeyboardButton(text="Change Timestamp", callback_data="vid_thumb_change")],
            [InlineKeyboardButton(text="Skip Thumbnail", callback_data="vid_thumb_skip")],
            [InlineKeyboardButton(text="Cancel", callback_data="vid_cancel")],
        ]
    )


def video_skip_keyboard() -> InlineKeyboardMarkup:
    """Skip button for optional fields in the video wizard."""
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="Skip", callback_data="vid_skip")],
            [InlineKeyboardButton(text="Cancel", callback_data="vid_cancel")],
        ]
    )


def video_confirm_keyboard() -> InlineKeyboardMarkup:
    """Confirm or cancel the video before posting."""
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(text="Confirm & Post", callback_data="vid_confirm"),
                InlineKeyboardButton(text="Cancel", callback_data="vid_cancel"),
            ]
        ]
    )


def download_session_button(redirect_url: str) -> InlineKeyboardMarkup:
    """Single 'Open Link' button pointing to verified redirect URL."""
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="Open Link", url=redirect_url)],
        ]
    )


# ──────────────────────────────────────────────
# Admin Panel — Main menu
# ──────────────────────────────────────────────

def admin_main_menu() -> InlineKeyboardMarkup:
    """Top-level admin dashboard."""
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(text="Statistics", callback_data="adm_stats"),
                InlineKeyboardButton(text="Settings", callback_data="adm_settings"),
            ],
            [
                InlineKeyboardButton(text="User Mgmt", callback_data="adm_users"),
                InlineKeyboardButton(text="Categories", callback_data="adm_categories"),
            ],
            [
                InlineKeyboardButton(text="Add Video", callback_data="adm_addvideo"),
                InlineKeyboardButton(text="Schedule Video", callback_data="adm_schedulevideo"),
            ],
            [
                InlineKeyboardButton(text="Auto Get & Run", callback_data="adm_autorun"),
                InlineKeyboardButton(text="Scheduled Queue", callback_data="adm_sched_queue"),
            ],
            [
                InlineKeyboardButton(text="Broadcast", callback_data="adm_broadcast"),
            ],
            [InlineKeyboardButton(text="Close Panel", callback_data="adm_close")],
        ]
    )


def admin_quick_panel_keyboard() -> InlineKeyboardMarkup:
    """Quick panel shown when admin sends a generic message."""
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="Open Panel", callback_data="adm_main")],
            [
                InlineKeyboardButton(text="Add Video", callback_data="adm_addvideo"),
                InlineKeyboardButton(text="Schedule Video", callback_data="adm_schedulevideo"),
            ],
            [
                InlineKeyboardButton(text="Auto Get & Run", callback_data="adm_autorun"),
            ],
        ]
    )


# ──────────────────────────────────────────────
# Admin Panel — Settings sub-menu
# ──────────────────────────────────────────────

# Friendly display names for config keys
_CONFIG_LABELS: dict[str, str] = {
    "REQUIRED_REFERRALS": "Required Referrals",
    "INVITE_EXPIRY_SECONDS": "Invite Expiry (sec)",
    "ADMIN_IDS": "Admin IDs",
    "AFFILIATE_LINK": "Affiliate Link",
    "WELCOME_MESSAGE": "Welcome Message",
    "SHRINKME_API_KEY": "ShrinkMe API Key",
    "SHRINKME_ENABLED": "ShrinkMe Shortener",
    "REDIRECT_BASE_URL": "Redirect Base URL",
    "MAINTENANCE_MODE": "Maintenance Mode",
    "BUNNY_STORAGE_API_KEY": "Bunny Storage Key",
    "BUNNY_STORAGE_ZONE": "Bunny Storage Zone",
    "BUNNY_STORAGE_REGION": "Bunny Storage Region",
}

# Keys that should render as ON/OFF toggle buttons instead of text editor
_TOGGLE_KEYS: set[str] = {"SHRINKME_ENABLED", "MAINTENANCE_MODE"}

# Keys managed by wizards — hidden from the settings list
_HIDDEN_KEYS: set[str] = {"MAINTENANCE_START", "MAINTENANCE_END"}


def admin_settings_menu(config_rows: list | None = None) -> InlineKeyboardMarkup:
    """Sub-menu showing ALL config keys from the database.

    Each config key gets its own edit button with a friendly label.
    Boolean keys in _TOGGLE_KEYS render as toggle buttons (ON/OFF).
    Falls back to static menu if config_rows not provided.
    """
    if config_rows:
        buttons = []
        for cfg in config_rows:
            key = cfg["key"]
            if key in _HIDDEN_KEYS:
                continue
            label = _CONFIG_LABELS.get(key, key.replace("_", " ").title())
            if key in _TOGGLE_KEYS:
                is_on = (cfg["value"] or "").strip().lower() in ("true", "1", "yes")
                toggle_label = f"{label}: {'ON' if is_on else 'OFF'}"
                buttons.append(
                    InlineKeyboardButton(
                        text=toggle_label,
                        callback_data=f"adm_toggle_{key}",
                    )
                )
            else:
                buttons.append(
                    InlineKeyboardButton(
                        text=label,
                        callback_data=f"adm_cfg_{key}",
                    )
                )
        # Arrange in rows of 2
        rows = [buttons[i:i + 2] for i in range(0, len(buttons), 2)]
        rows.append([InlineKeyboardButton(text="< Back", callback_data="adm_main")])
        return InlineKeyboardMarkup(inline_keyboard=rows)

    # Fallback static menu
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="Required Referrals", callback_data="adm_set_referrals")],
            [InlineKeyboardButton(text="Affiliate Link", callback_data="adm_set_affiliate")],
            [InlineKeyboardButton(text="Welcome Message", callback_data="adm_set_welcome")],
            [InlineKeyboardButton(text="Invite Expiry (sec)", callback_data="adm_set_expiry")],
            [InlineKeyboardButton(text="< Back", callback_data="adm_main")],
        ]
    )


# ──────────────────────────────────────────────
# Admin Panel — User management sub-menu
# ──────────────────────────────────────────────

def admin_users_menu() -> InlineKeyboardMarkup:
    """Sub-menu for user operations."""
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(text="Approve User", callback_data="adm_approve"),
                InlineKeyboardButton(text="Lookup User", callback_data="adm_lookup"),
            ],
            [InlineKeyboardButton(text="< Back", callback_data="adm_main")],
        ]
    )


# ──────────────────────────────────────────────
# Admin Panel — generic helpers
# ──────────────────────────────────────────────

def admin_back_main() -> InlineKeyboardMarkup:
    """Single 'Back to menu' button used after displaying info."""
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="< Back to Menu", callback_data="adm_main")]
        ]
    )


def admin_cancel() -> InlineKeyboardMarkup:
    """Cancel current FSM operation and return to menu."""
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="Cancel", callback_data="adm_cancel")]
        ]
    )


# ──────────────────────────────────────────────
# Maintenance mode
# ──────────────────────────────────────────────

def maintenance_toggle_keyboard() -> InlineKeyboardMarkup:
    """Options when enabling maintenance mode."""
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="Enable Now", callback_data="maint_now")],
            [InlineKeyboardButton(text="Set Schedule", callback_data="maint_schedule")],
            [InlineKeyboardButton(text="Cancel", callback_data="adm_cancel")],
        ]
    )


# ──────────────────────────────────────────────
# Duplicate video check
# ──────────────────────────────────────────────

def duplicate_video_keyboard() -> InlineKeyboardMarkup:
    """Shown when a duplicate video URL is detected in the wizard."""
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="Change Video", callback_data="vid_dup_change")],
            [InlineKeyboardButton(text="Continue Anyway", callback_data="vid_dup_continue")],
            [InlineKeyboardButton(text="Cancel", callback_data="vid_cancel")],
        ]
    )


# ──────────────────────────────────────────────
# Video scheduling
# ──────────────────────────────────────────────

def video_confirm_or_schedule_keyboard() -> InlineKeyboardMarkup:
    """Confirm to post now, schedule, or cancel."""
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(text="Confirm & Post", callback_data="vid_confirm"),
                InlineKeyboardButton(text="Schedule", callback_data="vid_schedule"),
            ],
            [InlineKeyboardButton(text="Cancel", callback_data="vid_cancel")],
        ]
    )


def schedule_queue_keyboard(items: list) -> InlineKeyboardMarkup:
    """Display scheduled items with cancel option."""
    rows = []
    for item in items:
        sid = item["schedule_id"]
        title = item["title"][:30]
        status = item["status"]
        sched_at = item["scheduled_at"].strftime("%m-%d %H:%M")
        label = f"[{status}] {title} @ {sched_at}"
        if status == "pending":
            rows.append([
                InlineKeyboardButton(text=label, callback_data=f"sched_info_{sid}"),
                InlineKeyboardButton(text="X", callback_data=f"sched_cancel_{sid}"),
            ])
        else:
            rows.append([InlineKeyboardButton(text=label, callback_data=f"sched_info_{sid}")])
    rows.append([InlineKeyboardButton(text="< Back", callback_data="adm_main")])
    return InlineKeyboardMarkup(inline_keyboard=rows)


# ──────────────────────────────────────────────
# Auto Get & Run
# ──────────────────────────────────────────────

def autorun_category_keyboard(categories: list, selected_ids: list | None = None) -> InlineKeyboardMarkup:
    """Category picker for Auto Get & Run (multi-select)."""
    selected_ids = selected_ids or []
    rows = []
    for g in categories:
        if not g["is_all"]:
            is_sel = g["topic_id"] in selected_ids
            label = f">> {g['name']}" if is_sel else g["name"]
            rows.append(
                [InlineKeyboardButton(text=label, callback_data=f"ar_cat_{g['topic_id']}")]
            )
    # All categories button
    rows.append([InlineKeyboardButton(text="Select All", callback_data="ar_cat_all")])
    bottom = []
    if selected_ids:
        bottom.append(InlineKeyboardButton(text="Next", callback_data="ar_cat_done"))
    bottom.append(InlineKeyboardButton(text="Cancel", callback_data="adm_cancel"))
    rows.append(bottom)
    return InlineKeyboardMarkup(inline_keyboard=rows)


def autorun_delay_keyboard() -> InlineKeyboardMarkup:
    """Preset delay options for Auto Get & Run."""
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(text="15 min", callback_data="ar_delay_15"),
                InlineKeyboardButton(text="30 min", callback_data="ar_delay_30"),
            ],
            [
                InlineKeyboardButton(text="1 hour", callback_data="ar_delay_60"),
                InlineKeyboardButton(text="2 hours", callback_data="ar_delay_120"),
            ],
            [InlineKeyboardButton(text="Custom (type minutes)", callback_data="ar_delay_custom")],
            [InlineKeyboardButton(text="Cancel", callback_data="adm_cancel")],
        ]
    )


def autorun_confirm_keyboard() -> InlineKeyboardMarkup:
    """Confirm or cancel Auto Get & Run."""
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(text="Confirm & Schedule", callback_data="ar_confirm"),
                InlineKeyboardButton(text="Cancel", callback_data="adm_cancel"),
            ]
        ]
    )
