import discord
from discord.ext import commands, tasks
import asyncio
from datetime import datetime
import os
import pytz
from pytz import timezone

class Misc(commands.Cog):

	def __init__(self, client) -> None:
		self.client = client


	@commands.Cog.listener()
	async def on_ready(self) -> None:
		self.server_status.start()
		print('Misc cog is online')


	@tasks.loop(minutes=1)
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
	# @commands.cooldown(1, 5, commands.BucketType.user)
	async def time(self, ctx: commands.Context, time: str = None, my_timezone: str = None) -> None:
		""" Tells the time in a given timezone, and compares to the CET one.
		:param time: The time you want to check. Ex: 7pm
		:param my_timezone: The time zone to convert """

		member = ctx.author

		if not time:
			return await ctx.send(f"**Now it's `{datetime.now(timezone('Etc/GMT')).strftime('%H:%M Etc/GMT')}`, {member.mention}**")

		if not my_timezone:
			return await ctx.send(f"**Please, inform a `my_timezone`, {member.mention}!**")

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
		GMT = timezone('Etc/GMT')

		date_to_utc = converted_time.astimezone(GMT).strftime('%H:%M')
		datetime_text = f"**`{converted_time.strftime('%H:%M')} ({given_timezone})` = `{date_to_utc} ({GMT})`**"
		await ctx.send(datetime_text)



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

def setup(client) -> None:
	client.add_cog(Misc(client))