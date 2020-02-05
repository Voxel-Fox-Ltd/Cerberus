from discord.ext import commands


class Duration(object):

    def __init__(self, period:str, duration:int):
        self.period = period
        self.duration = duration

    def keys(self):
        return [self.period]

    def __getitem__(self, key):
        return self.duration

    @classmethod
    async def convert(self, ctx, value):
        """Converts the given duration into a dict that can be passed straight into a timedelta"""

        try:
            attributes = Duration(value.split('=')[0], int(value.split('=')[1]))
        except (ValueError, IndexError):
            raise commands.BadArgument()
        return attributes
