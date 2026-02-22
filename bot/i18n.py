"""Bilingual text strings: Indonesian (id) and English (en).

Usage:
    from bot.i18n import t
    text = t(lang, "welcome")
"""

from __future__ import annotations

_STRINGS: dict[str, dict[str, str]] = {
    # ── Onboarding ────────────────────────────────
    "choose_language": {
        "id": "Pilih bahasa / Choose language:",
        "en": "Pilih bahasa / Choose language:",
    },
    "welcome": {
        "id": (
            "{welcome_msg}\n\n"
            "Untuk mengakses ZONA RATED, kamu perlu mengajak "
            "{required} orang melalui link referral kamu.\n\n"
            "Link referral kamu:\n"
            "<code>{ref_link}</code>\n\n"
            "Bagikan link di atas, lalu tekan Cek Persyaratan "
            "setelah selesai."
        ),
        "en": (
            "{welcome_msg}\n\n"
            "To access ZONA RATED, you need to invite "
            "{required} people through your referral link.\n\n"
            "Your referral link:\n"
            "<code>{ref_link}</code>\n\n"
            "Share the link above, then press Check Requirements "
            "when done."
        ),
    },
    "welcome_auto": {
        "id": (
            "{welcome_msg}\n\n"
            "Tidak ada syarat referral saat ini.\n"
            "Kamu bisa langsung join ZONA RATED!\n\n"
            "Tekan tombol di bawah:"
        ),
        "en": (
            "{welcome_msg}\n\n"
            "No referral requirement at this time.\n"
            "You can join ZONA RATED right away!\n\n"
            "Press the button below:"
        ),
    },

    # ── Buttons ───────────────────────────────────
    "btn_share": {
        "id": "Bagikan Link",
        "en": "Share Link",
    },
    "btn_check": {
        "id": "Cek Persyaratan",
        "en": "Check Requirements",
    },
    "btn_join": {
        "id": "Gabung Grup",
        "en": "Join Group",
    },
    "btn_join_supergroup": {
        "id": "Join ZONA RATED",
        "en": "Join ZONA RATED",
    },
    "btn_check_again": {
        "id": "Cek Lagi",
        "en": "Check Again",
    },
    "btn_share_again": {
        "id": "Bagikan Link",
        "en": "Share Link",
    },

    # ── Referral notifications ────────────────────
    "referral_credited": {
        "id": "Seseorang bergabung melalui link kamu!\nProgress: {count}/{required}",
        "en": "Someone joined through your link!\nProgress: {count}/{required}",
    },
    "referral_complete": {
        "id": (
            "SELAMAT!\n\n"
            "Kamu sudah mencapai target referral ({count}/{required})!\n"
            "Semua syarat terpenuhi!\n\n"
            "Klik tombol untuk join ZONA RATED:"
        ),
        "en": (
            "CONGRATULATIONS!\n\n"
            "You've reached the referral target ({count}/{required})!\n"
            "All requirements met!\n\n"
            "Click the button to join ZONA RATED:"
        ),
    },

    # ── Verification / Join ───────────────────────
    "not_registered": {
        "id": "Kamu belum terdaftar. Kirim /start dulu.",
        "en": "You are not registered. Send /start first.",
    },
    "verified_ready": {
        "id": (
            "Verifikasi lengkap!\n\n"
            "Referral: {count}/{required} [OK]\n"
            "Join Bot: Done\n\n"
            "PENTING:\n"
            "- Link berlaku {expiry_min} menit\n"
            "- Hanya bisa dipakai 1x\n"
            "- Klik segera!\n\n"
            "Setelah klik, kamu akan masuk ke ZONA RATED."
        ),
        "en": (
            "Verification complete!\n\n"
            "Referrals: {count}/{required} [OK]\n"
            "Bot joined: Done\n\n"
            "IMPORTANT:\n"
            "- Link valid for {expiry_min} minutes\n"
            "- Can only be used once\n"
            "- Click immediately!\n\n"
            "After clicking, you will enter ZONA RATED."
        ),
    },
    "not_verified": {
        "id": (
            "Kamu belum memenuhi syarat.\n\n"
            "Lengkapi langkah berikut:\n\n"
            "Referral: {count}/{required}\n"
            "Bagikan link ini dan ajak {needed} orang lagi:\n"
            "<code>{ref_link}</code>\n\n"
            "Join Bot: Done"
        ),
        "en": (
            "You have not met the requirements.\n\n"
            "Complete the following steps:\n\n"
            "Referrals: {count}/{required}\n"
            "Share this link and invite {needed} more people:\n"
            "<code>{ref_link}</code>\n\n"
            "Bot joined: Done"
        ),
    },
    "not_verified_auto": {
        "id": "Referral: Tidak diperlukan (auto-approve)\nJoin Bot: Done",
        "en": "Referrals: Not required (auto-approve)\nBot joined: Done",
    },
    "invite_created": {
        "id": "Link undangan dibuat!",
        "en": "Invite link created!",
    },
    "invite_failed": {
        "id": "Gagal membuat link. Coba lagi.",
        "en": "Failed to create link. Try again.",
    },
    "check_requirements_first": {
        "id": "Lengkapi syarat terlebih dahulu!",
        "en": "Complete the requirements first!",
    },

    # ── Join request ──────────────────────────────
    "join_approved": {
        "id": (
            "Join request disetujui!\n\n"
            "Selamat datang di ZONA RATED!\n"
            "Nikmati koleksi video premium kami!"
        ),
        "en": (
            "Join request approved!\n\n"
            "Welcome to ZONA RATED!\n"
            "Enjoy our premium video collection!"
        ),
    },
    "join_declined": {
        "id": (
            "Join request ditolak.\n\n"
            "Kemungkinan penyebab:\n{reasons}\n\n"
            "Silakan klik 'Cek Persyaratan' lagi di bot untuk mendapatkan link baru."
        ),
        "en": (
            "Join request declined.\n\n"
            "Possible reasons:\n{reasons}\n\n"
            "Please click 'Check Requirements' again in the bot to get a new link."
        ),
    },
    "reason_not_verified": {
        "id": "- Verifikasi belum lengkap",
        "en": "- Verification incomplete",
    },
    "reason_link_expired": {
        "id": "- Link sudah expired atau sudah dipakai",
        "en": "- Link expired or already used",
    },
    "reason_not_approved": {
        "id": "- Belum di-approve di sistem",
        "en": "- Not yet approved in the system",
    },

    # ── Common commands ───────────────────────────
    "help_text": {
        "id": (
            "Daftar Perintah:\n\n"
            "/start - Mulai dan daftar ke bot\n"
            "/status - Cek status verifikasi kamu\n"
            "/mylink - Lihat link referral kamu\n"
            "/help - Tampilkan bantuan ini"
        ),
        "en": (
            "Commands:\n\n"
            "/start - Start and register\n"
            "/status - Check your verification status\n"
            "/mylink - View your referral link\n"
            "/help - Show this help"
        ),
    },
    "status_text": {
        "id": (
            "Status Kamu:\n\n"
            "Referral: {count}/{required}\n"
            "Join Bot: Sudah\n"
            "Bergabung ZONA RATED: {sg_status}\n"
            "Verifikasi: {ver_status}\n\n"
            "Link referral kamu:\n<code>{ref_link}</code>"
        ),
        "en": (
            "Your Status:\n\n"
            "Referrals: {count}/{required}\n"
            "Bot joined: Done\n"
            "Joined ZONA RATED: {sg_status}\n"
            "Verification: {ver_status}\n\n"
            "Your referral link:\n<code>{ref_link}</code>"
        ),
    },
    "mylink_text": {
        "id": (
            "Link referral kamu:\n\n"
            "<code>{ref_link}</code>\n\n"
            "Bagikan link ini dan ajak orang untuk bergabung!\n"
            "Progress: {count}/{required}"
        ),
        "en": (
            "Your referral link:\n\n"
            "<code>{ref_link}</code>\n\n"
            "Share this link and invite people to join!\n"
            "Progress: {count}/{required}"
        ),
    },

    # ── Admin approve notification ────────────────
    "admin_approved_you": {
        "id": "Admin telah meng-approve akun kamu.\nKamu sekarang bisa join ZONA RATED!",
        "en": "Admin has approved your account.\nYou can now join ZONA RATED!",
    },

    # ── Share message ─────────────────────────────
    "share_text": {
        "id": "Gabung ke Zona Rated! Klik link ini: {ref_link}",
        "en": "Join Zona Rated! Click this link: {ref_link}",
    },

    # ── Fallback (unrecognized message) ────────────
    "fallback_registered": {
        "id": (
            "Hai! Berikut yang bisa kamu lakukan:\n\n"
            "Link referral kamu:\n<code>{ref_link}</code>\n\n"
            "Referral: {count}/{required}"
        ),
        "en": (
            "Hi! Here's what you can do:\n\n"
            "Your referral link:\n<code>{ref_link}</code>\n\n"
            "Referrals: {count}/{required}"
        ),
    },
    "fallback_new": {
        "id": "Hai! Tekan tombol di bawah untuk memulai.",
        "en": "Hi! Press the button below to get started.",
    },

    # ── Yes/No ────────────────────────────────────
    "yes": {"id": "Ya", "en": "Yes"},
    "no": {"id": "Tidak", "en": "No"},
    "ok": {"id": "OK", "en": "OK"},
    "done": {"id": "Selesai", "en": "Done"},
    "complete": {"id": "Lengkap", "en": "Complete"},
    "incomplete": {"id": "Belum", "en": "Incomplete"},

    # ── Download flow ─────────────────────────────
    "dl_not_registered": {
        "id": "Kamu belum terdaftar. Kirim /start ke @zonarated_bot dulu.",
        "en": "You are not registered. Send /start to @zonarated_bot first.",
    },
    "dl_not_verified": {
        "id": (
            "Kamu belum memenuhi syarat untuk download.\n\n"
            "Selesaikan verifikasi terlebih dahulu di @zonarated_bot."
        ),
        "en": (
            "You have not met the requirements to download.\n\n"
            "Complete verification first at @zonarated_bot."
        ),
    },
    "dl_affiliate_prompt": {
        "id": (
            "Untuk mendownload video ini, buka link berikut.\n\n"
            "Video akan otomatis dikirim ke chat ini setelah link dibuka."
        ),
        "en": (
            "To download this video, open the following link.\n\n"
            "The video will be sent to this chat automatically after you open it."
        ),
    },
    "dl_no_affiliate": {
        "id": "Memproses download...",
        "en": "Processing download...",
    },
    "dl_video_sent": {
        "id": "Berikut video yang kamu minta:",
        "en": "Here is the video you requested:",
    },
    "dl_video_url": {
        "id": "Berikut link video yang kamu minta:\n\n{url}",
        "en": "Here is the video link you requested:\n\n{url}",
    },
    "dl_session_expired": {
        "id": "Sesi download sudah expired. Klik tombol Download lagi di grup.",
        "en": "Download session expired. Click the Download button again in the group.",
    },
    "dl_error": {
        "id": "Terjadi kesalahan. Coba lagi nanti.",
        "en": "An error occurred. Try again later.",
    },
}


def t(lang: str | None, key: str, **kwargs: object) -> str:
    """Get a translated string. Falls back to Indonesian."""
    lang = lang if lang in ("id", "en") else "id"
    entry = _STRINGS.get(key)
    if entry is None:
        return key
    text = entry.get(lang, entry.get("id", key))
    if kwargs:
        text = text.format(**kwargs)
    return text
