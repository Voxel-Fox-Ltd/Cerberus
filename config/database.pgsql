CREATE TABLE guild_settings(
    guild_id BIGINT PRIMARY KEY,
    prefix VARCHAR(30),
    remove_old_roles BOOLEAN NOT NULL DEFAULT FALSE
);


CREATE TABLE user_messages(
    message_id BIGINT PRIMARY KEY,
    user_id BIGINT,
    guild_id BIGINT
);


CREATE TABLE user_vc_activity(
    user_id BIGINT,
    guild_id BIGINT,
    timestamp TIMESTAMP
);


CREATE TABLE role_gain(
    guild_id BIGINT NOT NULL,
    role_id BIGINT PRIMARY KEY,
    threshold INTEGER NOT NULL,
    period VARCHAR(10) NOT NULL,
    duration INTEGER NOT NULL
);


CREATE TABLE no_exp_channels(
    guild_id BIGINT,
    channel_id BIGINT PRIMARY KEY
);


CREATE TABLE no_exp_roles(
    guild_id BIGINT,
    role_id BIGINT PRIMARY KEY
);


CREATE TABLE user_settings(
    user_id BIGINT PRIMARY KEY
);


CREATE TABLE role_list(
    guild_id BIGINT,
    role_id BIGINT,
    key VARCHAR(50),
    value VARCHAR(50),
    PRIMARY KEY (guild_id, role_id, key)
);


CREATE TABLE channel_list(
    guild_id BIGINT,
    channel_id BIGINT,
    key VARCHAR(50),
    value VARCHAR(50),
    PRIMARY KEY (guild_id, channel_id, key)
);
