CREATE TABLE IF NOT EXISTS guild_settings(
    guild_id BIGINT PRIMARY KEY,
    prefix VARCHAR(30),
    remove_old_roles BOOLEAN NOT NULL DEFAULT FALSE
);


CREATE TABLE IF NOT EXISTS user_messages(
    timestamp TIMESTAMP,
    user_id BIGINT,
    guild_id BIGINT,
    channel_id BIGINT
);


CREATE TABLE IF NOT EXISTS user_vc_activity(
    user_id BIGINT,
    guild_id BIGINT,
    timestamp TIMESTAMP,
    channel_id BIGINT
);


CREATE TABLE IF NOT EXISTS role_gain(
    guild_id BIGINT NOT NULL,
    role_id BIGINT PRIMARY KEY,
    threshold INTEGER NOT NULL,
    period VARCHAR(10) NOT NULL,
    duration INTEGER NOT NULL
);


CREATE TABLE IF NOT EXISTS no_exp_channels(
    guild_id BIGINT,
    channel_id BIGINT PRIMARY KEY
);


CREATE TABLE IF NOT EXISTS no_exp_roles(
    guild_id BIGINT,
    role_id BIGINT PRIMARY KEY
);


CREATE TABLE IF NOT EXISTS user_settings(
    user_id BIGINT PRIMARY KEY
);


CREATE TABLE IF NOT EXISTS role_list(
    guild_id BIGINT,
    role_id BIGINT,
    key VARCHAR(50),
    value VARCHAR(50),
    PRIMARY KEY (guild_id, role_id, key)
);


CREATE TABLE IF NOT EXISTS channel_list(
    guild_id BIGINT,
    channel_id BIGINT,
    key VARCHAR(50),
    value VARCHAR(50),
    PRIMARY KEY (guild_id, channel_id, key)
);
