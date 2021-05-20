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



class Misc(commands.Cog):
	""" A miscellaneous category. """

	def __init__(self, client) -> None:
		self.client = client


	@commands.Cog.listener()
	async def on_ready(self) -> None:
		self.server_status.start()
		self.check_server_activity_status.start()
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

		if boosts_channel := guild.get_channel(int(os.getenv('BOOSTS_CHANNEL_ID'))):
			await boosts_channel.edit(name=f"Boosts: {guild.premium_subscription_count}")


	@commands.command()
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
		# print(f"Given date: {given_date.strftime('%H:%M')}")

		# Convert given date to given timezone
		tz = pytz.timezone(given_timezone)
		converted_time = datetime.now(tz=tz)
		converted_time = converted_time.replace(hour=given_date.hour, minute=given_date.minute)
		# print(f"Given date formated to given timezone: {converted_time.strftime('%H:%M')}")

		# Converting date to GMT (Etc/GMT-1)
		GMT = timezone(default_timezone)

		date_to_utc = converted_time.astimezone(GMT).strftime('%H:%M')
		datetime_text = f"**`{converted_time.strftime('%H:%M')} ({given_timezone})` = `{date_to_utc} ({GMT})`**"
		await ctx.send(datetime_text)

	@commands.command()
	@commands.cooldown(1, 300, commands.BucketType.user)
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


	# async def sort_time(self, guild: discord.Guild, at: datetime) -> str:

	# 	member_age = (datetime.utcnow() - at).total_seconds()
	# 	uage = {
	# 		"years": 0,
	# 		"months": 0,
	# 		"days": 0,
	# 		"hours": 0,
	# 		"minutes": 0,
	# 		"seconds": 0
	# 	}

	# 	text_list = []


	# 	if (years := round(member_age / 31536000)) > 0:
	# 		text_list.append(f"{years} years")
	# 		member_age -= 31536000 * years
	# 		# uage['years'] = years

	# 	if (months := round(member_age / 2628288)) > 0:
	# 		text_list.append(f"{months} months")
	# 		member_age -= 2628288 * months
	# 		# uage['months'] = months


	# 	text = ' and '.join(text_list)
	# 	text += ' ago'
	# 	return text


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
	async def get_timestamp() -> int:
		""" Gets the current timestamp. """

		epoch = datetime.utcfromtimestamp(0)
		the_time = (datetime.utcnow() - epoch).total_seconds()
		return the_time		

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
	async def emb(self, ctx):
		'''
		(MOD) Sends an embedded message.
		'''
		await ctx.message.delete()
		if len(ctx.message.content.split()) < 2:
			return await ctx.send('You must inform all parameters!')

		msg = ctx.message.content.split('!emb', 1)
		embed = discord.Embed(description=msg[1], colour=discord.Colour.dark_green())
		await ctx.send(embed=embed)


"""
Setup:
b!create_table_server_status
b!create_table_user_timezones
"""


def setup(client) -> None:
	client.add_cog(Misc(client))