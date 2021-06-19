import discord
from discord.ext import commands, tasks

import asyncio
from datetime import datetime
import os
import pytz
from pytz import timezone
from mysqldb import the_database
from typing import List, Union

import inspect
import io
import textwrap
import traceback

from contextlib import redirect_stdout

import emoji
import re

patreon_supporter_role_id = int(os.getenv('PATREON_SUPPORTER_ROLE_ID'))
staff_role_id = int(os.getenv('STAFF_ROLE_ID'))

class Misc(commands.Cog):
	""" A miscellaneous category. """

	def __init__(self, client) -> None:
		self.client = client


	@commands.Cog.listener()
	async def on_ready(self) -> None:
		self.server_status.start()
		self.check_server_activity_status.start()
		self.look_for_due_reminders.start()
		print('Misc cog is online')


	@commands.Cog.listener()
	async def on_message(self, message) -> None:
		""" Stores every message into the daily and weekly server status. """
		# return

		if not message.guild:
			return
		if message.author.bot:
			return

		if not await self.check_table_server_status():
			return

		current_ts = await Misc.get_timestamp()
		channel = message.channel
		await self.update_user_server_status_messages(status_ts=current_ts, label="daily-messages", past_days=1, channel_id=channel.id)
		await self.update_user_server_status_messages(status_ts=current_ts, label="weekly-messages", past_days=7, channel_id=channel.id)
		await self.check_emoji(message)


	@commands.Cog.listener()
	async def on_member_update(self, before, after) -> None:
		""" Checks users' last seen datetime and updates it. """
		
		if before.status == after.status:
			return

		if str(before.status) == 'offline' or str(after.status) == 'offline':

			current_ts = await Misc.get_timestamp()
			if await self.get_member_last_seen(after.id):
				await self.update_member_last_seen(after.id, current_ts)
			else:
				await self.insert_member_last_seen(after.id, current_ts)

	@commands.Cog.listener()
	async def on_interaction_update(self, message, member, button, response) -> None:

		if not message.guild:
			return

		if not button.custom_id.startswith(('english_translation', 'french_translation')):
			return

		custom_ids = button.custom_id.split(':')
		
		if int(custom_ids[1]) != member.id:
			return
		
		guild = message.guild

		if custom_ids[0] == 'english_translation':
			if custom_ids[2].endswith('all'):
				new_embed = await self.make_rules_embed(guild, 1)
			else:
				new_embed = await self.make_rule_embed(guild, custom_ids[2], 1)
			await message.edit(embed=new_embed)

		elif custom_ids[0] == 'french_translation':
			if custom_ids[2].endswith('all'):
				new_embed = await self.make_rules_embed(guild, 2)
			else:
				new_embed = await self.make_rule_embed(guild, custom_ids[2], 2)
				
			await message.edit(embed=new_embed)

		button.ping(response)
		
	

	@tasks.loop(minutes=1)
	async def check_server_activity_status(self):
		""" Checks whether the daily and weekly server status should be cleared. """

		if not await self.check_table_server_status():
			return

		current_ts = await Misc.get_timestamp()

		# Daily
		if (daily_msgs := await self.select_user_server_status_messages(label='daily-messages'))[0]:
			if current_ts - daily_msgs[0] >= 86400:
				await self.update_user_server_status_messages(label='daily-messages', clear=True)

		if (daily_time := await self.select_user_server_status_time(label='daily-time'))[0]:
			if current_ts - daily_time[0] >= 86400:
				await self.update_user_server_status_vc_time(label='daily-time', clear=True)

		# Weekly
		if (weekly_msgs := await self.select_user_server_status_messages(label='weekly-messages'))[0]:
			if current_ts - weekly_msgs[0] >= 604800:
				await self.update_user_server_status_messages(label='weekly-messages', clear=True)

		if (weekly_time := await self.select_user_server_status_time(label='weekly-time'))[0]:
			if current_ts - weekly_time[0] >= 604800:
				await self.update_user_server_status_vc_time(label='weekly-time', clear=True)


	@tasks.loop(minutes=6)
	async def server_status(self) -> None:
		""" Updates the server status; members and boosts counting. """

		guild = self.client.get_guild(int(os.getenv('SERVER_ID')))


		if members_channel := guild.get_channel(int(os.getenv('MEMBERS_CHANNEL_ID'))):
			await members_channel.edit(name=f"Members: {len(guild.members)}")

		if clock_channel := guild.get_channel(int(os.getenv('CLOCK_CHANNEL_ID'))):
			time_now = datetime.now()
			tzone = timezone('Etc/GMT')

			date_and_time = time_now.astimezone(tzone)
			date_and_time_in_text = date_and_time.strftime('%H:%M')

			await clock_channel.edit(name=f'🕐 GMT - {date_and_time_in_text}')

		# if boosts_channel := guild.get_channel(int(os.getenv('BOOSTS_CHANNEL_ID'))):
		# 	await boosts_channel.edit(name=f"Boosts: {guild.premium_subscription_count}")

	@tasks.loop(minutes=1)
	async def look_for_due_reminders(self) -> None:
		""" Looks for expired tempmutes and unmutes the users. """

		current_ts = await Misc.get_timestamp()
		reminders = await self.get_due_reminders(current_ts)
		guild = self.client.get_guild(int(os.getenv('SERVER_ID')))
		for reminder in reminders:
			member = discord.utils.get(guild.members, id=reminder[1])
			if member:
				try:	
					await member.send(f"**`Reminder:`** {reminder[2]}")
				except:
					pass
			
			await self.delete_member_reminder(reminder[0])


	async def check_emoji(self, message: discord.Message) -> None:
		""" Checks whether the message has emojis, if so, updates their counter in the database.
		:param message: The message to check. """


		text_de= emoji.demojize(message.content)
		all_emojis = re.findall(r'[<]?[a]?:[!_\-\w]+:[0-9]{0,18}[>]?', text_de)
		all_emojis = list(set(all_emojis))

		for emj in all_emojis:
			try:
				if the_emoji := await self.get_emoji(emj):
					await self.update_emoji(str(the_emoji[0]))
				else:
					await self.insert_emoji(emj)
			except Exception as e:
				print(e)

	def check_whitelist(client=None):
		async def real_check(ctx):
			the_client = ctx.command.cog.client if ctx.command.cog else client
			LevelSystem = the_client.get_cog('LevelSystem')

			if not await LevelSystem.get_important_var(label="bl_channel", value_int=ctx.channel.id):
				return True

			await ctx.send(f"**This command is blacklisted in this channel, please use a bot channel, {ctx.author.mention}!**")

		return commands.check(real_check)

	@commands.command()
	@check_whitelist()
	async def avatar(self, ctx, member: discord.Member = None) -> None:
		""" Shows the avatar of a member.
		:param member: The member to show (Optional).
		Ps: If not informed, it will show of the command's executor. """

		if not member:
			member = ctx.author

		await ctx.send(member.avatar_url)

	@commands.command()
	@commands.cooldown(1, 5, commands.BucketType.user)
	async def time(self, ctx: commands.Context, time: str = None, my_timezone: str = None) -> None:
		""" Tells the time in a given timezone, and compares to the CET one.
		:param time: The time you want to check. Ex: 7pm
		:param my_timezone: The time zone to convert """

		member = ctx.author
		default_timezone = 'Etc/GMT'

		user_timezone = await self.select_user_timezone(member.id)

		if not time:
			if user_timezone:
				time_now = datetime.now(timezone(user_timezone[1])).strftime(f"%H:%M {user_timezone[1]}")
			else:
				time_now = datetime.now(timezone(default_timezone)).strftime(f"%H:%M {default_timezone}")

			return await ctx.send(f"**Now it's `{time_now}`, {member.mention}**")

		if not my_timezone:
			if not user_timezone:
				return await ctx.send(f"**Please, inform a `my_timezone`, {member.mention}!**")
			my_timezone = user_timezone[1]

		if not my_timezone in (timezones := pytz.all_timezones):
			return await ctx.send(f"**Please, inform a valid timezone, {member.mention}!**\n`(Type b!timezones to get a full list with the timezones in your DM's)`")

		# Given info (time and timezone)
		given_time = time
		given_timezone = my_timezone.title()

		# Format given time
		given_date = datetime.strptime(given_time, '%H:%M')

		# Convert given date to given timezone
		tz = pytz.timezone(given_timezone)
		converted_time = datetime.now(tz=tz)
		converted_time = converted_time.replace(hour=given_date.hour, minute=given_date.minute)

		# Converting date to GMT (Etc/GMT-1)
		GMT = timezone(default_timezone)

		date_to_utc = converted_time.astimezone(GMT).strftime('%H:%M')
		datetime_text = f"**`{converted_time.strftime('%H:%M')} ({given_timezone})` = `{date_to_utc} ({GMT})`**"
		await ctx.send(datetime_text)

	@commands.command()
	@commands.cooldown(1, 300, commands.BucketType.user)
	@check_whitelist()
	async def timezones(self, ctx) -> None:
		""" Sends a full list with the timezones into the user's DM's. 
		(Cooldown) = 5 minutes. """

		member = ctx.author

		timezones = pytz.all_timezones
		timezone_text = ', '.join(timezones)
		try:
			await Misc.send_big_message(channel=member, message=timezone_text)
		except Exception as e:
			await ctx.send(f"**I couldn't do it for some reason, make sure your DM's are open, {member.mention}!**")
		else:
			await ctx.send(f"**List sent, {member.mention}!**")


	@staticmethod
	async def send_big_message(channel, message):
		""" Sends a big message to a given channel. """

		if (len(message) <= 2048):
			embed = discord.Embed(title="Timezones:", description=message, colour=discord.Colour.green())
			await channel.send(embed=embed)
		else:
			embedList = []
			n = 2048
			embedList = [message[i:i + n] for i in range(0, len(message), n)]
			for num, item in enumerate(embedList, start=1):
				if (num == 1):
					embed = discord.Embed(title="Timezones:", description=item, colour=discord.Colour.green())
					embed.set_footer(text=num)
					await channel.send(embed=embed)
				else:
					embed = discord.Embed(description=item, colour=discord.Colour.green())
					embed.set_footer(text=num)
					await channel.send(embed=embed)

	@commands.command()
	@check_whitelist()
	async def settimezone(self, ctx, my_timezone: str = None) -> None:
		""" Sets the timezone.
		:param my_timezone: Your timezone.
		Ps: Use b!timezones to get a full list with the timezones in your DM's. """

		member = ctx.author

		if not my_timezone:
			return await ctx.send(f"**Please, inform a timezone, {member.mention}!**")

		my_timezone = my_timezone.title()
		if not my_timezone in pytz.all_timezones:
			return await ctx.send(f"**Please, inform a valid timezone, {member.mention}!**")

		if user_timezone := await self.select_user_timezone(member.id):
			await self.update_user_timezone(member.id, my_timezone)
			await ctx.send(f"**Updated timezone from `{user_timezone[1]}` to `{my_timezone}`, {member.mention}!**")
		else:
			await self.insert_user_timezone(member.id, my_timezone)
			await ctx.send(f"**Set timezone to `{my_timezone}`, {member.mention}!**")


	# Database (CRUD)


	async def insert_user_timezone(self, user_id: int, my_timezone: str) -> None:
		""" Inserts a timezone for a user.
		:param user_id: The ID of the user to insert.
		:param my_timezone: The user's timezone. """

		mycursor, db = await the_database()
		await mycursor.execute("INSERT INTO UserTimezones (user_id, my_timezone) VALUES (%s, %s)", (user_id, my_timezone))
		await db.commit()
		await mycursor.close()

	async def select_user_timezone(self, user_id: int) -> None:
		""" Gets the user's timezone.
		:param user_id: The ID of the user to get. """

		mycursor, db = await the_database()
		await mycursor.execute("SELECT * FROM UserTimezones WHERE user_id = %s", (user_id,))
		user_timezone = await mycursor.fetchone()
		await mycursor.close()
		return user_timezone

	async def update_user_timezone(self, user_id: int, my_timezone: str) -> None:
		""" Updates the user's timezone.
		:param user_id: The ID of the user to update.
		:param my_timezone: The user's new timezone. """

		mycursor, db = await the_database()
		await mycursor.execute("UPDATE UserTimezones SET my_timezone = %s WHERE user_id = %s", (my_timezone, user_id))
		await db.commit()
		await mycursor.close()


	async def delete_user_timezone(self, user_id: int) -> None:
		""" Deletes the user's timezone.
		:param user_id: The ID of the user to delete. """

		mycursor, db = await the_database()
		await mycursor.execute("DELETE FROM UserTimezones WHERE user_id = %s", (user_id,))
		await db.commit()
		await mycursor.close()


	@commands.command(hidden=True)
	@commands.has_permissions(administrator=True)
	@check_whitelist()
	async def create_table_user_timezones(self, ctx) -> None:
		""" (ADM) Creates the UserTimezones table. """

		if await self.check_table_user_timezones():
			return await ctx.send("**Table __UserTimezones__ already exists!**")
		
		await ctx.message.delete()
		mycursor, db = await the_database()
		await mycursor.execute("CREATE TABLE UserTimezones (user_id BIGINT NOT NULL, my_timezone VARCHAR(50) NOT NULL)")
		await db.commit()
		await mycursor.close()

		return await ctx.send("**Table __UserTimezones__ created!**", delete_after=3)

	@commands.command(hidden=True)
	@commands.has_permissions(administrator=True)
	async def drop_table_user_timezones(self, ctx) -> None:
		""" (ADM) Creates the UserTimezones table """
		if not await self.check_table_user_timezones():
			return await ctx.send("**Table __UserTimezones__ doesn't exist!**")
		await ctx.message.delete()
		mycursor, db = await the_database()
		await mycursor.execute("DROP TABLE UserTimezones")
		await db.commit()
		await mycursor.close()

		return await ctx.send("**Table __UserTimezones__ dropped!**", delete_after=3)

	@commands.command(hidden=True)
	@commands.has_permissions(administrator=True)
	async def reset_table_user_timezones(self, ctx) -> None:
		""" (ADM) Creates the UserTimezones table """

		if not await self.check_table_user_timezones():
			return await ctx.send("**Table __UserTimezones__ doesn't exist yet!**")

		await ctx.message.delete()
		mycursor, db = await the_database()
		await mycursor.execute("DELETE FROM UserTimezones")
		await db.commit()
		await mycursor.close()

		return await ctx.send("**Table __UserTimezones__ reset!**", delete_after=3)

	async def check_table_user_timezones(self) -> bool:
		""" Checks if the UserTimezones table exists """

		mycursor, db = await the_database()
		await mycursor.execute("SHOW TABLE STATUS LIKE 'UserTimezones'")
		table_info = await mycursor.fetchall()
		await mycursor.close()

		if len(table_info) == 0:
			return False

		else:
			return True

	@staticmethod
	async def get_timestamp(tz: str = 'Etc/GMT') -> int:
		""" Gets the current timestamp. """

		tzone = timezone(tz)
		the_time = datetime.now(tzone)
		return the_time.timestamp()

	@staticmethod
	async def get_gmt_now() -> str:
		""" Gets the current time in GMT. """

		tzone = timezone('Etc/GMT')
		time_now = datetime.now(tzone)
		return time_now

	@commands.command(hidden=True)
	@commands.has_permissions(administrator=True)
	async def create_table_server_status(self, ctx) -> None:
		""" (ADM) Creates the ServerStatus table. """

		if await self.check_table_server_status():
			return await ctx.send("**Table __ServerStatus__ already exists!**")
		
		await ctx.message.delete()

		mycursor, db = await the_database()
		await mycursor.execute("""
			CREATE TABLE ServerStatus (
				status_ts BIGINT NOT NULL,
				label VARCHAR(20) NOT NULL, past_days TINYINT(3) NOT NULL,
				messages BIGINT DEFAULT 1, vc_time BIGINT DEFAULT 0,
				channel_id BIGINT NOT NULL)""")


		timestamp = await Misc.get_timestamp()

		channel = ctx.channel
		# await self.insert_user_server_status(status_ts=timestamp, label="daily-messages", past_days=1, channel_id=channel.id)
		# await self.insert_user_server_status(status_ts=timestamp, label="weekly-messages", past_days=7, channel_id=channel.id)

		# await self.insert_user_server_status(status_ts=timestamp, label="daily-time", past_days=1, channel_id=channel.id)
		# await self.insert_user_server_status(status_ts=timestamp, label="weekly-time", past_days=7, channel_id=channel.id)

		await db.commit()
		await mycursor.close()

		return await ctx.send("**Table __ServerStatus__ created!**", delete_after=3)

	@commands.command(hidden=True)
	@commands.has_permissions(administrator=True)
	async def drop_table_server_status(self, ctx) -> None:
		""" (ADM) Creates the ServerStatus table. """

		if not await self.check_table_server_status():
			return await ctx.send("**Table __ServerStatus__ doesn't exist!**")

		await ctx.message.delete()

		mycursor, db = await the_database()
		await mycursor.execute("DROP TABLE ServerStatus")
		await db.commit()
		await mycursor.close()

		return await ctx.send("**Table __ServerStatus__ dropped!**", delete_after=3)

	@commands.command(hidden=True)
	@commands.has_permissions(administrator=True)
	async def reset_table_server_status(self, ctx) -> None:
		""" (ADM) Creates the ServerStatus table; """

		if not await self.check_table_server_status():
			return await ctx.send("**Table __ServerStatus__ doesn't exist yet!**")

		await ctx.message.delete()

		mycursor, db = await the_database()
		await mycursor.execute("DELETE FROM ServerStatus")
		await db.commit()
		await mycursor.close()

		return await ctx.send("**Table __ServerStatus__ reset!**", delete_after=3)

	async def check_table_server_status(self) -> bool:
		""" Checks if the ServerStatus table exists. """

		mycursor, db = await the_database()
		await mycursor.execute("SHOW TABLE STATUS LIKE 'ServerStatus'")
		table_info = await mycursor.fetchall()
		await mycursor.close()

		if len(table_info) == 0:
			return False

		else:
			return True

	async def insert_user_server_status(self, status_ts: int, label: str, channel_id: int, past_days: int, messages: int = 1, vc_time: int = 0) -> None:
		""" Inserts a server status.
		:param status_ts: The timestamp of the.
		:param messages: The message counting.
		:param past_days: Data related to the past.
		:param label: A label for the status. """

		mycursor, db = await the_database()

		await mycursor.execute("""
			INSERT INTO ServerStatus (status_ts, label, messages, past_days, vc_time, channel_id) 
			VALUES (%s, %s, %s, %s, %s, %s)
			""", (status_ts, label, messages, past_days, vc_time, channel_id))


		# await mycursor.execute("""
		# 	INSERT INTO ServerStatus (
		# 		status_ts, messages, past_days, label, vc_time) VALUES (%s, %s, %s, %s, %s)
		# 	""", (status_ts, messages, past_days, label, vc_time))
		await db.commit()
		await mycursor.close()

	async def select_user_server_status_messages(self, label: str) -> int:
		""" Gets the sum of the server status messages.
		:param label: The label of the status. """

		mycursor, db = await the_database()
		await mycursor.execute("SELECT MIN(status_ts), SUM(messages) FROM ServerStatus WHERE label = %s", (label,))
		server_status = number if (number := await mycursor.fetchone())[0] else (None, 0)
		await mycursor.close()
		return server_status

	async def select_user_server_status_time(self, label: str) -> int:
		""" Gets the sum of the server status VC time.
		:param label: The label of the status. """

		mycursor, db = await the_database()
		await mycursor.execute("SELECT MIN(status_ts), SUM(vc_time) FROM ServerStatus WHERE label = %s", (label,))
		server_status = number if (number := await mycursor.fetchone())[0] else (None, 0)
		await mycursor.close()
		return server_status

	async def select_most_active_user_server_status(self, label: str, sublabel: str) -> List[Union[int, str]]:
		""" Gets the most active a server status.
		:param label: The label of the status. 
		:param sublabel: Whether it's active messsage or time-wise. """

		mycursor, db = await the_database()
		if sublabel == 'messages':
			await mycursor.execute("SELECT * FROM ServerStatus WHERE label = %s ORDER BY messages DESC LIMIT 1", (label,))
		else:
			await mycursor.execute("SELECT * FROM ServerStatus WHERE label = %s ORDER BY vc_time DESC LIMIT 1", (label,))
		server_status = await mycursor.fetchone()
		await mycursor.close()
		return server_status

	async def update_user_server_status_messages(self, label: str, channel_id: int = None, messages: int = 1, vc_time: int = 0, past_days: int = 0, status_ts: int = 0, clear: bool = False) -> None:
		""" Updates the server status messages.
		:param channel_id: The channel in which the message was sent.
		:param label: The label of the status.
		:param status_ts: Timestamp of the beginning of the status.
		:param clear: Clear messages. """

		mycursor, db = await the_database()
		if clear:
			await mycursor.execute("DELETE FROM ServerStatus WHERE label = %s", (label,))
		else:

			await mycursor.execute("SELECT channel_id FROM ServerStatus WHERE label = %s and channel_id = %s", (label, channel_id))
			if await mycursor.fetchone():

				await mycursor.execute("UPDATE ServerStatus SET messages = messages + 1 WHERE label = %s and channel_id = %s", (label, channel_id))
			else:
				await mycursor.execute("""
					INSERT INTO ServerStatus (status_ts, label, messages, past_days, vc_time, channel_id) 
					VALUES (%s, %s, %s, %s, %s, %s)
					""", (status_ts, label, messages, past_days, vc_time, channel_id))

		await db.commit()
		await mycursor.close()

	async def update_user_server_status_vc_time(self, label: str, channel_id: int = None, past_days: int = 0, status_ts: int = 0, addition: int = 0, clear: bool = False) -> None:
		""" Updates the server status vc time.
		:param status_ts: Timestamp of the beginning of the status.
		:param label: The label of the status.
		:param addition: The time addition in seconds.
		:param clear: Clear messages. """

		mycursor, db = await the_database()
		if clear:
			await mycursor.execute("DELETE FROM ServerStatus WHERE label = %s", (label,))
		else:
			# await mycursor.execute("UPDATE ServerStatus SET vc_time = vc_time + %s WHERE label = %s", (addition, label))


			await mycursor.execute("SELECT channel_id FROM ServerStatus WHERE label = %s and channel_id = %s", (label, channel_id))
			if await mycursor.fetchone():

				await mycursor.execute("UPDATE ServerStatus SET vc_time = vc_time + %s WHERE label = %s and channel_id = %s", (addition, label, channel_id))
			else:
				await mycursor.execute("""
					INSERT INTO ServerStatus (status_ts, label, past_days, vc_time, channel_id) 
					VALUES (%s, %s, %s, %s, %s)
					""", (status_ts, label, past_days, addition, channel_id))

		await db.commit()
		await mycursor.close()


	async def delete_user_server_status(self, label: str) -> None:
		""" Deletes the a server status.
		:param label: The labelof the server status. """

		mycursor, db = await the_database()
		await mycursor.execute("DELETE FROM ServerStatus WHERE label = %s", (label,))
		await db.commit()
		await mycursor.close()


	@commands.command(hidden=True)
	async def eval(self, ctx, *, body = None):
		'''
		(?) Executes a given command from Python onto Discord.
		:param body: The body of the command.
		'''
		if not ctx.guild:
			return

		if ctx.author.bot:
			return

		await ctx.message.delete()
		if ctx.author.id != 647452832852869120:
			return await ctx.send("**For your own safety you are not allowed to use this!**")

		if not body:
			return await ctx.send("**Please, inform the code body!**")

		"""Evaluates python code"""
		env = {
			'ctx': ctx,
			'client': self.client,
			'channel': ctx.channel,
			'author': ctx.author,
			'guild': ctx.guild,
			'message': ctx.message,
			'source': inspect.getsource
		}

		def cleanup_code(content):
			"""Automatically removes code blocks from the code."""
			# remove ```py\n```
			if content.startswith('```') and content.endswith('```'):
				return '\n'.join(content.split('\n')[1:-1])

			# remove `foo`
			return content.strip('` \n')

		def get_syntax_error(e):
			if e.text is None:
				return f'```py\n{e.__class__.__name__}: {e}\n```'
			return f'```py\n{e.text}{"^":>{e.offset}}\n{e.__class__.__name__}: {e}```'

		env.update(globals())

		body = cleanup_code(body)
		stdout = io.StringIO()
		err = out = None

		to_compile = f'async def func():\n{textwrap.indent(body, "  ")}'

		def paginate(text: str):
			'''Simple generator that paginates text.'''
			last = 0
			pages = []
			for curr in range(0, len(text)):
				if curr % 1980 == 0:
					pages.append(text[last:curr])
					last = curr
					appd_index = curr
			if appd_index != len(text)-1:
				pages.append(text[last:curr])
			return list(filter(lambda a: a != '', pages))

		try:
			exec(to_compile, env)
		except Exception as e:
			err = await ctx.send(f'```py\n{e.__class__.__name__}: {e}\n```')
			return await ctx.message.add_reaction('\u2049')

		func = env['func']
		try:
			with redirect_stdout(stdout):
				ret = await func()
		except Exception as e:
			value = stdout.getvalue()
			err = await ctx.send(f'```py\n{value}{traceback.format_exc()}\n```')
		else:
			value = stdout.getvalue()
			if ret is None:
				if value:
					try:

						out = await ctx.send(f'```py\n{value}\n```')
					except:
						paginated_text = paginate(value)
						for page in paginated_text:
							if page == paginated_text[-1]:
								out = await ctx.send(f'```py\n{page}\n```')
								break
							await ctx.send(f'```py\n{page}\n```')
			else:
				try:
					out = await ctx.send(f'```py\n{value}{ret}\n```')
				except:
					paginated_text = paginate(f"{value}{ret}")
					for page in paginated_text:
						if page == paginated_text[-1]:
							out = await ctx.send(f'```py\n{page}\n```')
							break
						await ctx.send(f'```py\n{page}\n```')

		if out:
			await ctx.message.add_reaction('\u2705')  # tick
		elif err:
			await ctx.message.add_reaction('\u2049')  # x
		else:
			await ctx.message.add_reaction('\u2705')

	# Sends an embedded message
	@commands.command()
	@commands.has_permissions(administrator=True)
	async def embed(self, ctx):
		'''
		(ADM) Sends an embedded message.
		'''
		await ctx.message.delete()
		if len(ctx.message.content.split()) < 2:
			return await ctx.send('You must inform all parameters!')

		msg = ctx.message.content.split('b!embed', 1)
		embed = discord.Embed(description=msg[1], colour=discord.Colour.dark_red())
		await ctx.send(embed=embed)


	@commands.command()
	@check_whitelist()
	async def patreon(self, ctx) -> None:
		""" Shows a list with all Patreon supporters. """

		patreon_supporter_role = discord.utils.get(ctx.guild.roles, id=patreon_supporter_role_id)

		supporters = ', '.join([m.mention for m in ctx.guild.members if patreon_supporter_role in m.roles])

		patreon_link = "https://www.patreon.com/user?u=24213557"

		embed = discord.Embed(
			title="__Patreon Supporters__",
			description=supporters,
			color=ctx.author.color,
			timestamp=ctx.message.created_at,
			url=patreon_link
		)

		component = discord.Component()
		component.add_button(style=5, label="Support Us!", url=patreon_link, emoji="<:Patreon:844644789809971230>")

		await ctx.send(embed=embed, components=[component])


	# Shows the specific rule
	@commands.command()
	@commands.has_role(staff_role_id)
	async def rule(self, ctx, numb: int = None):
		""" Shows a specific server rule.
		:param numb: The number of the rule to show. """

		await ctx.message.delete()
		if numb is None:
			return await ctx.send('**Invalid parameter!**')

		if numb <= 0 or numb > 15:
			return await ctx.send(f'**Inform a rule from `1-15` rules!**')

		the_rule = await self.get_rule(numb)
		embed = await self.make_rule_embed(ctx.guild, numb)

		compo = discord.Component()
		compo.add_button(style=1, label="English", emoji="🇬🇧", custom_id=f"english_translation:{ctx.author.id}:{numb}")
		compo.add_button(style=1, label="French", emoji="🇫🇷", custom_id=f"french_translation:{ctx.author.id}:{numb}")


		the_msg = await ctx.send(embed=embed, components=[compo])
		await asyncio.sleep(60)
		await the_msg.edit(components=None)


	async def make_rule_embed(self, guild, number: int , index: int = 1) -> discord.Embed:
		""" Makes an embed for a specific rule.
		:param number: The number of the rule.
		:param index: Whether it should be in English or French. Default = 1.
		1 - English; 2 - French. """



		rule = await self.get_rule(number)

		embed = discord.Embed(
			title=f"Rule number {rule[0]}",
			description=rule[index], url='https://discordapp.com/guidelines', colour=1406210)

		embed.set_footer(text=guild.owner,
							icon_url=guild.owner.avatar_url)
		embed.set_thumbnail(
			url=guild.icon_url)
		embed.set_author(name=guild.name, url='https://discordapp.com',icon_url=guild.icon_url)
		return embed

	async def make_rules_embed(self, guild, index: int = 1) -> discord.Embed:
		""" Makes an embed for the rules.
		:param index: Whether it should be in English or French. Default = 1.
		1 - English; 2 - French. """

		embed = discord.Embed(title="Discord’s Terms of Service and Community Guidelines",
								description="Rules Of The Server", url='https://discordapp.com/guidelines',
								colour=1406210)

		rules = await self.get_rules()
		rules = [r for r in rules if r[1] or r[2]]

		for rule in rules:
			embed.add_field(name=f"__{rule[0]}__:", value=rule[index], inline=False)

		embed.add_field(name="🇫🇷", value="Enjoy our Server!", inline=True)
		embed.add_field(name="🤖", value="Discover our Features!", inline=True)
		embed.add_field(name="🥖", value="We love chocolatine ~~and pain au chocolat~~!", inline=True)
		embed.set_footer(text=guild.owner,
							icon_url=guild.owner.avatar_url)
		embed.set_thumbnail(
			url=guild.icon_url)
		embed.set_author(name=guild.name, url='https://discordapp.com',
							icon_url=guild.icon_url)

		return embed

	@commands.command()
	@commands.has_permissions(administrator=True)
	async def rules(self, ctx):
		""" (STAFF) Sends an embedded message containing all rules in it. """

		guild = ctx.guild

		embed = await self.make_rules_embed(guild)

		compo = discord.Component()
		compo.add_button(style=1, label="English", emoji="🇬🇧", custom_id=f"english_translation:{ctx.author.id}:all")
		compo.add_button(style=1, label="French", emoji="🇫🇷", custom_id=f"french_translation:{ctx.author.id}:all")

		the_msg = await ctx.send(
			content=f"Hello, **{guild.name}** is a public Discord server for people all across the globe to meet, learn French and exchange knowledge and cultures. here are our rules of conduct.",
			embed=embed,
			components=[compo])
		await asyncio.sleep(60)
		await the_msg.edit(components=None)



	@commands.command(hidden=True)
	@commands.has_permissions(administrator=True)
	async def create_table_emojis(self, ctx) -> None:
		""" (ADM) Creates the Emojis table. """

		if await self.check_table_emojis():
			return await ctx.send("**Table __Emojis__ already exists!**")

		await ctx.message.delete()
		mycursor, db = await the_database()
		await mycursor.execute("""CREATE TABLE Emojis (
			emoji varchar(100) NOT NULL,
			count int NOT NULL DEFAULT 1,
			PRIMARY KEY (emoji)
			) CHARSET utf8mb4 COLLATE utf8mb4_unicode_ci""")
		await db.commit()
		await mycursor.close()

		return await ctx.send("**Table __Emojis__ created!**", delete_after=3)

	@commands.command(hidden=True)
	@commands.has_permissions(administrator=True)
	async def drop_table_emojis(self, ctx) -> None:
		""" (ADM) Creates the Emojis table """

		if not await self.check_table_emojis():
			return await ctx.send("**Table __Emojis__ doesn't exist!**")

		await ctx.message.delete()
		mycursor, db = await the_database()
		await mycursor.execute("DROP TABLE Emojis")
		await db.commit()
		await mycursor.close()

		return await ctx.send("**Table __Emojis__ dropped!**", delete_after=3)

	@commands.command(hidden=True)
	@commands.has_permissions(administrator=True)
	async def reset_table_emojis(self, ctx) -> None:
		""" (ADM) Creates the Emojis table """

		if not await self.check_table_emojis():
			return await ctx.send("**Table __Emojis__ doesn't exist yet!**")

		await ctx.message.delete()
		mycursor, db = await the_database()
		await mycursor.execute("DELETE FROM Emojis")
		await db.commit()
		await mycursor.close()

		return await ctx.send("**Table __Emojis__ reset!**", delete_after=3)

	async def check_table_emojis(self) -> bool:
		""" Checks if the Emojis table exists """

		mycursor, db = await the_database()
		await mycursor.execute("SHOW TABLE STATUS LIKE 'Emojis'")
		table_info = await mycursor.fetchall()
		await mycursor.close()

		if len(table_info) == 0:
			return False

		else:
			return True


	async def get_emoji(self, emj: str) -> List[Union[str, int]]:
		""" Gets an emoji from the database.
		:param emj: The emoji to get. """

		mycursor, db = await the_database()
		await mycursor.execute("SELECT * FROM Emojis WHERE emoji = %s", (emj,))
		the_emoji = await mycursor.fetchone()
		await mycursor.close()
		return the_emoji

	async def update_emoji(self, emj: str, increment: int = 1) -> None:
		""" Updates the counter of an emoji by a value.
		:param emj: The emoji to update.
		:param increment: The incremention to apply to the counter. Default = 1. """

		mycursor, db = await the_database()
		await mycursor.execute("UPDATE Emojis SET count = count + %s WHERE emoji = %s", (increment, emj))
		await db.commit()
		await mycursor.close()

	async def insert_emoji(self, emj: str, counter: int = 1) -> None:
		""" Inserts an emoji into the database.
		:param emj: The emoji to insert.
		:param counter: The emoji's initial counter. Default = 1. """

		mycursor, db = await the_database()
		await mycursor.execute("INSERT INTO Emojis (emoji, count) VALUES (%s, %s)", (emj, counter))
		await db.commit()
		await mycursor.close()

	async def get_top_emojis(self, limit: int = 3) -> List[List[Union[str, int]]]:
		""" Get top X more used emojis.
		:param limit: The amount of emojis to retrieve. """

		mycursor, db = await the_database()
		await mycursor.execute("SELECT * FROM Emojis ORDER BY count DESC LIMIT %s", (limit,))
		the_emojis = await mycursor.fetchall()
		await mycursor.close()
		return the_emojis


	@commands.command(hidden=True)
	@commands.has_permissions(administrator=True)
	async def create_table_last_seen(self, ctx) -> None:
		""" (ADM) Creates the LastSeen table. """

		if await self.check_table_last_seen():
			return await ctx.send("**Table __LastSeen__ already exists!**")

		await ctx.message.delete()
		mycursor, db = await the_database()
		await mycursor.execute("""CREATE TABLE LastSeen (
			user_id BIGINT NOT NULL,
			timestamp BIGINT NOT NULL,
			PRIMARY KEY (user_id)
			) """)
		await db.commit()
		await mycursor.close()

		return await ctx.send("**Table __LastSeen__ created!**", delete_after=3)

	@commands.command(hidden=True)
	@commands.has_permissions(administrator=True)
	async def drop_table_last_seen(self, ctx) -> None:
		""" (ADM) Creates the LastSeen table """

		if not await self.check_table_last_seen():
			return await ctx.send("**Table __LastSeen__ doesn't exist!**")

		await ctx.message.delete()
		mycursor, db = await the_database()
		await mycursor.execute("DROP TABLE LastSeen")
		await db.commit()
		await mycursor.close()

		return await ctx.send("**Table __LastSeen__ dropped!**", delete_after=3)

	@commands.command(hidden=True)
	@commands.has_permissions(administrator=True)
	async def reset_table_last_seen(self, ctx) -> None:
		""" (ADM) Creates the LastSeen table """

		if not await self.check_table_last_seen():
			return await ctx.send("**Table __LastSeen__ doesn't exist yet!**")

		await ctx.message.delete()
		mycursor, db = await the_database()
		await mycursor.execute("DELETE FROM LastSeen")
		await db.commit()
		await mycursor.close()

		return await ctx.send("**Table __LastSeen__ reset!**", delete_after=3)

	async def check_table_last_seen(self) -> bool:
		""" Checks if the LastSeen table exists """

		mycursor, db = await the_database()
		await mycursor.execute("SHOW TABLE STATUS LIKE 'LastSeen'")
		table_info = await mycursor.fetchall()
		await mycursor.close()

		if len(table_info) == 0:
			return False

		else:
			return True


	async def insert_member_last_seen(self, user_id: int, timestamp: int) -> None:
		""" Inserts an entry concerning the user's last seen datetime.
		:param user_id: The ID of the user.
		:param timestamp: The current timestamp. """

		mycursor, db = await the_database()
		await mycursor.execute("INSERT INTO LastSeen (user_id, timestamp) VALUES (%s, %s)", (user_id, timestamp))
		await db.commit()
		await mycursor.close()

	async def update_member_last_seen(self, user_id: int, new_timestamp: int) -> None:
		""" Updates the user's last seen datetime.
		:param user_id: The ID of the user.
		:param new_timestamp: The new timestamp. """

		mycursor, db = await the_database()
		await mycursor.execute("UPDATE LastSeen SET timestamp = %s WHERE user_id = %s", (new_timestamp, user_id))
		await db.commit()
		await mycursor.close()

	async def get_member_last_seen(self, user_id: int) -> List[int]:
		""" Gets the user's last seen datetime.
		:param user_id: The ID of the user. """

		mycursor, db = await the_database()
		await mycursor.execute("SELECT * FROM LastSeen WHERE user_id = %s", (user_id,))
		the_user = await mycursor.fetchone()
		await mycursor.close()
		return the_user

	# ===========

	@commands.command(hidden=True)
	@commands.has_permissions(administrator=True)
	async def create_table_member_reminder(self, ctx) -> None:
		""" (ADM) Creates the MemberReminder table. """

		if await self.check_table_member_reminder():
			return await ctx.send("**Table __MemberReminder__ already exists!**")

		await ctx.message.delete()
		mycursor, db = await the_database()
		await mycursor.execute("""CREATE TABLE MemberReminder (
			reminder_id BIGINT NOT NULL AUTO_INCREMENT,
			user_id BIGINT NOT NULL,
			text VARCHAR(100) NOT NULL,
			reminder_timestamp BIGINT NOT NULL,
			remind_in BIGINT NOT NULL,
			PRIMARY KEY (reminder_id)
			) """)
		await db.commit()
		await mycursor.close()

		return await ctx.send("**Table __MemberReminder__ created!**", delete_after=3)

	@commands.command(hidden=True)
	@commands.has_permissions(administrator=True)
	async def drop_table_member_reminder(self, ctx) -> None:
		""" (ADM) Creates the MemberReminder table """

		if not await self.check_table_member_reminder():
			return await ctx.send("**Table __MemberReminder__ doesn't exist!**")

		await ctx.message.delete()
		mycursor, db = await the_database()
		await mycursor.execute("DROP TABLE MemberReminder")
		await db.commit()
		await mycursor.close()

		return await ctx.send("**Table __MemberReminder__ dropped!**", delete_after=3)

	@commands.command(hidden=True)
	@commands.has_permissions(administrator=True)
	async def reset_table_member_reminder(self, ctx) -> None:
		""" (ADM) Creates the MemberReminder table """

		if not await self.check_table_member_reminder():
			return await ctx.send("**Table __MemberReminder__ doesn't exist yet!**")

		await ctx.message.delete()
		mycursor, db = await the_database()
		await mycursor.execute("DELETE FROM MemberReminder")
		await db.commit()
		await mycursor.close()

		return await ctx.send("**Table __MemberReminder__ reset!**", delete_after=3)

	async def check_table_member_reminder(self) -> bool:
		""" Checks if the MemberReminder table exists """

		mycursor, db = await the_database()
		await mycursor.execute("SHOW TABLE STATUS LIKE 'MemberReminder'")
		table_info = await mycursor.fetchall()
		await mycursor.close()

		if len(table_info) == 0:
			return False

		else:
			return True

	async def get_due_reminders(self, current_ts: int) -> List[int]:
		""" Gets reminders that are due.. 
		:param current_ts: The current timestamp. """

		mycursor, db = await the_database()
		await mycursor.execute("SELECT * FROM MemberReminder WHERE (%s -  reminder_timestamp) >= remind_in", (current_ts,))
		reminders = [(m[0], m[1], m[2]) for m in await mycursor.fetchall()]
		await mycursor.close()
		return reminders


	async def insert_member_reminder(self, user_id: int, text: str, reminder_timestamp: int, remind_in: int) -> None:
		""" Inserts an entry concerning the user's last seen datetime.
		:param user_id: The ID of the user.
		:param text: The text that has to be reminded.
		:param reminder_timestamp: The current timestamp.
		:param remind_in: The amount of seconds to wait until reminding the user. """

		mycursor, db = await the_database()
		await mycursor.execute("""
		INSERT INTO MemberReminder (user_id, text, reminder_timestamp, remind_in) 
		VALUES (%s, %s, %s, %s)""", (user_id, text, reminder_timestamp, remind_in))
		await db.commit()
		await mycursor.close()

	async def delete_member_reminder(self, reminder_id: int) -> None:
		""" Updates the user's last seen datetime.
		:param reminder_id: The ID of the reminder to delete. """

		mycursor, db = await the_database()
		await mycursor.execute("DELETE FROM MemberReminder WHERE reminder_id = %s", (reminder_id,))
		await db.commit()
		await mycursor.close()

	async def get_member_reminders(self, user_id: int) -> List[List[Union[str, int]]]:
		""" Gets the user's reminders.
		:param user_id: The ID of the user. """

		mycursor, db = await the_database()
		await mycursor.execute("SELECT * FROM MemberReminder WHERE user_id = %s", (user_id,))
		reminders = await mycursor.fetchall()
		await mycursor.close()
		return reminders

	async def get_reminder(self, reminder_id: int) -> List[Union[str, int]]:
		""" Gets a reminder by ID.
		:param reminder_id: The reminder ID. """
		
		mycursor, db = await the_database()
		await mycursor.execute("SELECT * FROM MemberReminder WHERE reminder_id = %s", (reminder_id,))
		reminder = await mycursor.fetchone()
		await mycursor.close()
		return reminder


	@commands.command(aliases=['reminder', 'remind', 'remindme', 'set_reminder'])
	@commands.cooldown(1, 10, commands.BucketType.user)
	@check_whitelist()
	async def setreminder(self, ctx, text: str = None, *, time: str = None):
		""" Sets a reminder for the user.
		:param text: The descriptive text for the bot to remind you about.
		:param time: The amount of time to wait before reminding you.

		- Text Format: If it contains more than 1 word, put everything within " "
		- Time Format: 12s 34m 56h 78d (Order doesn't matter).

		Example:
		b!setreminder "do the dishes" 3m 65s
		= The bot will remind you in 4 minutes and 5 seconds.

		PS: Seconds may not be always reliable, since the bot checks reminders every minute. """

		member = ctx.author

		if not text:
			return await ctx.send(f"**Specify a text to remind you, {member.mention}**")

		if len(text) > 100:
			return await ctx.send(f"**Please, inform a text with a maximum of 100 characters, {member.mention}!**")

		if not time:
			return await ctx.send(f"**Inform a time, {member.mention}!**")

		time_dict, seconds = await self.client.get_cog('Moderation').get_mute_time(ctx=ctx, time=time)
		if not seconds:
			return

		reminders = await self.get_member_reminders(member.id)
		if len(reminders) >= 3: # User reached limit of reminders.
			return await ctx.send(
				f"**You reached the limit of reminders, wait for them to finish before trying again, {member.mention}!**")

		current_ts = await Misc.get_timestamp()
		await self.insert_member_reminder(member.id, text, current_ts, seconds)

		tzone = timezone('Etc/GMT')
		time_now = datetime.fromtimestamp(current_ts + seconds)
		date_and_time = time_now.astimezone(tzone)
		remind_at = date_and_time.strftime('%Y/%m/%d at %H:%M:%S')
		await ctx.send(f"**Reminding you at `{remind_at}`, {member.mention}!**")

	@commands.command(aliases=['show_reminders', 'showreminders', 'rmdrs', 'rs'])
	@commands.cooldown(1, 5, commands.BucketType.user)
	@check_whitelist()
	async def reminders(self, ctx) -> None:
		""" Shows reminders that you've set. """

		if not ctx.guild:
			return await ctx.send(f"**You can only see your reminders in the server!**")

		member = ctx.author

		if not (reminders := await self.get_member_reminders(member.id)):
			return await ctx.send(f"**You don't have any reminder set yet, {member.mention}!**")

		embed = discord.Embed(
			title="__Your Reminders__",
			color=member.color,
			timestamp=ctx.message.created_at
		)

		embed.set_author(name=member, url=member.avatar_url, icon_url=member.avatar_url)
		embed.set_thumbnail(url=member.avatar_url)
		embed.set_footer(text="Requested at:", icon_url=member.guild.icon_url)
		
		current_ts = await Misc.get_gmt_now()

		for reminder in reminders:	

			remind_at = datetime.fromtimestamp(reminder[3] + reminder[4])
			remind_at = remind_at.strftime('%Y-%m-%d at %H:%M:%S')

			embed.add_field(
				name=f"ID: {reminder[0]}", 
				value=f"**Text:** {reminder[2]}\n**Set to:** `{remind_at}`",
				inline=False)

		await ctx.send(embed=embed)


	@commands.command(aliases=["remove_reminder", "dr", "rr", "dontremind", "dont_remind"])
	@commands.cooldown(1, 5, commands.BucketType.user)
	@check_whitelist()
	async def delete_reminder(self, ctx, reminder_id: int = None) -> None:
		""" Deletes a member reminder.
		:param reminder_id: The ID of the reminder to delete. """

		member = ctx.author

		if not reminder_id:
			return await ctx.send(f"**Please, provide a reminder ID, {member.mention}!**")

		if not (reminder := await self.get_reminder(reminder_id)):
			return await ctx.send(f"**Reminder with ID `{reminder_id}` doesn't exist, {member.mention}!**")

		if reminder[1] != member.id:
			return await ctx.send(f"**You're not the owner of this reminder, {member.mention}!**")

		await self.delete_member_reminder(reminder_id)
		await ctx.send(f"**Successfully deleted reminder with ID `{reminder_id}`, {member.mention}!**")


	@commands.command(hidden=True)
	@commands.has_permissions(administrator=True)
	async def create_table_rules(self, ctx) -> None:
		""" (ADM) Creates the Rules table. """

		if await self.check_table_rules():
			return await ctx.send("**Table __Rules__ already exists!**")

		await ctx.message.delete()
		mycursor, db = await the_database()
		await mycursor.execute("""CREATE TABLE Rules (
			rule_number TINYINT(2) NOT NULL, 
			english_text VARCHAR(500) DEFAULT NULL, french_text VARCHAR(500) DEFAULT NULL)""")

		for i in range(15):
			await mycursor.execute("INSERT INTO Rules (rule_number) VALUES (%s)", (i+1,))

		await db.commit()
		await mycursor.close()

		return await ctx.send("**Table __Rules__ created!**", delete_after=3)

	@commands.command(hidden=True)
	@commands.has_permissions(administrator=True)
	async def drop_table_rules(self, ctx) -> None:
		""" (ADM) Creates the Rules table """

		if not await self.check_table_rules():
			return await ctx.send("**Table __Rules__ doesn't exist!**")

		await ctx.message.delete()
		mycursor, db = await the_database()
		await mycursor.execute("DROP TABLE Rules")
		await db.commit()
		await mycursor.close()

		return await ctx.send("**Table __Rules__ dropped!**", delete_after=3)

	@commands.command(hidden=True)
	@commands.has_permissions(administrator=True)
	async def reset_table_rules(self, ctx) -> None:
		""" (ADM) Creates the Rules table """

		if not await self.check_table_rules():
			return await ctx.send("**Table __Rules__ doesn't exist yet!**")

		await ctx.message.delete()
		mycursor, db = await the_database()
		await mycursor.execute("DELETE FROM Rules")
		await db.commit()
		await mycursor.close()

		return await ctx.send("**Table __Rules__ reset!**", delete_after=3)

	async def check_table_rules(self) -> bool:
		""" Checks if the Rules table exists """

		mycursor, db = await the_database()
		await mycursor.execute("SHOW TABLE STATUS LIKE 'Rules'")
		table_info = await mycursor.fetchall()
		await mycursor.close()

		if len(table_info) == 0:
			return False

		else:
			return True

	async def update_rule(self, rule_number: int, english_text: str = None, french_text: str = None) -> None:
		""" Updates a rule in the database.
		:param rule_number: The number of the rule (1-15).
		:param english_text: The rule text in English.
		:param french_text: The rule text in French. """

		mycursor, db = await the_database()
		if english_text and french_text:
			await mycursor.execute(
				"UPDATE Rules SET english_text = %s, french_text = %s WHERE rule_number = %s", (
					english_text, french_text, rule_number))

		elif english_text:
			await mycursor.execute("UPDATE Rules SET english_text = %s WHERE rule_number = %s", (english_text, rule_number))

		elif french_text:
			await mycursor.execute("UPDATE Rules SET french_text = %s WHERE rule_number = %s", (french_text, rule_number))
		await db.commit()
		await mycursor.close()

	async def get_rules(self) -> List[List[Union[int, str]]]:
		""" Get all rules from the database. """

		mycursor, db = await the_database()
		await mycursor.execute("SELECT * FROM Rules")
		rules = await mycursor.fetchall()
		await mycursor.close()
		return rules

	async def get_rule(self, rule_number: int) -> List[Union[int, str]]:
		""" Get a specific rule from the database.
		:param rule_number: The number of the rule. """

		mycursor, db = await the_database()
		await mycursor.execute("SELECT * FROM Rules WHERE rule_number = %s", (rule_number,))
		the_rule = await mycursor.fetchone()
		await mycursor.close()
		return the_rule

	@commands.command(aliases=['setrule', 'sr'])
	@commands.has_permissions(administrator=True)
	async def set_rule(self, ctx, rule_number: int, english_text: str = None, french_text: str = None) -> None:
		""" Sets a rule.
		:param rule_number: The rule number. (1-15)
		:param english_text: The text for that rule. (MAX = 500 chars.)
		:param french_text: The text for that rule. (MAX = 500 chars.) """

		member = ctx.author

		if not rule_number:
			return await ctx.send(f"**Please, inform a rule number, {member.mention}!**")

		if rule_number <= 0 or rule_number > 15:
			return await ctx.send(f"**Please, inform a rule number from 1-15, {member.mention}!**")

		if not english_text:
			return await ctx.send(f"**Please, inform a rule in english, {member.mention}!**")

		if len(english_text) > 500:
			return await ctx.send(f"**Please, inform an English text with a max. of 500 characters, {member.mention}!**")

		if not french_text:
			return await ctx.send(f"**Please, inform a rule in french, {member.mention}!**")

		if len(french_text) > 500:
			return await ctx.send(f"**Please, inform a French text with a max. of 500 characters, {member.mention}!**")

		
		await self.update_rule(rule_number=rule_number, english_text=english_text, french_text=french_text)
		await ctx.send(f"**Successfully updated rule number `{rule_number}`, {member.mention}!**")


	@commands.command(aliases=['updatefrenchrule', 'ufr'])
	@commands.has_permissions(administrator=True)
	async def update_french_rule(self, ctx, rule_number: int, french_text: str = None) -> None:
		""" Sets a rule.
		:param rule_number: The rule number. (1-15)
		:param french_text: The text for that rule. (MAX = 500 chars.) """

		member = ctx.author

		if not rule_number:
			return await ctx.send(f"**Please, inform a rule number, {member.mention}!**")

		if rule_number <= 0 or rule_number > 15:
			return await ctx.send(f"**Please, inform a rule number from 1-15, {member.mention}!**")

		if not french_text:
			return await ctx.send(f"**Please, inform a rule in French, {member.mention}!**")

		if len(french_text) > 500:
			return await ctx.send(f"**Please, inform a French text with a max. of 500 characters, {member.mention}!**")

		
		await self.update_rule(rule_number=rule_number, french_text=french_text)
		await ctx.send(f"**Successfully updated the French text for rule number `{rule_number}`, {member.mention}!**")


	@commands.command(aliases=['updateenglishrule', 'uer'])
	@commands.has_permissions(administrator=True)
	async def update_english_rule(self, ctx, rule_number: int, english_text: str = None) -> None:
		""" Sets a rule.
		:param rule_number: The rule number. (1-15)
		:param english_text: The text for that rule. (MAX = 500 chars.) """

		member = ctx.author

		if not rule_number:
			return await ctx.send(f"**Please, inform a rule number, {member.mention}!**")

		if rule_number <= 0 or rule_number > 15:
			return await ctx.send(f"**Please, inform a rule number from 1-15, {member.mention}!**")

		if not english_text:
			return await ctx.send(f"**Please, inform a rule in English, {member.mention}!**")

		if len(english_text) > 500:
			return await ctx.send(f"**Please, inform a English text with a max. of 500 characters, {member.mention}!**")

		await self.update_rule(rule_number=rule_number, english_text=english_text)
		await ctx.send(f"**Successfully updated the English text for rule number `{rule_number}`, {member.mention}!**")
	
"""
Setup:
b!create_table_server_status
b!create_table_user_timezones
b!create_table_emojis
b!create_table_last_seen
b!create_table_member_reminder

b!create_table_rules
"""


def setup(client) -> None:
	client.add_cog(Misc(client))