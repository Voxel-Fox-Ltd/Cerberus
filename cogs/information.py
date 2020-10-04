import math
import typing
import collections
import random
from datetime import datetime as dt

import discord
from discord.ext import commands
from discord.ext import menus
from matplotlib import pyplot as plt

from cogs import utils


class LeaderboardSource(menus.ListPageSource):

    def __init__(self, bot, data, header):
        super().__init__(data, per_page=10)
        self.bot = bot
        self.header = header

    async def format_page(self, menu, entries):
        clean_rows = [(self.bot.get_user(i), o, j) for i, o, j in entries]
        text = '\n'.join(f"**{i!s}** - `{o + (j // 5):,}` (`{o:,}` text, `{utils.TimeValue(j * 60).clean or '0m'}` VC)" for i, o, j in clean_rows)
        max_page = math.ceil(len(self.entries) / self.per_page)
        return f'__{self.header}:__\n' + text + f'\n\nPage {menu.current_page + 1} of {max_page}'


class Information(utils.Cog):

    @commands.command(aliases=['g', 'graph'], cls=utils.Command, cooldown_after_parsing=True)
    @commands.bot_has_permissions(send_messages=True, embed_links=True)
    @utils.cooldown.cooldown(1, 60, commands.BucketType.user, cls=utils.cooldown.Cooldown(mapping=utils.cooldown.GroupedCooldownMapping("graph")))
    @commands.guild_only()
    async def graph(self, ctx:utils.Context, user:typing.Optional[discord.Member], window_days:typing.Optional[int]=7, segments_per_window_datapoint:typing.Optional[int]=None):
        """Graphs your points over a given time"""

        user = user or ctx.author
        return await self.make_graph(ctx, [user.id], window_days, colours={user.id: "000000"}, segments=segments_per_window_datapoint)

    @commands.command(cls=utils.Command, hidden=True, cooldown_after_parsing=True)
    @commands.bot_has_permissions(send_messages=True, embed_links=True)
    @utils.cooldown.cooldown(1, 60, commands.BucketType.user, cls=utils.cooldown.Cooldown(mapping=utils.cooldown.GroupedCooldownMapping("graph")))
    @commands.guild_only()
    async def multigraph(self, ctx:utils.Context, users:commands.Greedy[utils.converters.UserID], window_days:typing.Optional[int]=7, segments_per_window_datapoint:typing.Optional[int]=None):
        """Graphs your points over a given time"""

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
        """Graphs the points of a role over a given time"""

        await self.make_graph(ctx, [i.id for i in role.members], window_days, segments=segments_per_window_datapoint)

    @commands.command(aliases=['dynamicleaderboard', 'dlb', 'dylb', 'dynlb', 'lb'], cls=utils.Command)
    @commands.bot_has_permissions(send_messages=True, embed_links=True)
    @commands.guild_only()
    async def leaderboard(self, ctx:utils.Context, pages:int=1):
        """Gives you the leaderboard users for the server"""

        # Get all their valid user IDs
        all_keys_for_guild = [i for i in utils.CachedMessage.all_messages.keys() if i[1] == ctx.guild.id]
        all_data_for_guild = []  # (uid: int)

        # Get the user's points
        for key in all_keys_for_guild:
            all_data_for_guild.append((
                key[0],
                len(utils.CachedMessage.get_messages_after(key[0], ctx.guild, days=7)),
                len(utils.CachedVCMinute.get_minutes_after(key[0], ctx.guild, days=7)),
            ))

        # Order em
        valid_user_data = [i for i in all_data_for_guild if getattr(self.bot.get_user(i[0]), 'bot', False) is False and ctx.guild.get_member(i[0])]
        ordered_user_data = sorted(valid_user_data, key=lambda k: k[1] + (k[2] // 5), reverse=True)

        # Make menu
        pages = menus.MenuPages(
            source=LeaderboardSource(self.bot, ordered_user_data, "Tracked Points over 7 days"),
            clear_reactions_after=True
        )
        return await pages.start(ctx)

    @commands.command(aliases=['dynamic', 'dyn', 'dy', 'd', 'dpoints', 'dpoint', 'rank'], cls=utils.Command)
    @commands.bot_has_permissions(send_messages=True)
    @commands.guild_only()
    async def points(self, ctx:utils.Context, user:typing.Optional[discord.Member]=None, days:int=7):
        """Shows you your message amount over 7 days"""

        days = days if days > 0 else 7
        user = user or ctx.author
        text = len(utils.CachedMessage.get_messages_after(user.id, ctx.guild.id, days=days))
        vc = len(utils.CachedVCMinute.get_minutes_after(user.id, ctx.guild.id, days=days))
        await ctx.send(f"Over the past {days} days, {user.mention} has gained **{text:,}** tracked messages and been in VC for **{utils.TimeValue(vc * 60).clean or '0m'}**, giving them a total of **{text + (vc // 5):,}** points.", allowed_mentions=discord.AllowedMentions(users=[ctx.author]))

    @commands.command(aliases=['dynamicroles', 'dyroles', 'dynroles', 'droles'], cls=utils.Command, hidden=True)
    @commands.bot_has_permissions(send_messages=True)
    @commands.guild_only()
    async def roles(self, ctx:utils.Context):
        """Shows you the roles that have been set up for the guild"""

        # Get roles
        role_data = self.bot.guild_settings[ctx.guild.id]['role_gain']
        if not role_data:
            return await ctx.send("There are no roles set up for this guild.")
        role_object_data = sorted([(threshold, ctx.guild.get_role(role_id)) for role_id, threshold in role_data.items() if ctx.guild.get_role(role_id)], key=lambda x: x[0], reverse=True)

        # Output nicely
        output = []
        for threshold, role in role_object_data:
            output.append(f"**{role.name}** :: `{threshold}` tracked messages every 7 days")
        return await ctx.send('\n'.join(output))

    async def make_graph(self, ctx, users:typing.List[int], window_days:int, *, colours:dict=None, segments:int=None):
        """Makes the actual graph for the thing innit mate"""

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
                        AND timestamp > TIMEZONE('UTC', NOW()) - CAST(CONCAT($3, ' days') AS INTERVAL) + (INTERVAL '1 day' * generate_series) - INTERVAL '7 days'
                        AND timestamp <= TIMEZONE('UTC', NOW()) - CAST(CONCAT($3, ' days') AS INTERVAL) + (INTERVAL '1 day' * generate_series)
                    GROUP BY generate_series ORDER BY generate_series ASC""",
                    user_id, ctx.guild.id, window_days,
                )
                for row in message_rows:
                    points_per_week[user_id][row['generate_series'] - 1] += row['count']
                vc_rows = await db(
                    """SELECT COUNT(timestamp) AS count, generate_series
                    FROM user_vc_activity, generate_series(1, $3)
                    WHERE
                        user_id=$1 AND guild_id=$2
                        AND timestamp > TIMEZONE('UTC', NOW()) - CAST(CONCAT($3, ' days') AS INTERVAL) + (INTERVAL '1 day' * generate_series) - INTERVAL '7 days'
                        AND timestamp <= TIMEZONE('UTC', NOW()) - CAST(CONCAT($3, ' days') AS INTERVAL) + (INTERVAL '1 day' * generate_series)
                    GROUP BY generate_series ORDER BY generate_series ASC""",
                    user_id, ctx.guild.id, window_days,
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
        for user, i in points_per_week.items():
            if user in colours:
                colour = colours.get(user)
            else:
                colour = format(hex(random.randint(0, 0xffffff))[2:], "0>6")
            rgb_colour = tuple(int(colour[i:i + 2], 16) / 255 for i in (0, 2, 4))
            ax.plot(list(range(window_days)), i, 'k-', label=str(self.bot.get_user(user)) or user, color=rgb_colour)
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
        await ctx.send(f"Activity graph in a {window_days} day window{(' (' + truncation + ')') if truncation else ''}, showing average activity over each 7 day period.", embed=embed, file=discord.File("activity.png"))


def setup(bot:utils.Bot):
    x = Information(bot)
    bot.add_cog(x)
