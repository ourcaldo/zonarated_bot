"""FSM states used across the bot."""

from aiogram.fsm.state import State, StatesGroup


class AdminInput(StatesGroup):
    """States for the admin panel input flows."""

    waiting_referrals = State()
    waiting_affiliate = State()
    waiting_welcome = State()
    waiting_expiry = State()
    waiting_approve_id = State()
    waiting_lookup_id = State()
    waiting_broadcast = State()
    waiting_config_value = State()    # generic config key editor


class AdminCategory(StatesGroup):
    """States for category management flows."""

    waiting_category_name = State()


class AdminVideo(StatesGroup):
    """States for the add-video wizard."""

    waiting_title = State()
    waiting_category = State()       # callback: category picker
    waiting_description = State()
    waiting_file = State()           # video file or URL
    waiting_thumbnail = State()      # thumbnail preview / change / upload
    waiting_thumb_ts = State()       # admin types new timestamp
    waiting_affiliate = State()      # optional per-video affiliate
    confirming = State()             # preview + confirm / cancel


class UserOnboarding(StatesGroup):
    """States for user onboarding flow."""

    choosing_language = State()
