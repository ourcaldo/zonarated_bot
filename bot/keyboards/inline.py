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
    """Attach to video posts in the supergroup."""
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="Download", callback_data=f"dl_{video_id}")]
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
# Admin Panel — Main menu
# ──────────────────────────────────────────────

def admin_main_menu() -> InlineKeyboardMarkup:
    """Top-level admin dashboard."""
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="Statistics", callback_data="adm_stats")],
            [InlineKeyboardButton(text="Settings", callback_data="adm_settings")],
            [InlineKeyboardButton(text="User Management", callback_data="adm_users")],
            [InlineKeyboardButton(text="Broadcast", callback_data="adm_broadcast")],
            [InlineKeyboardButton(text="Close Panel", callback_data="adm_close")],
        ]
    )


# ──────────────────────────────────────────────
# Admin Panel — Settings sub-menu
# ──────────────────────────────────────────────

def admin_settings_menu() -> InlineKeyboardMarkup:
    """Sub-menu for dynamic config values."""
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
            [InlineKeyboardButton(text="Approve User", callback_data="adm_approve")],
            [InlineKeyboardButton(text="Lookup User", callback_data="adm_lookup")],
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
