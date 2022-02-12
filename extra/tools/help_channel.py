import discord
from discord.ext import commands
import os

help_channel_id: int = int(os.getenv('HELP_CHANNEL_ID'))

class HelpChannel(commands.Cog):
    """ Category for the help channel feature. """

    def __init__(self, client: commands.Bot) -> None:
        """ Class init method. """

        self.client = client

    @commands.Cog.listener()
    async def on_message(self, message) -> None:
        """ Checks whether the message was sent in the help channel. """

        if not message.guild:
            return

        if message.channel.id != help_channel_id:
            return

        help_channel = discord.utils.get(message.guild.text_channels, id=help_channel_id)
        thread = await message.create_thread(name="Help Thread")
        
