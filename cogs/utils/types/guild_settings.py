from typing import TypedDict


class GuildSettings(TypedDict):
    guild_id: int
    prefix: str
    remove_old_roles: bool
    activity_window_days: int
    minecraft_srv_authorization: str
    role_gain: dict[int, int]  # role_id: required_points
    blacklisted_channels: list[int]  # channel IDs
    blacklisted_text_roles: list[int]  # channel IDs
    blacklisted_vc_roles: list[int]  # channel IDs
