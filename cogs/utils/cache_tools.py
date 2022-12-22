from datetime import datetime as dt, timedelta
from enum import Enum, auto
from dataclasses import dataclass
import collections
import functools
import asyncio
from typing import AsyncGenerator, ClassVar, Iterable, Optional

from .async_iterators import alist


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


@dataclass
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
    A singleton class to hold information on users' points.
    Limits to the last 31 days, inclusive.
    """

    all_points: ClassVar[dict[int, dict[int, list[CachedPoint]]]]
    all_points = collections.defaultdict(
        functools.partial(collections.defaultdict, list),
    )  # {user_id: {guild_id: [points]}}

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

        point = CachedPoint(
            source=source,
            timestamp=timestamp or dt.utcnow(),
            user_id=user_id,
            guild_id=guild_id,
        )
        cls.all_points[user_id][guild_id].append(point)

    @classmethod
    def get_points(
            cls,
            user_id: int,
            guild_id: int) -> Iterable[CachedPoint]:
        """
        Get all points for a user in a guild.
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
        Get all points for a user in a guild between two ages.
        """

        for point in cls.all_points[user_id][guild_id]:
            if after <= point.timestamp <= before:
                await asyncio.sleep(0)
                yield point

    @classmethod
    async def get_points_above_age(
            cls,
            user_id: int,
            guild_id: int,
            **age) -> Iterable[CachedPoint]:
        """
        Get all points for a user in a guild above a certain age.
        """

        return [
            point
            async for point in alist(cls.all_points[user_id][guild_id])
            if point.timestamp > dt.utcnow() - timedelta(**age)
        ]

    @classmethod
    async def get_guild_points_above_age(
            cls,
            guild_id: int,
            **age) -> AsyncGenerator[CachedPoint, None]:
        """
        Get all points for a user in a guild above a certain age.
        """

        for _, guild_dict in cls.all_points.items():
            for guild, points in guild_dict.items():
                if guild == guild_id:
                    async for point in alist(points):
                        if point.timestamp > dt.utcnow() - timedelta(**age):
                            await asyncio.sleep(0)
                            yield point
