CREATE TABLE guild_settings(
    guild_id BIGINT PRIMARY KEY,
    prefix VARCHAR(30)
);


CREATE TABLE user_messages(
    message_id BIGINT PRIMARY KEY,
    user_id BIGINT,
    guild_id BIGINT
);


CREATE TABLE role_gain(
    guild_id BIGINT NOT NULL,
    role_id BIGINT PRIMARY KEY,
    threshold INTEGER NOT NULL,
    period VARCHAR(10) NOT NULL,
    duration INTEGER NOT NULL,
    PRIMARY KEY (role_id)
);


CREATE TABLE static_user_messages(
    user_id BIGINT,
    guild_id BIGINT,
    message_count INTEGER,
    PRIMARY KEY (user_id, guild_id)
);


CREATE TABLE static_role_gain(
    guild_id BIGINT NOT NULL,
    role_id BIGINT PRIMARY KEY,
    threshold INTEGER NOT NULL
    PRIMARY KEY (role_id)
);
