import collections

import discord
from discord.ext import commands, tasks

from cogs import utils


class RoleHandler(utils.Cog):

    def __init__(self, bot:utils.Bot):
        super().__init__(bot)
        self.role_handles = collections.defaultdict(lambda: None)
        self.static_role_handles = collections.defaultdict(lambda: None)
        self.user_role_looper.start()

    def cog_unload(self):
        self.user_role_looper.cancel()

    @commands.command(aliases=['adddrole', 'adrole'], cls=utils.Command)
    @commands.has_permissions(manage_roles=True)
    @commands.bot_has_permissions(send_messages=True)
    @commands.guild_only()
    async def adddynamicrole(self, ctx:utils.Context, threshold:int, *, role:discord.Role):
        """Adds a role that is given when a threshold is reached"""

        async with self.bot.database() as db:
            await db(
                """INSERT INTO role_gain (guild_id, role_id, threshold, period, duration) VALUES ($1, $2, $3, 'days', 7)
                ON CONFLICT (role_id) DO UPDATE SET threshold=excluded.threshold""",
                ctx.guild.id, role.id, threshold
            )
        current = self.role_handles[ctx.guild.id]
        if current is None:
            current = list()
        current.append({
            'role_id': role.id,
            'threshold': threshold,
        })
        self.role_handles[ctx.guild.id] = current
        await ctx.send(f"Now added - at an average of {threshold} points every 7 days, users will receive the **{role.name}** role.")
        self.logger.info(f"Added dynamic role {role.id} to guild {ctx.guild.id} at threshold {threshold}")

    @commands.command(aliases=['addsrole', 'asrole'], cls=utils.Command)
    @commands.has_permissions(manage_roles=True)
    @commands.bot_has_permissions(send_messages=True)
    @commands.guild_only()
    async def addstaticrole(self, ctx:utils.Context, threshold:int, *, role:discord.Role):
        """Adds a role when a user reaches a certain level"""

        async with self.bot.database() as db:
            await db(
                """INSERT INTO static_role_gain (guild_id, role_id, threshold) VALUES ($1, $2, $3)
                ON CONFLICT (role_id) DO UPDATE SET threshold=excluded.threshold""",
                ctx.guild.id, role.id, threshold
            )
        await ctx.send(f"Now added - {threshold} messages sent, users will receive the **{role.name}** role.")
        self.logger.info(f"Added static role {role.id} to guild {ctx.guild.id} at threshold {threshold}")

    @commands.command(aliases=['removedrole', 'rdrole'], cls=utils.Command)
    @commands.has_permissions(manage_roles=True)
    @commands.bot_has_permissions(send_messages=True)
    @commands.guild_only()
    async def removedynamicrole(self, ctx:utils.Context, *, role:discord.Role):
        """Removes a role that is given"""

        async with self.bot.database() as db:
            await db("DELETE FROM role_gain WHERE role_id=$1", role.id)
        current = self.role_handles[ctx.guild.id]
        if current is not None:
            current = [i for i in current if i['role_id'] != role.id]
            self.role_handles[ctx.guild.id] = current
        await ctx.send(f"Now removed users receiving the **{role.name}** role.")
        self.logger.info(f"Removed dynamic role {role.id} to guild {ctx.guild.id}")

    @commands.command(aliases=['removesrole', 'rsrole'], cls=utils.Command)
    @commands.has_permissions(manage_roles=True)
    @commands.bot_has_permissions(send_messages=True)
    @commands.guild_only()
    async def removestaticrole(self, ctx:utils.Context, *, role:discord.Role):
        """Removes a level role"""

        async with self.bot.database() as db:
            await db(
                "DELETE FROM static_role_gain WHERE role_id=$1", role.id
            )
        await ctx.send(f"Now removed users receiving the **{role.name}** role.")
        self.logger.info(f"Removed static role {role.id} to guild {ctx.guild.id}")

    @tasks.loop(hours=1)
    async def user_role_looper(self):
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

        # Grab data
        current = self.role_handles[user.guild.id]
        if current is None:
            async with self.bot.database() as db:
                roles = await db("SELECT * FROM role_gain WHERE guild_id=$1", user.guild.id)
            current = list()
            for i in roles:
                current.append(dict(i))
            self.role_handles[user.guild.id] = current

        # Work out an average for the time
        text_points = utils.CachedMessage.get_messages_between(user.id, user.guild.id, before={'days': 0}, after={'days': 7})
        vc_points = utils.CachedVCMinute.get_minutes_between(user.id, user.guild.id, before={'days': 0}, after={'days': 7})
        points_in_week = len(text_points) + (len(vc_points) // 5)  # Add how many points they got in that week

        # Run for each role
        for row in current:

            # Shorten variable names
            role_id = row['role_id']
            threshold = row['threshold']
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

            # TODO remove old roles??

            # Are they over the threshold? - role handle
            if points_in_week >= threshold and role_id not in user._roles:
                try:
                    await user.add_roles(role)
                    self.logger.info(f"Added role with ID {role.id} to user {user.id} in guild {user.guild.id}")
                except Exception as e:
                    self.logger.info(f"Can't manage {role_id} role for user {user.id} in guild {user.guild.id} - {e}")
            elif points_in_week < threshold and role_id in user._roles:
                try:
                    await user.remove_roles(role)
                    self.logger.info(f"Removed role with ID {role.id} from user {user.id} in guild {user.guild.id}")
                except Exception as e:
                    self.logger.info(f"Can't manage {role_id} role for user {user.id} in guild {user.guild.id} - {e}")

    @utils.Cog.listener("on_user_points_receive")
    async def static_user_role_handler(self, user:discord.Member, channel:discord.TextChannel=None):
        """Looks for when a user passes the threshold of points and then handles their roles accordingly"""

        # Grab static data
        current_static = self.static_role_handles[user.guild.id]
        if current_static is None:
            async with self.bot.database() as db:
                static_roles = await db("SELECT * FROM static_role_gain WHERE guild_id=$1", user.guild.id)
            current_static = list()
            for i in static_roles:
                current_static.append(dict(i))
            self.static_role_handles[user.guild.id] = current_static

        # Make sure there are roles to handle
        if not current_static:
            return

        # Get the max role
        user_exp = self.bot.message_count.get((user.id, user.guild.id), 0) + (self.bot.minute_count.get((user.id, user.guild.id), 0) // 5)
        max_role = max([i for i in current_static if i['threshold'] <= user_exp], key=lambda i: i['threshold'], default=None)

        # Decide whether or not to remove old roles
        remove_old_roles = self.bot.guild_settings[user.guild.id]['remove_old_roles']

        # Run for each static role
        for row in current_static:

            # Shorten variable names
            role_id = row['role_id']
            threshold = row['threshold']
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

            # Do we wanna remove old roles? - role handle
            if user_exp > threshold and remove_old_roles and max_role and max_role['role_id'] != role.id:
                try:
                    if role in user.roles:
                        await user.remove_roles(role)
                        self.logger.info(f"Removed role {role_id} from user {user.id}")
                except Exception as e:
                    self.logger.info(f"Can't manage {role_id} role for user {user.id} in guild {user.guild.id} - {e}")
                continue

            # Are they over the exp_count threshold? - role handle
            if user_exp >= threshold and role_id not in user._roles:
                try:
                    dispatch_role_update = False
                    if role not in user.roles:
                        dispatch_role_update = True
                    await user.add_roles(role)
                    if dispatch_role_update:
                        self.bot.dispatch("user_static_new_role", user, role, channel)
                        self.logger.info(f"Added role {role_id} to user {user.id}")
                except Exception as e:
                    self.logger.info(f"Can't manage {role_id} role for user {user.id} in guild {user.guild.id} - {e}")

    @utils.Cog.listener("on_user_static_level_up")
    async def user_level_up_message_poster(self, user:discord.Member, channel:discord.TextChannel, new_level:int):
        """Posts in the chat when the user levels up"""

        # TODO check the guild settings to see if level up messages should be posted

        if user.bot:
            return
        if channel is None:
            return
        await channel.send(f"Well done {user.mention}, you're now **level {new_level}**!")
        self.logger.info(f"Sent level up message to {channel.guild.id}/{channel.id} for {user.id} at level {new_level}")

    @utils.Cog.listener("on_user_static_new_role")
    async def user_role_level_up_poster(self, user:discord.Member, role:discord.Role, channel:discord.TextChannel):
        """Posts in the chat when the user levels up"""

        # TODO check the guild settings to see if level up messages should be posted

        if user.bot:
            return
        if channel is None:
            return
        await channel.send(f"Well done {user.mention}, you've received the **{role.name}** role!")
        self.logger.info(f"Sent role up message to {channel.guild.id}/{channel.id} for {user.id} at role {role.id}")


def setup(bot:utils.Bot):
    x = RoleHandler(bot)
    bot.add_cog(x)
