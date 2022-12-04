from discord.ext import vbu

from .guild_settings import GuildSettings


__all__ = (
    "GuildSettings",
    "Bot",
)


class Bot(vbu.Bot):

    guild_settings: dict[int, GuildSettings]
