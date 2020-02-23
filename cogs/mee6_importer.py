from discord.ext import commands

from cogs import utils


class Mee6Importer(utils.Cog):

    def __init__(self, bot:utils.Bot):
        super().__init__(bot)
        self.mee6_exp_for_level = {}

    def get_exp_for_level(self, level:int):
        """Gets the amount of exp associated with a level"""

        # https://mee6.github.io/Mee6-documentation/levelxp/
        # 5 * (lvl ^ 2) + 50 * lvl + 100 

        if level in self.mee6_exp_for_level:
            return self.mee6_exp_for_level[level]
        if level == 0:
            return 0
        exp = 5 * ((level - 1) ** 2) + 50 * (level - 1) + 100 + self.get_exp_for_level(level - 1)
        self.mee6_exp_for_level[level] = exp
        return exp

    @commands.command(cls=utils.Command, hidden=True)
    @commands.guild_only()
    async def listmee6roles(self, ctx:utils.Context):
        """Lists the roles set up with Mee6"""

        # Get data from the Mee6 API
        base = "https://mee6.xyz/api/plugins/levels/leaderboard/"
        async with self.bot.session.get(base + str(ctx.guild.id)) as r:
            data = await r.json()
        if str(r.status) == '404':
            return await ctx.send("The leaderboard page for this guild is either not public or not present - Mee6 must be on your server for this to work.")

        # Output to user
        role_rewards = sorted(data['role_rewards'], key=lambda r: r['rank'])
        lines = [f"You have {len(role_rewards)} roles set up to be given out by Mee6."]
        for role in role_rewards:
            lines.append(f"Role at level {role['rank']}: **{role['role']['name']}**")
        return await ctx.send('\n'.join(lines))

    @commands.command(cls=utils.Command)
    @commands.has_permissions(manage_guild=True)
    @commands.guild_only()
    async def copymee6roles(self, ctx:utils.Context):
        """Copies the Mee6 roles into your static role handling"""

        async with ctx.typing():

            # Get data from the Mee6 API
            base = "https://mee6.xyz/api/plugins/levels/leaderboard/"
            async with self.bot.session.get(base + str(ctx.guild.id)) as r:
                data = await r.json()
            if str(r.status) == '404':
                return await ctx.send("The leaderboard page for this guild is either not public or not present - Mee6 must be on your server for this to work.")

            # Save to db
            role_rewards = data['role_rewards']
            async with self.bot.database() as db:
                for role in role_rewards:
                    await db(
                        """INSERT INTO static_role_gain (guild_id, role_id, threshold) 
                        VALUES ($1, $2, $3) ON CONFLICT (role_id) DO NOTHING""",
                        ctx.guild.id, int(role['role']['id']), self.get_exp_for_level(role['rank'])
                    )

        # Output to user
        return await ctx.send("Your roles from Mee6 have been copied over.")

    @commands.command(cls=utils.Command)
    @commands.has_permissions(manage_guild=True)
    @commands.guild_only()
    async def copymee6exp(self, ctx:utils.Context):
        """Copies the Mee6 exp into Cerberus"""

        async with ctx.typing():

            # Get data from the Mee6 API
            base = "https://mee6.xyz/api/plugins/levels/leaderboard/"
            user_data = []
            while True:
                async with self.bot.session.get(base + str(ctx.guild.id), params={'page': i, 'limit': 1000}) as r:
                    data = await r.json()
                if str(r.status) == '404':
                    return await ctx.send("The leaderboard page for this guild is either not public or not present - Mee6 must be on your server for this to work.")
                if data['players']:
                    user_data.extend(data['players'])
                else:
                    break

            # Store in database
            async with self.bot.database() as db:
                for user in user_data:
                    self.bot.message_count[(int(user['id']), ctx.guild.id)] += user['message_count']
                    await db(
                        """INSERT INTO static_user_messages (user_id, guild_id, message_count) 
                        VALUES ($1, $2, $3) ON CONFLICT (user_id, guild_id) DO UPDATE SET message_count=$3""",
                        int(user['id']), ctx.guild.id, self.bot.message_count[(int(user['id']), ctx.guild.id)]
                    )
                    # self.bot.dispatch('user_points_receive', message.author)

        return await ctx.send(f"Copied over {len(user_data)} users' exp from Mee6.")


def setup(bot:utils.Bot):
    x = Mee6Importer(bot)
    bot.add_cog(x)
