import discord
from discord.ext import tasks

from cogs import utils


class RoleHandler(utils.Cog):

    def __init__(self, bot:utils.Bot):
        super().__init__(bot)
        self.user_role_looper.start()

    def cog_unload(self):
        self.user_role_looper.cancel()

    @tasks.loop(hours=1)
    async def user_role_looper(self):
        """Loop every hour to remove roles from everyone who might have talked"""

        self.logger.info("Pinging every guild member with an update")
        for guild in self.bot.guilds:
            for member in guild.members:
                if member.bot:
                    continue
                self.bot.dispatch('user_points_receive', member)

    @user_role_looper.before_loop
    async def before_user_role_looper(self):
        await self.bot.wait_until_ready()

    @utils.Cog.listener("on_user_points_receive")
    async def user_role_handler(self, user:discord.Member, channel:discord.TextChannel=None):
        """Looks for when a user passes the threshold of points and then handles their roles accordingly"""

        # Don't add roles to bots
        if user.bot:
            return

        # Some lines for when testing
        # if user.id not in self.bot.owner_ids:
        #     return
        self.logger.info(f"Pinging attempted role updates to user {user.id} in guild {user.guild.id}")

        # Grab data
        role_data_dict = self.bot.guild_settings[user.guild.id]['role_gain']
        remove_old_roles = self.bot.guild_settings[user.guild.id]['remove_old_roles']
        role_data = sorted([(role_id, threshold) for role_id, threshold in role_data_dict.items()], key=lambda x: x[1], reverse=True)

        # Work out an average for the time
        text_points = utils.CachedMessage.get_messages_between(user.id, user.guild.id, before={'days': 0}, after={'days': 7})
        vc_points = utils.CachedVCMinute.get_minutes_between(user.id, user.guild.id, before={'days': 0}, after={'days': 7})
        points_in_week = len(text_points) + (len(vc_points) // 5)  # Add how many points they got in that week

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
            if points_in_week >= threshold and channel is not None:
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
