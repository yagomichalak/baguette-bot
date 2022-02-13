import discord
from discord.ext import commands
import aiomysql
from os import getenv
import asyncio
from typing import List, Union, Any, Dict
import time

from extra.view import ReportSupportView
from extra.moderation.ticket import TicketTable
from extra import utils

from mysqldb import the_database

moderation_cogs: List[commands.Cog] = [
	TicketTable
]

class Ticket(*moderation_cogs):
	""" A class regarding the management of tickets and their channels. """

	def __init__(self, client) -> None:
		""" An ordinary bot initialization method. """

		self.client = client
		self.loop = asyncio.get_event_loop()
		self.ticket_category_id: int = int(getenv('TICKET_CAT_ID'))
		self.cache: Dict[int, int] = {}
		self.report_cache = {}

	@commands.Cog.listener()
	async def on_ready(self) -> None:
		""" Fires when the bot loads the cog. """

		self.client.add_view(view=ReportSupportView(self.client))
		print("Ticket cog is online!")

	@commands.command(aliases=['make_report_msg', 'reportmsg', 'report_msg', 'supportmsg', 'support_msg'])
	@commands.has_permissions(administrator=True)
	async def make_report_support_message(self, ctx) -> None:
		""" (ADM) Makes a Report-Support message. """
		
		guild = ctx.guild
		embed = discord.Embed(
			title="__Create a Ticket / Créer un Ticket__",
			description="""🇬🇧 If you have a problem in the server or with a user and would like us to have a look, click the reaction below to create a ticket.

🇫🇷 Si vous avez un problème sur le serveur, avec une ou plusieurs personnes, et que vous voulez qu'on y jette un œil, cliquez sur la réaction ci-dessous pour créer un ticket.""",
			color=ctx.author.color,
			timestamp=ctx.message.created_at,
		)
		embed.set_author(name=self.client.user.display_name, url=self.client.user.display_avatar, icon_url=self.client.user.display_avatar)
		embed.set_thumbnail(url=guild.icon.url)
		embed.set_footer(text=guild.name, icon_url=guild.icon.url)
		view = ReportSupportView(self.client)
		await ctx.send(embed=embed, view=view)
		self.client.add_view(view=view)

	@commands.command(aliases=['close_ticket', 'cc', 'ct'])
	@commands.has_permissions(administrator=True)
	async def close_channel(self, ctx):
		""" Closes a Ticket-Channel. """

		user_channel = await self.get_ticket_channel(ctx.channel.id)
		if not user_channel:
			return await ctx.send(f"**What do you think that you are doing? You cannot delete this channel, {ctx.author.mention}!**")

		channel = discord.utils.get(ctx.guild.channels, id=user_channel[1])
		embed = discord.Embed(title="Confirmation",
			description="Are you sure that you want to delete this ticket channel?",
			color=ctx.author.color,
			timestamp=ctx.message.created_at)
		confirmation = await ctx.send(content=ctx.author.mention, embed=embed)
		await confirmation.add_reaction('✅')
		await confirmation.add_reaction('❌')
		try:
			reaction, user = await self.client.wait_for('reaction_add', timeout=20, 
			check=lambda r, u: u == ctx.author and r.message.channel == ctx.channel and str(r.emoji) in ['✅', '❌'])
		except asyncio.TimeoutError:
			embed = discord.Embed(title="Confirmation",
			description="You took too long to answer the question; not deleting it!",
			color=discord.Color.red(),
			timestamp=ctx.message.created_at)
			return await confirmation.edit(content=ctx.author.mention, embed=embed)
		else:
			if str(reaction.emoji) == '✅':
				embed.description = f"**Ticket-Channel {ctx.channel.mention} is being deleted...**"
				await confirmation.edit(content=ctx.author.mention, embed=embed)
				await asyncio.sleep(3)
				await channel.delete()
				await self.remove_ticket_channel(user_channel[0])
			else:
				embed.description = "Not deleting it!"
				await confirmation.edit(content='', embed=embed)


	async def open_ticket(self, interaction, member, guild, data) -> None:
		""" Opens a ticket. """

		if channel_id := await self.has_ticket_channel(member.id):
			channel = self.client.get_channel(channel_id)
			embed = discord.Embed(
				title="Error!", 
				description=f"**You already have an open channel! {channel.mention}**", color=discord.Color.red())
			return await interaction.followup.send(embed=embed, ephemeral=True)

		self.report_cache[member.id] = await utils.get_timestamp()
		counter = await self.get_ticket_number()

		# Gets the staff role
		staff = discord.utils.get(guild.roles, id=int(getenv('STAFF_ROLE_ID')))

		# Creates the Ticket channel
		case_cat = discord.utils.get(guild.categories, id=self.ticket_category_id)
		overwrites = {guild.default_role: discord.PermissionOverwrite(
		read_messages=False, send_messages=False, view_channel=False), 
		member: discord.PermissionOverwrite(
		read_messages=True, send_messages=True, view_channel=True, embed_links=True, attach_files=True),
		staff: discord.PermissionOverwrite(
		read_messages=True, send_messages=True, view_channel=True)
		}

		# Checks whether the counter is a prohibited number
		if counter == 7*100*2 + 20*4 + 3*3 - 1:
			counter += 1

		the_channel = await guild.create_text_channel(name=f"{data['title']}-{counter}", category=case_cat, overwrites=overwrites)

		# Sends the DM embed
		created_embed = discord.Embed(
		title=f"{data['title']} channel created!", 
		description=f"Please, go to {the_channel.mention}!", 
		color=discord.Color.green()
		)
		await interaction.followup.send(embed=created_embed, ephemeral=True)
		await self.insert_ticket_channel(member.id, the_channel.id)
		await self.increase_ticket_number()

		# Sends the server embed
		embed = discord.Embed(
		title=f"{data['title']} opened!", 
		description=data['message'], 
		color=discord.Color.green()
		)

		await the_channel.send(content=f"{member.mention} • {data['formatted_pings']}", embed=embed)




"""
b!create_ticket_table
b!create_ticket_counter_table
"""

def setup(client):
	client.add_cog(Ticket(client))