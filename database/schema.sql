-- ===========================================
-- Rated Bot - Database Schema
-- Supabase PostgreSQL
-- ===========================================
-- Run this SQL in Supabase SQL Editor to create
-- all required tables, columns, indexes, and
-- seed default configuration values.
-- ===========================================


-- ===========================================
-- 1. CONFIG TABLE
-- Dynamic key-value settings managed at runtime
-- via admin bot commands (e.g. /setrequirement)
-- ===========================================
CREATE TABLE IF NOT EXISTS config (
    key         VARCHAR(100) PRIMARY KEY,
    value       TEXT         NOT NULL,
    description TEXT,
    updated_at  TIMESTAMPTZ  DEFAULT NOW()
);

-- Seed default configuration values
INSERT INTO config (key, value, description) VALUES
    ('REQUIRED_REFERRALS',    '1',                               'Number of referrals needed to join supergroup (0 = auto-approve)'),
    ('INVITE_EXPIRY_SECONDS', '300',                             'How long a one-time invite link stays valid (seconds)'),
    ('ADMIN_IDS',             '',                                'Comma-separated Telegram user IDs of bot admins'),
    ('AFFILIATE_LINK',        '',                                'Default affiliate link shown before downloads'),
    ('WELCOME_MESSAGE',       'Selamat datang di ZONA RATED!', 'Welcome message sent when user starts the bot')
ON CONFLICT (key) DO NOTHING;


-- ===========================================
-- 2. USERS TABLE
-- Stores every user who has interacted with the bot
-- ===========================================
CREATE TABLE IF NOT EXISTS users (
    user_id              BIGINT       PRIMARY KEY,               -- Telegram user ID
    username             VARCHAR(255),                            -- Telegram @username (nullable)
    first_name           VARCHAR(255),                            -- Telegram first name
    referral_link        VARCHAR(255) UNIQUE,                     -- User's unique referral deep link
    referral_count       INT          DEFAULT 0,                  -- How many people this user has referred
    referred_by          BIGINT,                                  -- User ID of whoever referred this user (nullable)

    -- Language preference
    language             VARCHAR(2),                              -- 'id' or 'en' (NULL until chosen)

    -- Verification flags
    bot_joined           BOOLEAN      DEFAULT TRUE,               -- Always true after /start
    verification_complete BOOLEAN     DEFAULT FALSE,              -- All requirements met

    -- Supergroup join flow
    approved             BOOLEAN      DEFAULT FALSE,              -- Marked when all requirements are satisfied
    ready_to_join        BOOLEAN      DEFAULT FALSE,              -- Temporary flag while invite link is active
    joined_supergroup    BOOLEAN      DEFAULT FALSE,              -- Successfully joined the supergroup

    -- Timestamps
    join_date            TIMESTAMPTZ  DEFAULT NOW(),              -- When user first started the bot
    last_updated         TIMESTAMPTZ  DEFAULT NOW(),

    CONSTRAINT fk_referred_by FOREIGN KEY (referred_by) REFERENCES users(user_id) ON DELETE SET NULL
);

-- Indexes for frequent lookups
CREATE INDEX IF NOT EXISTS idx_users_referral_link ON users(referral_link);
CREATE INDEX IF NOT EXISTS idx_users_referred_by   ON users(referred_by);
CREATE INDEX IF NOT EXISTS idx_users_joined_sg     ON users(joined_supergroup);


-- ===========================================
-- 3. REFERRALS TABLE
-- Tracks every referrer → referred relationship
-- ===========================================
CREATE TABLE IF NOT EXISTS referrals (
    referral_id      BIGSERIAL PRIMARY KEY,
    referrer_user_id BIGINT    NOT NULL,                          -- User who shared the link
    referred_user_id BIGINT    NOT NULL,                          -- User who joined through the link
    referral_date    TIMESTAMPTZ DEFAULT NOW(),

    CONSTRAINT fk_referrer FOREIGN KEY (referrer_user_id) REFERENCES users(user_id) ON DELETE CASCADE,
    CONSTRAINT fk_referred FOREIGN KEY (referred_user_id) REFERENCES users(user_id) ON DELETE CASCADE,

    -- Prevent duplicate referral pairs
    CONSTRAINT uq_referral_pair UNIQUE (referrer_user_id, referred_user_id)
);

CREATE INDEX IF NOT EXISTS idx_referrals_referrer ON referrals(referrer_user_id);
CREATE INDEX IF NOT EXISTS idx_referrals_referred ON referrals(referred_user_id);


-- ===========================================
-- 4. VIDEOS TABLE
-- Metadata for every video posted in the supergroup
-- ===========================================
CREATE TABLE IF NOT EXISTS videos (
    video_id       BIGSERIAL    PRIMARY KEY,
    title          VARCHAR(255) NOT NULL,
    category       VARCHAR(100),
    description    TEXT,
    file_url       TEXT         NOT NULL,                         -- Direct URL or Telegram file_id
    affiliate_link TEXT,                                          -- Per-video affiliate override (nullable, falls back to global)
    topic_id       BIGINT,                                       -- Telegram forum topic ID
    message_id     BIGINT,                                       -- Telegram message ID in the supergroup
    views          INT          DEFAULT 0,
    downloads      INT          DEFAULT 0,
    post_date      TIMESTAMPTZ  DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_videos_category ON videos(category);
CREATE INDEX IF NOT EXISTS idx_videos_topic    ON videos(topic_id);


-- ===========================================
-- 5. DOWNLOAD SESSIONS TABLE
-- Tracks each download attempt lifecycle:
-- button click → affiliate visit → video delivered
-- ===========================================
CREATE TABLE IF NOT EXISTS download_sessions (
    session_id        VARCHAR(255) PRIMARY KEY,                   -- Unique tracking ID for this session
    user_id           BIGINT       NOT NULL,
    video_id          BIGINT       NOT NULL,
    affiliate_visited BOOLEAN      DEFAULT FALSE,                 -- User opened the affiliate link
    video_sent        BOOLEAN      DEFAULT FALSE,                 -- Video URL/file delivered to user
    created_at        TIMESTAMPTZ  DEFAULT NOW(),
    expires_at        TIMESTAMPTZ,                                -- Session expiry for cleanup

    CONSTRAINT fk_ds_user  FOREIGN KEY (user_id)  REFERENCES users(user_id)  ON DELETE CASCADE,
    CONSTRAINT fk_ds_video FOREIGN KEY (video_id) REFERENCES videos(video_id) ON DELETE CASCADE
);

CREATE INDEX IF NOT EXISTS idx_ds_user      ON download_sessions(user_id);
CREATE INDEX IF NOT EXISTS idx_ds_video     ON download_sessions(video_id);
CREATE INDEX IF NOT EXISTS idx_ds_expires   ON download_sessions(expires_at);


-- ===========================================
-- 6. DOWNLOADS TABLE
-- Permanent log of completed downloads (analytics)
-- ===========================================
CREATE TABLE IF NOT EXISTS downloads (
    download_id           BIGSERIAL    PRIMARY KEY,
    user_id               BIGINT       NOT NULL,
    video_id              BIGINT       NOT NULL,
    session_id            VARCHAR(255),                           -- Links back to the download session
    affiliate_link_clicked BOOLEAN     DEFAULT FALSE,
    download_completed     BOOLEAN     DEFAULT FALSE,
    download_date          TIMESTAMPTZ,
    created_at             TIMESTAMPTZ DEFAULT NOW(),

    CONSTRAINT fk_dl_user    FOREIGN KEY (user_id)    REFERENCES users(user_id)    ON DELETE CASCADE,
    CONSTRAINT fk_dl_video   FOREIGN KEY (video_id)   REFERENCES videos(video_id)  ON DELETE CASCADE,
    CONSTRAINT fk_dl_session FOREIGN KEY (session_id)  REFERENCES download_sessions(session_id) ON DELETE SET NULL
);

CREATE INDEX IF NOT EXISTS idx_dl_user    ON downloads(user_id);
CREATE INDEX IF NOT EXISTS idx_dl_video   ON downloads(video_id);
CREATE INDEX IF NOT EXISTS idx_dl_session ON downloads(session_id);


-- ===========================================
-- 7. INVITE LINKS TABLE
-- Tracks one-time invite links generated for
-- verified users (Method 3 audit trail)
-- ===========================================
CREATE TABLE IF NOT EXISTS invite_links (
    id          BIGSERIAL    PRIMARY KEY,
    user_id     BIGINT       NOT NULL,
    invite_link TEXT         NOT NULL,
    used        BOOLEAN      DEFAULT FALSE,
    created_at  TIMESTAMPTZ  DEFAULT NOW(),
    expires_at  TIMESTAMPTZ  NOT NULL,

    CONSTRAINT fk_il_user FOREIGN KEY (user_id) REFERENCES users(user_id) ON DELETE CASCADE
);

CREATE INDEX IF NOT EXISTS idx_il_user    ON invite_links(user_id);
CREATE INDEX IF NOT EXISTS idx_il_expires ON invite_links(expires_at);
