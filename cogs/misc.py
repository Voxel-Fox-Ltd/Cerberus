from discord.ext import commands

from cogs import utils


class Misc(utils.cog):

    @commands.command(aliases=['git', 'code'])
    async def github(self, ctx:utils.Context):
        """Sends the GitHub Repository link"""

        await ctx.send(f"<{self.bot.config.get('github')}>")


def setup(bot:utils.CustomBot):
    x = Misc(bot)
    bot.add_cog(x)
