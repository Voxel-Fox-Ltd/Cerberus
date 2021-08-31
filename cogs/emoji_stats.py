import re

import discord
import voxelbotutils as vbu


class EmojiStats(vbu.Cog):

    EMOJI_REGEX = re.compile(r"<a?:(?P<name>.+?):(?P<id>\d+?)>")

    @vbu.Cog.listener()
    async def on_message(self, message: discord.Message):
        """
        Listen for emojis being sent and then log their usage in the database.
        """

        if not message.guild:
            return
        matches = list(self.EMOJI_REGEX.finditer(message.content))
        if not matches:
            return
        async with self.bot.database() as db:
            for m in matches:
                await db(
                    """INSERT INTO emoji_usage (guild_id, user_id, emoji_id, timestamp) VALUES ($1, $2, $3, $4)""",
                    message.guild.id, message.author.id, int(m.group('id')), message.created_at,
                )


def setup(bot: vbu.Bot):
    x = EmojiStats(bot)
    bot.add_cog(x)
