import typing
from datetime import datetime as dt, timedelta
import collections

import discord
from discord.ext import tasks, commands

from cogs import utils


class UserMessageHandler(utils.Cog):

    def __init__(self, bot:utils.CustomBot):
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
            self.log_handler.info(f"Storing 0 cached messages in database")
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
        self.log_handler.info(f"Storing {len(records)} cached messages in database")
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

        # Make sure it's in the time we want
        last_message_from_user = self.last_message[message.author]
        if last_message_from_user < dt.utcnow() - timedelta(minutes=1):
            self.last_message[message.author] = message.created_at
        else:
            return

        # Cache to be saved
        self.cached_for_saving.append(message)

        # Cache for internal use
        utils.CachedMessage(
            user_id=message.author.id,
            guild_id=message.guild.id,
            message_id=message.id
        )

    @commands.command()
    async def getpoints(self, ctx:utils.Context, user:typing.Optional[discord.User], *attrs):

        attributes = {i.split('=')[0]: int(i.split('=')[1]) for i in attrs}
        user = user or ctx.author
        data = utils.CachedMessage.get_messages(user, ctx.guild, **attributes)
        await ctx.send(len(data))


def setup(bot:utils.CustomBot):
    x = UserMessageHandler(bot)
    bot.add_cog(x)
