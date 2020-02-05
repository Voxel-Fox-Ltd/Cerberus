import math
import typing

import discord
from discord.ext import commands
from matplotlib import pyplot as plt

from cogs import utils


class Information(utils.Cog):

    @commands.command(aliases=['points'], cls=utils.Command)
    async def graph(self, ctx:utils.Context, user:typing.Optional[discord.Member], window_days:typing.Optional[int]=7):
        """Graphs your points over a given time"""

        await ctx.channel.trigger_typing()

        # Set up our most used vars
        user = user or ctx.author
        points_per_week = [0] * window_days  # A list of the amount of points the user have in each given day (index)

        # Go through each day and work out how many points it has
        for index in range(window_days):

            between = 7 + window_days - index - 1, window_days - index - 1
            print(between)

            points_per_week[index] = len(utils.CachedMessage.get_messages_between(
                user.id, ctx.guild.id, after=dict(days=between[0]), before=dict(days=between[1])
            ))

        print(points_per_week)

        # Get roles
        async with self.bot.database() as db:
            role_data = await db("SELECT role_id, threshold FROM role_gain WHERE guild_id=$1", ctx.guild.id)
        role_object_data = sorted([(row['threshold'], ctx.guild.get_role(row['role_id'])) for row in role_data], key=lambda x: x[0])

        # Build our output graph
        fig = plt.figure()
        ax = fig.subplots()

        # Plot data
        ax.plot(list(range(window_days)), points_per_week, 'k-')

        # Set size
        MINOR_AXIS_STOP = 50
        graph_height = max([role_object_data[-1][0] + MINOR_AXIS_STOP, math.ceil((max(points_per_week) + 1) / MINOR_AXIS_STOP) * MINOR_AXIS_STOP])
        ax.axis([0, window_days, 0, graph_height])

        # Fix axies
        ax.axis('off')

        # Add background colour
        for zorder, tier in zip(range(-100, -100 + len(role_object_data)), role_object_data):
            plt.axhspan(tier[0], graph_height, facecolor=f"#{tier[1].colour.value or 0xffffff:0>6X}", zorder=zorder)

        # Tighten border
        fig.tight_layout()

        # Output to user baybeeee
        fig.savefig('activity.png', bbox_inches='tight', pad_inches=0)
        with utils.Embed() as embed:
            embed.set_image(url="attachment://activity.png")
        await ctx.send(f"Activity graph of **{user.nick or user.name}** in a {window_days} window, showing average activity over each 7 day period.", embed=embed, file=discord.File("activity.png"))

    @commands.command(cls=utils.Command)
    async def leaderboard(self, ctx:utils.Context):
        """Gives you the top 10 leaderboard users for the server"""

        all_keys_for_guild = [i for i in utils.CachedMessage.all_messages.keys() if i[1] == ctx.guild.id]
        all_data_for_guild = {}
        for key in all_keys_for_guild:
            all_data_for_guild[key[0]] = len(utils.CachedMessage.get_messages(key[0], ctx.guild, days=7))
        ordered_user_ids = sorted(all_data_for_guild.keys(), key=lambda k: all_data_for_guild[k], reverse=True)
        filtered_list = [i for i in ordered_user_ids if ctx.guild.get_member(i) is not None and self.bot.get_user(i).bot is False]
        await ctx.send(f"Points over 7 days:\n\n" + '\n'.join([f"**{self.bot.get_user(i)!s}** - {all_data_for_guild[i]}" for i in filtered_list[:10]]))


def setup(bot:utils.Bot):
    x = Information(bot)
    bot.add_cog(x)
