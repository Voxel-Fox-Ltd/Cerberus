from discord.ext import commands


class DurationConverter(commands.Converter):

    async def convert(self, ctx, value):
        """Converts the given duration into a dict that can be passed straight into a timedelta"""

        attributes = {i.split('=')[0]: int(i.split('=')[1]) for i in value}
        if len(attributes) == 1:
            return attributes
        raise commands.BadArgument()
