import uuid

import discord
from discord.ext import vbu


menus = vbu.menus


# Remove old roles
def _remove_old_roles_display(ctx: vbu.SlashContext) -> str:
    s = ctx.bot.guild_settings[ctx.guild.id]['remove_old_roles']
    s = bool(s)
    s = str(s).lower()
    return f"Remove old roles (currently {s})"
remove_old_roles = menus.Option(
    display=_remove_old_roles_display,
    component_display="Remove old roles",
    converters=[
        menus.Converter(
            prompt="Do you want to remove old roles when new ones are gained?",
            converter=lambda payload: str(payload.custom_id).endswith(" YES"),
            timeout_message="Timed out asking for old role removal.",
            components=discord.ui.MessageComponents.boolean_buttons(
                yes=("Yes", f"{uuid.uuid4()} YES"),
                no=("No", f"{uuid.uuid4()} NO"),
            ),
        ),
    ],
    callback=menus.MenuCallbacks.set_table_column(
        menus.DataLocation.GUILD,
        "guild_settings",
        "remove_old_roles",
    ),
    cache_callback=menus.MenuCallbacks.set_cache_from_key(
        menus.DataLocation.GUILD,
        "remove_old_roles",
    ),
)


# Role interval time
def _role_interval_time_display(ctx: vbu.SlashContext) -> str:
    s = ctx.bot.guild_settings[ctx.guild.id]['activity_window_days']
    return f"Set role interval time (currently {s:,} days)"
def _role_interval_time_check(interaction: discord.Interaction) -> bool:
    val: str = interaction.components[0].components[0].value  # type: ignore
    return val.isdigit() and int(val) in range(7, 31)
role_interval_time = menus.Option(
    display=_role_interval_time_display,
    component_display="Role interval time",
    converters=[
        menus.Converter(
            prompt="How many days should activity be tracked over?",
            checks=[
                menus.ModalCheck(
                    check=_role_interval_time_check,
                    on_failure=menus.Check.failures.RETRY,
                    fail_message="You need to give a *number* between **7** and **31**.",
                ),
            ],
            converter=int,
            timeout_message="Timed out asking for activity window days.",
        ),
    ],
    callback=menus.MenuCallbacks.set_table_column(
        menus.DataLocation.GUILD,
        "guild_settings",
        "activity_window_days",
    ),
    cache_callback=menus.MenuCallbacks.set_cache_from_key(
        menus.DataLocation.GUILD,
        "activity_window_days",
    ),
    allow_none=False,
)


# Role gain menu
role_gain_settings = vbu.menus.Option(
    display="Role gain settings",
    callback=menus.MenuIterable(
        select_sql="""
            SELECT
                *
            FROM
                role_list
            WHERE
                guild_id=$1
            AND
                key = 'RoleGain'
            """,
        select_sql_args=lambda ctx: (
            ctx.guild.id,
        ),
        insert_sql="""
            INSERT INTO
                role_list
                (
                    guild_id,
                    role_id,
                    value,
                    key
                )
            VALUES
                (
                    $1,
                    $2,
                    $3,
                    'RoleGain'
                )
            """,
        insert_sql_args=lambda ctx, data: (
            ctx.guild.id,
            data[0].id,
            str(data[1]),
        ),
        delete_sql="""
            DELETE FROM
                role_list
            WHERE
                guild_id=$1
            AND
                role_id=$2
            AND
                key = 'RoleGain'
            """,
        delete_sql_args=lambda ctx, row: (
            ctx.guild.id,
            row['role_id'],
        ),
        converters=[
            menus.Converter(
                prompt="What role do you want to be gainable?",
                converter=lambda interaction: (
                    None
                    if interaction.custom_id.endswith("CANCEL")
                    else
                    list(interaction.resolved.roles.values())[0]
                ),
                components=discord.ui.MessageComponents(
                    discord.ui.ActionRow(
                        discord.ui.RoleSelectMenu(),
                    ),
                    discord.ui.ActionRow(
                        discord.ui.Button(
                            label="Cancel",
                            custom_id=f"{uuid.uuid4()} CANCEL",
                        ),
                    ),
                ),
            ),
            menus.Converter(
                prompt="How many points does this role require to be gainable?",
                converter=int,
            ),
        ],
        row_text_display=lambda ctx, row: (
            f"{ctx.get_mentionable_role(row['role_id']).mention} - {int(row['value']):,}"
        ),
        row_component_display=lambda ctx, row: (
            ctx.get_mentionable_role(row['role_id']).name,
            row['role_id'],
        ),
        cache_callback=menus.MenuCallbacks.set_iterable_dict_cache(
            menus.DataLocation.GUILD,
            "role_gain",
        ),
        cache_delete_callback=menus.MenuCallbacks.delete_iterable_dict_cache(
            menus.DataLocation.GUILD,
            "role_gain",
        ),
        cache_delete_args=lambda row: (
            row['role_id'],
        )
    ),
)


# Blacklisted channel settings
blacklisted_channel_settings = menus.Option(
    display="Blacklisted channel settings",
    callback=menus.MenuIterable(
        select_sql="""
            SELECT * FROM channel_list
            WHERE guild_id=$1
            AND key='BlacklistedChannel'""",
        select_sql_args=lambda ctx: (
            ctx.guild.id,
        ),
        insert_sql="""
            INSERT INTO channel_list (guild_id, channel_id, key)
            VALUES ($1, $2, 'BlacklistedChannel')""",
        insert_sql_args=lambda ctx, data: (
            ctx.guild.id,
            data[0].id,
        ),
        delete_sql="""
            DELETE FROM channel_list
            WHERE guild_id=$1
            AND channel_id=$2
            AND key='BlacklistedChannel'""",
        delete_sql_args=lambda ctx, row: (
            ctx.guild.id,
            row['channel_id'],
        ),
        converters=[
            menus.Converter(
                prompt="What channel would you like to blacklist users getting points in?",
                converter=discord.TextChannel,
            ),
        ],
        row_text_display=lambda ctx, row: ctx.get_mentionable_channel(row['channel_id']).mention,
        row_component_display=lambda ctx, row: (
            ctx.get_mentionable_channel(row['channel_id']).name,
            str(uuid.uuid4()),
        ),
        cache_callback=menus.MenuCallbacks.set_iterable_list_cache(
            menus.DataLocation.GUILD,
            "blacklisted_channels",
        ),
        cache_delete_callback=menus.MenuCallbacks.delete_iterable_list_cache(
            menus.DataLocation.GUILD,
            "blacklisted_channels",
        ),
        cache_delete_args=lambda row: (
            row['channel_id'],
        ),
    ),
)


# Menu for blacklisted roles (message points)
blacklisted_role_messages = menus.Option(
    display="Blacklisted role settings (text points)",
    callback=menus.MenuIterable(
        select_sql="""
            SELECT * FROM role_list
            WHERE guild_id=$1
            AND key='BlacklistedRoles'""",
        select_sql_args=lambda ctx: (
            ctx.guild.id,
        ),
        insert_sql="""
            INSERT INTO role_list (guild_id, role_id, key)
            VALUES ($1, $2, 'BlacklistedRoles')""",
        insert_sql_args=lambda ctx, data: (
            ctx.guild.id,
            data[0].id,
        ),
        delete_sql="""
            DELETE FROM role_list
            WHERE guild_id=$1
            AND role_id=$2
            AND key='BlacklistedRoles'""",
        delete_sql_args=lambda ctx, row: (
            ctx.guild.id,
            row['role_id'],
        ),
        converters=[
            menus.Converter(
                prompt="What role would you like to blacklist users getting points with?",
                converter=discord.Role,
            ),
        ],
        row_text_display=lambda ctx, row: ctx.get_mentionable_role(row['role_id']).mention,
        row_component_display=lambda ctx, row: (
            ctx.get_mentionable_role(row['role_id']).name,
            row['role_id'],
        ),
        cache_callback=menus.MenuCallbacks.set_iterable_list_cache(
            menus.DataLocation.GUILD,
            "blacklisted_text_roles",
        ),
        cache_delete_callback=menus.MenuCallbacks.delete_iterable_list_cache(
            menus.DataLocation.GUILD,
            "blacklisted_text_roles",
        ),
        cache_delete_args=lambda row: (
            row['role_id'],
        ),
    ),
)


# Blacklisted role settings (VC points)
blacklisted_role_voice = menus.Option(
    display="Blacklisted role settings (VC points)",
    callback=menus.MenuIterable(
        select_sql="""
            SELECT * FROM role_list
            WHERE guild_id=$1
            AND key='BlacklistedVCRoles'""",
        select_sql_args=lambda ctx: (
            ctx.guild.id,
        ),
        insert_sql="""
            INSERT INTO role_list (guild_id, role_id, key)
            VALUES ($1, $2, 'BlacklistedVCRoles')""",
        insert_sql_args=lambda ctx, data: (
            ctx.guild.id,
            data[0].id,
        ),
        delete_sql="""
            DELETE FROM role_list
            WHERE guild_id=$1
            AND role_id=$2
            AND key='BlacklistedVCRoles'""",
        delete_sql_args=lambda ctx, row: (
            ctx.guild.id,
            row['role_id'],
        ),
        converters=[
            menus.Converter(
                prompt="What role would you like to blacklist users getting VC points with?",
                converter=discord.Role,
            ),
        ],
        row_text_display=lambda ctx, row: ctx.get_mentionable_role(row['role_id']).mention,
        row_component_display=lambda ctx, row: (
            ctx.get_mentionable_role(row['role_id']).name,
            row['role_id'],
        ),
        cache_callback=menus.MenuCallbacks.set_iterable_list_cache(
            menus.DataLocation.GUILD,
            "blacklisted_vc_roles",
        ),
        cache_delete_callback=menus.MenuCallbacks.delete_iterable_list_cache(
            menus.DataLocation.GUILD,
            "blacklisted_vc_roles",
        ),
        cache_delete_args=lambda row: (
            row['role_id'],
        ),
    ),
)


settings_menu = vbu.menus.Menu(
    remove_old_roles,
    role_interval_time,
    role_gain_settings,
    blacklisted_channel_settings,
    blacklisted_role_messages,
    blacklisted_role_voice,
)


def setup(bot: vbu.Bot):
    x = settings_menu.create_cog(bot)
    bot.add_cog(x)


def teardown(bot: vbu.Bot):
    bot.remove_cog("Bot Settings")
