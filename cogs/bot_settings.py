import uuid

import discord
from discord.ext import vbu


settings_menu = vbu.menus.Menu(
    vbu.menus.Option(
        display=lambda ctx: f"Remove old roles (currently {ctx.bot.guild_settings[ctx.guild.id]['remove_old_roles']})",
        component_display="Remove old roles",
        converters=[
            vbu.menus.Converter(
                prompt="Do you want to remove old roles when new ones are gained?",
                converter=lambda payload: payload.custom_id == "YES",
                timeout_message="Timed out asking for old role removal.",
                components=discord.ui.MessageComponents.boolean_buttons(),
            ),
        ],
        callback=vbu.menus.Menu.callbacks.set_table_column(vbu.menus.DataLocation.GUILD, "guild_settings", "remove_old_roles"),
        cache_callback=vbu.menus.Menu.callbacks.set_cache_from_key(vbu.menus.DataLocation.GUILD, "remove_old_roles"),
    ),
    vbu.menus.Option(
        display=lambda ctx: f"Set role interval time (currently {ctx.bot.guild_settings[ctx.guild.id]['activity_window_days']:,} days)",
        component_display="Role interval time",
        converters=[
            vbu.menus.Converter(
                prompt="How many days should activity be tracked over?",
                checks=[
                    vbu.menus.Check(
                        check=lambda message: message.content.isdigit() and int(message.content) in range(7, 31),
                        on_failure=vbu.menus.Check.failures.RETRY,
                        fail_message="You need to give a *number* between **7** and **31**.",
                    ),
                ],
                converter=int,
                timeout_message="Timed out asking for activity window days.",
            ),
        ],
        callback=vbu.menus.Menu.callbacks.set_table_column(vbu.menus.DataLocation.GUILD, "guild_settings", "activity_window_days"),
        cache_callback=vbu.menus.Menu.callbacks.set_cache_from_key(vbu.menus.DataLocation.GUILD, "activity_window_days"),
        allow_none=False,
    ),
    vbu.menus.Option(
        display="Role gain settings",
        callback=vbu.menus.MenuIterable(
            select_sql="""SELECT * FROM role_list WHERE guild_id=$1 AND key='RoleGain'""",
            select_sql_args=lambda ctx: (ctx.guild.id,),
            insert_sql="""INSERT INTO role_list (guild_id, role_id, value, key) VALUES ($1, $2, $3, 'RoleGain')""",
            insert_sql_args=lambda ctx, data: (ctx.guild.id, data[0].id, str(data[1])),
            delete_sql="""DELETE FROM role_list WHERE guild_id=$1 AND role_id=$2 AND key='RoleGain'""",
            delete_sql_args=lambda ctx, row: (ctx.guild.id, row['role_id'],),
            converters=[
                vbu.menus.Converter(
                    prompt="What role do you want to be gainable?",
                    converter=discord.Role,
                ),
                vbu.menus.Converter(
                    prompt="How many points does this role require to be gainable?",
                    converter=int,
                ),
            ],
            row_text_display=lambda ctx, row: f"{ctx.get_mentionable_role(row['role_id']).mention} - {int(row['value']):,}",
            row_component_display=lambda ctx, row: (ctx.get_mentionable_role(row['role_id']).name, row['role_id'],),
            cache_callback=vbu.menus.Menu.callbacks.set_iterable_dict_cache(vbu.menus.DataLocation.GUILD, "role_gain"),
            cache_delete_callback=vbu.menus.Menu.callbacks.delete_iterable_dict_cache(vbu.menus.DataLocation.GUILD, "role_gain"),
            cache_delete_args=lambda row: (row['role_id'],)
        ),
    ),
    vbu.menus.Option(
        display="Blacklisted channel settings",
        callback=vbu.menus.MenuIterable(
            select_sql="""SELECT * FROM channel_list WHERE guild_id=$1 AND key='BlacklistedChannel'""",
            select_sql_args=lambda ctx: (ctx.guild.id,),
            insert_sql="""INSERT INTO channel_list (guild_id, channel_id, key) VALUES ($1, $2, 'BlacklistedChannel')""",
            insert_sql_args=lambda ctx, data: (ctx.guild.id, data[0].id,),
            delete_sql="""DELETE FROM channel_list WHERE guild_id=$1 AND channel_id=$2 AND key='BlacklistedChannel'""",
            delete_sql_args=lambda ctx, row: (ctx.guild.id, row['channel_id'],),
            converters=[
                vbu.menus.Converter(
                    prompt="What channel would you like to blacklist users getting points in?",
                    converter=discord.TextChannel,
                ),
            ],
            row_text_display=lambda ctx, row: ctx.get_mentionable_channel(row['channel_id']).mention,
            row_component_display=lambda ctx, row: (ctx.get_mentionable_channel(row['channel_id']).name, uuid.uuid4()),
            cache_callback=vbu.menus.Menu.callbacks.set_iterable_list_cache(vbu.menus.DataLocation.GUILD, "blacklisted_channels"),
            cache_delete_callback=vbu.menus.Menu.callbacks.delete_iterable_list_cache(vbu.menus.DataLocation.GUILD, "blacklisted_channels"),
            cache_delete_args=lambda row: (row['channel_id'],)
        ),
    ),
    vbu.menus.Option(
        display="Blacklisted role settings (text points)",
        callback=vbu.menus.MenuIterable(
            select_sql="""SELECT * FROM role_list WHERE guild_id=$1 AND key='BlacklistedRoles'""",
            select_sql_args=lambda ctx: (ctx.guild.id,),
            insert_sql="""INSERT INTO role_list (guild_id, role_id, key) VALUES ($1, $2, 'BlacklistedRoles')""",
            insert_sql_args=lambda ctx, data: (ctx.guild.id, data[0].id),
            delete_sql="""DELETE FROM role_list WHERE guild_id=$1 AND role_id=$2 AND key='BlacklistedRoles'""",
            delete_sql_args=lambda ctx, row: (ctx.guild.id, row['role_id'],),
            converters=[
                vbu.menus.Converter(
                    prompt="What role would you like to blacklist users getting points with?",
                    converter=discord.Role,
                ),
            ],
            row_text_display=lambda ctx, row: ctx.get_mentionable_role(row['role_id']).mention,
            row_component_display=lambda ctx, row: (ctx.get_mentionable_role(row['role_id']).name, row['role_id']),
            cache_callback=vbu.menus.Menu.callbacks.set_iterable_list_cache(vbu.menus.DataLocation.GUILD, "blacklisted_text_roles"),
            cache_delete_callback=vbu.menus.Menu.callbacks.delete_iterable_list_cache(vbu.menus.DataLocation.GUILD, "blacklisted_text_roles"),
            cache_delete_args=lambda row: (row['role_id'],)
        ),
    ),
    vbu.menus.Option(
        display="Blacklisted role settings (VC points)",
        callback=vbu.menus.MenuIterable(
            select_sql="""SELECT * FROM role_list WHERE guild_id=$1 AND key='BlacklistedVCRoles'""",
            select_sql_args=lambda ctx: (ctx.guild.id,),
            insert_sql="""INSERT INTO role_list (guild_id, role_id, key) VALUES ($1, $2, 'BlacklistedVCRoles')""",
            insert_sql_args=lambda ctx, data: (ctx.guild.id, data[0].id,),
            delete_sql="""DELETE FROM role_list WHERE guild_id=$1 AND role_id=$2 AND key='BlacklistedVCRoles'""",
            delete_sql_args=lambda ctx, row: (ctx.guild.id, row['role_id'],),
            converters=[
                vbu.menus.Converter(
                    prompt="What role would you like to blacklist users getting VC points with?",
                    converter=discord.Role,
                ),
            ],
            row_text_display=lambda ctx, row: ctx.get_mentionable_role(row['role_id']).mention,
            row_component_display=lambda ctx, row: (ctx.get_mentionable_role(row['role_id']).name, row['role_id']),
            cache_callback=vbu.menus.Menu.callbacks.set_iterable_list_cache(vbu.menus.DataLocation.GUILD, "blacklisted_vc_roles"),
            cache_delete_callback=vbu.menus.Menu.callbacks.delete_iterable_list_cache(vbu.menus.DataLocation.GUILD, "blacklisted_vc_roles"),
            cache_delete_args=lambda row: (row['role_id'],)
        ),
    ),
)


def setup(bot: vbu.Bot):
    x = settings_menu.create_cog(bot)
    bot.add_cog(x)


def teardown(bot: vbu.Bot):
    bot.remove_cog("Bot Settings")
