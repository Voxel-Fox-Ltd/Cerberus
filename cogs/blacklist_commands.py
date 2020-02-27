import discord
from discord.ext import commands

from cogs import utils


class BlacklistCommands(utils.Cog):

	@commands.command(cls=utils.Command)
	@commands.has_permissions(manage_guild=True)
	@commands.guild_only()
	async def blacklistrole(self, ctx:utils.Context, *, role:discord.Role):
		"""Sets it so people don't receive points with a given role"""
		
		if(ctx.guild.id, role.id) in self.bot.blacklisted_roles:
			return await ctx.send(f"{role.name} is already blacklisted.")
		self.bot.blacklisted_roles.add((ctx.guild.id, role.id))
		async with self.bot.database as db:
			await db("INSERT INTO no_exp_roles VALUES ($1, $2) ON CONFLICT (channel_id) DO NOTHING", ctx.guild.id, role.id)
		return await ctx.send(f"Stopped tracking user messages with {role.name}.")

	@commands.command(cls=utils.Command)
	@commands.has_permissions(manage_guild=True)
	@commands.guild_only()
	async def whitelistrole(self, utils.Context, *, role:discord.Role)
		"""Re-allows the bot to track messages with a given role"""

		if(ctx.guild.id, role.id) not in self.bot.blacklisted_roles:
			return await ctx.send(f"{role.name} is not blacklisted")
		self.bot.blacklisted_roles.remove((ctx.guild.id, channel.id))
		async with self.bot.database() as db:
			await db("DELETE FROM no_exp_roles WHERE guild_id=$1 AND role_id=$2", ctx.guild.id, role.id)
		return await ctx.send(f"Now tracking user messages with {role.name}.")

    @commands.command(cls=utils.Command)
    @commands.has_permissions(manage_guild=True)
    @commands.guild_only()
    async def blacklistchannel(self, ctx:utils.Context, channel:discord.TextChannel=None):
        """Sets it so people don't receive points in a given text channel"""

        channel = channel or ctx.channel
        if (ctx.guild.id, channel.id) in self.bot.blacklisted_channels:
            return await ctx.send(f"{channel.mention} is already blacklisted.")
        self.bot.blacklisted_channels.add((ctx.guild.id, channel.id))
        async with self.bot.database() as db:
            await db("INSERT INTO no_exp_channels VALUES ($1, $2) ON CONFLICT (channel_id) DO NOTHING", ctx.guild.id, channel.id)
        return await ctx.send(f"Stopped tracking user messages in {channel.mention}.")

    @commands.command(cls=utils.Command, aliases=['unblacklistchannel'])
    @commands.has_permissions(manage_guild=True)
    @commands.guild_only()
    async def whitelistchannel(self, ctx:utils.Context, channel:discord.TextChannel=None):
        """Re-allows the bot to track messages in a given channel"""

        channel = channel or ctx.channel
        if (ctx.guild.id, channel.id) not in self.bot.blacklisted_channels:
            return await ctx.send(f"{channel.mention} is not blacklisted.")
        self.bot.blacklisted_channels.remove((ctx.guild.id, channel.id))
        async with self.bot.database() as db:
            await db("DELETE FROM no_exp_channels WHERE guild_id=$1 AND channel_id=$2", ctx.guild.id, channel.id)
        return await ctx.send(f"Now tracking user messages in {channel.mention}.")


def setup(bot:utils.Bot):
    x = BlacklistCommands(bot)
    bot.add_cog(x)

