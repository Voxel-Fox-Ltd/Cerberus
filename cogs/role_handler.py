import asyncio

import discord
from discord.ext import tasks
import voxelbotutils as utils


class RoleHandler(utils.Cog):

    def __init__(self, bot:utils.Bot):
        super().__init__(bot)
        self.user_role_looper.start()

    def cog_unload(self):
        self.user_role_looper.cancel()

    async def cache_setup(self, db):
        """
        Set up the roles and blacklisted items.
        """

        # Get role settings
        data = await self.bot._get_list_table_data(db, "role_list", "RoleGain")
        for row in data:
            self.bot.guild_settings[row['guild_id']].setdefault('role_gain', dict())[int(row['role_id'])] = int(row['value'])

        # Get blacklisted channel settings
        data = await self.bot._get_list_table_data(db, "channel_list", "BlacklistedChannel")
        for row in data:
            self.bot.guild_settings[row['guild_id']].setdefault('blacklisted_channels', list()).append(int(row['channel_id']))

        # Get blacklisted role settings
        data = await self.bot._get_list_table_data(db, "role_list", "BlacklistedRoles")
        for row in data:
            self.bot.guild_settings[row['guild_id']].setdefault('blacklisted_text_roles', list()).append(int(row['role_id']))

        # Get blacklisted role settings
        data = await self.bot._get_list_table_data(db, "role_list", "BlacklistedVCRoles")
        for row in data:
            self.bot.guild_settings[row['guild_id']].setdefault('blacklisted_vc_roles', list()).append(int(row['role_id']))

    @tasks.loop(hours=1)
    async def user_role_looper(self):
        """
        Loop every hour to remove roles from everyone who might have talked.
        """

        # Set up an inner method so we can try and do all of this at once
        async def inner_method(guild, db):
            bot_user = guild.get_member(self.bot.user.id) or await self.bot.fetch_member(self.bot.user.id)
            if not bot_user.guild_permissions.manage_roles:
                return
            for member in guild.members:
                if member.bot:
                    return
                await self.user_role_handler(member, db)

        # Ping every guild member
        self.logger.info("Pinging every guild member with an update")
        tasks = []
        async with self.bot.database() as db:
            for guild in self.bot.guilds:
                tasks.append(inner_method(guild, db))
            await asyncio.gather(tasks)
        self.logger.info("Done pinging every guild member")

    @user_role_looper.before_loop
    async def before_user_role_looper(self):
        await self.bot.wait_until_ready()

    @utils.Cog.listener("on_user_points_receive")
    async def user_role_handler(self, user:discord.Member, only_check_for_descending:bool=False, db:utils.DatabaseConnection=None):
        """
        Looks for when a user passes the threshold of points and then handles their roles accordingly.
        """

        # Don't add roles to bots
        if user.bot:
            return

        # See if we should care about the guild at all
        if user.guild.me.guild_permissions.manage_roles is False:
            return

        # Grab data
        role_data_dict = self.bot.guild_settings[user.guild.id].setdefault('role_gain', dict())
        remove_old_roles = self.bot.guild_settings[user.guild.id]['remove_old_roles']
        role_data = sorted([(role_id, threshold) for role_id, threshold in role_data_dict.items()], key=lambda x: x[1], reverse=True)

        # See if they even have any roles worth worrying about
        if only_check_for_descending and not any([i for i in user._roles if i in role_data_dict.keys()]):
            return

        # Okay cool now it's time to actually look at their roles
        self.logger.info(f"Pinging attempted role updates to user {user.id} in guild {user.guild.id}")

        # Grab data from the db
        close_db = False
        if db is None:
            db = await self.bot.database.get_connection()
            close_db = True
        message_rows = await db(
            """SELECT user_id, COUNT(timestamp) FROM user_messages WHERE guild_id=$1 AND user_id=$2
            AND timestamp > TIMEZONE('UTC', NOW()) - MAKE_INTERVAL(days => $3) GROUP BY user_id""",
            user.guild.id, user.id, self.bot.guild_settings[user.guild.id]['activity_window_days'],
        )
        vc_rows = await db(
            """SELECT user_id, COUNT(timestamp) FROM user_vc_activity WHERE guild_id=$1 AND user_id=$2
            AND timestamp > TIMEZONE('UTC', NOW()) - MAKE_INTERVAL(days => $3) GROUP BY user_id""",
            user.guild.id, user.id, self.bot.guild_settings[user.guild.id]['activity_window_days'],
        )
        mc_rows = await db(
            """SELECT user_id, COUNT(timestamp) FROM minecraft_server_activity WHERE guild_id=$1 AND user_id=$2
            AND timestamp > TIMEZONE('UTC', NOW()) - MAKE_INTERVAL(days => $3) GROUP BY user_id""",
            user.guild.id, user.id, self.bot.guild_settings[user.guild.id]['activity_window_days'],
        )
        if close_db:
            await db.disconnect()

        # Work out the user points
        try:
            text_points = message_rows[0]['count']
        except IndexError:
            text_points = 0
        try:
            vc_points = vc_rows[0]['count']
        except IndexError:
            vc_points = 0
        try:
            mc_points = mc_rows[0]['count']
        except IndexError:
            mc_points = 0
        points_in_week = text_points + (vc_points // 5) + (mc_points // 5)  # Add how many points they got in that week

        # Run for each role
        added_top_role = False
        for index, (role_id, threshold) in enumerate(role_data):

            # Shorten variable names
            role = user.guild.get_role(role_id)
            if role is None:
                continue

            # Check if we can manage roles
            if not user.guild.me.guild_permissions.manage_roles:
                self.logger.info(f"Can't manage {role_id} role for user {user.id} in guild {user.guild.id} - no perms")
                continue
            if user.guild.me.top_role.position <= role.position:
                self.logger.info(f"Can't manage {role_id} role for user {user.id} in guild {user.guild.id} - too low")
                continue

            # Add role if they're over the threshold - check for channel make sure users are only GIVEN roles if they actually sent a message
            # if points_in_week >= threshold and channel is not None:
            if points_in_week >= threshold:
                if added_top_role is False or remove_old_roles is False:
                    if role_id not in user._roles:
                        try:
                            await user.add_roles(role)
                            self.logger.info(f"Added role with ID {role.id} to user {user.id} in guild {user.guild.id}")
                        except Exception as e:
                            self.logger.info(f"Can't manage {role_id} role for user {user.id} in guild {user.guild.id} - {e}")
                    added_top_role = True
                elif remove_old_roles is True:
                    if role_id in user._roles:
                        try:
                            await user.remove_roles(role)
                            self.logger.info(f"Removed role with ID {role.id} from user {user.id} in guild {user.guild.id}")
                            added_top_role = True
                        except Exception as e:
                            self.logger.info(f"Can't manage {role_id} role for user {user.id} in guild {user.guild.id} - {e}")

            # Remove role if they're under the threshold - no channel check means that too-high roles will always be removed
            elif points_in_week < threshold and role_id in user._roles:
                try:
                    await user.remove_roles(role)
                    self.logger.info(f"Removed role with ID {role.id} from user {user.id} in guild {user.guild.id}")
                except Exception as e:
                    self.logger.info(f"Can't manage {role_id} role for user {user.id} in guild {user.guild.id} - {e}")


def setup(bot:utils.Bot):
    x = RoleHandler(bot)
    bot.add_cog(x)
