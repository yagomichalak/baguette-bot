import discord
from discord.ext import commands
import os

help_channel_id: int = int(os.getenv('HELP_CHANNEL_ID'))
help_channel2_id: int = int(os.getenv('HELP_CHANNEL2_ID'))
help_channel3_id: int = int(os.getenv('HELP_CHANNEL3_ID'))
no_thread_role_id: int = int(os.getenv('NO_THREAD_ROLE_ID'))
declinator_bot_id: int = int(os.getenv('DECLINATOR_BOT_ID'))

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

        if message.channel.id not in [help_channel_id, help_channel2_id, help_channel3_id]:
            return

        if message.author.get_role(no_thread_role_id):
            return

        thread = await message.create_thread(name=str(message.author))
        try:
            if bot := discord.utils.get(message.guild.members, id=declinator_bot_id):
                await thread.add_user(bot)
        except:
            pass
        
