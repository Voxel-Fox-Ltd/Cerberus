import typing

import discord
from discord.ext import commands
from matplotlib import pyplot as plt

from cogs import utils


class Information(utils.Cog):

    @commands.command(cls=utils.Command)
    async def graph(self, ctx:utils.Context, user:typing.Optional[discord.Member], window_days:typing.Optional[int]=7):
        """Graphs your points over a given time"""

        await ctx.channel.trigger_typing()

        # Set up our most used vars
        user = user or ctx.author
        user_points = utils.UserPoints.get_user(user.id)
        points_per_day = [0] * window_days  # A list of the amount of points the user have in each given day (index)

        # Get the points in the given window
        cached_messages = user_points.get_cached_messages(days=window_days * 2)
        cached_minutes = user_points.get_cached_minutes(days=window_days * 2)

        # Set up our start time so we can filter day by day
        start = dt.utcnow() - timedelta(days=window_days)

        # Go through each day and work out how many points it has
        for index in range(window_days):

            def check(message_time):
                """Take the given time, return whether it's within our range or not"""
                current_day_max = (start + timedelta(days=index + 1))
                return (current_day_max - timedelta(days=window_days)) < message_time <= current_day_max

            a = len([i for i in cached_messages if check(i.created_at)])  # Message points
            b = len([i for i in cached_minutes if check(i.timestamp)])  # VC points
            points_per_day[index] = ((a + b) / window_days) * 10  # average * 10 (to make it a bigger number)

        # Build our output graph
        role_tiers = sorted(self.bot.config['role_tiers'], key=lambda t: t['required_score'])
        fig = plt.figure()
        ax = fig.subplots()

        # Plot data
        ax.plot(list(range(window_days)), points_per_day, 'k-')

        # Set size
        MINOR_AXIS_STOP = 500
        graph_height = max([role_tiers[-1]['required_score'] + MINOR_AXIS_STOP, math.ceil((max(points_per_day) + 1) / MINOR_AXIS_STOP) * MINOR_AXIS_STOP])
        ax.axis([0, window_days, 0, graph_height])

        # Fix axies
        ax.axis('off')

        # Add background colour
        for zorder, tier in zip(range(-100, -100 + len(role_tiers)), role_tiers):
            plt.axhspan(tier['required_score'], graph_height, facecolor=f"#{tier['embed_colour']:X}", zorder=zorder)

        # Tighten border
        fig.tight_layout()

        # Output to user baybeeee
        fig.savefig('activity.png', bbox_inches='tight', pad_inches=0)
        with utils.Embed() as embed:
            embed.set_image(url="attachment://activity.png")
        await ctx.send(f"Activity graph of **{user.nick or user.name}** over {window_days} days", embed=embed, file=discord.File("activity.png"))

    @commands.command(cls=utils.Command)
    async def points(self, ctx:utils.Context, user:typing.Optional[discord.Member], duration:typing.Optional[int]=7):
        """Tells you how many points a given user has"""

        user = user or ctx.author
        data = utils.CachedMessage.get_messages(user, ctx.guild, **duration)
        await ctx.send(f"{user.mention} has {len(data)} points over {duration} days.")

    @commands.command(cls=utils.Command)
    async def leaderboard(self, ctx:utils.Context, duration:typing.Optional[int]=7):
        """Gives you the top 10 leaderboard users for the server"""

        all_keys_for_guild = [i for i in utils.CachedMessage.all_messages.keys() if i[1] == ctx.guild.id]
        all_data_for_guild = {}
        for key in all_keys_for_guild:
            all_data_for_guild[key[0]] = len(utils.CachedMessage.get_messages(key[0], ctx.guild, days=duration))
        ordered_user_ids = sorted(all_data_for_guild.keys(), key=lambda k: all_data_for_guild[k], reverse=True)
        filtered_list = [i for i in ordered_user_ids if ctx.guild.get_member(i) is not None and self.bot.get_user(i).bot is False]
        await ctx.send(f"Points over {duration} days:\n\n" + '\n'.join([f"**{self.bot.get_user(i)!s}** - {all_data_for_guild[i]}" for i in filtered_list[:10]]))

    @commands.command(cls=utils.Command)
    async def averagepoints(self, ctx:commands.Context, user:typing.Optional[discord.Member], duration:typing.Optional[int]=7):
        """Gives you the average amount of points that a user has gained over a given period"""

        user = user or ctx.author

        # Work out an average for the time
        working = []
        for i in range(duration, 0, -1):
            after = {'day': duration - i + 1}
            before = {'day': duration - i}
            points = utils.CachedMessage.get_messages_between(user.id, user.guild.id, before=before, after=after)
            working.append(len(points))

        # Work out average
        average = sum(working) / len(working)

        # Return to user
        await ctx.send(f"{user.mention} has {average:.2f} average points over {duration} days ([{', '.join([str(i) for i in working])}]).")


def setup(bot:utils.Bot):
    x = Information(bot)
    bot.add_cog(x)
