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

    @commands.command(cls=utils.Command)
    @commands.has_permissions(manage_roles=True)
    @commands.guild_only()
    async def addrole(self, ctx:utils.Context, threshold:int, *, role:discord.Role):
        """Adds a role that is given when a threshold is reached"""

        async with self.bot.database() as db:
            await db(
                "INSERT INTO role_gain (guild_id, role_id, threshold, period, duration) VALUES ($1, $2, $3, 'days', 7)",
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

    @commands.command(cls=utils.Command)
    @commands.has_permissions(manage_roles=True)
    @commands.guild_only()
    async def addstaticrole(self, ctx:utils.Context, threshold:int, *, role:discord.Role):
        """Adds a role when a user reaches a certain level"""

        async with self.bot.database() as db:
            await db(
                "INSERT INTO static_role_gain (guild_id, role_id, threshold) VALUES ($1, $2, $3)",
                ctx.guild.id, role.id, threshold
            )
        await ctx.send(f"Now added - {threshold} messages sent, users will receive the **{role.name}** role.")

    @commands.command(cls=utils.Command)
    @commands.has_permissions(manage_roles=True)
    @commands.guild_only()
    async def removerole(self, ctx:utils.Context, *, role:discord.Role):
        """Removes a role that is given"""

        async with self.bot.database() as db:
            await db("DELETE FROM role_gain WHERE role_id=$1", role.id)
        current = self.role_handles[ctx.guild.id]
        if current is not None:
            current = [i for i in current if i['role_id'] != role.id]
            self.role_handles[ctx.guild.id] = current
        await ctx.send(f"Now removed users receiving the **{role.name}** role.")

    @commands.command(cls=utils.Command)
    @commands.has_permissions(manage_roles=True)
    @commands.guild_only()
    async def removestaticrole(self, ctx:utils.Context, *, role:discord.Role):
        """Removes a level role"""

        async with self.bot.database() as db:
            await db(
                "DELETE FROM static_role_gain WHERE role_id=$1", role.id
                )
        await ctx.send(f"Now removed users receiving the **{role.name}** role.")

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
    async def user_role_handler(self, user:discord.Member):
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
        points = utils.CachedMessage.get_messages_between(user.id, user.guild.id, before={'days': 0}, after={'days': 7})
        points_in_week = len(points)  # Add how many points they got in that week

        # Run for each role
        for row in current:

            # Shorten variable names
            role_id = row['role_id']
            threshold = row['threshold']

            # Are they over the threshold? - role handle
            if points_in_week >= threshold and role_id not in user._roles:
                role = user.guild.get_role(role_id)
                try:
                    await user.add_roles(role)
                    self.logger.info(f"Added role with ID {role.id} to user {user.id}")
                except Exception as e:
                    self.logger.info(f"Can't manage {role_id} role for user {user.id} in guild {user.guild.id} - {e}")
            elif points_in_week < threshold and role_id in user._roles:
                role = user.guild.get_role(role_id)
                try:
                    await user.remove_roles(role)
                    self.logger.info(f"Removed role with ID {role.id} from user {user.id}")
                except Exception as e:
                    self.logger.info(f"Can't manage {role_id} role for user {user.id} in guild {user.guild.id} - {e}")


    @utils.Cog.listener("on_user_points_receive")
    async def static_user_role_handler(self, user:discord.Member):
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
        
        # Run for each static role
        for row in current_static:
            
            # Shorten variable names
            role_id = row['role_id']
            threshold = row['threshold']

            # Are they over the message_count threshold? - role handle
            if self.bot.message_count[(user.id, user.guild.id)] >= threshold and role_id not in user._roles:
                role = user.guild.get_role(role_id)
                try:
                    await user.add_roles(role)
                    self.logger.info(f"Added static role with ID {role.id} to user {user.id}")
                except Exception as e:
                    self.logger.info(f"Can't manage {role_id} role for user {user.id} in guild {user.guild.id} - {e}")
            elif self.bot.message_count[(user.id, user.guild.id)] < threshold and role_id in user._roles:
                role = user.guild.get_role(role_id)
                try:
                    await user.remove_roles(role)
                    self.logger.info(f"Removed static role with ID {role.id} from user {user.id}")
                except Exception as e:
                    self.logger.info(f"Can't manage {role_id} role for user {user.id} in guild {user.guild.id} - {e}")



def setup(bot:utils.Bot):
    x = RoleHandler(bot)
    bot.add_cog(x)
