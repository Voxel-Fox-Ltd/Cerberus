CREATE TABLE IF NOT EXISTS guild_settings(
    guild_id BIGINT PRIMARY KEY,
    prefix VARCHAR(30),
    remove_old_roles BOOLEAN NOT NULL DEFAULT FALSE,
    activity_window_days SMALLINT NOT NULL DEFAULT 7,
    minecraft_srv_authorization TEXT
);


DO $$ BEGIN
    CREATE TYPE point_source AS ENUM('message', 'voice', 'minecraft');
EXCEPTION
    WHEN duplicate_object THEN null;
END $$;


CREATE TABLE IF NOT EXISTS user_points(
    user_id BIGINT NOT NULL,
    timestamp TIMESTAMP NOT NULL,
    guild_id BIGINT NOT NULL,
    channel_id BIGINT,
    source point_source NOT NULL
);


CREATE TABLE IF NOT EXISTS user_point_hourly_counts (
    guild_id BIGINT NOT NULL,
    user_id BIGINT NOT NULL,
    hour TIMESTAMP NOT NULL,
    source point_source NOT NULL,
    points DOUBLE PRECISION NOT NULL DEFAULT 0,
    PRIMARY KEY (guild_id, user_id, hour, source)
);


CREATE TABLE IF NOT EXISTS user_point_daily_counts (
    guild_id BIGINT NOT NULL,
    user_id BIGINT NOT NULL,
    day DATE NOT NULL,
    source point_source NOT NULL,
    points DOUBLE PRECISION NOT NULL DEFAULT 0,
    PRIMARY KEY (guild_id, user_id, day, source)
);


CREATE TABLE IF NOT EXISTS user_point_monthly_counts (
    guild_id BIGINT NOT NULL,
    user_id BIGINT NOT NULL,
    month DATE NOT NULL,
    source point_source NOT NULL,
    points DOUBLE PRECISION NOT NULL DEFAULT 0,
    PRIMARY KEY (guild_id, user_id, month, source)
);


CREATE TABLE IF NOT EXISTS user_settings(
    user_id BIGINT PRIMARY KEY
);


CREATE TABLE IF NOT EXISTS role_list(
    guild_id BIGINT,
    role_id BIGINT,
    key TEXT,
    value TEXT,
    PRIMARY KEY (guild_id, role_id, key)
);


CREATE TABLE IF NOT EXISTS channel_list(
    guild_id BIGINT,
    channel_id BIGINT,
    key TEXT,
    value TEXT,
    PRIMARY KEY (guild_id, channel_id, key)
);


-- CREATE TABLE IF NOT EXISTS emoji_usage (
--     guild_id BIGINT,
--     user_id BIGINT,
--     emoji_id BIGINT,
--     timestamp TIMESTAMP
-- );


-- SELECT emoji_id, COUNT(timestamp) FROM emoji_usage WHERE guild_id={guild} GROUP BY emoji_id ORDER BY COUNT(timestamp) DESC LIMIT 10;
