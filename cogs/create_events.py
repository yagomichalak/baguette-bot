import discord
from discord.ext import commands

class CreateEvents(commands.Cog):
    """ Category for creating event channels. """

    def __init__(self, client: commands.Bot) -> None:
        """ Class init method. """

        self.client = client

def setup(client: commands.Bot) -> None:
    """ Cog's setup function. """
    
    client.add_cog(CreateEvents(client))