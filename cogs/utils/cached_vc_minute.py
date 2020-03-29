from datetime import datetime as dt, timedelta
import collections
import typing

import discord


class CachedVCMinute(object):
    """An object for a minute in VC to be cached with minimal overhead

    Params:
        user_id: int
            The ID for the user who posted the message
        guild_id: int
            The ID of the guild the message was posted in
        timestamp: dateime.datetime
            The timestamp that the minute was cached at
    """

    all_minutes: typing.Dict[typing.List[int], typing.List['CachedVCMinute']] = collections.defaultdict(list)
    __slots__ = ('user_id', 'guild_id', 'timestamp')

    def __init__(self, user_id:int, guild_id:int, timestamp:dt):
        self.user_id = user_id
        self.guild_id = guild_id
        self.timestamp = timestamp
        self.all_minutes[(self.user_id, self.guild_id)].append(self)

    def minute_cached_after(self, **kwargs) -> bool:
        """Returns whether or not the message was posted after a given time
        kwargs are passed directly into a timedelta"""

        return self.timestamp > dt.utcnow() - timedelta(**kwargs)

    def minute_cached_before(self, **kwargs) -> bool:
        """Returns whether or not the message was posted before a given time
        kwargs are passed directly into a timedelta"""

        return self.timestamp < dt.utcnow() - timedelta(**kwargs)

    @classmethod
    def get_minutes_after(cls, user_id:typing.Union[discord.User, int], guild_id:typing.Union[discord.Guild, int], **kwargs) -> typing.List['CachedMessage']:
        """Returns all messages from a given user (via their ID) after a given time
        kwargs are passed directly into a timedelta

        Params:
            user_id: int
                The ID of the user you want to get objects for
        """

        user_id = getattr(user_id, 'id', user_id)
        guild_id = getattr(guild_id, 'id', guild_id)
        if kwargs:
            check = lambda m: m.minute_cached_after(**kwargs)
        else:
            check = lambda m: True
        return [i for i in cls.all_minutes[(user_id, guild_id)] if check(i)]

    @classmethod
    def get_minutes_between(cls, user_id:typing.Union[discord.User, int], guild_id:typing.Union[discord.Guild, int], before:dict, after:dict) -> typing.List['CachedMessage']:
        """Returns all messages from a given user (via their ID) after a given time
        kwargs are passed directly into a timedelta

        Params:
            user_id: int
                The ID of the user you want to get objects for
        """

        user_id = getattr(user_id, 'id', user_id)
        guild_id = getattr(guild_id, 'id', guild_id)
        check = lambda m: m.minute_cached_after(**after) and m.minute_cached_before(**before)
        return [i for i in cls.all_minutes[(user_id, guild_id)] if check(i)]
