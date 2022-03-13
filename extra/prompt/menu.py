import discord
from typing import Union

class ConfirmButton(discord.ui.View):
    """ View for prompting user confirmation. """

    def __init__(self, member: Union[discord.User, discord.Member], timeout: int = 180):
        """ Class init method. """

        super().__init__(timeout=timeout)
        self.member = member
        self.value = None
        self.interaction = None

    @discord.ui.button(label='Confirm', style=discord.ButtonStyle.green)
    async def confirm(self, button: discord.ui.Button, interaction: discord.Interaction) -> None:
        """ Confirms the prompt. """
        
        self.value = True
        self.interaction = interaction
        self.stop()

    # This one is similar to the confirmation button except sets the inner value to `False`
    @discord.ui.button(label='Cancel', style=discord.ButtonStyle.grey)
    async def cancel(self, button: discord.ui.Button, interaction: discord.Interaction) -> None:
        """ Cancels the prompt. """

        self.value = False
        self.interaction = interaction
        self.stop()

    async def interaction_check(self, interaction: discord.Interaction) -> bool:
        """ Checks whether the person who interacted wih the button is the one
        who started it. """

        return self.member.id == interaction.user.id
