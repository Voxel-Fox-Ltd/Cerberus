import typing
from datetime import datetime as dt

import discord
from discord.ext import tasks
import voxelbotutils as utils


class UserVCHandler(utils.Cog):

    def __init__(self, bot:utils.Bot):
        super().__init__(bot)
        self.user_vc_databaser.start()

    def cog_unload(self):
        self.user_vc_databaser.stop()

    @staticmethod
    def valid_voice_state(voice_state:discord.VoiceState) -> bool:
        """
        Returns whether or not a voice state is unmuted, undeafened, etc.
        """

        return not any([
            voice_state.deaf,
            voice_state.mute,
            voice_state.self_mute,
            voice_state.self_deaf,
            voice_state.afk,
        ])

    @tasks.loop(minutes=1)
    async def user_vc_databaser(self):
        """
        Saves all VC points into the database.
        """

        # Grab all the VCs
        voice_channels: typing.List[discord.VoiceChannel] = []
        for i in self.bot.guilds:
            voice_channels.extend(i.voice_channels)

        # Grab VCs where there's multiple people in them
        voice_members: typing.List[typing.Tuple[int, int]] = []  # (uid, gid)...
        for vc in voice_channels:
            try:
                _ = vc.id
                _ = vc.guild.id
            except AttributeError:
                continue
            non_bot_users = [(user_id, state) for user_id, state in vc.voice_states.items() if self.bot.get_user(user_id) and self.bot.get_user(user_id).bot is False]
            if len(non_bot_users) > 1:
                voice_members.extend([(user_id, vc.guild.id, vc.id) for user_id, state in non_bot_users if self.valid_voice_state(state)])

        # Filter out the bastards
        for user_id, guild_id, channel_id in voice_members.copy():
            blacklisted_roles = self.bot.guild_settings[guild_id].setdefault('blacklisted_vc_roles', list())
            guild = self.bot.get_guild(guild_id)
            try:
                member = guild.get_member(user_id) or await guild.fetch_member(user_id)
                assert member is not None
            except (AssertionError, discord.HTTPException):
                voice_members.remove((user_id, guild_id, channel_id))
                continue
            if set(member._roles).intersection(blacklisted_roles):
                voice_members.remove((user_id, guild_id, channel_id))

        # Make our records
        records: typing.List[typing.Tuple[int, int, dt, int]] = [(i, o, dt.utcnow(), p) for i, o, p in voice_members]  # (uid, gid, timestamp, cid)...

        # Only save messages if there _were_ any
        if len(records) == 0:
            self.logger.info("Storing 0 cached VC messages in database")
            return

        # Copy the records into the db
        self.logger.info(f"Storing {len(records)} cached VC minutes in database")
        async with self.bot.database() as db:
            await db.conn.copy_records_to_table(
                'user_vc_activity',
                columns=('user_id', 'guild_id', 'timestamp', 'channel_id'),
                records=records
            )


def setup(bot:utils.Bot):
    x = UserVCHandler(bot)
    bot.add_cog(x)
