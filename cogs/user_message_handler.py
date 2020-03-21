import typing
from datetime import datetime as dt, timedelta
import collections

import discord
from discord.ext import tasks

from cogs import utils


class UserMessageHandler(utils.Cog):

    def __init__(self, bot:utils.Bot):
        super().__init__(bot)
        self.last_message: typing.Dict[discord.Member, dt] = collections.defaultdict(lambda: dt(2000, 1, 1, 0, 0))
        self.cached_for_saving: typing.List[discord.Message] = list()
        self.user_message_databaser.start()
        self.user_vc_databaser.start()

    def cog_unload(self):
        """Stop the databaser loop very gently so it stores everything in cache first"""

        self.user_message_databaser.stop()
        self.user_vc_databaser.stop()

    @staticmethod
    def valid_voice_state(voice_state:discord.VoiceState) -> bool:
        """Returns whether or not a voice state is unmuted, undeafened, etc"""

        return not any([
            voice_state.deaf,
            voice_state.mute,
            voice_state.self_mute,
            voice_state.self_deaf,
            voice_state.afk,
        ])

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

    @tasks.loop(minutes=1)
    async def user_vc_databaser(self):
        """Saves all VC points into the database"""

        # Grab all the VCs
        voice_channels = []
        for i in self.bot.guilds:
            voice_channels.extend(i.voice_channels)

        # Grab VCs where there's multiple people in them
        voice_members = []
        for vc in voice_channels:
            if len(vc.voice_states) > 1:
                voice_members.extend([(user_id, vc.guild.id) for user_id, state in vc.voice_states.items() if self.bot.get_user(user_id).bot is False and self.valid_voice_state(state)])

        # Make our records
        records = [(i, o, dt.utcnow()) for i, o in voice_members]

        # Only save messages if there _were_ any
        if len(records) == 0:
            self.logger.info(f"Storing 0 cached VC messages in database")
            return

        # Copy the records into the db
        self.logger.info(f"Storing {len(records)} cached VC minutes in database")
        async with self.bot.database() as db:
            await db.conn.copy_records_to_table(
                'user_vc_activity',
                columns=('user_id', 'guild_id', 'timestamp'),
                records=records
            )

    @utils.Cog.listener("on_message")
    async def user_message_cacher(self, message:discord.Message):
        """Listens for a user sending a message, and then saves that message as a point
        into the db should their last message be long enough ago"""

        # Filter out DMs
        if not isinstance(message.author, discord.Member):
            return

        # Filter out blacklisted roles
        blacklisted_roles = self.bot.blacklisted_roles[message.guild.id]
        if set(message.author._roles).intersection(blacklisted_roles):
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
        self.bot.dispatch('user_points_receive', message.author, message.channel)


def setup(bot:utils.Bot):
    x = UserMessageHandler(bot)
    bot.add_cog(x)
