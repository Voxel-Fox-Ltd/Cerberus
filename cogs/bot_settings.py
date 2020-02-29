import asyncpg
from discord.ext import commands

from cogs import utils


class BotSettings(utils.Cog):

    @commands.command(cls=utils.Command)
    @commands.guild_only()
    @commands.bot_has_permissions(send_messages=True)
    @commands.has_permissions(manage_guild=True)
    async def prefix(self, ctx:utils.Context, *, new_prefix:str):
        """Changes the prefix that the bot uses"""

        # Validate prefix
        if len(new_prefix) > 30:
            return await ctx.send(f"The maximum length a prefix can be is 30 characters.")

        # Store setting
        self.bot.guild_settings[ctx.guild.id]['prefix'] = new_prefix
        async with self.bot.database() as db:
            try:
                await db("INSERT INTO guild_settings (guild_id, prefix) VALUES ($1, $2)", ctx.guild.id, new_prefix)
            except asyncpg.UniqueViolationError:
                await db("UPDATE guild_settings SET prefix=$2 WHERE guild_id=$1", ctx.guild.id, new_prefix)
        await ctx.send(f"My prefix has been updated to `{new_prefix}`.")

    @commands.command(cls=utils.Command)
    @commands.guild_only()
    @commands.bot_has_permissions(send_messages=True)
    @commands.has_permissions(manage_guild=True)
    async def removeoldroles(self, ctx:utils.Context, remove_old_roles:bool):
        """Whether or not to remove old roles upon level up or not."""
        
        # Store setting
        self.bot.guild_settings[ctx.guild.id]['remove_old_roles'] = remove_old_roles
        async with self.bot.database() as db:
            try:
                await db("INSERT INTO guild_settings (guild_id, remove_old_roles) VALUES ($1, $2)", ctx.guild.id, remove_old_roles)
            except asyncpg.UniqueViolationError:
                await db("UPDATE guild_settings SET remove_old_roles=$2 WHERE guild_id=$1", ctx.guild.id, remove_old_roles)
        if remove_old_roles is True:
            await ctx.send(f"I will now remove old roles upon level up.")
        else:
            await ctx.send(f"I will now no longer remove old roles upon level up.")


def setup(bot:utils.Bot):
    x = BotSettings(bot)
    bot.add_cog(x)
