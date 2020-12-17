import math
import typing
import collections
import random
from datetime import datetime as dt, timedelta

import discord
from discord.ext import commands
from discord.ext import menus
from matplotlib import pyplot as plt
import voxelbotutils as utils


class LeaderboardSource(menus.ListPageSource):

    def __init__(self, bot, data, header):
        super().__init__(data, per_page=10)
        self.bot = bot
        self.header = header

    async def format_page(self, menu, entries):
        clean_rows = [(i, o, j) for i, o, j in entries]
        text = '\n'.join(f"**<@{i}>** - `{o + (j // 5):,}` (`{o:,}` text, `{utils.TimeValue(j * 60).clean or '0m'}` VC)" for i, o, j in clean_rows)
        max_page = math.ceil(len(self.entries) / self.per_page)
        return {
            "content": f"""__{self.header}:__\n{text}\n\nPage {menu.current_page + 1} of {max_page}""",
            "allowed_mentions": discord.AllowedMentions.none()
        }


class Information(utils.Cog):

    @commands.command(cls=utils.Command, cooldown_after_parsing=True)
    @commands.bot_has_permissions(send_messages=True, embed_links=True)
    @utils.cooldown.cooldown(1, 60, commands.BucketType.user, cls=utils.cooldown.Cooldown(mapping=utils.cooldown.GroupedCooldownMapping("graph")))
    @commands.guild_only()
    async def graph(self, ctx:utils.Context, user:typing.Optional[discord.Member], window_days:typing.Optional[int]=7, segments_per_window_datapoint:typing.Optional[int]=None):
        """
        Graphs your points over a given time.
        """

        user = user or ctx.author
        return await self.make_graph(ctx, [user.id], window_days, colours={user.id: "000000"}, segments=segments_per_window_datapoint)

    @commands.command(cls=utils.Command, hidden=True, cooldown_after_parsing=True)
    @commands.bot_has_permissions(send_messages=True, embed_links=True)
    @utils.cooldown.cooldown(1, 60, commands.BucketType.user, cls=utils.cooldown.Cooldown(mapping=utils.cooldown.GroupedCooldownMapping("graph")))
    @commands.guild_only()
    async def multigraph(self, ctx:utils.Context, users:commands.Greedy[utils.converters.UserID], window_days:typing.Optional[int]=7, segments_per_window_datapoint:typing.Optional[int]=None):
        """
        Graphs your points over a given time.
        """

        if not users:
            return await ctx.send("You haven't given any users to look at.")
        if len(users) == 1:
            users = users + [ctx.author.id]
        await self.make_graph(ctx, users, window_days, segments=segments_per_window_datapoint)

    @commands.command(cls=utils.Command, hidden=True, cooldown_after_parsing=True)
    @commands.bot_has_permissions(send_messages=True, embed_links=True)
    @utils.cooldown.cooldown(1, 60, commands.BucketType.user, cls=utils.cooldown.Cooldown(mapping=utils.cooldown.GroupedCooldownMapping("graph")))
    @commands.guild_only()
    async def multigraphrole(self, ctx:utils.Context, role:discord.Role, window_days:typing.Optional[int]=7, segments_per_window_datapoint:typing.Optional[int]=None):
        """
        Graphs the points of a role over a given time.
        """

        await self.make_graph(ctx, [i.id for i in role.members], window_days, segments=segments_per_window_datapoint)

    @commands.command(aliases=['dynamicleaderboard', 'dlb', 'dylb', 'dynlb', 'lb'], cls=utils.Command)
    @commands.bot_has_permissions(send_messages=True, embed_links=True)
    @commands.guild_only()
    async def leaderboard(self, ctx:utils.Context, days:int=None):
        """
        Gives you the leaderboard users for the server.
        """

        if days is None:
            days = self.bot.guild_settings[ctx.guild.id]['activity_window_days']
        elif days <= 0:
            days = 7
        elif days > 365:
            days = 365

        # This takes a while
        async with ctx.typing():

            # Get all their valid user IDs
            async with self.bot.database() as db:
                message_rows = await db(
                    """SELECT user_id, COUNT(timestamp) FROM user_messages WHERE guild_id=$1 AND
                    timestamp > TIMEZONE('UTC', NOW()) - MAKE_INTERVAL(days => $2) GROUP BY user_id
                    ORDER BY COUNT(timestamp) DESC LIMIT 30;""",
                    ctx.guild.id, days,
                )
                vc_rows = await db(
                    """SELECT user_id, COUNT(timestamp) FROM user_vc_activity WHERE guild_id=$1 AND
                    timestamp > TIMEZONE('UTC', NOW()) - MAKE_INTERVAL(days => $2) GROUP BY user_id
                    ORDER BY COUNT(timestamp) DESC LIMIT 30;""",
                    ctx.guild.id, days,
                )

            # Sort that into more formattable data
            user_data_dict = collections.defaultdict({'message_count': 0, 'vc_minute_count': 0}.copy)  # uid: {message_count: int, vc_minute_count: int}
            for row in message_rows:
                user_data_dict[row['user_id']]['message_count'] = row['count']
            for row in vc_rows:
                user_data_dict[row['user_id']]['vc_minute_count'] = row['count']

            # And now make it into something we can sort
            guild_user_data = [(uid, d['message_count'], d['vc_minute_count']) for uid, d in user_data_dict.items()]
            valid_guild_user_data = []
            for i in guild_user_data:
                try:
                    if ctx.guild.get_member(i[0]) or await ctx.guild.fetch_member(i[0]):
                        valid_guild_user_data.append(i)
                except discord.HTTPException:
                    pass
            ordered_guild_user_data = sorted(valid_guild_user_data, key=lambda k: k[1] + (k[2] // 5), reverse=True)

        # Make menu
        pages = menus.MenuPages(
            source=LeaderboardSource(self.bot, ordered_guild_user_data, f"Tracked Points over {days} days"),
            clear_reactions_after=True
        )
        return await pages.start(ctx)

    @commands.command(aliases=['dynamic', 'dyn', 'dy', 'd', 'dpoints', 'dpoint', 'rank'], cls=utils.Command)
    @commands.bot_has_permissions(send_messages=True)
    @commands.guild_only()
    async def points(self, ctx:utils.Context, user:typing.Optional[discord.Member]=None, days:int=None):
        """
        Shows you your message amount over 7 days.
        """

        default_days = self.bot.guild_settings[ctx.guild.id]['activity_window_days']
        days = days if days > 0 else default_days
        user = user or ctx.author
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
        try:
            text = message_rows[0]['count']
        except IndexError:
            text = 0
        try:
            vc = vc_rows[0]['count']
        except IndexError:
            vc = 0
        await ctx.send(f"Over the past {days} days, {user.mention} has gained **{text:,}** tracked messages and been in VC for **{utils.TimeValue(vc * 60).clean or '0m'}**, giving them a total of **{text + (vc // 5):,}** points.", allowed_mentions=discord.AllowedMentions(users=[ctx.author]))

    @commands.command(aliases=['dynamicroles', 'dyroles', 'dynroles', 'droles'], cls=utils.Command, hidden=True)
    @commands.bot_has_permissions(send_messages=True)
    @commands.guild_only()
    async def roles(self, ctx:utils.Context):
        """
        Shows you the roles that have been set up for the guild.
        """

        # Get roles
        role_data = self.bot.guild_settings[ctx.guild.id]['role_gain']
        if not role_data:
            return await ctx.send("There are no roles set up for this guild.")
        role_object_data = sorted([(threshold, ctx.guild.get_role(role_id)) for role_id, threshold in role_data.items() if ctx.guild.get_role(role_id)], key=lambda x: x[0], reverse=True)

        # Output nicely
        output = []
        for threshold, role in role_object_data:
            output.append(f"**{role.name}** :: `{threshold}` tracked messages every {self.bot.guild_settings[ctx.guild.id]['activity_window_days']} days")
        return await ctx.send('\n'.join(output))

    async def make_graph(self, ctx, users:typing.List[int], window_days:int, *, colours:dict=None, segments:int=None):
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
        await ctx.channel.trigger_typing()

        # Set up our most used vars
        original = window_days
        truncation = None
        if window_days > 365:
            window_days = 365
            truncation = f"shortened from your original request of {original} days for going over the 365 day max"
        if window_days > (dt.utcnow() - ctx.guild.me.joined_at).days:
            window_days = (dt.utcnow() - ctx.guild.me.joined_at).days
            truncation = f"shortened from your original request of {original} days as I haven't been in the guild that long"

        # Make sure there's actually a day
        if window_days == 0:
            window_days = 1

        # Go through each day and work out how many points it has
        points_per_week_base = [0 for _ in range(window_days)]  # A list of the amount of points the user have in each given day (index)
        points_per_week = collections.defaultdict(points_per_week_base.copy)
        async with self.bot.database() as db:
            for user_id in users:
                message_rows = await db(
                    """SELECT COUNT(timestamp) AS count, generate_series
                    FROM user_messages, generate_series(1, $3)
                    WHERE
                        user_id=$1 AND guild_id=$2
                        AND timestamp > TIMEZONE('UTC', NOW()) - MAKE_INTERVAL(days => $3) + (MAKE_INTERVAL(days => 1) * generate_series) - MAKE_INTERVAL(days => $4)
                        AND timestamp <= TIMEZONE('UTC', NOW()) - MAKE_INTERVAL(days => $3) + (MAKE_INTERVAL(days => 1) * generate_series)
                    GROUP BY generate_series ORDER BY generate_series ASC""",
                    user_id, ctx.guild.id, window_days, self.bot.guild_settings[ctx.guild.id]['activity_window_days'],
                )
                for row in message_rows:
                    points_per_week[user_id][row['generate_series'] - 1] += row['count']
                vc_rows = await db(
                    """SELECT COUNT(timestamp) AS count, generate_series
                    FROM user_vc_activity, generate_series(1, $3)
                    WHERE
                        user_id=$1 AND guild_id=$2
                        AND timestamp > TIMEZONE('UTC', NOW()) - MAKE_INTERVAL(days => $3) + (MAKE_INTERVAL(days => 1) * generate_series) - MAKE_INTERVAL(days => $4)
                        AND timestamp <= TIMEZONE('UTC', NOW()) - MAKE_INTERVAL(days => $3) + (MAKE_INTERVAL(days => 1) * generate_series)
                    GROUP BY generate_series ORDER BY generate_series ASC""",
                    user_id, ctx.guild.id, window_days, self.bot.guild_settings[ctx.guild.id]['activity_window_days'],
                )
                for row in vc_rows:
                    points_per_week[user_id][row['generate_series'] - 1] += row['count'] // 5
                self.logger.info(points_per_week[user_id])

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
            ax.plot(list(range(window_days)), points, 'k-', label=str(self.bot.get_user(user)) or user, color=rgb_colour)
        if len(points_per_week) > 1:
            fig.legend(loc="upper left")

        # Set size
        MINOR_AXIS_STOP = 50
        if role_object_data:
            graph_height = max([role_object_data[-1][0] + MINOR_AXIS_STOP, math.ceil((max([max(i) for i in points_per_week.values()]) + 1) / MINOR_AXIS_STOP) * MINOR_AXIS_STOP])
        else:
            graph_height = math.ceil((max([max(i) for i in points_per_week.values()]) + 1) / MINOR_AXIS_STOP) * MINOR_AXIS_STOP
        ax.axis([0, window_days, 0, graph_height])

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
        with utils.Embed() as embed:
            embed.set_image(url="attachment://activity.png")
        if len(points_per_week) > 1:
            await ctx.send(f"Activity graph in a {window_days} day window{(' (' + truncation + ')') if truncation else ''}, showing average activity over each {self.bot.guild_settings[ctx.guild.id]['activity_window_days']} day period.", embed=embed, file=discord.File("activity.png"))
        else:
            await ctx.send(f"<@!{users[0]}>'s graph in a {window_days} day window{(' (' + truncation + ')') if truncation else ''}, showing average activity over each {self.bot.guild_settings[ctx.guild.id]['activity_window_days']} day period.", embed=embed, file=discord.File("activity.png"), allowed_mentions=discord.AllowedMentions(users=False))

    @commands.command(cls=utils.Command, cooldown_after_parsing=True)
    @commands.bot_has_permissions(send_messages=True, embed_links=True)
    @utils.cooldown.cooldown(1, 60, commands.BucketType.user, cls=utils.cooldown.Cooldown(mapping=utils.cooldown.GroupedCooldownMapping("graph")))
    @commands.is_owner()
    @commands.guild_only()
    async def ograph(self, ctx:utils.Context, user:typing.Optional[discord.Member], window_days:typing.Optional[int]=7, segments_per_window_datapoint:typing.Optional[int]=None):
        """
        Graphs your points over a given time.
        """

        user = user or ctx.author
        return await self.online_make_graph(ctx, [user.id], window_days, colours={user.id: "00ff00"}, segments=segments_per_window_datapoint)

    @commands.command(cls=utils.Command, cooldown_after_parsing=True)
    @commands.bot_has_permissions(send_messages=True, embed_links=True)
    @utils.cooldown.cooldown(1, 60, commands.BucketType.user, cls=utils.cooldown.Cooldown(mapping=utils.cooldown.GroupedCooldownMapping("graph")))
    @commands.is_owner()
    @commands.guild_only()
    async def multiograph(self, ctx:utils.Context, users:commands.Greedy[utils.converters.UserID], window_days:typing.Optional[int]=7, segments_per_window_datapoint:typing.Optional[int]=None):
        """
        Graphs your points over a given time.
        """

        return await self.online_make_graph(ctx, users, window_days, segments=segments_per_window_datapoint)

    async def online_make_graph(self, ctx, users:typing.List[int], window_days:int, *, colours:dict=None, segments:int=None):
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
        await ctx.channel.trigger_typing()

        # Set up our most used vars
        original = window_days
        truncation = None
        if window_days > 365:
            window_days = 365
            truncation = f"shortened from your original request of {original} days for going over the 365 day max"
        if window_days > (dt.utcnow() - ctx.guild.me.joined_at).days:
            window_days = (dt.utcnow() - ctx.guild.me.joined_at).days
            truncation = f"shortened from your original request of {original} days as I haven't been in the guild that long"

        # Make sure there's actually a day
        if window_days == 0:
            window_days = 1

        # Go through each day and work out how many points it has
        points_per_week_base = [0 for _ in range(24 * 4)]  # A list of the amount of points the user have in each given day (index)
        points_per_week = collections.defaultdict(points_per_week_base.copy)
        async with self.bot.database() as db:
            for user_id in users:
                added_ticks = set()
                message_rows = await db(
                    """SELECT COUNT(timestamp) AS count, generate_series
                    FROM user_messages, generate_series(1, $3)
                    WHERE
                        user_id=$1 AND guild_id=$2
                        AND timestamp > TIMEZONE('UTC', NOW()) - MAKE_INTERVAL(mins => $3 * 15) + (MAKE_INTERVAL(mins => 15) * generate_series)
                        AND timestamp <= TIMEZONE('UTC', NOW()) - MAKE_INTERVAL(mins => $3 * 15) + (MAKE_INTERVAL(mins => 15) * (generate_series + 1))
                    GROUP BY generate_series ORDER BY generate_series ASC""",
                    user_id, ctx.guild.id, window_days * 24 * 4,
                )
                for row in message_rows:
                    points_per_week[user_id][(row['generate_series'] - 1) % len(points_per_week_base)] += int(bool(row['count']))
                    added_ticks.add(row['generate_series'])
                vc_rows = await db(
                    """SELECT COUNT(timestamp) AS count, generate_series
                    FROM user_vc_activity, generate_series(1, $3)
                    WHERE
                        user_id=$1 AND guild_id=$2
                        AND timestamp > TIMEZONE('UTC', NOW()) - MAKE_INTERVAL(mins => $3 * 15) + (MAKE_INTERVAL(mins => 15) * generate_series)
                        AND timestamp <= TIMEZONE('UTC', NOW()) - MAKE_INTERVAL(mins => $3 * 15) + (MAKE_INTERVAL(mins => 15) * (generate_series + 1))
                    GROUP BY generate_series ORDER BY generate_series ASC""",
                    user_id, ctx.guild.id, window_days * 24 * 4,
                )
                for row in vc_rows:
                    if row['generate_series'] in added_ticks:
                        continue
                    points_per_week[user_id][(row['generate_series'] - 1) % len(points_per_week_base)] += int(bool(row['count']))
                # self.logger.info(points_per_week[user_id])

        # Don't bother uploading if they've not got any data
        if sum([sum(user_points) for user_points in points_per_week.values()]) == 0:
            return await ctx.send("They've not sent any messages that I can graph.")

        # Build our output graph
        fig = plt.figure()
        ax = fig.subplots()

        # Plot colour fills
        user_rgb_colours = {}
        for user, point in points_per_week.items():
            if user in colours:
                colour = colours.get(user)
            else:
                colour = format(hex(random.randint(0, 0xffffff))[2:], "0>6")
            rgb_colour = tuple(int(colour[i:i + 2], 16) / 255 for i in (0, 2, 4))
            user_rgb_colours[user] = rgb_colour
            ax.fill_between(list(range(24 * 4)), 0, point, color=rgb_colour, step='pre', alpha=0.6 if len(points_per_week) > 1 else 1)

        # Plot data
        if len(points_per_week) <= 1:
            for user, point in points_per_week.items():
                ax.plot(list(range(24 * 4)), point, 'k-', label=str(self.bot.get_user(user)) or user, color=user_rgb_colours[user], drawstyle='steps')
        if len(points_per_week) > 1:
            fig.legend(loc="upper left")

        # Set size
        ax.axis([0, 24 * 4, 0, max([max(i) for i in points_per_week.values()])])

        # Fix axies
        plt.xticks(
            [i * 4 for i in range(24)],
            [(dt.utcnow() - timedelta(days=1) + timedelta(hours=i)).strftime('%H:%M') for i in range(24)],
            rotation='vertical',
        )
        # plt.yticks([0, 1], ['Offline', 'Online'])
        plt.yticks()
        ax.grid(True)

        # Tighten border
        fig.tight_layout()

        # Output to user baybeeee
        fig.savefig('activity.png', bbox_inches='tight', pad_inches=0)
        with utils.Embed() as embed:
            embed.set_image(url="attachment://activity.png")
        if len(points_per_week) > 1:
            await ctx.send(f"Activity graph in a {window_days} day window{(' (' + truncation + ')') if truncation else ''}, showing average activity over each 7 day period.", embed=embed, file=discord.File("activity.png"))
        else:
            await ctx.send(f"<@!{users[0]}>'s graph in a {window_days} day window{(' (' + truncation + ')') if truncation else ''}, showing average activity over each 7 day period.", embed=embed, file=discord.File("activity.png"), allowed_mentions=discord.AllowedMentions(users=False))


def setup(bot:utils.Bot):
    x = Information(bot)
    bot.add_cog(x)
