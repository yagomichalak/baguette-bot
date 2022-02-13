from datetime import datetime
import discord
from discord.ext import commands, tasks
from mysqldb import the_database
from extra import utils
import os

general_channel_id: int = int(os.getenv('GENERAL_CHANNEL_ID'))

class ScheduledEventsSystem(commands.Cog):
    """ Class for managing the ScheduledEventsSystem table in the database. """

    def __init__(self, client: commands.Bot) -> None:
        """ Class init method. """

        self.client = client


    @tasks.loop(seconds=60)
    async def advertise_patreon(self) -> None:
        """ Checks the time for advertising Patreon. """

        current_time = await utils.get_time()

        # Checks whether advertising time is due
        if not await self.check_advertising_slots(current_time):
            return

        # Gets text and advertises.
        general_channel = self.client.get_channel(general_channel_id)

        text: str = ''
        with open('./media/texts/patreon_ad.txt', 'r', encoding="utf-8") as f:
            text = f.read()
        
        await general_channel.send(text)

    async def check_advertising_slots(self, current_time: datetime) -> bool:
        """ Checks whether the current time is one of the pre-selected ones
        at which to advertise the Patreon ad. """

        return current_time.hour in (12, 17, 22) and current_time.minute == 0

