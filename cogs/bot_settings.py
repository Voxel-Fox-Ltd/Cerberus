import asyncpg
from discord.ext import commands

from cogs import utils


class BotSettings(utils.Cog):

    @commands.command(cls=utils.Command)
    @commands.has_permissions(manage_guild=True)
    @commands.bot_has_permissions(send_messages=True)
    @commands.guild_only()
    async def prefix(self, ctx:utils.Context, *, new_prefix:str):
        """Changes the prefix that the bot uses"""

        # Validate prefix
        if len(new_prefix) > 30:
            return await ctx.send(f"The maximum length a prefix can be is 30 characters.")

        # Store setting
        self.bot.guild_settings[ctx.guild.id]['prefix'] = new_prefix
        async with self.bot.database() as db:
            await db("INSERT INTO guild_settings (guild_id, prefix) VALUES ($1, $2) ON CONFLICT (guild_id) DO UPDATE SET prefix=excluded.prefix", ctx.guild.id, new_prefix)
        await ctx.send(f"My prefix has been updated to `{new_prefix}`.")

    # @commands.command(cls=utils.Command)
    # @commands.bot_has_permissions(send_messages=True)
    # @commands.has_permissions(manage_guild=True)
    # @commands.guild_only()
    # async def removeoldroles(self, ctx:utils.Context):
    #     """Removes old roles upon level up."""
        
    #     # Store setting
    #     self.bot.guild_settings[ctx.guild.id]['remove_old_roles'] = False
    #     async with self.bot.database() as db:
    #         try:
    #             await db("INSERT INTO guild_settings (guild_id, remove_old_roles) VALUES ($1, $2)", ctx.guild.id, False)
    #         except asyncpg.UniqueViolationError:
    #             await db("UPDATE guild_settings SET remove_old_roles=$2 WHERE guild_id=$1", ctx.guild.id, False)
        
    #     await ctx.send(f"I will now remove old roles upon level up.")
    
    # @commands.command(cls=utils.Command)
    # @commands.guild_only()
    # @commands.bot_has_permissions(send_messages=True)
    # @commands.has_permissions(manage_guild=True)
    # async def keepoldroles(self, ctx:utils.Context):
    #     """Keeps old roles upon level up."""
        
    #     # Store setting
    #     self.bot.guild_settings[ctx.guild.id]['remove_old_roles'] = True
    #     async with self.bot.database() as db:
    #         try:
    #             await db("INSERT INTO guild_settings (guild_id, remove_old_roles) VALUES ($1, $2)", ctx.guild.id, True)
    #         except asyncpg.UniqueViolationError:
    #             await db("UPDATE guild_settings SET remove_old_roles=$2 WHERE guild_id=$1", ctx.guild.id, True)
        
    #     await ctx.send(f"I will now keep old roles upon level up.")
        

    @commands.group(cls=utils.Group)
    @commands.has_permissions(manage_guild=True)
    @commands.bot_has_permissions(send_messages=True, embed_links=True, add_reactions=True)
    @commands.guild_only()
    async def setup(self, ctx:utils.Context):
        """Run the bot setup"""

        # Make sure it's only run as its own command, not a parent
        if ctx.invoked_subcommand is not None:
            return

        # Create settings menu
        menu = utils.SettingsMenu()
        settings_mention = utils.SettingsMenuOption.get_guild_settings_mention
        menu.bulk_add_options(
            ctx,
            {
                'display': lambda c: "Remove old roles (currently {0})".format(settings_mention(c, 'remove_old_roles')),
                'converter_args': [("Do you want to remove old roles when you get a new one?", "old role removal", commands.BooleanConverter)],
                'callback': utils.SettingsMenuOption.get_set_guild_settings_callback('guild_settings', 'remove_old_roles'),
            },
            {
                'display': "Role settings",
                'callback': self.bot.get_command("setup roles"),
            },
        )
        try:
            await menu.start(ctx)
            await ctx.send("Done setting up!")
        except utils.errors.InvokedMetaCommand:
            pass

    @setup.command(cls=utils.Command)
    @utils.checks.meta_command()
    async def roles(self, ctx:utils.Context):
        """Run the bot setup"""

        # Create settings menu
        key_display_function = lambda k: getattr(ctx.guild.get_role(k), 'mention', 'none')
        menu = utils.SettingsMenuIterable(
            'role_gain', 'role_id', 'role_gain', 'RoleGain',
            commands.RoleConverter, "What role would you like to add to the shop?", key_display_function,
            int, "How much should the role cost?",
        )
        await menu.start(ctx)

    @commands.group(cls=utils.Group, enabled=False)
    @commands.bot_has_permissions(send_messages=True, embed_links=True, add_reactions=True)
    @utils.cooldown.cooldown(1, 60, commands.BucketType.member)
    @commands.guild_only()
    async def usersettings(self, ctx:utils.Context):
        """Run the bot setup"""

        # Make sure it's only run as its own command, not a parent
        if ctx.invoked_subcommand is not None:
            return

        # Create settings menu
        menu = utils.SettingsMenu()
        settings_mention = utils.SettingsMenuOption.get_user_settings_mention
        menu.bulk_add_options(
            ctx,
            {
                'display': lambda c: "Set setting (currently {0})".format(settings_mention(c, 'setting_id')),
                'converter_args': [("What do you want to set the setting to?", "setting channel", commands.TextChannelConverter)],
                'callback': utils.SettingsMenuOption.get_set_user_settings_callback('user_settings', 'setting_id'),
            },
        )
        try:
            await menu.start(ctx)
            await ctx.send("Done setting up!")
        except utils.errors.InvokedMetaCommand:
            pass


def setup(bot:utils.Bot):
    x = BotSettings(bot)
    bot.add_cog(x)
