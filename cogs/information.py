from datetime import datetime as dt, timedelta
import math
from typing import Optional, cast
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
        return await self.make_graph(ctx, [user.id], window_days, colours={user.id: "000000"}, segments=None)

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
        assert isinstance(days, int)

        # Type hint properly
        assert ctx.guild

        # This takes a while
        async with ctx.typing():

            # Get all their valid user IDs
            async with self.bot.database() as db:
                point_rows = await db(
                    """SELECT user_id, source, COUNT(timestamp) FROM user_points WHERE guild_id=$1 AND
                    timestamp > TIMEZONE('UTC', NOW()) - MAKE_INTERVAL(days => $2) GROUP BY user_id, source
                    ORDER BY COUNT(timestamp) DESC;""",
                    ctx.guild.id, days,
                )

            # Sort that into more formattable data
            user_data_dict = collections.defaultdict({
                'message': 0,
                'voice': 0,
                'minecraft': 0
            }.copy)
            for row in point_rows:
                user_data_dict[row['user_id']][row['source']] += row['count']

            # Get all data in a list format, ready to be sorted
            valid_guild_user_data = [
                {
                    'id': uid,
                    **d,
                }
                for uid, d in user_data_dict.items()
                if ctx.guild.get_member(uid)
            ]

            # Sort said list
            ordered_guild_user_data = sorted(
                valid_guild_user_data,
                key=lambda k: k['message'] + (k['voice'] // 5) + (k['minecraft'] // 5),
                reverse=True,
            )

            # And now make it into strings
            ordered_guild_user_strings = []
            for d in ordered_guild_user_data:
                total_points = utils.get_all_points(d)
                vc_time = vbu.TimeValue(d['voice'] * 60).clean_spaced or '0m'
                if self.bot.guild_settings[ctx.guild.id]['minecraft_srv_authorization']:
                    text = (
                        "**<@{id}>** - **{total_points:,}** "
                        "(**{message:,}** text, **{voice}** VC, **{minecraft:,}** Minecraft)"
                    )
                else:
                    text = (
                        "**<@{id}>** - **{total_points:,}** "
                        "(**{message:,}** text, **{voice}** VC)"
                    )
                ordered_guild_user_strings.append(text.format(
                    id=d['id'], message=d['message'], minecraft=d['minecraft'],
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

        # Work out what our vars are
        default_days: int = self.bot.guild_settings[ctx.guild.id]['activity_window_days']
        days = days or default_days
        days = days if days > 0 else default_days
        user = user or ctx.author  # type: ignore

        # Typehint
        assert isinstance(days, int)
        assert user

        # And now get the points
        user_point_objects = await utils.cache.PointHolder.get_points_above_age(
            user.id,
            ctx.guild.id,
            days=days,
        )

        # Get our counts
        user_points = {
            "message": 0,
            "voice": 0,
            "minecraft": 0,
        }
        async for up in utils.alist(user_point_objects):
            user_points[up.source.name] += 1

        # And format into a list
        if self.bot.guild_settings[ctx.guild.id]['minecraft_srv_authorization']:
            total_points = utils.get_all_points(user_points)
            text = (
                f"Over the past {days} days, {user.mention} has gained **{user_points['message']:,}** "
                f"tracked messages, has been in VC for "
                f"**{vbu.TimeValue(user_points['voice'] * 60).clean or '0m'}**, and has been "
                f"on the Minecraft server for **{vbu.TimeValue(user_points['minecraft'] * 60).clean or '0m'}**, "
                f"giving them a total of **{total_points:,}** points."
            )
        else:
            total_points = user_points['message'] + (user_points['voice'] // 5)
            text = (
                f"Over the past {days} days, {user.mention} has gained **{user_points['message']:,}** "
                f"tracked messages and been in VC for "
                f"**{vbu.TimeValue(user_points['voice'] * 60).clean or '0m'}**, giving them "
                f"a total of **{total_points:,}** points."
            )
        await ctx.send(text, allowed_mentions=discord.AllowedMentions(users=[ctx.author]))

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
            colours: Optional[dict] = None,
            segments: Optional[int] = None):
        """
        Makes the actual graph for the thing innit mate.
        """

        # Make sure there's people
        if not users:
            return await ctx.send("You can't make a graph of 0 users.")
        if len(users) > 10:
            return await ctx.send((
                "There's more than 10 people in that graph - "
                "it would take too long for me to generate."
            ))

        # Pick up colours
        if colours is None:
            colours = {}

        # This takes a lil bit so let's gooooooo
        await ctx.trigger_typing()

        # Set up our most used vars
        original = window_days
        truncation = None
        if window_days > 365:
            window_days = 365
            truncation = (
                f"shortened from your original request of {original} "
                "days for going over the 365 day max"
            )
        if window_days > (discord.utils.utcnow() - ctx.guild.me.joined_at).days:
            window_days = (discord.utils.utcnow() - ctx.guild.me.joined_at).days
            truncation = (
                f"shortened from your original request of {original} "
                "days as I haven't been in the guild that long"
            )

        # Say how much time we're looking through
        # time_interval = ('days', 1,)
        # time_interval = ('hours', 24,)
        time_interval = ('hours', 6,)

        # Go through each day and work out how many points it has
        guild_day_range = self.bot.guild_settings[ctx.guild.id]['activity_window_days']
        points_per_week_base = [0.0 for _ in range(window_days * time_interval[1])]  # A list of the amount of points the user have in each given day (index)
        points_per_week: collections.defaultdict[int, list[float]]
        points_per_week = collections.defaultdict(points_per_week_base.copy)
        async for user_id in utils.alist(users):
            hour_range = window_days * time_interval[1]
            async for hour in utils.alist(range(hour_range)):
                all_point_generator = utils.cache.PointHolder.get_points_between_datetime(
                    user_id,
                    ctx.guild.id,
                    after=dt.utcnow() - timedelta(**{
                        time_interval[0]: (
                            hour_range
                            - hour
                            + (guild_day_range * time_interval[1])
                        )
                    }),
                    before=dt.utcnow() - timedelta(**{
                            time_interval[0]: (
                            hour_range
                            - hour
                        )
                    }),
                )
                user_points = 0.0
                async for point in all_point_generator:
                    point = cast(utils.cache.CachedPoint, point)
                    user_points += utils.get_points(1, point.source.name)
                points_per_week[user_id][hour] += user_points

        # Don't bother uploading if they've not got any data
        if sum([sum(user_points) for user_points in points_per_week.values()]) == 0:
            return await ctx.send("They've not sent any messages that I can graph.")

        # Get roles
        role_data: dict = (
            self.bot.guild_settings[ctx.guild.id]
            .get('role_gain', dict())
        )  # type: ignore
        role_object_data = sorted(
            [
                (threshold, ctx.guild.get_role(role_id))
                for role_id, threshold in role_data.items()
                if ctx.guild.get_role(role_id)
            ],
            key=lambda x: x[0],
        )

        # Build our output graph
        fig: plt.Figure = plt.figure()
        ax: plt.Axes = fig.subplots()

        # Plot data
        for user, points in points_per_week.items():
            if user in colours:
                colour = colours[user]
            else:
                colour = format(hex(random.randint(0, 0xffffff))[2:], "0>6")
            rgb_colour = tuple(int(colour[x:x + 2], 16) / 255 for x in (0, 2, 4))
            ax.plot(
                list(range(window_days * time_interval[1])),
                points,
                'k-',
                label=str(self.bot.get_user(user)) or user,
                color=rgb_colour,
            )
        if len(points_per_week) > 1:
            fig.legend(loc="upper left")

        # Set size
        MINOR_AXIS_STOP = 50
        if role_object_data:
            graph_height = max(
                [
                    role_object_data[-1][0] + MINOR_AXIS_STOP,
                    math.ceil(
                        (
                            max(
                                [max(i) for i in points_per_week.values()]
                            ) + 1
                        ) / MINOR_AXIS_STOP
                    ) * MINOR_AXIS_STOP,
                ]
            )
        else:
            graph_height = math.ceil(
                (
                    max(
                        [max(i) for i in points_per_week.values()]
                    ) + 1
                ) / MINOR_AXIS_STOP
            ) * MINOR_AXIS_STOP

        # Set axies
        ax.axis([
            0,
            window_days * time_interval[1],
            0,
            graph_height,
        ])

        # Fix axies
        ax.axis('off')
        ax.grid(True)

        # Add background colour
        for zorder, tier in zip(range(-100, -100 + (len(role_object_data) * 2), 2), role_object_data):
            plt.axhspan(
                tier[0],
                graph_height,
                facecolor=f"#{tier[1].colour.value or 0xffffff:0>6X}",
                zorder=zorder,
            )  # Add colour
            plt.axhspan(
                tier[0],
                tier[0] + 1,
                facecolor="#000000",
                zorder=zorder + 1,
            )  # Add single black line

        # Tighten border
        fig.tight_layout()

        # Output to user baybeeee
        fig.savefig('activity.png', bbox_inches='tight', pad_inches=0, format='png')
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
