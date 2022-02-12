import discord
from discord.ext import commands
import os

help_channel_id: int = int(os.getenv('HELP_CHANNEL_ID'))
help_channel2_id: int = int(os.getenv('HELP_CHANNEL2_ID'))
no_thread_role_id: int = int(os.getenv('NO_THREAD_ROLE_ID'))

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

        if message.channel.id not in [help_channel_id, help_channel2_id]:
            return

        if message.author.get_role(no_thread_role_id):
            return

        await message.create_thread(name="Help Thread")
        
