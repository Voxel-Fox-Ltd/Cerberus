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

    # @commands.command(aliases=['adddynamicrole'], cls=utils.Command)
    # @commands.has_permissions(manage_roles=True)
    # @commands.bot_has_permissions(send_messages=True)
    # @commands.guild_only()
    # async def addrole(self, ctx:utils.Context, threshold:int, *, role:discord.Role):
    #     """Adds a role that is given when a threshold is reached"""

    #     async with self.bot.database() as db:
    #         await db(
    #             """INSERT INTO role_gain (guild_id, role_id, threshold, period, duration) VALUES ($1, $2, $3, 'days', 7)
    #             ON CONFLICT (role_id) DO UPDATE SET threshold=excluded.threshold""",
    #             ctx.guild.id, role.id, threshold
    #         )
    #     current = self.role_handles[ctx.guild.id]
    #     if current is None:
    #         current = list()
    #     current.append({
    #         'role_id': role.id,
    #         'threshold': threshold,
    #     })
    #     self.role_handles[ctx.guild.id] = current
    #     await ctx.send(f"Now added - at an average of {threshold} points every 7 days, users will receive the **{role.name}** role.")
    #     self.logger.info(f"Added dynamic role {role.id} to guild {ctx.guild.id} at threshold {threshold}")

    # @commands.command(aliases=['removedrole', 'rdrole', 'removedynamicrole'], cls=utils.Command)
    # @commands.has_permissions(manage_roles=True)
    # @commands.bot_has_permissions(send_messages=True)
    # @commands.guild_only()
    # async def removerole(self, ctx:utils.Context, *, role:discord.Role):
    #     """Removes a role that is given"""

    #     async with self.bot.database() as db:
    #         await db("DELETE FROM role_gain WHERE role_id=$1", role.id)
    #     current = self.role_handles[ctx.guild.id]
    #     if current is not None:
    #         current = [i for i in current if i['role_id'] != role.id]
    #         self.role_handles[ctx.guild.id] = current
    #     await ctx.send(f"Now removed users receiving the **{role.name}** role.")
    #     self.logger.info(f"Removed dynamic role {role.id} to guild {ctx.guild.id}")        

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
