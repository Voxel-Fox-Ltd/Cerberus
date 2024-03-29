import asyncio
from typing import Optional, Tuple, cast

import discord
from discord.ext import tasks, vbu

from cogs import utils


class RoleHandler(vbu.Cog[utils.types.Bot]):

    def __init__(self, bot: utils.types.Bot):
        super().__init__(bot)
        # self.user_role_looper.start()

    def cog_unload(self):
        self.user_role_looper.cancel()

    async def cache_setup(self, db: vbu.Database):
        """
        Set up the roles and blacklisted items.
        """

        # Get role settings
        data = await self.bot._get_list_table_data(
            db,
            "role_list",
            "RoleGain",
        )
        async for row in utils.alist(data):
            guild_id: int = row['guild_id']
            role_id: int = int(row['role_id'])
            value: int = int(row['value'])
            (
                self.bot.guild_settings[guild_id]
                .setdefault('role_gain', dict())[role_id]
            ) = value

        # Get blacklisted channel settings
        data = await self.bot._get_list_table_data(
            db,
            "channel_list",
            "BlacklistedChannel",
        )
        async for row in utils.alist(data):
            guild_id: int = row['guild_id']
            channel_id: int = int(row['channel_id'])
            (
                self.bot.guild_settings[guild_id]
                .setdefault('blacklisted_channels', list())
                .append(channel_id)
            )

        # Get blacklisted role settings
        data = await self.bot._get_list_table_data(
            db,
            "role_list",
            "BlacklistedRoles",
        )
        async for row in utils.alist(data):
            guild_id: int = row['guild_id']
            role_id: int = int(row['role_id'])
            (
                self.bot.guild_settings[guild_id]
                .setdefault('blacklisted_text_roles', list())
                .append(role_id)
            )

        # Get blacklisted role settings
        data = await self.bot._get_list_table_data(
            db,
            "role_list",
            "BlacklistedVCRoles",
        )
        async for row in utils.alist(data):
            guild_id: int = row['guild_id']
            role_id: int = int(row['role_id'])
            (
                self.bot.guild_settings[guild_id]
                .setdefault('blacklisted_vc_roles', list())
                .append(role_id)
            )

        # And done
        return True

    @tasks.loop(hours=1)
    async def user_role_looper(self):
        """
        Loop every hour to remove roles from everyone who might have talked.
        """

        # Ping every guild member
        self.logger.info("Pinging every guild member with an update")

        # Open a connection we can use this whole time
        db = await self.bot.database.get_connection()

        # Get all users with an activity role for each of the guilds
        for guild in self.bot.guilds:

            # Get the settings for the guild
            role_data_dict: dict[int, int]  # roleId: threshold
            role_data_dict = (
                self.bot.guild_settings[guild.id]
                .setdefault('role_gain', dict())
            )
            all_users_with_level_roles: set[discord.Member] = set()

            # Get each level role, add all of its members
            for role_id in role_data_dict.keys():
                role: Optional[discord.Role] = guild.get_role(role_id)
                if role is None:
                    continue
                all_users_with_level_roles.update(role.members)

            # For each user in that role, ping all of the members with an update
            for user in all_users_with_level_roles:
                await self.user_role_handler(user, db)

        # And we should be done
        await db.disconnect()
        self.logger.info("Done pinging every guild member")

    @user_role_looper.before_loop
    async def before_user_role_looper(self):
        await asyncio.sleep(60 * len(self.bot.shard_ids or [0]))

    @vbu.Cog.listener("on_user_points_receive")
    async def user_role_handler(
            self,
            user: discord.Member,
            db: Optional[vbu.Database] = None):
        """
        Looks for when a user passes the threshold of points and then handles
        their roles accordingly.
        """

        # Make sure the startup method has completed before continuing
        await self.bot.wait_until_ready()
        if self.bot.startup_method and not self.bot.startup_method.done():
            return

        # Don't add roles to bots
        if user.bot:
            return

        # See if we should care about the guild at all
        me = user.guild.me
        if me is None:
            self.logger.warning(
                (
                    "Bot does not have the guilds scope - "
                    "not attempting to manage roles."
                )
            )
            return
        if me.guild_permissions.manage_roles is False:
            return

        # Grab data
        role_data_dict: dict = (
            self.bot.guild_settings[user.guild.id]
            .setdefault('role_gain', dict())
        )
        remove_old_roles: bool = (
            self.bot.guild_settings[user.guild.id]
            ['remove_old_roles']
        )
        role_data: list[Tuple[int, int]]
        role_data = sorted(
            [
                (int(role_id), threshold)
                for role_id, threshold in role_data_dict.items()
            ],
            key=lambda x: x[1],
            reverse=True,
        )

        # Okay cool now it's time to actually look at their roles
        self.logger.info(
            (
                f"Pinging attempted role updates to user "
                f"{user.id} in guild {user.guild.id}"
            )
        )

        # Get the user's points
        point_rows = await utils.cache.PointHolder.get_points_above_age(
            user.id,
            user.guild.id,
            days=self.bot.guild_settings[user.guild.id]['activity_window_days'],
        )

        # Work out the user point values
        user_points = {
            "message": 0,
            "voice": 0,
            "minecraft": 0,
        }
        async for row in utils.alist(point_rows):
            user_points[row.source.name] += 1
        points_in_week = utils.get_all_points(user_points)

        # Run for each role
        added_top_role = False
        for role_id, threshold in role_data:

            # Shorten variable names
            user.guild = cast(discord.Guild, user.guild)
            role = user.guild.get_role(role_id)
            if role is None:
                self.logger.info(
                    (
                        f"Couldn't find role in guild {user.guild.id} "
                        f"with ID {role_id!r}"
                    )
                )
                continue

            # Check if we can manage roles
            if not user.guild.me.guild_permissions.manage_roles:
                self.logger.info((
                    f"Can't manage {role_id} role for user "
                    f"{user.id} in guild {user.guild.id} - no perms"
                ))
                continue
            if user.guild.me.top_role.position <= role.position:
                self.logger.info((
                    f"Can't manage {role_id} role for user "
                    f"{user.id} in guild {user.guild.id} - too low"
                ))
                continue

            # Add role if they're over the threshold -
            # check for channel make sure users are only
            # GIVEN roles if they actually sent a message
            if points_in_week >= threshold:
                if added_top_role is False or remove_old_roles is False:
                    if role_id not in user._roles:
                        try:
                            await user.add_roles(role)
                            self.logger.info(
                                (
                                    f"Added role with ID {role.id} to user "
                                    f"{user.id} in guild {user.guild.id}"
                                )
                            )
                        except Exception as e:
                            self.logger.info(
                                (
                                    f"Can't manage {role_id} role for user "
                                    f"{user.id} in guild {user.guild.id} - {e}"
                                )
                            )
                    added_top_role = True
                elif remove_old_roles is True:
                    if role_id in user._roles:
                        try:
                            await user.remove_roles(role)
                            self.logger.info(
                                (
                                    f"Removed role with ID {role.id} from "
                                    f"user {user.id} in guild {user.guild.id}"
                                )
                            )
                            added_top_role = True
                        except Exception as e:
                            self.logger.info(
                                (
                                    f"Can't manage {role_id} role for user "
                                    f"{user.id} in guild {user.guild.id} - {e}"
                                )
                            )

            # Remove role if they're under the threshold -
            # no channel check means that too-high roles
            # will always be removed
            elif points_in_week < threshold and role_id in user._roles:
                try:
                    await user.remove_roles(role)
                    self.logger.info(
                        (
                            f"Removed role with ID {role.id} from "
                            f"user {user.id} in guild {user.guild.id}"
                        )
                    )
                except Exception as e:
                    self.logger.info(
                        (
                            f"Can't manage {role_id} role for user "
                            f"{user.id} in guild {user.guild.id} - {e}"
                        )
                    )


def setup(bot: utils.types.Bot):
    x = RoleHandler(bot)
    bot.add_cog(x)
