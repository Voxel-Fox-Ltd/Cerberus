from discord.ext import commands

from cogs import utils


class Mee6Importer(utils.Cog):

    @commands.command(cls=utils.Command)
    @commands.guild_only()
    async def listmee6roles(self, ctx:utils.Context):
        """Lists the roles set up with Mee6"""

        # Get data from the Mee6 API
        base = "https://mee6.xyz/api/plugins/levels/leaderboard/"
        async with self.bot.session.get(base + str(ctx.guild.id)) as r:
            data = await r.json()
        if str(r.status) == '404':
            return await ctx.send("The leaderboard page for this guild is either not public or not present - Mee6 must be on your server for this to work.")

        # Output to user
        role_rewards = sorted(data['role_rewards'], key=lambda r: r['rank'])
        lines = [f"You have {len(role_rewards)} roles set up to be given out by Mee6."]
        for role in role_rewards:
            lines.append(f"Role at level {role['rank']}: **{role['role']['name']}**")
        return await ctx.send('\n'.join(lines))


def setup(bot:utils.Bot):
    x = Mee6Importer(bot)
    bot.add_cog(x)
