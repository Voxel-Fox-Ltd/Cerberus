from . import cache_tools as cache


__all__ = (
    "get_points",
    "get_all_points",
    "cache",
)


POINT_DIVISOR = {
    "message": 1,
    "voice": 5,
    "minecraft": 5,
}


def get_points(value: int, source: str) -> int:
    """
    Get the number of points given a key and a divisor.

    Parameters
    ----------
    value : int
        The raw number of points.
    source : str
        The source of the points.
    """

    return value // POINT_DIVISOR[source]


def get_all_points(all_points: dict) -> int:
    """
    Get the total number of points for a user given a dict
    of values and source points.

    Parameters
    ----------
    all_points : dict
        All of the points that the user has achieved.
    """

    total = 0
    for source, value in all_points.items():
        if source in POINT_DIVISOR:
            total += get_points(value, source)
    return total
