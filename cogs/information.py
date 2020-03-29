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


POINTS_MESSAGE = """
Cerberus uses multiple methods of keeping track of points. To see your sent messages in the past 7 days, run `{0.prefix}dynamic` (or `{0.prefix}d`). To see your total sent messages, run `{0.prefix}static` (or `{0.prefix}s`).
""".strip()
LEADERBOARD_MESSAGE = """
Cerberus uses multiple methods of keeping track of points. To the leaderboard of sent messages in the past 7 days, run `{0.prefix}dynamicleaderboard` (or `{0.prefix}dlb`). To see the total sent message leaderboard, run `{0.prefix}staticleaderboard` (or `{0.prefix}slb`).
""".strip()
ROLES_MESSAGE = """
Cerberus uses multiple methods of keeping track of points. To the which roles you get for dynamic points days, run `{0.prefix}dynamicroles` (or `{0.prefix}droles`). To see the roles you receive for static messages, run `{0.prefix}staticroles` (or `{0.prefix}sroles`).
""".strip()


class VCLeaderboardSource(menus.ListPageSource):

    def __init__(self, bot, data):
        super().__init__(data, per_page=10)
        self.bot = bot

    async def format_page(self, menu, entries):
        offset = menu.current_page * self.per_page
        clean_rows = [(self.bot.get_user(row['user_id']), row['count'] * 60) for _, row in enumerate(entries, start=offset)]
        text = '\n'.join(f"**{i!s}** - `{utils.TimeValue(o).clean}`" for _, (i, o) in enumerate(clean_rows, start=offset))
        max_page = math.ceil(len(self.entries) / self.per_page)
        return '__Tracked VC Activity:__\n' + text + f'\n\nPage {menu.current_page + 1} of {max_page}'


class TextLeaderboardSource(menus.ListPageSource):

    def __init__(self, bot, data, header):
        super().__init__(data, per_page=10)
        self.bot = bot
        self.header = header

    async def format_page(self, menu, entries):
        offset = menu.current_page * self.per_page
        clean_rows = [(self.bot.get_user(i), o) for _, (i, o) in enumerate(entries, start=offset)]
        text = '\n'.join(f"**{i!s}** - `{o}`" for _, (i, o) in enumerate(clean_rows, start=offset))
        max_page = math.ceil(len(self.entries) / self.per_page)
        return f'__{self.header}:__\n' + text + f'\n\nPage {menu.current_page + 1} of {max_page}'


class Information(utils.Cog):

    @commands.command(cls=utils.Command)
    @commands.guild_only()
    async def graph(self, ctx:utils.Context, user:typing.Optional[discord.Member], window_days:typing.Optional[int]=7):
        """Graphs your points over a given time"""

        user = user or ctx.author
        return await self.make_graph(ctx, [user], window_days, {user.id: "000000"})

    @commands.command(cls=utils.Command, hidden=True)
    @commands.guild_only()
    async def multigraph(self, ctx:utils.Context, users:commands.Greedy[discord.Member], window_days:typing.Optional[int]=7):
        """Graphs your points over a given time"""

        if not users:
            return await ctx.send("You haven't given any users to look at.")
        if len(users) == 1:
            users = users + [ctx.author]
        await self.make_graph(ctx, users, window_days)

    @commands.command(cls=utils.Command, hidden=True)
    @commands.guild_only()
    async def multigraphrole(self, ctx:utils.Context, role:discord.Role, window_days:typing.Optional[int]=7):
        """Graphs the points of a role over a given time"""

        await self.make_graph(ctx, role.members, window_days)

    async def make_graph(self, ctx, users:typing.List[discord.Member], window_days:int, colours:dict=None):
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
        if window_days > (dt.utcnow() - min([i.joined_at for i in users])).days:
            window_days = (dt.utcnow() - min([i.joined_at for i in users])).days
            truncation = f"shortened from your original request of {original} days as {'someone you pinged has not' if len(users) > 1 else 'they have not'} been in the guild that long"
        if window_days > (dt.utcnow() - ctx.guild.me.joined_at).days:
            window_days = (dt.utcnow() - ctx.guild.me.joined_at).days
            truncation = f"shortened from your original request of {original} days as I haven't been in the guild that long"

        # Make sure there's actually a day
        if window_days == 0:
            window_days = 1

        # Check our window, see if we can make it a lil bigger for them
        # if window_days <= 1:
        #     window = 'minutes', window_days * 24 * 60, 24 * 60
        if window_days <= 10:
            window = 'hours', window_days * 24, 24
        else:
            window = 'days', window_days, 1

        # Go through each day and work out how many points it has
        points_per_week_base = [0] * window[1]  # A list of the amount of points the user have in each given day (index)
        points_per_week = collections.defaultdict(points_per_week_base.copy)
        for user in users:
            for index in range(window[1]):
                between = (7 * window[2]) + window[1] - index - 1, window[1] - index - 1
                points_per_week[user][index] = len(utils.CachedMessage.get_messages_between(
                    user.id, ctx.guild.id, after={window[0]: between[0]}, before={window[0]: between[1]}
                ))

        # Don't bother uploading if they've not got any data
        if sum([sum(user_points) for user_points in points_per_week.values()]) == 0:
            return await ctx.send("They've not sent any messages that I can graph.")

        # Get roles
        async with self.bot.database() as db:
            role_data = await db("SELECT role_id, threshold FROM role_gain WHERE guild_id=$1", ctx.guild.id)
        role_object_data = sorted([(row['threshold'], ctx.guild.get_role(row['role_id'])) for row in role_data if ctx.guild.get_role(row['role_id'])], key=lambda x: x[0])

        # Build our output graph
        fig = plt.figure()
        ax = fig.subplots()

        # Plot data
        for user, i in points_per_week.items():
            if user.id in colours:
                colour = colours.get(user.id)
            else:
                colour = format(hex(random.randint(0, 0xffffff))[2:], "0>6")
            rgb_colour = tuple(int(colour[i:i + 2], 16) / 255 for i in (0, 2, 4))
            ax.plot(list(range(window[1])), i, 'k-', label=(user.nick or user.name), color=rgb_colour)
        fig.legend(loc="upper left")

        # Set size
        MINOR_AXIS_STOP = 50
        if role_object_data:
            graph_height = max([role_object_data[-1][0] + MINOR_AXIS_STOP, math.ceil((max([max(i) for i in points_per_week.values()]) + 1) / MINOR_AXIS_STOP) * MINOR_AXIS_STOP])
        else:
            graph_height = math.ceil((max([max(i) for i in points_per_week.values()]) + 1) / MINOR_AXIS_STOP) * MINOR_AXIS_STOP
        ax.axis([0, window[1], 0, graph_height])

        # Fix axies
        ax.axis('off')
        ax.grid(True)

        # Add background colour
        for zorder, tier in zip(range(-100, -100 + (len(role_object_data) * 2), 2), role_object_data):
            plt.axhspan(tier[0], graph_height, facecolor=f"#{tier[1].colour.value or 0xffffff:0>6X}", zorder=zorder)
            plt.axhspan(tier[0], tier[0] + 1, facecolor=f"#000000", zorder=zorder + 1)

        # Tighten border
        fig.tight_layout()

        # Output to user baybeeee
        fig.savefig('activity.png', bbox_inches='tight', pad_inches=0)
        with utils.Embed() as embed:
            embed.set_image(url="attachment://activity.png")
        await ctx.send(f"Activity graph in a {window_days} day window{(' (' + truncation + ')') if truncation else ''}, showing average activity over each 7 day period.", embed=embed, file=discord.File("activity.png"))

    @commands.command(aliases=['rank'], cls=utils.Command)
    async def points(self, ctx:utils.Context):
        """Shows you all of the points based commands"""

        await ctx.send(POINTS_MESSAGE.format(ctx))

    @commands.command(aliases=['lb'], cls=utils.Command)
    async def leaderboard(self, ctx:utils.Context):
        """Shows you all of the leaderboard based commands"""

        await ctx.send(LEADERBOARD_MESSAGE.format(ctx))

    @commands.command(cls=utils.Command)
    async def roles(self, ctx:utils.Context):
        """Shows you all of the role based commands"""

        await ctx.send(ROLES_MESSAGE.format(ctx))

    @commands.command(aliases=['dlb', 'dylb', 'dynlb'], cls=utils.Command, hidden=True)
    @commands.guild_only()
    async def dynamicleaderboard(self, ctx:utils.Context, pages:int=1):
        """Gives you the leaderboard users for the server"""

        # Get all their valid user IDs
        all_keys_for_guild = [i for i in utils.CachedMessage.all_messages.keys() if i[1] == ctx.guild.id]
        all_data_for_guild = []  # (uid: int)

        # Get the user's points
        for key in all_keys_for_guild:
            all_data_for_guild.append((key[0], len(utils.CachedMessage.get_messages_after(key[0], ctx.guild, days=7))))

        # Order em
        valid_user_data = [i for i in all_data_for_guild if getattr(self.bot.get_user(i[0]), 'bot', False) is False and ctx.guild.get_member(i[0])]
        ordered_user_data = sorted(valid_user_data, key=lambda k: k[1], reverse=True)

        # Make menu
        pages = menus.MenuPages(
            source=TextLeaderboardSource(self.bot, ordered_user_data, "Tracked Messages over 7 days"),
            clear_reactions_after=True
        )
        return await pages.start(ctx)

    @commands.command(aliases=['slb', 'stlb'], cls=utils.Command, hidden=True)
    @commands.guild_only()
    async def staticleaderboard(self, ctx:utils.Context, pages:int=1):
        """Gives you the leaderboard users for the server"""

        static_message_count = [(i[0], o) for i, o in self.bot.message_count.items() if i[1] == ctx.guild.id]
        filtered_list = [i for i in static_message_count if ctx.guild.get_member(i[0]) is not None and self.bot.get_user(i[0]).bot is False]
        ordered_list = sorted(filtered_list, key=lambda x: x[1], reverse=True)
        max_page = math.ceil(len(ordered_list) / 10)
        await ctx.send(f"__Tracked Messages:__\n" + '\n'.join([f"**{self.bot.get_user(i[0])!s}** - {i[1]:,}" for i in ordered_list[(pages * 10) - 10:(pages * 10)]]) + f"\nPage **{pages}** out of **{max_page}**")

        # Get all their valid user IDs
        all_keys_for_guild = [(i[0], o) for i, o in self.bot.message_count.items() if i[1] == ctx.guild.id]

        # Order em
        valid_user_data = [i for i in all_keys_for_guild if getattr(self.bot.get_user(i[0]), 'bot', False) is False and ctx.guild.get_member(i[0])]
        ordered_user_data = sorted(valid_user_data, key=lambda k: k[1], reverse=True)

        # Make menu
        pages = menus.MenuPages(
            source=TextLeaderboardSource(self.bot, ordered_user_data, "Tracked Messages over 7 days"),
            clear_reactions_after=True
        )
        return await pages.start(ctx)

    @commands.command(aliases=['dyn', 'dy', 'd', 'dpoints', 'dpoint'], cls=utils.Command, hidden=True)
    @commands.guild_only()
    async def dynamic(self, ctx:utils.Context, user:typing.Optional[discord.Member]=None):
        """Shows you your message amount over 7 days"""

        user = user or ctx.author
        amount = len(utils.CachedMessage.get_messages_after(user.id, ctx.guild.id, days=7))
        await ctx.send(f"Over the past 7 days, {user.mention} has sent **{amount:,}** tracked messages.")

    @commands.command(aliases=['s', 'st', 'staticlevel', 'slevel', 'stlevel', 'srank', 'staticrank', 'strank', 'spoints', 'spoint'], cls=utils.Command, hidden=True)
    @commands.guild_only()
    async def static(self, ctx:utils.Context, user:typing.Optional[discord.Member]=None):
        """Tells you how many total messages you've sent"""

        user = user or ctx.author
        static_message_count = self.bot.message_count[(user.id, ctx.guild.id)]
        await ctx.send(f"{user.mention} has sent **{static_message_count:,}** total tracked messages.")

    @commands.command(aliases=['dyroles', 'dynroles', 'droles'], cls=utils.Command, hidden=True)
    @commands.guild_only()
    async def dynamicroles(self, ctx:utils.Context):
        """Shows you the roles that have been set up for the guild"""

        # Get roles
        async with self.bot.database() as db:
            role_data = await db("SELECT role_id, threshold FROM role_gain WHERE guild_id=$1", ctx.guild.id)
        if not role_data:
            return await ctx.send("There are no roles set up for this guild.")
        role_object_data = sorted([(row['threshold'], ctx.guild.get_role(row['role_id'])) for row in role_data if ctx.guild.get_role(row['role_id'])], key=lambda x: x[0], reverse=True)

        # Output nicely
        output = []
        for threshold, role in role_object_data:
            output.append(f"**{role.name}** :: `{threshold}` tracked messages every 7 days")
        return await ctx.send('\n'.join(output))

    @commands.command(aliases=['sroles', 'stroles'], cls=utils.Command, hidden=True)
    @commands.guild_only()
    async def staticroles(self, ctx:utils.Context):
        """Shows you the static roles that have been set up for the guild"""

        # Get roles
        async with self.bot.database() as db:
            role_data = await db("SELECT role_id, threshold FROM static_role_gain WHERE guild_id=$1", ctx.guild.id)
        if not role_data:
            return await ctx.send("There are no static roles set up for this guild.")
        role_object_data = sorted([(row['threshold'], ctx.guild.get_role(row['role_id'])) for row in role_data if ctx.guild.get_role(row['role_id'])], key=lambda x: x[0], reverse=True)

        # Output nicely
        output = []
        for threshold, role in role_object_data:
            output.append(f"**{role.name}** :: `{threshold}` tracked messages")
        return await ctx.send('\n'.join(output))

    @commands.command(cls=utils.Command, hidden=True)
    @commands.guild_only()
    async def vcpoints(self, ctx:utils.Context, user:typing.Optional[discord.Member]=None):
        """Shows you the static roles that have been set up for the guild"""

        # Get data
        user = user or ctx.author
        async with self.bot.database() as db:
            data = await db("SELECT COUNT(*) FROM user_vc_activity WHERE guild_id=$1 AND user_id=$2", ctx.guild.id, user.id)

        # Output nicely
        timevalue = utils.TimeValue(data[0]['count'] * 60)
        return await ctx.send(f"{user.mention} has `{timevalue.clean}` of recorded VC activity.")

    @commands.command(cls=utils.Command, hidden=True)
    @commands.guild_only()
    async def vclb(self, ctx:utils.Context):
        """Shows you the static roles that have been set up for the guild"""

        # Get data
        async with self.bot.database() as db:
            data = await db("SELECT count(timestamp), user_id FROM user_vc_activity WHERE guild_id=$1 GROUP BY user_id ORDER BY count DESC", ctx.guild.id)
        if not data:
            return await ctx.send("Nobody in your server has any recorded VC activity.")

        # Output nicely
        pages = menus.MenuPages(source=VCLeaderboardSource(self.bot, data), clear_reactions_after=True)
        return await pages.start(ctx)


def setup(bot:utils.Bot):
    x = Information(bot)
    bot.add_cog(x)
