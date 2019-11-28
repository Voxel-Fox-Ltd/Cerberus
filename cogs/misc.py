import discord
from discord.ext.commands import commands

from cogs import utils

class Misc(utils.cog):

  def __init__(self, bot:utils.CustomBot):
    super().__init__(bot)
    
  @commands.command()
  async def github(self, ctx:utils.Context):
      '''
      Sends the GitHub Repository link
      '''

      await ctx.send("<https://github.com/4Kaylum/Cerberus/>")
      
  def setup(bot:utils.CustomBot):
    x = misc(bot)
    bot.add_cog(x)
