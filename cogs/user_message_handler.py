import typing
from datetime import datetime as dt, timedelta
import collections

import discord
from discord.ext import tasks

from cogs import utils


class UserMessageHandler(utils.Cog):

    def __init__(self, bot:utils.Bot):
        super().__init__(bot)
        the_start_of_time = lambda: dt(2000, 1, 1, 0, 0)
        self.last_message: typing.Dict[discord.Member, dt] = collections.defaultdict(the_start_of_time)
        self.cached_for_saving: typing.List[discord.Message] = list()
        self.user_message_databaser.start()

    def cog_unload(self):
        """Stop the databaser loop very gently so it stores everything in cache first"""

        self.user_message_databaser.stop()

    @tasks.loop(minutes=1)
    async def user_message_databaser(self):
        """Saves all messages stored in self.cached_for_saving to db"""

        # Only save messages if there _were_ any
        if len(self.cached_for_saving) == 0:
            self.logger.info(f"Storing 0 cached messages in database")
            return

        # Get the messages we want to save
        currently_saving = self.cached_for_saving.copy()  # Make a copy to fend off the race conditions
        for m in currently_saving:
            try:
                self.cached_for_saving.remove(m)
            except ValueError:
                pass

        # Sort them into a nice easy tuple
        records = [(i.id, i.author.id, i.guild.id) for i in currently_saving if i.author.bot is False]

        # Copy the records into the db
        self.logger.info(f"Storing {len(records)} cached messages in database")
        async with self.bot.database() as db:
            await db.conn.copy_records_to_table(
                'user_messages',
                columns=('message_id', 'user_id', 'guild_id'),
                records=records
            )

    @utils.Cog.listener("on_message")
    async def user_message_cacher(self, message:discord.Message):
        """Listens for a user sending a message, and then saves that message as a point
        into the db should their last message be long enough ago"""

        # Filter out DMs
        if message.guild is None:
            return

        # Filter blacklisted channels
        if (message.guild.id, message.channel.id) in self.bot.blacklisted_channels:
            return

        # Make sure it's in the time we want
        last_message_from_user = self.last_message[message.author]
        if last_message_from_user < dt.utcnow() - timedelta(minutes=1):
            self.last_message[message.author] = message.created_at
        else:
            return

        # Cache for dynamic role handles
        self.cached_for_saving.append(message)
        utils.CachedMessage(
            user_id=message.author.id,
            guild_id=message.guild.id,
            message_id=message.id
        )

        # Store for non-dynamic role handles
        self.logger.info(f"Adding static exp to user {message.author.id} in guild {message.guild.id}")
        self.bot.message_count[(message.author.id, message.guild.id)] += 1
        static_message_count = self.bot.message_count[(message.author.id, message.guild.id)]
        async with self.bot.database() as db:
            await db(
                """INSERT INTO static_user_messages (user_id, guild_id, message_count)
                VALUES ($1, $2, $3) ON CONFLICT (user_id, guild_id) DO UPDATE SET message_count=$3""",
                message.author.id, message.guild.id, static_message_count
            )

        # Dispatch points event
        self.bot.dispatch('user_points_receive', message.author)

        # Dispatch level up event
        mee6_data = self.bot.get_cog('Mee6Data')
        if mee6_data is None:
            return
        current_level = mee6_data.get_level_by_messages(static_message_count)
        previous_level = mee6_data.get_level_by_messages(static_message_count - 1)
        if current_level > previous_level:
            self.bot.dispatch('user_static_level_up', message.author)


def setup(bot:utils.Bot):
    x = UserMessageHandler(bot)
    bot.add_cog(x)
