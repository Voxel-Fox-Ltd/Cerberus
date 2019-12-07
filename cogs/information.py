import typing

import discord
from discord.ext import commands

from cogs import utils


class Information(utils.Cog):

    @commands.command()
    async def points(self, ctx:utils.Context, user:typing.Optional[discord.User], duration:typing.Optional[utils.converters.DurationConverter]={"days": 1}):
        """Tells you how many points a given user has"""

        user = user or ctx.author
        data = utils.CachedMessage.get_messages(user, ctx.guild, **duration)
        await ctx.send(len(data))

    @commands.command()
    async def leaderboard(self, ctx:utils.Context, duration:typing.Optional[utils.converters.DurationConverter]={"days": 1}):
        """Gives you the top 10 leaderboard users for the server"""

        all_keys_for_guild = [i for i in utils.CachedMessage.all_messages.keys() if i[1] == ctx.guild.id]
        all_data_for_guild = {}
        for key in all_keys_for_guild:
            all_data_for_guild[key[0]] = len(utils.CachedMessage.get_messages(key[0], ctx.guild, **duration))
        ordered_user_ids = sorted(all_data_for_guild.keys(), key=lambda k: all_data_for_guild[k], reverse=True)
        filtered_list = [i for i in ordered_user_ids if ctx.guild.get_member(i) is not None and self.bot.get_user(i).bot is False]
        await ctx.send('\n'.join([f"**{self.bot.get_user(i)!s}** - {all_data_for_guild[i]}" for i in filtered_list[:10]]))


def setup(bot:utils.CustomBot):
    x = Information(bot)
    bot.add_cog(x)
