from discord.ext import vbu

from . import utils


class CacheHandler(vbu.Cog[vbu.Bot]):

    async def cache_setup(self, db: vbu.Database):
        """
        Get the last 31 days out of storage and put them into memory.
        Very intensive, yes, but it speeds up the graphing process.
        """

        # Get the last 31 days of points
        rows = await db.call(
            """
            SELECT
                *
            FROM
                user_points
            WHERE
                timestamp > (TIMEZONE('UTC', NOW()) - INTERVAL '31 days')
            """,
        )

        # Add them to the cache
        for row in rows:
            utils.cache.PointHolder.add_point(
                row["user_id"],
                row["guild_id"],
                utils.cache.PointSource(row["source"]),
                row["timestamp"],
            )



def setup(bot: vbu.Bot):
    x = CacheHandler(bot)
    bot.add_cog(x)
