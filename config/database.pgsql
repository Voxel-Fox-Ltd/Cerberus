CREATE TABLE user_messages(
    message_id BIGINT PRIMARY KEY,
    user_id BIGINT,
    guild_id BIGINT
);
