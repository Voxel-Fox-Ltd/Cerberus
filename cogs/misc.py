from discord.ext import commands

from cogs import utils


class Misc(utils.cog):

    @commands.command()
    async def github(self, ctx:utils.Context):
        """Sends the GitHub Repository link"""

        await ctx.send("<https://github.com/4Kaylum/Cerberus/>")


def setup(bot:utils.CustomBot):
    x = Misc(bot)
    bot.add_cog(x)
