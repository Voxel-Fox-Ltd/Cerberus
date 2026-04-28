from datetime import datetime as dt, timedelta
import math
from typing import Optional
import collections
import random

import discord
from discord.ext import commands, vbu
from matplotlib import pyplot as plt

from cogs import utils


class Information(vbu.Cog[utils.types.Bot]):

    @commands.command(
        cooldown_after_parsing=True,
        application_command_meta=commands.ApplicationCommandMeta(
            options=[
                discord.ApplicationCommandOption(
                    name="user",
                    description="The user who you want to graph the activity of.",
                    type=discord.ApplicationCommandOptionType.user,
                    required=False,
                ),
                discord.ApplicationCommandOption(
                    name="window_days",
                    description="The number of days of activity that you want to graph.",
                    type=discord.ApplicationCommandOptionType.integer,
                    required=False,
                    min_value=2,
                ),
            ],
            guild_only=True,
        ),
    )
    @commands.defer()
    @commands.bot_has_permissions(send_messages=True, embed_links=True)
    @commands.cooldown(1, 60, commands.BucketType.user)
    @commands.guild_only()
    @vbu.checks.bot_is_ready()
    async def graph(
            self,
            ctx: vbu.Context,
            user: Optional[discord.Member] = None,
            window_days: Optional[int] = None):
        """
        Graphs your points over a given time.
        """

        user = user or ctx.author  # type: ignore
        assert user
        window_days = window_days or self.bot.guild_settings[ctx.guild.id]['activity_window_days']
        assert window_days
        return await self.make_graph(ctx, [user.id], window_days, colours={user.id: "000000"})

    @commands.command(
        aliases=['lb'],
        application_command_meta=commands.ApplicationCommandMeta(
            options=[
                discord.ApplicationCommandOption(
                    name="days",
                    description="The number of days of activity that you want to check.",
                    type=discord.ApplicationCommandOptionType.integer,
                    required=False,
                    min_value=2,
                ),
            ],
        ),
    )
    @commands.defer()
    @commands.bot_has_permissions(send_messages=True, embed_links=True)
    @commands.guild_only()
    @vbu.checks.bot_is_ready()
    async def leaderboard(self, ctx: vbu.Context, days: Optional[int] = None):
        """
        Gives you the leaderboard users for the server.
        """

        # Work out how long to graph over
        if days is None:
            days = self.bot.guild_settings[ctx.guild.id]['activity_window_days']  # type: ignore
        elif days <= 0:
            days = 7
        elif days > 365:
            days = 365
        elif isinstance(days, int):
            pass

        # Type hint properly
        assert ctx.guild

        # This takes a while
        async with ctx.typing():

            user_points = await utils.cache.PointHolder.get_guild_points_above_age(
                ctx.guild.id,
                days=days,
            )

            # Get all data in a list format, ready to be sorted
            valid_guild_user_data = [
                {
                    "id": uid,
                    "points": d,
                }
                for uid, d in user_points.items()
                if ctx.guild.get_member(uid)
            ]

            # Sort said list
            ordered_guild_user_data = sorted(
                valid_guild_user_data,
                key=lambda d: utils.cache.PointHolder.total_points(d["points"]),
                reverse=True,
            )

            # And now make it into strings
            ordered_guild_user_strings = []
            for d in ordered_guild_user_data:
                total_points = utils.cache.PointHolder.total_points(d["points"])
                vc_time = vbu.TimeValue(d["points"].get(utils.cache.PointSource.voice, 0) * 60).clean_spaced or '0m'
                text = (
                    "**<@{id}>** - **{total_points:,}** "
                    "(**{message:,}** text, **{voice}** VC)"
                )
                ordered_guild_user_strings.append(text.format(
                    id=d["id"], message=int(d["points"].get(utils.cache.PointSource.message, 0)),
                    total_points=total_points, voice=vc_time,
                ))

        # Make menu
        return await vbu.Paginator(
            ordered_guild_user_strings,
            formatter=vbu.Paginator.default_ranked_list_formatter,
        ).start(ctx)

    @commands.command(
        application_command_meta=commands.ApplicationCommandMeta(
            options=[
                discord.ApplicationCommandOption(
                    name="user",
                    description="The user who you want to get the activity of.",
                    type=discord.ApplicationCommandOptionType.user,
                    required=False,
                ),
                discord.ApplicationCommandOption(
                    name="days",
                    description="The number of days of activity that you want to get.",
                    type=discord.ApplicationCommandOptionType.integer,
                    required=False,
                    min_value=2,
                ),
            ],
        ),
    )
    @commands.defer()
    @commands.bot_has_permissions(send_messages=True)
    @commands.guild_only()
    @vbu.checks.bot_is_ready()
    async def points(
            self,
            ctx: vbu.Context,
            user: Optional[discord.Member] = None,
            days: Optional[int] = None):
        """
        Shows you how many points you've achieved over a period of time.
        """

        default_days: int = self.bot.guild_settings[ctx.guild.id]['activity_window_days']
        days = days or default_days
        days = days if days > 0 else default_days
        user = user or ctx.author  # type: ignore

        assert isinstance(days, int)
        assert user

        after = dt.utcnow() - timedelta(days=days)

        user_points: dict[utils.cache.PointSource, float] = collections.defaultdict(float)

        # Use daily buckets for longer ranges, hourly buckets for short ranges.
        bucket_type = "day"
        if days <= 15:
            bucket_type = "hour"
        elif days > 365:
            bucket_type = "month"

        bucketed_points = utils.cache.PointHolder.get_bucketed_points(
            user.id,
            ctx.guild.id,
            bucket=bucket_type,
        )

        for bucket_timestamp, source_counter in bucketed_points.items():
            if bucket_timestamp < after:
                continue

            for source, points in source_counter.items():
                user_points[source] += points

        # If these should be displayed as whole numbers
        user_points = {
            source: int(points)
            for source, points in user_points.items()
        }
        total_points = utils.cache.PointHolder.total_points(user_points)
        message_points = user_points.get(utils.cache.PointSource.message, 0.0)
        vc_points = user_points.get(utils.cache.PointSource.voice, 0.0)
        text = (
            f"Over the past {days} days, {user.mention} has gained **{message_points:,}** "
            f"tracked messages and been in VC for "
            f"**{vbu.TimeValue(vc_points * 60).clean or '0m'}**, giving them "
            f"a total of **{total_points:,}** points."
        )

        await ctx.send(
            text,
            allowed_mentions=discord.AllowedMentions(users=[ctx.author]),
        )

    @commands.command(
        application_command_meta=commands.ApplicationCommandMeta(),
    )
    @commands.defer()
    @commands.bot_has_permissions(send_messages=True)
    @commands.guild_only()
    async def roles(self, ctx: vbu.Context):
        """
        Shows you the roles that have been set up for the guild.
        """

        # Typehint
        assert ctx.guild

        # Get roles
        role_data = self.bot.guild_settings[ctx.guild.id]['role_gain']
        if not role_data:
            return await ctx.send("There are no roles set up for this guild.")
        role_object_data = sorted(
            [
                (threshold, ctx.guild.get_role(role_id))
                for role_id, threshold in role_data.items()
                if ctx.guild.get_role(role_id)
            ],
            key=lambda x: x[0],
            reverse=True,
        )

        # Get roles with member counts
        counted_users = set()
        role_object_data_with_counts = []
        for threshold, role in role_object_data:
            if not role:
                continue
            counter = len([i for i in role.members if i not in counted_users])
            counted_users.update(role.members)
            role_object_data_with_counts.append((threshold, role, counter))

        # Output nicely
        output = []
        activity_window_days = self.bot.guild_settings[ctx.guild.id]['activity_window_days']
        for threshold, role, counter in role_object_data_with_counts:
            output.append((
                f"**{role.mention}** :: `{threshold:,}` tracked activity "
                f"every {activity_window_days} days ({counter:,} current members)"
            ))
        return await ctx.send('\n'.join(output), allowed_mentions=discord.AllowedMentions.none())

    async def make_graph(
            self,
            ctx,
            users: list[int],
            window_days: int,
            *,
            colours: Optional[dict] = None):
        """
        Makes the actual graph for the thing innit mate.
        """

        if not users:
            return await ctx.send("You can't make a graph of 0 users.")

        if len(users) > 10:
            return await ctx.send((
                "There's more than 10 people in that graph - "
                "it would take too long for me to generate."
            ))

        colours = colours or {}

        await ctx.trigger_typing()

        original = window_days
        truncation = None

        # if window_days > 365:
        #     window_days = 365
        #     truncation = (
        #         f"shortened from your original request of {original} "
        #         "days for going over the 365 day max"
        #     )

        joined_days = (discord.utils.utcnow() - ctx.guild.me.joined_at).days
        if window_days > joined_days:
            window_days = joined_days
            truncation = (
                f"shortened from your original request of {original} "
                "days as I haven't been in the guild that long"
            )

        guild_day_range = self.bot.guild_settings[ctx.guild.id]['activity_window_days']

        today = dt.utcnow().replace(hour=0, minute=0, second=0, microsecond=0)
        graph_start = today - timedelta(days=window_days - 1)

        points_per_week: dict[int, list[float]] = {}

        if window_days <= 15:
            bucket_type = "hour"
        elif window_days > 365 * 2:
            bucket_type = "month"
        else:
            bucket_type = "day"

        for user_id in users:
            bucketed_points = utils.cache.PointHolder.get_bucketed_points(
                user_id,
                ctx.guild.id,
                bucket=bucket_type,
            )

            if bucket_type == "month":
                current_month = graph_start.replace(day=1)
                end_month = today.replace(day=1)

                monthly_points: list[float] = []
                bucket = current_month

                while bucket <= end_month:
                    source_counter = bucketed_points.get(bucket)
                    monthly_points.append(
                        utils.cache.PointHolder.total_points(source_counter)
                        if source_counter is not None
                        else 0.0
                    )

                    if bucket.month == 12:
                        bucket = bucket.replace(year=bucket.year + 1, month=1)
                    else:
                        bucket = bucket.replace(month=bucket.month + 1)

                points_per_week[user_id] = monthly_points
                continue

            if bucket_type == "hour":
                step_count = window_days * 24
                rolling_window_size = guild_day_range * 24

                graph_start_bucket = (
                    dt.utcnow()
                    .replace(minute=0, second=0, microsecond=0)
                    - timedelta(hours=step_count - 1)
                )

                history_start = graph_start_bucket - timedelta(hours=rolling_window_size)
                step_delta = timedelta(hours=1)

            else:
                step_count = window_days
                rolling_window_size = guild_day_range

                graph_start_bucket = graph_start.replace(
                    hour=0,
                    minute=0,
                    second=0,
                    microsecond=0,
                )

                history_start = graph_start_bucket - timedelta(days=rolling_window_size)
                step_delta = timedelta(days=1)

            raw_points: list[float] = []

            for offset in range(step_count + rolling_window_size):
                bucket = history_start + (step_delta * offset)

                if bucket_type == "hour":
                    bucket = bucket.replace(minute=0, second=0, microsecond=0)
                else:
                    bucket = bucket.replace(hour=0, minute=0, second=0, microsecond=0)

                source_counter = bucketed_points.get(bucket)

                raw_points.append(
                    utils.cache.PointHolder.total_points(source_counter)
                    if source_counter is not None
                    else 0.0
                )

            rolling_points: list[float] = []
            rolling_total = 0.0

            for index, points in enumerate(raw_points):
                rolling_total += points

                if index >= rolling_window_size:
                    rolling_total -= raw_points[index - rolling_window_size]

                if index >= rolling_window_size:
                    rolling_points.append(rolling_total)

            points_per_week[user_id] = rolling_points[:step_count]

        if sum(sum(user_points) for user_points in points_per_week.values()) == 0:
            return await ctx.send("They've not sent any messages that I can graph.")

        role_data: dict = (
            self.bot.guild_settings[ctx.guild.id]
            .get("role_gain", dict())
        )  # type: ignore

        role_object_data = sorted(
            [
                (threshold, ctx.guild.get_role(role_id))
                for role_id, threshold in role_data.items()
                if ctx.guild.get_role(role_id)
            ],
            key=lambda x: x[0],
        )

        fig: plt.Figure = plt.figure()
        ax: plt.Axes = fig.subplots()

        for user, points in points_per_week.items():
            if user in colours:
                colour = colours[user]
            else:
                colour = format(hex(random.randint(0, 0xffffff))[2:], "0>6")

            rgb_colour = tuple(
                int(colour[x:x + 2], 16) / 255
                for x in (0, 2, 4)
            )

            x_values = list(range(len(points)))

            ax.plot(
                x_values,
                points,
                'k-',
                label=str(self.bot.get_user(user)) or user,
                color=rgb_colour,
            )

        if len(points_per_week) > 1:
            fig.legend(loc="upper left")

        MINOR_AXIS_STOP = 50

        max_points = max(
            max(points)
            for points in points_per_week.values()
            if points
        )

        if role_object_data:
            graph_height = max(
                [
                    role_object_data[-1][0] + MINOR_AXIS_STOP,
                    math.ceil((max_points + 1) / MINOR_AXIS_STOP) * MINOR_AXIS_STOP,
                ]
            )
        else:
            graph_height = (
                math.ceil((max_points + 1) / MINOR_AXIS_STOP)
                * MINOR_AXIS_STOP
            )

        max_x = max(len(points) for points in points_per_week.values())

        ax.axis([
            0,
            max_x,
            0,
            graph_height,
        ])

        ax.axis('off')
        ax.grid(True)

        for zorder, tier in zip(
                range(-100, -100 + (len(role_object_data) * 2), 2),
                role_object_data):
            plt.axhspan(
                tier[0],
                graph_height,
                facecolor=f"#{tier[1].colour.value or 0xffffff:0>6X}",
                zorder=zorder,
            )
            plt.axhspan(
                tier[0],
                tier[0] + 1,
                facecolor="#000000",
                zorder=zorder + 1,
            )

        fig.tight_layout()

        fig.savefig(
            'activity.png',
            bbox_inches='tight',
            pad_inches=0,
            format='png',
        )

        embed = vbu.Embed().set_image(url="attachment://activity.png")
        self.bot.set_footer_from_config(embed)

        if len(points_per_week) > 1:
            await ctx.send(
                (
                    f"Activity graph in a {window_days} day window"
                    f"{(' (' + truncation + ')') if truncation else ''}, "
                    f"showing average activity over each "
                    f"{self.bot.guild_settings[ctx.guild.id]['activity_window_days']} "
                    f"day period."
                ),
                embed=embed,
                file=discord.File("activity.png"),
            )
        else:
            await ctx.send(
                (
                    f"<@!{users[0]}>'s graph in a {window_days} day window"
                    f"{(' (' + truncation + ')') if truncation else ''}, "
                    f"showing average activity over each "
                    f"{self.bot.guild_settings[ctx.guild.id]['activity_window_days']} "
                    f"day period."
                ),
                embed=embed,
                file=discord.File("activity.png"),
                allowed_mentions=discord.AllowedMentions.none(),
            )


def setup(bot: utils.types.Bot):
    x = Information(bot)
    bot.add_cog(x)
