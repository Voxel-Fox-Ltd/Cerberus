import collections

import discord
from discord.ext import commands

from cogs import utils


class RoleHandler(utils.Cog):

    def __init__(self, bot:utils.CustomBot):
        super().__init__(bot)
        self.role_handles = collections.defaultdict(lambda: None)

    @commands.command()
    @commands.guild_only()
    async def addrole(self, ctx:utils.Context, role:discord.Role, threshold:int, duration:utils.converters.DurationConverter):
        """Adds a role that is given when a threshold is reached"""

        async with self.bot.database() as db:
            await db(
                "INSERT INTO role_gain (guild_id, role_id, threshold, period, duration) VALUES ($1, $2, $3, $4, $5)",
                ctx.guild.id, role.id, threshold, duration.period, duration.duration,
            )
        current = self.role_handles[ctx.guild.id]
        if current is None:
            current = list()
        current.append({
            'role_id': role.id,
            'period': duration.period,
            'duration': duration.duration,
            'threshold': threshold,
        })
        self.role_handles[ctx.guild.id] = current
        await ctx.send(f"Now added - at an average of {threshold} points every {duration.duration} {duration.period}, users will receive the **{role.name}** role.")

    @commands.command()
    @commands.guild_only()
    async def removerole(self, ctx:utils.Context, role:discord.Role):
        """Removes a role that is given"""

        async with self.bot.database() as db:
            await db("DELETE FROM role_gain WHERE role_id=$1", role.id)
        current = self.role_handles[ctx.guild.id]
        if current is not None:
            current = [i for i in current if i['role_id'] != role.id]
            self.role_handles[ctx.guild.id] = current
        await ctx.send(f"Now removed users receiving the **{role.name}** role.")

    @utils.Cog.listener("on_user_points_receive")
    async def user_role_handler(self, user:discord.Member, message:utils.CachedMessage):
        """Looks for when a user passes the threshold of points and then handles their roles accordingly"""

        # TODO make this also run daily so people aren't stuck with the role forever

        # Grab data
        current = self.role_handles[user.guild.id]
        if current is None:
            async with self.bot.database() as db:
                roles = await db("SELECT * FROM role_gain WHERE guild_id=$1", user.guild.id)
            current = list()
            for i in roles:
                current.append(dict(i))
            self.role_handles[user.guild.id] = current

        # Run for each role
        for row in current:
            # Shorten variable names
            role_id = row['role_id']
            period = row['period']
            duration = row['duration']
            threshold = row['threshold']

            # Work out an average for the time
            working = []
            for i in range(duration, 0, -1):
                after = {period: duration - i + 1}
                before = {period: duration - i}
                points = utils.CachedMessage.get_messages_between(user.id, user.guild.id, before=before, after=after)
                working.append(len(points))

            # Are they over the threshold? - role handle
            average = sum(working) / len(working)
            if average >= threshold and role_id not in user._roles:
                role = user.guild.get_role(role_id)
                self.log_handler.info(f"Adding role with ID {role.id} to user {user.id}")
                await user.add_roles(role)
            elif average < threshold and role_id in user._roles:
                role = user.guild.get_role(role_id)
                self.log_handler.info(f"Removing role with ID {role.id} from user {user.id}")
                await user.remove_roles(role)


def setup(bot:utils.CustomBot):
    x = RoleHandler(bot)
    bot.add_cog(x)
