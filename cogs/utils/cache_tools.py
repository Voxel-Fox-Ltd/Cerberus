from __future__ import annotations

from datetime import datetime as dt, timedelta
from enum import Enum, auto
from dataclasses import dataclass
import collections
from typing import AsyncGenerator, ClassVar, Iterable, Optional, Union, cast


__all__ = (
    "PointSource",
    "CachedPoint",
    "PointHolder",
)


class PointSource(Enum):
    """
    Enum for the source of a point.
    """

    message = auto()
    voice = auto()
    minecraft = auto()


@dataclass(slots=True)
class CachedPoint:
    """
    A class to hold a cached point.
    """

    source: PointSource
    timestamp: dt
    user_id: Optional[int] = None
    guild_id: Optional[int] = None

    @property
    def is_old(self) -> bool:
        """
        Check if the point is old.
        """

        return self.timestamp < dt.utcnow() - timedelta(days=31)


class PointHolder:
    """
    Holds recent user points.

    Raw points are kept for exact lookups/debugging.
    Hourly/daily/monthly counters are kept for fast graphs.
    """

    # {user_id: {guild_id: [points]}}
    all_points: ClassVar[dict[int, dict[int, list[CachedPoint]]]]
    all_points = collections.defaultdict(
        lambda: collections.defaultdict(list),
    )

    # {guild_id: {user_id: {bucket: {source: points}}}}
    hourly_points: dict[int, dict[int, dict[dt, collections.Counter[PointSource]]]]
    hourly_points = collections.defaultdict(
        lambda: collections.defaultdict(
            lambda: collections.defaultdict(collections.Counter)
        )
    )
    daily_points: dict[int, dict[int, dict[dt, collections.Counter[PointSource]]]]
    daily_points = collections.defaultdict(
        lambda: collections.defaultdict(
            lambda: collections.defaultdict(collections.Counter)
        )
    )
    monthly_points: dict[int, dict[int, dict[dt, collections.Counter[PointSource]]]]
    monthly_points = collections.defaultdict(
        lambda: collections.defaultdict(
            lambda: collections.defaultdict(collections.Counter)
        )
    )

    @staticmethod
    def _hour_bucket(timestamp: dt) -> dt:
        return timestamp.replace(minute=0, second=0, microsecond=0)

    @staticmethod
    def _day_bucket(timestamp: dt) -> dt:
        return timestamp.replace(hour=0, minute=0, second=0, microsecond=0)

    @staticmethod
    def _month_bucket(timestamp: dt) -> dt:
        return timestamp.replace(day=1, hour=0, minute=0, second=0, microsecond=0)

    @staticmethod
    def _point_value(source: PointSource) -> float:
        match source:
            case PointSource.message:
                return 1.0
            case PointSource.voice:
                return 0.2
            case PointSource.minecraft:
                return 0.2

    @classmethod
    def add_point(
            cls,
            user_id: int,
            guild_id: int,
            source: PointSource,
            timestamp: Optional[dt] = None) -> None:
        """
        Add a point to the cache.
        """

        timestamp = timestamp or dt.utcnow()
        point = CachedPoint(
            source=source,
            timestamp=timestamp,
            user_id=user_id,
            guild_id=guild_id,
        )
        cls.all_points[user_id][guild_id].append(point)

        # Add to the cache buckets
        value = cls._point_value(source)
        cls.hourly_points[guild_id][user_id][cls._hour_bucket(timestamp)][source] += value  # pyright: ignore
        cls.daily_points[guild_id][user_id][cls._day_bucket(timestamp)][source] += value  # pyright: ignore
        cls.monthly_points[guild_id][user_id][cls._month_bucket(timestamp)][source] += value  # pyright: ignore

    @classmethod
    def get_points(
            cls,
            user_id: int,
            guild_id: int) -> Iterable[CachedPoint]:
        """
        Get all raw points for a user in a guild.
        """

        return cls.all_points[user_id][guild_id]

    @classmethod
    async def get_points_between_datetime(
            cls,
            user_id: int,
            guild_id: int,
            *,
            after: dt,
            before: dt) -> AsyncGenerator[CachedPoint, None]:
        """
        Get raw points for a user in a guild between two datetimes.
        """

        for point in cls.all_points[user_id][guild_id]:
            if after <= point.timestamp <= before:
                yield point

    @classmethod
    def get_points_above_age(
            cls,
            user_id: int,
            guild_id: int,
            **age) -> list[CachedPoint]:
        """
        Get raw points for a user in a guild above a certain age.
        """

        cutoff = dt.utcnow() - timedelta(**age)

        return [
            point
            for point in cls.all_points[user_id][guild_id]
            if point.timestamp > cutoff
        ]

    @classmethod
    async def get_guild_points_above_age(
            cls,
            guild_id: int,
            **age) -> dict[int, dict[str, float]]:
        """
        Get raw points in a guild above a certain age.
        """

        cutoff = dt.utcnow() - timedelta(**age)

        people_dict = collections.defaultdict({
            PointSource.message: 0.0,
            PointSource.voice: 0.0,
            PointSource.minecraft: 0.0,
        }.copy)
        for user_id, user_dict in cls.hourly_points[guild_id].items():
            for timestamp, source_counter in user_dict.items():
                if timestamp < cutoff:
                    continue
                current = people_dict[user_id]
                for source, points in source_counter.items():
                    current[source] += points
                people_dict[user_id] = current

        return people_dict

    @classmethod
    def get_point_total_above_age(
            cls,
            user_id: int,
            guild_id: int,
            **age) -> float:

        cutoff = dt.utcnow() - timedelta(**age)

        totals = {
            PointSource.message: 0.0,
            PointSource.voice: 0.0,
            PointSource.minecraft: 0.0,
        }

        bucketed_points = cls.hourly_points[guild_id][user_id]

        for bucket_timestamp, source_counter in bucketed_points.items():
            if bucket_timestamp < cutoff:
                continue

            for source, points in source_counter.items():
                totals[source] += points

        return sum([cls._point_value(source) * count for source, count in totals.items()])

    @classmethod
    def get_bucketed_points(
            cls,
            user_id: int,
            guild_id: int,
            *,
            bucket: str = "hour") -> dict[dt, collections.Counter[PointSource]]:
        """
        Get pre-counted bucket data for graphing.

        bucket can be:
        - "hour"
        - "day"
        - "month"
        """

        match bucket:
            case "hour":
                return cls.hourly_points[guild_id][user_id]
            case "day":
                return cls.daily_points[guild_id][user_id]
            case "month":
                return cls.monthly_points[guild_id][user_id]
            case _:
                raise ValueError(f"Unknown bucket type: {bucket!r}")

    @classmethod
    def get_bucket_total(
            cls,
            user_id: int,
            guild_id: int,
            timestamp: dt,
            *,
            bucket: str = "hour") -> float:
        """
        Get total points for a specific bucket.
        """

        buckets = cls.get_bucketed_points(
            user_id,
            guild_id,
            bucket=bucket,
        )

        match bucket:
            case "hour":
                key = cls._hour_bucket(timestamp)
            case "day":
                key = cls._day_bucket(timestamp)
            case "month":
                key = cls._month_bucket(timestamp)
            case _:
                raise ValueError(f"Unknown bucket type: {bucket!r}")

        return sum(buckets[key].values())

    @classmethod
    def total_points(
            cls,
            data: Union[
                dict[PointSource, float],
                dict[dt, dict[PointSource, float]],
                collections.Counter[PointSource]]) -> float:
        """
        Total points for a dict of PointSource to count.
        """

        if isinstance(data, collections.Counter):
            return sum(cls._point_value(source) * count for source, count in data.items())
        elif isinstance(data, dict):
            if all(isinstance(value, dict) for value in data.values()):
                data = cast(dict[dt, dict[PointSource, float]], data)
                return sum(
                    cls.total_points(source_counter)
                    for source_counter in data.values()
                )
            else:
                data = cast(dict[PointSource, float], data)
                return sum(cls._point_value(source) * count for source, count in data.items())
