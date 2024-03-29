import asyncio

from discord.ext import vbu

from . import utils


async def aiterator(iterable):
    for i in iterable:
        await asyncio.sleep(0)
        yield i


class CacheHandler(vbu.Cog[vbu.Bot]):

    async def cache_setup(self, db: vbu.Database):
        """
        Get the last 31 days out of storage and put them into memory.
        Very intensive, yes, but it speeds up the graphing process.
        """

        # Get the last 31 days of points
        self.logger.info("Getting all points from database")
        rows = await db.call(
            """
            SELECT
                *
            FROM
                user_points
            -- WHERE timestamp > NOW() - INTERVAL '65 days'
            """,
        )
        self.logger.info(f"Got {len(rows)} points from database")

        # Add them to the cache
        self.logger.info("Adding points to cache")
        async for index, row in aiterator(enumerate(rows)):
            if index % 10_000 == 0:
                self.logger.info(f"Added {index:,}/{len(rows):,} ({index / len(rows) * 100:.2f}%) points to cache")
            utils.cache.PointHolder.add_point(
                row["user_id"],
                row["guild_id"],
                utils.cache.PointSource[row["source"]],
                row["timestamp"],
            )
        self.logger.info("Added all points to cache")

        # And done
        return True


def setup(bot: vbu.Bot):
    x = CacheHandler(bot)
    bot.add_cog(x)
