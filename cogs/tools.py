import discord
from discord.ext import commands
import os
from typing import List

from extra.tools.help_channel import HelpChannel
from extra.tools.scheduled_events import ScheduledEventsSystem, ScheduledEventsTable
from extra.tools.user_voice import UserVoiceTable, UserVoiceSystem

tool_cogs: List[commands.Cog] = [
    HelpChannel, UserVoiceTable, UserVoiceSystem,
    ScheduledEventsSystem, ScheduledEventsTable
]

class Tools(*tool_cogs):
    """ Category for tool commands and features. """

    def __init__(self, client: commands.Bot) -> None:
        """ Class init method. """
        
        super().__init__(self)
        self.client = client

    @commands.Cog.listener()
    async def on_ready(self) -> None:
        """ Tells when the cog is ready to go. """

        self.advertise_patreon.start()
        self.solve_broken_roles.start()
        print('Tool cog is online!')

def setup(client: commands.Bot) -> None:
    """ Cog's setup function. """

    client.add_cog(Tools(client))

