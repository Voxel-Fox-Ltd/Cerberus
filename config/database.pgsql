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
    duration INTEGER NOT NULL
);
