from discord.ext import commands
import voxelbotutils as utils


class BotSettings(utils.Cog):

    @utils.group()
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
        settings_mention = utils.SettingsMenuOption.get_guild_settings_mention
        menu = utils.SettingsMenu()
        menu.add_multiple_options(
            utils.SettingsMenuOption(
                ctx=ctx,
                display=lambda c: "Remove old roles (currently {0})".format(settings_mention(c, 'remove_old_roles')),
                converter_args=(
                    utils.SettingsMenuConverter(
                        prompt="Do you want to remove old roles when you get a new one?",
                        asking_for="old role removal",
                        converter=utils.converters.BooleanConverter,
                    ),
                ),
                callback=utils.SettingsMenuOption.get_set_guild_settings_callback('guild_settings', 'remove_old_roles'),
                allow_nullable=False,
            ),
            utils.SettingsMenuOption(
                ctx=ctx,
                display=lambda c: "Set role interval time (currently {0} days)".format(settings_mention(c, 'activity_window_days')),
                converter_args=(
                    utils.SettingsMenuConverter(
                        prompt="How many days should activity be tracked over?",
                        asking_for="activity window",
                        converter=int,
                    ),
                ),
                callback=utils.SettingsMenuOption.get_set_guild_settings_callback('guild_settings', 'activity_window_days'),
                allow_nullable=False,
            ),
            utils.SettingsMenuOption(
                ctx=ctx,
                display="Role gain settings",
                callback=self.bot.get_command("setup roles"),
            ),
            utils.SettingsMenuOption(
                ctx=ctx,
                display="Blacklisted channel settings",
                callback=self.bot.get_command("setup blacklistedchannels"),
            ),
            utils.SettingsMenuOption(
                ctx=ctx,
                display="Blacklisted role settings",
                callback=self.bot.get_command("setup blacklistedroles"),
            ),
            utils.SettingsMenuOption(
                ctx=ctx,
                display="Blacklisted VC role settings",
                callback=self.bot.get_command("setup blacklistedvcroles"),
            ),
        )

        # Run the menu
        try:
            await menu.start(ctx)
            await ctx.send("Done setting up!")
        except utils.errors.InvokedMetaCommand:
            pass

    @setup.command()
    @utils.checks.meta_command()
    async def roles(self, ctx:utils.Context):
        """
        Run the bot setup.
        """

        menu = utils.SettingsMenuIterable(
            table_name='role_list',
            column_name='role_id',
            cache_key='role_gain',
            database_key='RoleGain',
            key_display_function=lambda k: getattr(ctx.guild.get_role(k), 'mention', 'none'),
            value_display_function=int,
            converters=(
                utils.SettingsMenuConverter(
                    prompt="What activity role would you like to add?",
                    asking_for="activity role",
                    converter=commands.RoleConverter,
                ),
                utils.SettingsMenuConverter(
                    prompt="How many tracked points does a user have earn to get that role?",
                    asking_for="point amount",
                    converter=int,
                ),
            ),
        )
        await menu.start(ctx)

    @setup.command()
    @utils.checks.meta_command()
    async def blacklistedchannels(self, ctx:utils.Context):
        """
        Run the bot setup.
        """

        menu = utils.SettingsMenuIterable(
            table_name='channel_list',
            column_name='channel_id',
            cache_key='blacklisted_channels',
            database_key='BlacklistedChannel',
            key_display_function=lambda k: getattr(ctx.bot.get_channel(k), 'mention', 'none'),
            converters=(
                utils.SettingsMenuConverter(
                    prompt="What channel would you like to blacklist users getting points in?",
                    asking_for="blacklist channel",
                    converter=commands.TextChannelConverter,
                ),
            ),
        )
        await menu.start(ctx)

    @setup.command()
    @utils.checks.meta_command()
    async def blacklistedroles(self, ctx:utils.Context):
        """
        Run the bot setup.
        """

        menu = utils.SettingsMenuIterable(
            table_name='role_list',
            column_name='role_id',
            cache_key='blacklisted_text_roles',
            database_key='BlacklistedRoles',
            key_display_function=lambda k: getattr(ctx.guild.get_role(k), 'mention', 'none'),
            converters=(
                utils.SettingsMenuConverter(
                    prompt="What role would you like to blacklist users getting points with?",
                    asking_for="blacklist role",
                    converter=commands.RoleConverter,
                ),
            ),
        )
        await menu.start(ctx)

    @setup.command()
    @utils.checks.meta_command()
    async def blacklistedvcroles(self, ctx:utils.Context):
        """
        Run the bot setup.
        """

        menu = utils.SettingsMenuIterable(
            table_name='role_list',
            column_name='role_id',
            cache_key='blacklisted_vc_roles',
            database_key='BlacklistedVCRoles',
            key_display_function=lambda k: getattr(ctx.guild.get_role(k), 'mention', 'none'),
            converters=(
                utils.SettingsMenuConverter(
                    prompt="What role would you like to blacklist users getting VC points with?",
                    asking_for="blacklist role",
                    converter=commands.RoleConverter,
                ),
            ),
        )
        await menu.start(ctx)

    @utils.group(enabled=False)
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
