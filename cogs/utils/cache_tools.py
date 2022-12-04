from datetime import datetime as dt, timedelta
from enum import Enum, auto
from dataclasses import dataclass
import collections
import functools
from typing import ClassVar, Optional
from typing_extensions import Self
import asyncio


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
    )
    # _point_removal_tasks: set[asyncio.Task] = set()

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

        point = CachedPoint(source, timestamp or dt.utcnow())
        cls.all_points[user_id][guild_id].append(point)

    @classmethod
    def get_points(
            cls,
            user_id: int,
            guild_id: int) -> list[CachedPoint]:
        """
        Get all points for a user in a guild.
        """

        return cls.all_points[user_id][guild_id]

    @classmethod
    def get_points_above_age(
            cls,
            user_id: int,
            guild_id: int,
            age: timedelta) -> list[CachedPoint]:
        """
        Get all points for a user in a guild above a certain age.
        """

        return [
            point
            for point in cls.all_points[user_id][guild_id]
            if point.timestamp > dt.utcnow() - age
        ]
