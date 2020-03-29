import typing
from datetime import datetime as dt

import discord
from discord.ext import tasks

from cogs import utils


class UserVCHandler(utils.Cog):

    def __init__(self, bot:utils.Bot):
        super().__init__(bot)
        self.user_vc_databaser.start()

    def cog_unload(self):
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
    async def user_vc_databaser(self):
        """Saves all VC points into the database"""

        # Grab all the VCs
        voice_channels: typing.List[discord.VoiceChannel] = []
        for i in self.bot.guilds:
            voice_channels.extend(i.voice_channels)

        # Grab VCs where there's multiple people in them
        voice_members: typing.List[typing.Tuple[int, int]] = []  # (uid, gid)...
        for vc in voice_channels:
            if len(vc.voice_states) > 1:
                voice_members.extend([(user_id, vc.guild.id) for user_id, state in vc.voice_states.items() if self.bot.get_user(user_id).bot is False and self.valid_voice_state(state)])

        # Make our records
        records: typing.List[typing.Tuple[int, int, dt]] = [(i, o, dt.utcnow()) for i, o in voice_members]  # (uid, gid, timestamp)...

        # Let's cache the static VC minutes, just for fun
        for uid, gid, timestamp in records:
            utils.CachedVCMinute(user_id=uid, guild_id=gid, timestamp=timestamp)
            self.bot.minute_count[(uid, gid)] += 1

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
            for uid, gid, timestamp in records:
                await db(
                    """INSERT INTO static_user_vc_activity (user_id, guild_id, minutes)
                    VALUES ($1, $2, $3) ON CONFLICT (user_id, guild_id)
                    DO UPDATE SET minutes=static_user_vc_activity.minutes+excluded.minutes""",
                    uid, gid, self.bot.minute_count[uid, gid]
                )  # TODO this is dreadfully inefficient. Please fix this. Please.


def setup(bot:utils.Bot):
    x = UserVCHandler(bot)
    bot.add_cog(x)
