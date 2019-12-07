import typing

import discord
from discord.ext import commands

from cogs import utils


class Information(utils.Cog):

    @commands.command()
    async def points(self, ctx:utils.Context, user:typing.Optional[discord.Member], duration:typing.Optional[utils.converters.DurationConverter]=utils.Duration('days', 7)):
        """Tells you how many points a given user has"""

        user = user or ctx.author
        data = utils.CachedMessage.get_messages(user, ctx.guild, **duration)
        await ctx.send(f"{user.mention} has {len(data)} points over {duration.duration} {duration.period}.")

    @commands.command()
    async def leaderboard(self, ctx:utils.Context, duration:typing.Optional[utils.converters.DurationConverter]=utils.Duration('days', 7)):
        """Gives you the top 10 leaderboard users for the server"""

        all_keys_for_guild = [i for i in utils.CachedMessage.all_messages.keys() if i[1] == ctx.guild.id]
        all_data_for_guild = {}
        for key in all_keys_for_guild:
            all_data_for_guild[key[0]] = len(utils.CachedMessage.get_messages(key[0], ctx.guild, **duration))
        ordered_user_ids = sorted(all_data_for_guild.keys(), key=lambda k: all_data_for_guild[k], reverse=True)
        filtered_list = [i for i in ordered_user_ids if ctx.guild.get_member(i) is not None and self.bot.get_user(i).bot is False]
        await ctx.send(f"Points over {duration.duration} {duration.period}:\n\n" + '\n'.join([f"**{self.bot.get_user(i)!s}** - {all_data_for_guild[i]}" for i in filtered_list[:10]]))

    @commands.command()
    async def averagepoints(self, ctx:commands.Context, user:typing.Optional[discord.Member], duration:typing.Optional[utils.converters.DurationConverter]=utils.Duration('days', 7)):
        """Gives you the average amount of points that a user has gained over a given period"""

        # Work out an average for the time
        working = []
        for i in range(duration.duration, 0, -1):
            after = {duration.period: (2 * duration.duration) - i}
            before = {duration.period: duration.duration - i}
            points = utils.CachedMessage.get_messages_between(user.id, user.guild.id, before=before, after=after)
            working.append(len(points))

        # Work out average
        average = sum(working) / len(working)

        # Return to user
        await ctx.send(f"{user.mention} has {average:.2f} average points over {duration.duration} {duration.period} ([{', '.join(working)}]).")


def setup(bot:utils.CustomBot):
    x = Information(bot)
    bot.add_cog(x)
