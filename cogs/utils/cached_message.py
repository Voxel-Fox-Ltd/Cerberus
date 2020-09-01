from datetime import datetime as dt, timedelta
import collections
import typing

import discord


class CachedMessage(object):
    """An object for the message to be cached with minimal overhead

    Params:
        user_id: int
            The ID for the user who posted the message
        guild_id: int
            The ID of the guild the message was posted in
        message_id: int
            The ID of the message that was posted
            Used instead of timestamp so I can have it as a primary key in the DB, since snowflakes
            have a datetime inbuilt
    """

    all_messages: typing.Dict[typing.List[int], typing.List['CachedMessage']] = collections.defaultdict(list)
    __slots__ = ('user_id', 'guild_id', 'timestamp')

    def __init__(self, user_id:int, guild_id:int, timestamp:dt, message_id:int=None):
        self.user_id = user_id
        self.guild_id = guild_id
        self.timestamp = timestamp
        self.all_messages[(self.user_id, self.guild_id)].append(self)

    def message_posted_after(self, **kwargs) -> bool:
        """Returns whether or not the message was posted after a given time
        kwargs are passed directly into a timedelta"""

        return self.timestamp > dt.utcnow() - timedelta(**kwargs)

    def message_posted_before(self, **kwargs) -> bool:
        """Returns whether or not the message was posted before a given time
        kwargs are passed directly into a timedelta"""

        return self.timestamp < dt.utcnow() - timedelta(**kwargs)

    @classmethod
    def get_messages_after(cls, user_id:typing.Union[discord.User, int], guild_id:typing.Union[discord.Guild, int], **kwargs) -> typing.List['CachedMessage']:
        """Returns all messages from a given user (via their ID) after a given time
        kwargs are passed directly into a timedelta

        Params:
            user_id: int
                The ID of the user you want to get objects for
        """

        user_id = getattr(user_id, 'id', user_id)
        guild_id = getattr(guild_id, 'id', guild_id)
        if kwargs:
            check = lambda m: m.message_posted_after(**kwargs)
        else:
            check = lambda m: True
        return [i for i in cls.all_messages[(user_id, guild_id)] if check(i)]

    @classmethod
    def get_messages_between(cls, user_id:typing.Union[discord.User, int], guild_id:typing.Union[discord.Guild, int], before:dict, after:dict) -> typing.List['CachedMessage']:
        """Returns all messages from a given user (via their ID) after a given time
        kwargs are passed directly into a timedelta

        Params:
            user_id: int
                The ID of the user you want to get objects for
        """

        user_id = getattr(user_id, 'id', user_id)
        guild_id = getattr(guild_id, 'id', guild_id)
        check = lambda m: m.message_posted_after(**after) and m.message_posted_before(**before)
        return [i for i in cls.all_messages[(user_id, guild_id)] if check(i)]
