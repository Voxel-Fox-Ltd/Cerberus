import typing
from datetime import datetime as dt
import collections

import discord
from discord.ext import tasks, vbu

from . import utils


class UserVCHandler(vbu.Cog):

    def __init__(self, bot: vbu.Bot):
        super().__init__(bot)
        self.user_vc_databaser.start()

    def cog_unload(self):
        self.user_vc_databaser.stop()

    @staticmethod
    def valid_voice_state(voice_state: discord.VoiceState) -> bool:
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

        voice_channels: typing.List[discord.VoiceChannel] = []
        for i in self.bot.guilds:
            voice_channels.extend(i.voice_channels)

        voice_members: typing.List[typing.Tuple[int, int, int]] = []

        for vc in voice_channels:
            try:
                _ = vc.id
                _ = vc.guild.id
            except AttributeError:
                continue

            try:
                non_bot_users = [
                    (user_id, state)
                    for user_id, state in vc.voice_states.items()
                    if (
                        self.bot.get_user(user_id)
                        and self.bot.get_user(user_id).bot is False
                    )
                ]
            except Exception:
                non_bot_users = []

            if len(non_bot_users) > 1:
                voice_members.extend([
                    (user_id, vc.guild.id, vc.id)
                    for user_id, state in non_bot_users
                    if self.valid_voice_state(state)
                ])

        for user_id, guild_id, channel_id in voice_members.copy():
            blacklisted_roles: typing.List[int] = (
                self.bot.guild_settings[guild_id]
                .setdefault('blacklisted_vc_roles', list())
            )

            guild = self.bot.get_guild(guild_id)

            try:
                member = guild.get_member(user_id) or await guild.fetch_member(user_id)
                assert member is not None
            except (AssertionError, discord.HTTPException):
                voice_members.remove((user_id, guild_id, channel_id))
                continue

            if set(member._roles).intersection(blacklisted_roles):
                voice_members.remove((user_id, guild_id, channel_id))

        now = discord.utils.naive_dt(discord.utils.utcnow())

        records: typing.List[
            typing.Tuple[int, int, dt, int, typing.Literal["voice"]]
        ]
        records = [
            (
                user_id,
                guild_id,
                now,
                channel_id,
                "voice",
            )
            for user_id, guild_id, channel_id in voice_members
        ]

        if len(records) == 0:
            self.logger.info("Storing 0 cached VC messages in database")
            return

        hourly_counts = collections.Counter()
        daily_counts = collections.Counter()
        monthly_counts = collections.Counter()

        for user_id, guild_id, timestamp, channel_id, source in records:
            hour = timestamp.replace(minute=0, second=0, microsecond=0)
            day = timestamp.date()
            month = timestamp.replace(
                day=1,
                hour=0,
                minute=0,
                second=0,
                microsecond=0,
            ).date()

            key = (guild_id, user_id, source)

            hourly_counts[(*key, hour)] += 1
            daily_counts[(*key, day)] += 1
            monthly_counts[(*key, month)] += 1

        self.logger.info(f"Storing {len(records)} cached VC minutes in database")

        async with self.bot.database() as db:
            await db.conn.copy_records_to_table(
                'user_points',
                columns=(
                    'user_id',
                    'guild_id',
                    'timestamp',
                    'channel_id',
                    'source',
                ),
                records=records,
            )

            await db.conn.executemany(
                """
                INSERT INTO user_point_hourly_counts (
                    guild_id,
                    user_id,
                    source,
                    hour,
                    points
                )
                VALUES ($1, $2, $3::point_source, $4, $5)
                ON CONFLICT (guild_id, user_id, hour, source)
                DO UPDATE SET points = user_point_hourly_counts.points + EXCLUDED.points
                """,
                [
                    (guild_id, user_id, source, hour, points)
                    for (guild_id, user_id, source, hour), points
                    in hourly_counts.items()
                ],
            )

            await db.conn.executemany(
                """
                INSERT INTO user_point_daily_counts (
                    guild_id,
                    user_id,
                    source,
                    day,
                    points
                )
                VALUES ($1, $2, $3::point_source, $4, $5)
                ON CONFLICT (guild_id, user_id, day, source)
                DO UPDATE SET points = user_point_daily_counts.points + EXCLUDED.points
                """,
                [
                    (guild_id, user_id, source, day, points)
                    for (guild_id, user_id, source, day), points
                    in daily_counts.items()
                ],
            )

            await db.conn.executemany(
                """
                INSERT INTO user_point_monthly_counts (
                    guild_id,
                    user_id,
                    source,
                    month,
                    points
                )
                VALUES ($1, $2, $3::point_source, $4, $5)
                ON CONFLICT (guild_id, user_id, month, source)
                DO UPDATE SET points = user_point_monthly_counts.points + EXCLUDED.points
                """,
                [
                    (guild_id, user_id, source, month, points)
                    for (guild_id, user_id, source, month), points
                    in monthly_counts.items()
                ],
            )

        for user_id, guild_id, timestamp, channel_id, source in records:
            utils.cache.PointHolder.add_point(
                user_id,
                guild_id,
                utils.cache.PointSource["voice"],
                timestamp,
            )


def setup(bot: vbu.Bot):
    x = UserVCHandler(bot)
    bot.add_cog(x)
