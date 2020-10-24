from discord.ext import commands
import voxelbotutils as utils


class BotSettings(utils.Cog):

    @commands.group(cls=utils.Group)
    @commands.has_permissions(manage_guild=True)
    @commands.bot_has_permissions(send_messages=True, embed_links=True, add_reactions=True)
    @commands.guild_only()
    async def setup(self, ctx:utils.Context):
        """
        Run the bot setup.
        """

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
                'converter_args': [("Do you want to remove old roles when you get a new one?", "old role removal", utils.converters.BooleanConverter)],
                'callback': utils.SettingsMenuOption.get_set_guild_settings_callback('guild_settings', 'remove_old_roles'),
            },
            {
                'display': "Role gain settings",
                'callback': self.bot.get_command("setup roles"),
            },
            {
                'display': "Blacklisted channel settings",
                'callback': self.bot.get_command("setup blacklistedchannels"),
            },
            {
                'display': "Blacklisted role settings",
                'callback': self.bot.get_command("setup blacklistedroles"),
            },
            {
                'display': "Blacklisted VC role settings",
                'callback': self.bot.get_command("setup blacklistedvcroles"),
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
        """
        Run the bot setup.
        """

        # Create settings menu
        key_display_function = lambda k: getattr(ctx.guild.get_role(k), 'mention', 'none')
        menu = utils.SettingsMenuIterableBase(cache_key='role_gain', key_display_function=key_display_function, value_display_function=str)
        menu.add_convertable_value("What activity role would you like to add?", commands.RoleConverter)
        menu.add_convertable_value("How many tracked messages does a user have to send over 7 days to get that role?", int)
        menu.iterable_add_callback = utils.SettingsMenuOption.get_set_iterable_add_callback(
            database_name="role_list", column_name="role_id", cache_key="role_gain", database_key="RoleGain"
        )
        menu.iterable_delete_callback = utils.SettingsMenuOption.get_set_iterable_delete_callback(
            database_name="role_list", column_name="role_id", cache_key="role_gain", database_key="RoleGain"
        )
        await menu.start(ctx)

    @setup.command(cls=utils.Command)
    @utils.checks.meta_command()
    async def blacklistedchannels(self, ctx:utils.Context):
        """
        Run the bot setup.
        """

        # Create settings menu
        key_display_function = lambda k: getattr(ctx.bot.get_channel(k), 'mention', 'none')
        menu = utils.SettingsMenuIterableBase(cache_key='blacklisted_channels', key_display_function=key_display_function)
        menu.add_convertable_value("What channel would you like to blacklist?", commands.TextChannelConverter)
        menu.iterable_add_callback = utils.SettingsMenuOption.get_set_iterable_add_callback(
            database_name="channel_list", column_name="channel_id", cache_key="blacklisted_channels", database_key="BlacklistedChannel"
        )
        menu.iterable_delete_callback = utils.SettingsMenuOption.get_set_iterable_delete_callback(
            database_name="channel_list", column_name="channel_id", cache_key="blacklisted_channels", database_key="BlacklistedChannel"
        )
        await menu.start(ctx)

    @setup.command(cls=utils.Command)
    @utils.checks.meta_command()
    async def blacklistedroles(self, ctx:utils.Context):
        """
        Run the bot setup.
        """

        # Create settings menu
        key_display_function = lambda k: getattr(ctx.guild.get_role(k), 'mention', 'none')
        menu = utils.SettingsMenuIterableBase(cache_key='blacklisted_text_roles', key_display_function=key_display_function)
        menu.add_convertable_value("What channel would you like to blacklist?", commands.RoleConverter)
        menu.iterable_add_callback = utils.SettingsMenuOption.get_set_iterable_add_callback(
            database_name="role_list", column_name="role_id", cache_key="blacklisted_text_roles", database_key="BlacklistedRoles"
        )
        menu.iterable_delete_callback = utils.SettingsMenuOption.get_set_iterable_delete_callback(
            database_name="role_list", column_name="role_id", cache_key="blacklisted_text_roles", database_key="BlacklistedRoles"
        )
        await menu.start(ctx)

    @setup.command(cls=utils.Command)
    @utils.checks.meta_command()
    async def blacklistedvcroles(self, ctx:utils.Context):
        """
        Run the bot setup.
        """

        # Create settings menu
        key_display_function = lambda k: getattr(ctx.guild.get_role(k), 'mention', 'none')
        menu = utils.SettingsMenuIterableBase(cache_key='blacklisted_vc_roles', key_display_function=key_display_function)
        menu.add_convertable_value("What channel would you like to blacklist?", commands.RoleConverter)
        menu.iterable_add_callback = utils.SettingsMenuOption.get_set_iterable_add_callback(
            database_name="role_list", column_name="role_id", cache_key="blacklisted_vc_roles", database_key="BlacklistedVCRoles"
        )
        menu.iterable_delete_callback = utils.SettingsMenuOption.get_set_iterable_delete_callback(
            database_name="role_list", column_name="role_id", cache_key="blacklisted_vc_roles", database_key="BlacklistedVCRoles"
        )
        await menu.start(ctx)

    @commands.group(cls=utils.Group, enabled=False)
    @commands.bot_has_permissions(send_messages=True, embed_links=True, add_reactions=True)
    @utils.cooldown.cooldown(1, 60, commands.BucketType.member)
    @commands.guild_only()
    async def usersettings(self, ctx:utils.Context):
        """
        Run the bot setup.
        """

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
