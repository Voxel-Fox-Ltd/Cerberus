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

    @commands.command(cls=utils.Command)
    @commands.bot_has_permissions(send_messages=True, embed_links=True)
    @commands.guild_only()
    async def graph(self, ctx:utils.Context, user:typing.Optional[discord.Member], window_days:typing.Optional[int]=7, segments_per_window_datapoint:typing.Optional[int]=None):
        """Graphs your points over a given time"""

        user = user or ctx.author
        return await self.make_graph(ctx, [user.id], window_days, colours={user.id: "000000"}, segments=segments_per_window_datapoint)

    @commands.command(cls=utils.Command, hidden=True)
    @commands.bot_has_permissions(send_messages=True, embed_links=True)
    @commands.guild_only()
    async def multigraph(self, ctx:utils.Context, users:commands.Greedy[utils.converters.UserID], window_days:typing.Optional[int]=7, segments_per_window_datapoint:typing.Optional[int]=None):
        """Graphs your points over a given time"""

        if not users:
            return await ctx.send("You haven't given any users to look at.")
        if len(users) == 1:
            users = users + [ctx.author.id]
        await self.make_graph(ctx, users, window_days, segments=segments_per_window_datapoint)

    @commands.command(cls=utils.Command, hidden=True)
    @commands.bot_has_permissions(send_messages=True, embed_links=True)
    @commands.guild_only()
    async def multigraphrole(self, ctx:utils.Context, role:discord.Role, window_days:typing.Optional[int]=7, segments_per_window_datapoint:typing.Optional[int]=None):
        """Graphs the points of a role over a given time"""

        await self.make_graph(ctx, [i.id for i in role.members], window_days, segments=segments_per_window_datapoint)

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
        # if window_days > (dt.utcnow() - min([i.joined_at for i in users])).days:
        #     window_days = (dt.utcnow() - min([i.joined_at for i in users])).days
        #     truncation = f"shortened from your original request of {original} days as {'someone you pinged has not' if len(users) > 1 else 'they have not'} been in the guild that long"
        if window_days > (dt.utcnow() - ctx.guild.me.joined_at).days:
            window_days = (dt.utcnow() - ctx.guild.me.joined_at).days
            truncation = f"shortened from your original request of {original} days as I haven't been in the guild that long"

        # Make sure there's actually a day
        if window_days == 0:
            window_days = 1

        # Check our window, see if we can make it a lil bigger for them
        # if window_days <= 1:
        #     window = 'minutes', window_days * 24 * 60, 24 * 60
        if window_days <= 3:
            window = 'hours', window_days * 24, 24
        else:
            window = 'days', window_days, 1
        # duration_name, segments_in_graph, datapoints_per_segment = window

        # Go through each day and work out how many points it has
        points_per_week_base = [0] * window[1]  # A list of the amount of points the user have in each given day (index)
        points_per_week = collections.defaultdict(points_per_week_base.copy)
        for user in users:
            for index in range(window[1]):
                between = (7 * window[2]) + window[1] - index - 1, window[1] - index - 1  # duration_start, duration_end
                cached_message_amount = len(utils.CachedMessage.get_messages_between(
                    user, ctx.guild.id, after={window[0]: between[0]}, before={window[0]: between[1]}
                ))
                cached_vc_minute_amount = len(utils.CachedVCMinute.get_minutes_between(
                    user, ctx.guild.id, after={window[0]: between[0]}, before={window[0]: between[1]}
                )) // 5
                points_per_week[user][index] = cached_message_amount + cached_vc_minute_amount

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
            if user in colours:
                colour = colours.get(user)
            else:
                colour = format(hex(random.randint(0, 0xffffff))[2:], "0>6")
            rgb_colour = tuple(int(colour[i:i + 2], 16) / 255 for i in (0, 2, 4))
            ax.plot(list(range(window[1])), i, 'k-', label=str(self.bot.get_user(user)) or user, color=rgb_colour)
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
            plt.axhspan(tier[0], tier[0] + 1, facecolor="#000000", zorder=zorder + 1)

        # Tighten border
        fig.tight_layout()

        # Output to user baybeeee
        fig.savefig('activity.png', bbox_inches='tight', pad_inches=0)
        with utils.Embed() as embed:
            embed.set_image(url="attachment://activity.png")
        await ctx.send(f"Activity graph in a {window_days} day window{(' (' + truncation + ')') if truncation else ''}, showing average activity over each 7 day period.", embed=embed, file=discord.File("activity.png"))

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
    async def points(self, ctx:utils.Context, user:typing.Optional[discord.Member]=None):
        """Shows you your message amount over 7 days"""

        user = user or ctx.author
        text = len(utils.CachedMessage.get_messages_after(user.id, ctx.guild.id, days=7))
        vc = len(utils.CachedVCMinute.get_minutes_after(user.id, ctx.guild.id, days=7))
        await ctx.send(f"Over the past 7 days, {user.mention} has gained **{text:,}** tracked messages and been in VC for **{utils.TimeValue(vc * 60).clean or '0m'}**, giving them a total of **{text + (vc // 5):,}** points.")

    # @commands.command(aliases=['dyroles', 'dynroles', 'droles'], cls=utils.Command, hidden=True)
    # @commands.bot_has_permissions(send_messages=True)
    # @commands.guild_only()
    # async def dynamicroles(self, ctx:utils.Context):
    #     """Shows you the roles that have been set up for the guild"""

    #     # Get roles
    #     async with self.bot.database() as db:
    #         role_data = await db("SELECT role_id, threshold FROM role_gain WHERE guild_id=$1", ctx.guild.id)
    #     if not role_data:
    #         return await ctx.send("There are no roles set up for this guild.")
    #     role_object_data = sorted([(row['threshold'], ctx.guild.get_role(row['role_id'])) for row in role_data if ctx.guild.get_role(row['role_id'])], key=lambda x: x[0], reverse=True)

    #     # Output nicely
    #     output = []
    #     for threshold, role in role_object_data:
    #         output.append(f"**{role.name}** :: `{threshold}` tracked messages every 7 days")
    #     return await ctx.send('\n'.join(output))


def setup(bot:utils.Bot):
    x = Information(bot)
    bot.add_cog(x)
