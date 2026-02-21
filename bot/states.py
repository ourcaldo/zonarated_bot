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


class UserOnboarding(StatesGroup):
    """States for user onboarding flow."""

    choosing_language = State()
