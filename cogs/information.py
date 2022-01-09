import math
import typing
import collections
import random
from datetime import datetime as dt

import discord
from discord.ext import commands, vbu
from matplotlib import pyplot as plt


class Information(vbu.Cog):

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
        ),
    )
    @commands.defer()
    @commands.bot_has_permissions(send_messages=True, embed_links=True)
    @commands.cooldown(1, 60, commands.BucketType.user)
    @commands.guild_only()
    async def graph(self, ctx: vbu.Context, user: discord.Member = None, window_days: int = None):
        """
        Graphs your points over a given time.
        """

        user = user or ctx.author
        window_days = window_days or self.bot.guild_settings[ctx.guild.id]['activity_window_days']

        assert user
        assert window_days

        return await self.make_graph(ctx, [user.id], window_days, colours={user.id: "000000"}, segments=None)

    # @vbu.command(hidden=True, cooldown_after_parsing=True, add_slash_command=False, enabled=False)
    # @commands.bot_has_permissions(send_messages=True, embed_links=True)
    # @vbu.cooldown.cooldown(1, 60, commands.BucketType.user, cls=vbu.cooldown.Cooldown(mapping=vbu.cooldown.GroupedCooldownMapping("graph")))
    # @commands.guild_only()
    # async def multigraph(self, ctx:vbu.Context, users:commands.Greedy[vbu.converters.UserID], window_days:typing.Optional[int]=None):
    #     """
    #     Graphs your points over a given time.
    #     """

    #     if not users:
    #         return await ctx.send("You haven't given any users to look at.")
    #     if len(users) == 1:
    #         users = users + [ctx.author.id]
    #     window_days = window_days or self.bot.guild_settings[ctx.guild.id]['activity_window_days']
    #     await self.make_graph(ctx, users, window_days, segments=None)

    # @vbu.command(hidden=True, cooldown_after_parsing=True, add_slash_command=False)
    # @commands.bot_has_permissions(send_messages=True, embed_links=True)
    # @vbu.cooldown.cooldown(1, 60, commands.BucketType.user, cls=vbu.cooldown.Cooldown(mapping=vbu.cooldown.GroupedCooldownMapping("graph")))
    # @commands.guild_only()
    # async def multigraphrole(self, ctx:vbu.Context, role:discord.Role, window_days:typing.Optional[int]=None):
    #     """
    #     Graphs the points of a role over a given time.
    #     """

    #     window_days = window_days or self.bot.guild_settings[ctx.guild.id]['activity_window_days']
    #     await self.make_graph(ctx, [i.id for i in role.members], window_days, segments=None)

    @commands.command(
        aliases=['dynamicleaderboard', 'dlb', 'dylb', 'dynlb', 'lb'],
        application_command_meta=commands.ApplicationCommandMeta(
            options=[
                discord.ApplicationCommandOption(
                    name="window_days",
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
    async def leaderboard(self, ctx: vbu.Context, days: int = None):
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
                message_rows = await db(
                    """SELECT user_id, COUNT(timestamp) FROM user_messages WHERE guild_id=$1 AND
                    timestamp > TIMEZONE('UTC', NOW()) - MAKE_INTERVAL(days => $2) GROUP BY user_id
                    ORDER BY COUNT(timestamp) DESC;""",
                    ctx.guild.id, days,
                )
                vc_rows = await db(
                    """SELECT user_id, COUNT(timestamp) FROM user_vc_activity WHERE guild_id=$1 AND
                    timestamp > TIMEZONE('UTC', NOW()) - MAKE_INTERVAL(days => $2) GROUP BY user_id
                    ORDER BY COUNT(timestamp) DESC;""",
                    ctx.guild.id, days,
                )
                if self.bot.guild_settings[ctx.guild.id]['minecraft_srv_authorization']:
                    minecraft_rows = await db(
                        """SELECT user_id, COUNT(timestamp) FROM minecraft_server_activity WHERE guild_id=$1 AND
                        timestamp > TIMEZONE('UTC', NOW()) - MAKE_INTERVAL(days => $2) GROUP BY user_id
                        ORDER BY COUNT(timestamp) DESC;""",
                        ctx.guild.id, days,
                    )
                else:
                    minecraft_rows = []

            # Sort that into more formattable data
            user_data_dict = collections.defaultdict({'message_count': 0, 'vc_minute_count': 0, 'minecraft_minute_count': 0}.copy)  # uid: {message_count: int, vc_minute_count: int}
            for row in message_rows:
                user_data_dict[row['user_id']]['message_count'] = row['count']
            for row in vc_rows:
                user_data_dict[row['user_id']]['vc_minute_count'] = row['count']
            for row in minecraft_rows:
                user_data_dict[row['user_id']]['minecraft_minute_count'] = row['count']

            # And now make it into something we can sort
            valid_guild_user_data = [
                {'id': uid, 'm': d['message_count'], 'vc': d['vc_minute_count'], 'mc': d['minecraft_minute_count']}
                for uid, d in user_data_dict.items()
                if ctx.guild.get_member(uid)
            ]
            ordered_guild_user_data = sorted(valid_guild_user_data, key=lambda k: k['m'] + (k['vc'] // 5) + (k['mc'] // 5), reverse=True)

            # And now make it into strings
            ordered_guild_user_strings = []
            for d in ordered_guild_user_data:
                total_points = d['m'] + (d['vc'] // 5) + (d['mc'] // 5)
                vc_time = vbu.TimeValue(d['vc'] * 60).clean_spaced or '0m'
                if self.bot.guild_settings[ctx.guild.id]['minecraft_srv_authorization']:
                    ordered_guild_user_strings.append(f"**<@{d['id']}>** - **{total_points:,}** (**{d['m']:,}** text, **{vc_time}** VC, **{d['mc']:,}** Minecraft)")
                else:
                    ordered_guild_user_strings.append(f"**<@{d['id']}>** - **{total_points:,}** (**{d['m']:,}** text, **{vc_time}** VC)")

        # Make menu
        return await vbu.Paginator(ordered_guild_user_strings, formatter=vbu.Paginator.default_ranked_list_formatter).start(ctx)

    @commands.command(
        aliases=['dynamic', 'dyn', 'dy', 'd', 'dpoints', 'dpoint', 'rank'],
        application_command_meta=commands.ApplicationCommandMeta(
            options=[
                discord.ApplicationCommandOption(
                    name="user",
                    description="The user who you want to get the activity of.",
                    type=discord.ApplicationCommandOptionType.user,
                    required=False,
                ),
                discord.ApplicationCommandOption(
                    name="window_days",
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
    async def points(self, ctx: vbu.Context, user: discord.Member = None, days: int = None):
        """
        Shows you how many points you've achieved over a period of time.
        """

        # Work out what our vars are
        default_days: int = self.bot.guild_settings[ctx.guild.id]['activity_window_days']
        days = days or default_days
        days = days if days > 0 else default_days
        user = user or ctx.author

        # Typehint
        assert isinstance(days, int)
        assert isinstance(user, discord.Member)

        # And now get the points
        async with self.bot.database() as db:
            message_rows = await db(
                """SELECT user_id, COUNT(timestamp) FROM user_messages WHERE guild_id=$1 AND user_id=$2
                AND timestamp > TIMEZONE('UTC', NOW()) - MAKE_INTERVAL(days => $3 * 1) GROUP BY user_id""",
                ctx.guild.id, user.id, days,
            )
            vc_rows = await db(
                """SELECT user_id, COUNT(timestamp) FROM user_vc_activity WHERE guild_id=$1 AND user_id=$2
                AND timestamp > TIMEZONE('UTC', NOW()) - MAKE_INTERVAL(days => $3 * 1) GROUP BY user_id""",
                ctx.guild.id, user.id, days,
            )
            if self.bot.guild_settings[ctx.guild.id]['minecraft_srv_authorization']:
                minecraft_rows = await db(
                    """SELECT user_id, COUNT(timestamp) FROM minecraft_server_activity WHERE guild_id=$1 AND user_id=$2
                    AND timestamp > TIMEZONE('UTC', NOW()) - MAKE_INTERVAL(days => $3 * 1) GROUP BY user_id""",
                    ctx.guild.id, user.id, days,
                )
            else:
                minecraft_rows = []

        # Get our counts
        try:
            text = message_rows[0]['count']
        except IndexError:
            text = 0
        try:
            vc = vc_rows[0]['count']
        except IndexError:
            vc = 0
        try:
            mc = minecraft_rows[0]['count']
        except IndexError:
            mc = 0

        # And format into a list
        if self.bot.guild_settings[ctx.guild.id]['minecraft_srv_authorization']:
            await ctx.send(f"Over the past {days} days, {user.mention} has gained **{text:,}** tracked messages, has been in VC for **{vbu.TimeValue(vc * 60).clean or '0m'}**, and has been on the Minecraft server for **{vbu.TimeValue(mc * 60).clean or '0m'}**, giving them a total of **{text + (vc // 5) + (mc // 5):,}** points.", allowed_mentions=discord.AllowedMentions(users=[ctx.author]))
        else:
            await ctx.send(f"Over the past {days} days, {user.mention} has gained **{text:,}** tracked messages and been in VC for **{vbu.TimeValue(vc * 60).clean or '0m'}**, giving them a total of **{text + (vc // 5):,}** points.", allowed_mentions=discord.AllowedMentions(users=[ctx.author]))

    @commands.command(
        aliases=['dynamicroles', 'dyroles', 'dynroles', 'droles'],
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
        role_object_data = sorted([(threshold, ctx.guild.get_role(role_id)) for role_id, threshold in role_data.items() if ctx.guild.get_role(role_id)], key=lambda x: x[0], reverse=True)

        # Get roles with member counts
        counted_users = set()
        role_object_data_with_counts = []
        for index, (threshold, role) in enumerate(role_object_data):
            if not role:
                continue
            counter = len([i for i in role.members if i not in counted_users])
            counted_users.update(role.members)
            role_object_data_with_counts.append((threshold, role, counter))

        # Output nicely
        output = []
        activity_window_days = self.bot.guild_settings[ctx.guild.id]['activity_window_days']
        for threshold, role, counter in role_object_data_with_counts:
            output.append(f"**{role.mention}** :: `{threshold:,}` tracked activity every {activity_window_days} days ({counter:,} current members)")
        return await ctx.send('\n'.join(output), allowed_mentions=discord.AllowedMentions.none())

    async def make_graph(self, ctx, users: typing.List[int], window_days: int, *, colours: dict = None, segments: int = None):
        """
        Makes the actual graph for the thing innit mate.
        """

        # Make sure there's people
        if not users:
            return await ctx.send("You can't make a graph of 0 users.")
        if len(users) > 10:
            return await ctx.send("There's more than 10 people in that graph - it would take too long for me to generate.")

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
            truncation = f"shortened from your original request of {original} days for going over the 365 day max"
        if window_days > (discord.utils.utcnow() - ctx.guild.me.joined_at).days:
            window_days = (discord.utils.utcnow() - ctx.guild.me.joined_at).days
            truncation = f"shortened from your original request of {original} days as I haven't been in the guild that long"

        # Make sure there's actually a day
        window_interval = ('days', 1,)
        if window_days <= 2:
            window_days = 2
            window_interval = ('hours', 24,)

        # Go through each day and work out how many points it has
        points_per_week_base = [0 for _ in range(window_days * window_interval[1])]  # A list of the amount of points the user have in each given day (index)
        points_per_week = collections.defaultdict(points_per_week_base.copy)
        async with self.bot.database() as db:
            for user_id in users:
                message_rows = await db(
                    """SELECT COUNT(timestamp) AS count, generate_series
                    FROM user_messages, generate_series(1, $3)
                    WHERE
                        user_id=$1 AND guild_id=$2
                        AND timestamp > TIMEZONE('UTC', NOW()) - MAKE_INTERVAL({interval} => $3) + (MAKE_INTERVAL({interval} => 1) * generate_series) - MAKE_INTERVAL(days => $4)
                        AND timestamp <= TIMEZONE('UTC', NOW()) - MAKE_INTERVAL({interval} => $3) + (MAKE_INTERVAL({interval} => 1) * generate_series)
                    GROUP BY generate_series ORDER BY generate_series ASC""".format(interval=window_interval[0]),
                    user_id, ctx.guild.id, window_days * window_interval[1], self.bot.guild_settings[ctx.guild.id]['activity_window_days'],
                )
                for row in message_rows:
                    points_per_week[user_id][row['generate_series'] - 1] += row['count']
                vc_rows = await db(
                    """SELECT COUNT(timestamp) AS count, generate_series
                    FROM user_vc_activity, generate_series(1, $3)
                    WHERE
                        user_id=$1 AND guild_id=$2
                        AND timestamp > TIMEZONE('UTC', NOW()) - MAKE_INTERVAL({interval} => $3) + (MAKE_INTERVAL({interval} => 1) * generate_series) - MAKE_INTERVAL(days => $4)
                        AND timestamp <= TIMEZONE('UTC', NOW()) - MAKE_INTERVAL({interval} => $3) + (MAKE_INTERVAL({interval} => 1) * generate_series)
                    GROUP BY generate_series ORDER BY generate_series ASC""".format(interval=window_interval[0]),
                    user_id, ctx.guild.id, window_days * window_interval[1], self.bot.guild_settings[ctx.guild.id]['activity_window_days'],
                )
                for row in vc_rows:
                    points_per_week[user_id][row['generate_series'] - 1] += row['count'] // 5
                mc_rows = await db(
                    """SELECT COUNT(timestamp) AS count, generate_series
                    FROM minecraft_server_activity, generate_series(1, $3)
                    WHERE
                        user_id=$1 AND guild_id=$2
                        AND timestamp > TIMEZONE('UTC', NOW()) - MAKE_INTERVAL({interval} => $3) + (MAKE_INTERVAL({interval} => 1) * generate_series) - MAKE_INTERVAL(days => $4)
                        AND timestamp <= TIMEZONE('UTC', NOW()) - MAKE_INTERVAL({interval} => $3) + (MAKE_INTERVAL({interval} => 1) * generate_series)
                    GROUP BY generate_series ORDER BY generate_series ASC""".format(interval=window_interval[0]),
                    user_id, ctx.guild.id, window_days * window_interval[1], self.bot.guild_settings[ctx.guild.id]['activity_window_days'],
                )
                for row in mc_rows:
                    points_per_week[user_id][row['generate_series'] - 1] += row['count'] // 5

        # Don't bother uploading if they've not got any data
        if sum([sum(user_points) for user_points in points_per_week.values()]) == 0:
            return await ctx.send("They've not sent any messages that I can graph.")

        # Get roles
        role_data = self.bot.guild_settings[ctx.guild.id]['role_gain']
        role_object_data = sorted([(threshold, ctx.guild.get_role(role_id)) for role_id, threshold in role_data.items() if ctx.guild.get_role(role_id)], key=lambda x: x[0])

        # Build our output graph
        fig = plt.figure()
        ax = fig.subplots()

        # Plot data
        for user, points in points_per_week.items():
            if user in colours:
                colour = colours.get(user)
            else:
                colour = format(hex(random.randint(0, 0xffffff))[2:], "0>6")
            rgb_colour = tuple(int(colour[x:x + 2], 16) / 255 for x in (0, 2, 4))
            ax.plot(list(range(window_days * window_interval[1])), points, 'k-', label=str(self.bot.get_user(user)) or user, color=rgb_colour)
        if len(points_per_week) > 1:
            fig.legend(loc="upper left")

        # Set size
        MINOR_AXIS_STOP = 50
        if role_object_data:
            graph_height = max([role_object_data[-1][0] + MINOR_AXIS_STOP, math.ceil((max([max(i) for i in points_per_week.values()]) + 1) / MINOR_AXIS_STOP) * MINOR_AXIS_STOP])
        else:
            graph_height = math.ceil((max([max(i) for i in points_per_week.values()]) + 1) / MINOR_AXIS_STOP) * MINOR_AXIS_STOP
        ax.axis([0, window_days * window_interval[1], 0, graph_height])

        # Fix axies
        ax.axis('off')
        ax.grid(True)

        # Add background colour
        for zorder, tier in zip(range(-100, -100 + (len(role_object_data) * 2), 2), role_object_data):
            plt.axhspan(tier[0], graph_height, facecolor=f"#{tier[1].colour.value or 0xffffff:0>6X}", zorder=zorder)
            plt.axhspan(tier[0], tier[0] + 1, facecolor="#000000", zorder=zorder + 1)

        # Tighten border
        fig.tight_layout()

        # Output to user baybeeee
        fig.savefig('activity.png', bbox_inches='tight', pad_inches=0)
        with vbu.Embed() as embed:
            embed.set_image(url="attachment://activity.png")
        self.bot.set_footer_from_config(embed)
        if len(points_per_week) > 1:
            await ctx.send(f"Activity graph in a {window_days} day window{(' (' + truncation + ')') if truncation else ''}, showing average activity over each {self.bot.guild_settings[ctx.guild.id]['activity_window_days']} day period.", embed=embed, file=discord.File("activity.png"))
        else:
            await ctx.send(f"<@!{users[0]}>'s graph in a {window_days} day window{(' (' + truncation + ')') if truncation else ''}, showing average activity over each {self.bot.guild_settings[ctx.guild.id]['activity_window_days']} day period.", embed=embed, file=discord.File("activity.png"), allowed_mentions=discord.AllowedMentions(users=False))

    # @vbu.command(cooldown_after_parsing=True, add_slash_command=False)
    # @commands.bot_has_permissions(send_messages=True, embed_links=True)
    # @vbu.cooldown.cooldown(1, 60, commands.BucketType.user, cls=vbu.cooldown.Cooldown(mapping=vbu.cooldown.GroupedCooldownMapping("graph")))
    # @commands.is_owner()
    # @commands.guild_only()
    # async def ograph(self, ctx:vbu.Context, user:typing.Optional[discord.Member], window_days:typing.Optional[int]=7, segments_per_window_datapoint:typing.Optional[int]=None):
    #     """
    #     Graphs your points over a given time.
    #     """

    #     user = user or ctx.author
    #     return await self.online_make_graph(ctx, [user.id], window_days, colours={user.id: "00ff00"}, segments=segments_per_window_datapoint)

    # @vbu.command(cooldown_after_parsing=True, add_slash_command=False)
    # @commands.bot_has_permissions(send_messages=True, embed_links=True)
    # @vbu.cooldown.cooldown(1, 60, commands.BucketType.user, cls=vbu.cooldown.Cooldown(mapping=vbu.cooldown.GroupedCooldownMapping("graph")))
    # @commands.is_owner()
    # @commands.guild_only()
    # async def multiograph(self, ctx:vbu.Context, users:commands.Greedy[vbu.converters.UserID], window_days:typing.Optional[int]=7, segments_per_window_datapoint:typing.Optional[int]=None):
    #     """
    #     Graphs your points over a given time.
    #     """

    #     return await self.online_make_graph(ctx, users, window_days, segments=segments_per_window_datapoint)

    # async def online_make_graph(self, ctx, users:typing.List[int], window_days:int, *, colours:dict=None, segments:int=None):
    #     """
    #     Makes the actual graph for the thing innit mate.
    #     """

    #     # Make sure there's people
    #     if not users:
    #         return await ctx.send("You can't make a graph of 0 users.")
    #     if len(users) > 10:
    #         return await ctx.send("There's more than 10 people in that graph - it would take too long for me to generate.")

    #     # Pick up colours
    #     if colours is None:
    #         colours = {}

    #     # This takes a lil bit so let's gooooooo
    #     await ctx.channel.trigger_typing()

    #     # Set up our most used vars
    #     original = window_days
    #     truncation = None
    #     if window_days > 365:
    #         window_days = 365
    #         truncation = f"shortened from your original request of {original} days for going over the 365 day max"
    #     if window_days > (discord.utils.utcnow() - ctx.guild.me.joined_at).days:
    #         window_days = (discord.utils.utcnow() - ctx.guild.me.joined_at).days
    #         truncation = f"shortened from your original request of {original} days as I haven't been in the guild that long"

    #     # Make sure there's actually a day
    #     if window_days == 0:
    #         window_days = 1

    #     # Go through each day and work out how many points it has
    #     points_per_week_base = [0 for _ in range(24 * 4)]  # A list of the amount of points the user have in each given day (index)
    #     points_per_week = collections.defaultdict(points_per_week_base.copy)
    #     async with self.bot.database() as db:
    #         for user_id in users:
    #             added_ticks = set()
    #             message_rows = await db(
    #                 """SELECT COUNT(timestamp) AS count, generate_series
    #                 FROM user_messages, generate_series(1, $3)
    #                 WHERE
    #                     user_id=$1 AND guild_id=$2
    #                     AND timestamp > TIMEZONE('UTC', NOW()) - MAKE_INTERVAL(mins => $3 * 15) + (MAKE_INTERVAL(mins => 15) * generate_series)
    #                     AND timestamp <= TIMEZONE('UTC', NOW()) - MAKE_INTERVAL(mins => $3 * 15) + (MAKE_INTERVAL(mins => 15) * (generate_series + 1))
    #                 GROUP BY generate_series ORDER BY generate_series ASC""",
    #                 user_id, ctx.guild.id, window_days * 24 * 4,
    #             )
    #             for row in message_rows:
    #                 points_per_week[user_id][(row['generate_series'] - 1) % len(points_per_week_base)] += int(bool(row['count']))
    #                 added_ticks.add(row['generate_series'])
    #             vc_rows = await db(
    #                 """SELECT COUNT(timestamp) AS count, generate_series
    #                 FROM user_vc_activity, generate_series(1, $3)
    #                 WHERE
    #                     user_id=$1 AND guild_id=$2
    #                     AND timestamp > TIMEZONE('UTC', NOW()) - MAKE_INTERVAL(mins => $3 * 15) + (MAKE_INTERVAL(mins => 15) * generate_series)
    #                     AND timestamp <= TIMEZONE('UTC', NOW()) - MAKE_INTERVAL(mins => $3 * 15) + (MAKE_INTERVAL(mins => 15) * (generate_series + 1))
    #                 GROUP BY generate_series ORDER BY generate_series ASC""",
    #                 user_id, ctx.guild.id, window_days * 24 * 4,
    #             )
    #             for row in vc_rows:
    #                 if row['generate_series'] in added_ticks:
    #                     continue
    #                 points_per_week[user_id][(row['generate_series'] - 1) % len(points_per_week_base)] += int(bool(row['count']))
    #             # self.logger.info(points_per_week[user_id])

    #     # Don't bother uploading if they've not got any data
    #     if sum([sum(user_points) for user_points in points_per_week.values()]) == 0:
    #         return await ctx.send("They've not sent any messages that I can graph.")

    #     # Build our output graph
    #     fig = plt.figure()
    #     ax = fig.subplots()

    #     # Plot colour fills
    #     user_rgb_colours = {}
    #     for user, point in points_per_week.items():
    #         if user in colours:
    #             colour = colours.get(user)
    #         else:
    #             colour = format(hex(random.randint(0, 0xffffff))[2:], "0>6")
    #         rgb_colour = tuple(int(colour[i:i + 2], 16) / 255 for i in (0, 2, 4))
    #         user_rgb_colours[user] = rgb_colour
    #         ax.fill_between(list(range(24 * 4)), 0, point, color=rgb_colour, step='pre', alpha=0.6 if len(points_per_week) > 1 else 1)

    #     # Plot data
    #     if len(points_per_week) <= 1:
    #         for user, point in points_per_week.items():
    #             ax.plot(list(range(24 * 4)), point, 'k-', label=str(self.bot.get_user(user)) or user, color=user_rgb_colours[user], drawstyle='steps')
    #     if len(points_per_week) > 1:
    #         fig.legend(loc="upper left")

    #     # Set size
    #     ax.axis([0, 24 * 4, 0, max([max(i) for i in points_per_week.values()])])

    #     # Fix axies
    #     plt.xticks(
    #         [i * 4 for i in range(24)],
    #         [(discord.utils.utcnow() - timedelta(days=1) + timedelta(hours=i)).strftime('%H:%M') for i in range(24)],
    #         rotation='vertical',
    #     )
    #     # plt.yticks([0, 1], ['Offline', 'Online'])
    #     plt.yticks()
    #     ax.grid(True)

    #     # Tighten border
    #     fig.tight_layout()

    #     # Output to user baybeeee
    #     fig.savefig('activity.png', bbox_inches='tight', pad_inches=0)
    #     with vbu.Embed() as embed:
    #         embed.set_image(url="attachment://activity.png")
    #     if len(points_per_week) > 1:
    #         await ctx.send(f"Activity graph in a {window_days} day window{(' (' + truncation + ')') if truncation else ''}, showing average activity over each 7 day period.", embed=embed, file=discord.File("activity.png"))
    #     else:
    #         await ctx.send(f"<@!{users[0]}>'s graph in a {window_days} day window{(' (' + truncation + ')') if truncation else ''}, showing average activity over each 7 day period.", embed=embed, file=discord.File("activity.png"), allowed_mentions=discord.AllowedMentions(users=False))


def setup(bot: vbu.Bot):
    x = Information(bot)
    bot.add_cog(x)
