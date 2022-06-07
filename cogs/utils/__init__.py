POINT_DIVISOR = {
    "message": 1,
    "voice": 5,
    "minecraft": 5,
}


def get_points(value: int, origin: str) -> int:
    """
    Get the number of points given a key and a divisor.

    Parameters
    ----------
    value : int
        The raw number of points.
    origin : str
        The origin of the points.
    """

    return value // POINT_DIVISOR[origin]


def get_all_points(all_points: dict) -> int:
    """
    Get the total number of points for a user given a dict
    of values and origin points.

    Parameters
    ----------
    all_points : dict
        All of the points that the user has achieved.
    """

    total = 0
    for origin, value in all_points.items():
        total += get_points(value, origin)
    return total
