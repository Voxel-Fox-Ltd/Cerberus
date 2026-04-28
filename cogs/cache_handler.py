import asyncio
from datetime import datetime as dt

from discord.ext import vbu

from . import utils


class CacheHandler(vbu.Cog[vbu.Bot]):

    async def cache_setup(self, db: vbu.Database):
        """
        Load pre-aggregated point buckets into memory.

        Reads from rollup tables instead of rebuilding buckets from user_points.
        """

        self.logger.info("Getting hourly point buckets from database")
        hourly_rows = await db.call(
            """
            SELECT
                guild_id,
                user_id,
                hour AS bucket,
                source,
                points
            FROM
                user_point_hourly_counts
            """,
        )
        self.logger.info(f"Got {len(hourly_rows):,} hourly buckets from database")

        self.logger.info("Adding hourly buckets to cache")
        for index, row in enumerate(hourly_rows):
            if index % 10_000 == 0:
                self.logger.info(
                    f"Added {index:,}/{len(hourly_rows):,} "
                    f"({index / len(hourly_rows) * 100:.2f}%) hourly buckets"
                )
                await asyncio.sleep(0)

            utils.cache.PointHolder.hourly_points[
                row["guild_id"]
            ][
                row["user_id"]
            ][
                row["bucket"].replace(minute=0, second=0, microsecond=0)
            ][
                utils.cache.PointSource[row["source"]]
            ] += row["points"]

        self.logger.info("Getting daily point buckets from database")
        daily_rows = await db.call(
            """
            SELECT
                guild_id,
                user_id,
                day AS bucket,
                source,
                points
            FROM
                user_point_daily_counts
            """,
        )
        self.logger.info(f"Got {len(daily_rows):,} daily buckets from database")

        self.logger.info("Adding daily buckets to cache")
        for index, row in enumerate(daily_rows):
            if index % 10_000 == 0:
                self.logger.info(
                    f"Added {index:,}/{len(daily_rows):,} "
                    f"({index / len(daily_rows) * 100:.2f}%) daily buckets"
                )
                await asyncio.sleep(0)

            bucket = row["bucket"]
            if not isinstance(bucket, dt):
                bucket = dt.combine(bucket, dt.min.time())

            utils.cache.PointHolder.daily_points[
                row["guild_id"]
            ][
                row["user_id"]
            ][
                bucket.replace(hour=0, minute=0, second=0, microsecond=0)
            ][
                utils.cache.PointSource[row["source"]]
            ] += row["points"]

        self.logger.info("Getting monthly point buckets from database")
        monthly_rows = await db.call(
            """
            SELECT
                guild_id,
                user_id,
                month AS bucket,
                source,
                points
            FROM
                user_point_monthly_counts
            """,
        )
        self.logger.info(f"Got {len(monthly_rows):,} monthly buckets from database")

        self.logger.info("Adding monthly buckets to cache")
        for index, row in enumerate(monthly_rows):
            if index % 10_000 == 0:
                self.logger.info(
                    f"Added {index:,}/{len(monthly_rows):,} "
                    f"({index / len(monthly_rows) * 100:.2f}%) monthly buckets"
                )
                await asyncio.sleep(0)

            bucket = row["bucket"]
            if not isinstance(bucket, dt):
                bucket = dt.combine(bucket, dt.min.time())

            utils.cache.PointHolder.monthly_points[
                row["guild_id"]
            ][
                row["user_id"]
            ][
                bucket.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
            ][
                utils.cache.PointSource[row["source"]]
            ] += row["points"]

        self.logger.info("Added all bucketed points to cache")
        return True


def setup(bot: vbu.Bot):
    x = CacheHandler(bot)
    bot.add_cog(x)
