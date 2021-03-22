import discord
from discord.ext import commands, menus


class Confirm(menus.Menu):
	""" Class related to confirmation skill actions. """

	def __init__(self, msg, content: str = None):
		""" Class initializing method that inherits the parent's initializer. """

		super().__init__(timeout=60, delete_message_after=False, clear_reactions_after=True)

		self.content = content
		self.msg = msg
		self.result = None

	async def send_initial_message(self, ctx, channel) -> discord.Message:
		""" Sends the initial message. """

		self.sent_msg = await channel.send(content=self.content, embed=discord.Embed(description=self.msg, color=discord.Color.orange()))
		return self.sent_msg

	async def finalize(self, timed_out) -> None:
		""" Runs when it finalizes.
		:param timed_out: Whether it timed-out or not. """
		
		if timed_out:
			await self.sent_msg.edit(embed=discord.Embed(description="**Timeout!**", color=discord.Color.red()))

	def reaction_check(self, payload):
		"""The function that is used to check whether the payload should be processed.
		This is passed to :meth:`discord.ext.commands.Bot.wait_for <Bot.wait_for>`.
		There should be no reason to override this function for most users (But I'm not like most users).
		Parameters
		------------
		payload: :class:`discord.RawReactionActionEvent`
			The payload to check.
		Returns
		---------
		:class:`bool`
			Whether the payload should be processed.
		"""
		if payload.message_id != self.message.id:
			return False
		if payload.user_id != self._author_id:
			return False

		return payload.emoji in self.buttons

	@menus.button('\N{WHITE HEAVY CHECK MARK}')
	async def do_confirm(self, payload):
		""" Confirms skill action."""

		embed = self.sent_msg.embeds[0]
		embed.color = discord.Color.green()
		embed.title="Confirmed!"
		await self.sent_msg.edit(embed=embed)
		self.result = True
		self.stop()

	@menus.button('\N{CROSS MARK}')
	async def do_deny(self, payload):
		""" Denies skill action."""

		embed = self.sent_msg.embeds[0]
		embed.color = discord.Color.red()
		embed.title="Denied!"
		await self.sent_msg.edit(embed=embed)
		self.result = False
		self.stop()

	async def prompt(self, ctx):
		""" Prompts the question. """

		await self.start(ctx, wait=True)
		return self.result



class LoopMenu(menus.ListPageSource):
	""" A class for iterating through inventory items. """

	def __init__(self, data):
		super().__init__(data, per_page=10)

	async def format_page(self, menu, entries) -> discord.Embed:
		""" Formats the inventory for each page. """

		offset = menu.current_page * self.per_page


		# for i, v in enumerate(entries, start=offset):
		# 	embed.add_field(name=f"{i+1}.", value=f"**Merchant:** <@{v[0]}>\n**Item Price:** `{v[7]}`", inline=True)
		# 	embed.set_footer(text=f"({i+1}-{i+6} of {len(self.entries)})")

		return embed


class SwitchPages(menus.ListPageSource):
	""" A class for switching tribe pages. """

	def __init__(self, data, **kwargs):
		""" Class initializing method. """

		super().__init__(data, per_page=10)
		self.change_embed = kwargs.get('change_embed')
		self.kwargs = kwargs


	async def format_page(self, menu, entries):
		""" Formats each page. """

		offset = menu.current_page * self.per_page
		return await self.change_embed(
			ctx=menu.ctx, entries=entries, offset=offset+1, lentries=len(self.entries), kwargs=self.kwargs
			)