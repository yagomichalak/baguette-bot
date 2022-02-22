import discord
from discord.ext import commands
import os
from typing import List

help_channel_id: int = int(os.getenv('HELP_CHANNEL_ID'))
help_channel2_id: int = int(os.getenv('HELP_CHANNEL2_ID'))
help_channel3_id: int = int(os.getenv('HELP_CHANNEL3_ID'))
no_thread_role_id: int = int(os.getenv('NO_THREAD_ROLE_ID'))
declinator_bot_id: int = int(os.getenv('DECLINATOR_BOT_ID'))
suggestion_channel_id: int = int(os.getenv('SUGGESTION_CHANNEL_ID'))

class HelpChannel(commands.Cog):
    """ Category for the help channel feature. """

    def __init__(self, client: commands.Bot) -> None:
        """ Class init method. """

        self.client = client
        self.help_channels: List[int] = [help_channel_id, help_channel2_id, help_channel3_id]
        self.reactions: List[str] = [
            '⬆', '⬇', '✅', '❌', '❔'
        ]
        self.suggestion_channel_id: int = suggestion_channel_id

    @commands.Cog.listener(name='on_raw_reaction_add')
    async def on_raw_reaction_add_suggestion(self, payload) -> None:
        """ Checks reactions related to suggestion channels. """

        # Checks if it wasn't a bot's reaction
        if not payload.guild_id:
            return

        member = payload.member

        # Checks whether it's a valid member and not a bot
        if not member or member.bot:
            return

        if payload.channel_id != self.suggestion_channel_id:
            return

        guild = self.client.get_guild(payload.guild_id)

        if guild.owner_id != member.id:
            return

        emoji = str(payload.emoji)
        channel = self.client.get_channel(payload.channel_id)
        message = await channel.fetch_message(payload.message_id)
        if message.author.bot:
            return

        # Checks whether it's a steal
        if emoji == '✅':
            try:
                embed = discord.Embed(
                    title="__Approved Suggestion__",
                    description=message.content,
                    color=member.color,
                    timestamp=message.created_at
                )
                embed.set_thumbnail(url=member.display_avatar)
                embed.set_footer(text=f"Suggested by: {member}", icon_url=member.display_avatar)
                await channel.send(embed=embed)
            except:
                pass
            finally:
                await message.delete()

        elif emoji == '❌':
            try:
                await message.clear_reactions()
            except:
                pass
            finally:
                await message.add_reaction('❌')

        elif emoji == '❔':
            try:
                thread = await message.create_thread(name=str(message.author.nick or message.author))
                await thread.send(f"**Your suggestion has been brought here to this thread for review, {payload.member.mention}!**")
                if bot := discord.utils.get(message.guild.members, id=declinator_bot_id):
                    await thread.add_user(bot)
            except:
                pass

    @commands.Cog.listener(name="on_message")
    async def on_message_suggestion_channel(self, message) -> None:
        """ Checks whether the message was sent in the help channel. """


        if not message.guild:
            return
        
        if message.author.bot:
            return

        if message.channel.id != self.suggestion_channel_id:
            return

        if message.author.get_role(no_thread_role_id):
            return

        for reaction in self.reactions:
            await message.add_reaction(reaction)

    @commands.Cog.listener(name="on_message")
    async def on_message_help_channel(self, message) -> None:
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