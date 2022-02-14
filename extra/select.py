import discord
from discord.ext import commands
import os
from typing import List, Union, Dict, Any

staff_role_id: int = int(os.getenv('STAFF_ROLE_ID'))
lucas_id: int = int(os.getenv('LUCAS_ID'))

class ReportSupportSelect(discord.ui.Select):
    def __init__(self, client: commands.Bot):
        super().__init__(
            custom_id="report_support_select", placeholder="Select what kind of Help you need", 
            min_values=1, max_values=1, 
            options=[
                discord.SelectOption(label="Report", description="Report a user or issue / Signaler un problème", emoji="🔨"),
                discord.SelectOption(label="Server", value="Question", description="Ask a server question / Poser une question par rapport au serveur", emoji="❓"),
                # discord.SelectOption(label="Complaint", description="Make a complaint / Faire une plainte en rapport avec serveur", emoji="🆘"),
                discord.SelectOption(label="Nevermind", description="Nevermind / Laisse tomber", emoji="🤔"),
            ])
        self.client = client
        self.cog = client.get_cog('Ticket')
    
    async def callback(self, interaction: discord.Interaction):

        await interaction.response.defer()
        
        member = interaction.user

        option = interaction.data['values'][0]

        data: Dict[str, Any] = {
            'title': option,
            'message': '',
            'pings': [],
            'formatted_pings': []
        }

        if option == 'Nevermind':
            return await interaction.followup.send("**Understandable, have a nice day!**", ephemeral=True)

        if option == 'Question':
            data['message'] = f"Please, {member.mention}, try to explain what happened and how we can help you with."

        elif option == 'Server':
            data['message'] = f"Please, {member.mention}, try to explain what kind of help you want related to the server."
            data["pings"] = [{"id": staff_role_id, "role": True}]
                
        # elif option == 'Complaint':
        #     data['message'] = f"Please, {member.mention}, inform us what roles you want, and if you spotted a specific problem with the reaction-role selection."
        #     data["pings"] = [{"id": lucas_id, "role": False}]
            
        data['formatted_pings'] = await self.format_ticket_pings(interaction.guild, data['pings'])
        await self.cog.open_ticket(interaction, member, interaction.guild, data)

    async def format_ticket_pings(self, guild: discord.Guild, pings: List[Dict[str, Union[int, bool]]]) -> str:
        """ Formats pings for a ticket type.
        :param guild: The guild to get the users and roles from.
        :param pings: The pings to format. """

        ping_mentions: List[Union[discord.Member, discord.Role]] = []

        for ping in pings:
            if ping['role']:
                role = discord.utils.get(guild.roles, id=ping['id'])
                ping_mentions.append(role.mention)
            else:
                member = discord.utils.get(guild.members, id=ping['id'])
                ping_mentions.append(member.mention)

        if ping_mentions:
            return ', '.join(ping_mentions)

        return ''
