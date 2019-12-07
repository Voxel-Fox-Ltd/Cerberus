import discord
from discord.ext import commands

from cogs import utils


class RoleHandler(utils.Cog):

    @commands.command()
    @commands.guild_only()
    async def addrole(self, ctx:utils.Context, role:discord.Role, threshold:int, duration:utils.converters.DurationConverter):
        """Adds a role that is given when a threshold is reached"""

        async with self.bot.database() as db:
            await db(
                "INSERT INTO role_gain (guild_id, role_id, threshold, period, duration) VALUES ($1, $2, $3, $4, $5)",
                ctx.guild.id, role.id, threshold, duration.period, duration.duration,
            )
        await ctx.send(f"Now added - at an average of {threshold} points every {duration.duration} {duration.period}, users will receive the **{role.name}** role.")

    @utils.Cog.listener("on_user_points_receive")
    async def user_role_handler(self, user:discord.Member, message:utils.CachedMessage):
        """Looks for when a user passes the threshold of points and then handles their roles accordingly"""

        # TODO make this also run daily so people aren't stuck with the role forever

        # Grab data
        async with self.bot.database() as db:
            roles = await db("SELECT * FROM role_gain WHERE guild_id=$1", user.guild.id)

        # Run for each role
        for row in roles:
            # Shorten variable names
            role_id = row['role_id']
            period = row['period']
            duration = row['duration']
            threshold = row['threshold']

            # Work out an average for the time
            working = []
            for i in range(duration - 1, -1, -1):
                after = {period: (2 * duration) - i}
                before = {period: duration - i}
                points = utils.CachedMessage.get_messages_between(user.id, user.guild.id, before=before, after=after)
                working.append(len(points))

            # Are they over the threshold? - role handle
            average = sum(working) / len(working)
            if average >= threshold and role_id not in user._roles:
                role = user.guild.get_role(role_id)
                await user.add_roles(role)
            elif average < threshold and role_id in user._roles:
                role = user.guild.get_role(role_id)
                await user.remove_roles(role)


def setup(bot:utils.CustomBot):
    x = RoleHandler(bot)
    bot.add_cog(x)
