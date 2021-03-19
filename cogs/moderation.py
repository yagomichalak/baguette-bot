import discord
from discord.ext import commands, tasks
import asyncio
from mysqldb import the_database
from datetime import datetime
import time
from typing import List, Union
import os
from extra.banned_things import chat_filter, website_filter
from typing import List, Dict

mod_log_id = int(os.getenv('MOD_LOG_CHANNEL_ID'))
muted_role_id = int(os.getenv('MUTED_ROLE_ID'))
general_channel = int(os.getenv('GENERAL_CHANNEL_ID'))
last_deleted_message = []
mod_role_id = int(os.getenv('MOD_ROLE_ID'))
jr_mod_role_id = int(os.getenv('JR_MOD_ROLE_ID'))
trial_mod_role_id = int(os.getenv('TRIAL_MOD_ROLE_ID'))
admin_role_id = int(os.getenv('ADMIN_ROLE_ID'))
owner_role_id = int(os.getenv('OWNER_ROLE_ID'))
server_id = int(os.getenv('SERVER_ID'))
nsfw_channel_id = int(os.getenv('NSFW_CHANNEL_ID'))
staff_role_id = int(os.getenv('STAFF_ROLE_ID'))

allowed_roles = [owner_role_id, admin_role_id, mod_role_id, jr_mod_role_id, trial_mod_role_id]


class Moderation(commands.Cog):
	""" Category for moderation commands. """

	def __init__(self, client) -> None:
		self.client = client

		# Timestamp for user actions
		self.banned_words_cache = {}
		self.image_cache = {}
		self.message_cache = {}


	@commands.Cog.listener()
	async def on_ready(self) -> None:
		self.look_for_expired_tempmutes.start()
		print("Moderation cog is online!")


	@tasks.loop(minutes=1)
	async def look_for_expired_tempmutes(self) -> None:
		""" Looks for expired tempmutes and unmutes the users. """

		epoch = datetime.utcfromtimestamp(0)
		current_ts = (datetime.utcnow() - epoch).total_seconds()
		tempmutes = await self.get_expired_tempmutes(current_ts)

		guild = self.client.get_guild(server_id)

		for tm in tempmutes:
			member = discord.utils.get(guild.members, id=tm)
			if not member:
				continue

			try:
				role = discord.utils.get(guild.roles, id=muted_role_id)

				if role in member.roles:
					user_roles = await self.get_muted_roles(member.id)
					if user_roles:
						for mrole in user_roles:
							the_role = discord.utils.get(guild.roles, id=mrole[1])
							try:
								await member.add_roles(the_role, atomic=True)
								await self.remove_role_from_system(member.id, the_role.id)
							except Exception:
								pass
					await member.remove_roles(role)
					# Moderation log embed
					moderation_log = discord.utils.get(guild.channels, id=mod_log_id)
					embed = discord.Embed(
						description=F"**Unmuted** {member.mention}\n**Reason:** Tempmute is over",
						color=discord.Color.light_gray())
					embed.set_author(name=f"{self.client.user} (ID {self.client.user.id})", icon_url=self.client.user.avatar_url)
					embed.set_thumbnail(url=member.avatar_url)
					await moderation_log.send(embed=embed)
					try:
						await member.send(embed=embed)
					except:
						pass





			except:
				continue

	async def get_expired_tempmutes(self, current_ts: int) -> List[int]:
		""" Gets expired tempmutes. 
		:param current_ts: The current timestamp. """

		mycursor, db = await the_database()
		await mycursor.execute("SELECT DISTINCT(user_id) FROM MutedMember WHERE (%s -  mute_ts) >= muted_for_seconds", (current_ts,))
		tempmutes = list(map(lambda m: m[0], await mycursor.fetchall()))
		await mycursor.close()
		return tempmutes

	@commands.Cog.listener()
	async def on_member_join(self, member):
		if member.bot:
			return

		if await self.get_muted_roles(member.id):
			muted_role = discord.utils.get(member.guild.roles, id=muted_role_id)
			await member.add_roles(muted_role)
			# general = discord.utils.get(member.guild.channels, id=general_channel)
			await member.send(f"**{member.mention}, you were muted, left and rejoined the server, so you shall stay muted! 🔇**")
	

	# Chat filter
	@commands.Cog.listener()
	async def on_message(self, message):
		if not message.guild:
			return

		if message.author.bot:
			return

		perms = message.channel.permissions_for(message.author)
		if perms.administrator:
			return

		for role in message.author.roles:
			if role.id in allowed_roles:
				return

		ctx = await self.client.get_context(message)
		ctx.author = self.client.user

		# Checks banned words
		await self.check_cache_messages(ctx=ctx, message=message)
		
		# Checks banned websites
		await self.check_banned_websites(ctx=ctx, message=message)

		# Checks message spam
		await self.check_message_spam(ctx=ctx, message=message)

		# Checks image spam
		await self.check_image_spam(ctx=ctx, message=message)

		# Checks mass mention
		if len(message.mentions) >= 10:
			await message.delete()
			await self.warn(ctx=ctx, member=message.author, reason="Mass Mention")

		# Checks whether it's an invite
		if 'discord.gg/' in str(message.content).lower():
			await message.delete()
			return await message.author.send("**Please, stop sending invites! (Invite Advertisement)**")


	async def check_cache_messages(self, ctx: commands.Context, message: discord.Message) -> None:
		""" Checks the user who used a banned word. 
		:param member: The user that is gonna be added to cache. """

		if ctx.channel.id == nsfw_channel_id:
			return

		contents = message.content.split()
		for word in contents:
			if word.lower() in chat_filter:

				await message.delete()
				# await message.channel.send(f"**Watch your language, {message.author.mention}!**", delete_after=2)

				# Cache message
				timestamp = time.time()
				member = message.author

				if user_cache := self.banned_words_cache.get(member.id):
					user_cache.append(timestamp)
				else:
					self.banned_words_cache[member.id] = [timestamp]


				if len(user_cache := self.banned_words_cache.get(member.id)) >= 3:
					sub = user_cache[-1] - user_cache[-3]
					if sub <= 60:
						try:
							await message.author.send("**Excess of Banned Words, please stop!**")
						except:
							pass
						return
						# return await self.warn(ctx=ctx, member=member, reason="Excess of Banned Words")

	async def check_banned_websites(self, ctx: commands.Context, message: discord.Message) -> None:
		""" Checks whether the user posted a banned website link. 
		:param ctx: The ctx of the user message.
		:param message: The user message. """

		for msg in message.content.lower().split():
			if msg in website_filter:
				await message.delete()
				try:
					await message.author.send(ctx=ctx, member=message.author, reason="Banned Website Link")
				except:
					pass
				return


	async def check_message_spam(self, ctx: commands.Context, message: discord.Message) -> None:
		""" Checks whether it is a message spam. 
		:param ctx: The context of the message.
		:param message: The user message. """

		member = message.author
		timestamp = time.time()

		lmsg = len(message.content)

		if user_cache := self.message_cache.get(member.id):
			user_cache.append({'timestamp': timestamp, 'size': lmsg})
		else:
			self.message_cache[member.id] = [{'timestamp': timestamp, 'size': lmsg}]
			
		if len(user_cache := self.message_cache.get(member.id)) >= 10:
			sub = user_cache[-1]['timestamp'] - user_cache[-10]['timestamp']
			if sub <= 8:
				await message.delete()
				return await self.mute(ctx=ctx, member=member, reason="Message Spam")

		if lmsg >= 50:
			user_cache = self.message_cache.get(member.id)
			if len(self.message_cache[member.id]) >= 3:
				sub = user_cache[-1]['timestamp'] - user_cache[-3]['timestamp']
				if sub <= 10:
					if user_cache[-3]['size'] >= 50:
						await message.delete()
						return await self.mute(ctx=ctx, member=member, reason="Message Spam")

	async def check_image_spam(self, ctx: commands.Context, message: discord.Message) -> None:
		""" Checks whether it is an image spam. 
		:param ctx: The context of the message.
		:param message: The user message. """


		lenat = len(message.attachments)

		if lenat == 0:
			return

		member = message.author
		timestamp = time.time()

		if user_cache := self.image_cache.get(member.id):
			user_cache.append(timestamp)
		else:
			self.image_cache[member.id] = [timestamp] * len(message.attachments)


		if len(message.attachments) >= 5:
			await message.delete()
			return await self.warn(ctx=ctx, member=member, reason="Image Spam")


		if len(self.image_cache[member.id]) >= 10:
			sub = user_cache[-1] - user_cache[-10]
			if sub <= 60:
				await message.delete()
				return await self.warn(ctx=ctx, member=member, reason="Image Spam")

	@commands.Cog.listener()
	async def on_message_delete(self, message):
		if message.author.bot:
			return
		last_deleted_message.clear()
		last_deleted_message.append(message)


	@commands.command(aliases=['userinfo', 'whois'])
	# @commands.has_any_role(*[trial_mod_role_id, jr_mod_role_id, mod_role_id, admin_role_id, owner_role_id])
	async def user(self, ctx, member: discord.Member = None):
		'''
		Shows all the information about a member.
		:param member: The member to show the info.
		:return: An embedded message with the user's information
		'''
		member = ctx.author if not member else member
		roles = [role for role in member.roles]

		embed = discord.Embed(colour=member.color, timestamp=ctx.message.created_at)

		embed.set_author(name=f"User Info: {member}")
		embed.set_thumbnail(url=member.avatar_url)
		embed.set_footer(text=f"Requested by {ctx.author}", icon_url=ctx.author.avatar_url)

		embed.add_field(name="ID:", value=member.id, inline=False)
		embed.add_field(name="Server name:", value=member.display_name, inline=False)

		sorted_time_create = await self.sort_time(ctx.guild, member.created_at)
		sorted_time_join = await self.sort_time(ctx.guild, member.joined_at)

		embed.add_field(name="Created at:", value=f"{member.created_at.strftime('%d/%m/%y')} ({sorted_time_create})",
						inline=False)
		embed.add_field(name="Joined at:", value=f"{member.joined_at.strftime('%d/%m/%y')} ({sorted_time_join})", inline=False)

		embed.add_field(name="Top role:", value=member.top_role.mention, inline=False)

		await ctx.send(embed=embed)

	@commands.command(aliases=['si', 'server'])
	# @commands.has_any_role(*[trial_mod_role_id, jr_mod_role_id, mod_role_id, admin_role_id, owner_role_id])
	async def serverinfo(self, ctx):
		'''
		Shows some information about the server.
		'''
		await ctx.message.delete()
		guild = ctx.guild
		color = discord.Color.green()


		em = discord.Embed(description=guild.description, color=ctx.author.color)
		online = len({m.id for m in guild.members if m.status is not discord.Status.offline})
		em.add_field(name="Server ID", value=guild.id, inline=True)
		em.add_field(name="Owner", value=guild.owner.mention, inline=True)

		staff_role = discord.utils.get(guild.roles, id=staff_role_id)
		staff = ', '.join([m.mention for m in guild.members if staff_role in m.roles])
		em.add_field(name="Staff Members", value=staff, inline=False)
		em.add_field(name="Members", value=f"🟢 {online} members ⚫ {len(guild.members)} members", inline=False)
		em.add_field(name="Channels", value=f"⌨️ {len(guild.text_channels)} | 🔈 {len(guild.voice_channels)}", inline=True)
		em.add_field(name="Roles", value=len(guild.roles), inline=False)
		em.add_field(name="Emojis", value=len(guild.emojis), inline=True)
		em.add_field(name="🌐 Region", value=str(guild.region).title() if guild.region else None, inline=False)
		em.add_field(name="🔨 Bans", value=len(await guild.bans()), inline=False)
		em.add_field(name="🌟 Boosts", value=f"{guild.premium_subscription_count} (Level {guild.premium_tier})", inline=False)
		features = '\n'.join(list(map(lambda f: f.replace('_', ' ').capitalize(), guild.features)))
		em.add_field(name="Server Features", value=features if features else None, inline=False)


		em.set_thumbnail(url=None or guild.icon_url)
		em.set_image(url=guild.banner_url)
		em.set_author(name=guild.name, icon_url=None or guild.icon_url)
		created_at = await self.sort_time(guild, guild.created_at)
		em.set_footer(text=f"Created: {guild.created_at.strftime('%d/%m/%y')} ({created_at})")
		await ctx.send(embed=em)


	async def sort_time(self, guild: discord.Guild, at: datetime) -> str:

		member_age = (datetime.utcnow() - at).total_seconds()
		uage = {
			"years": 0,
			"months": 0,
			"days": 0,
			"hours": 0,
			"minutes": 0,
			"seconds": 0
		}

		text_list = []


		if (years := round(member_age / 31536000)) > 0:
			text_list.append(f"{years} years")
			member_age -= 31536000 * years
			# uage['years'] = years

		if (months := round(member_age / 2628288)) > 0:
			text_list.append(f"{months} months")
			member_age -= 2628288 * months
			# uage['months'] = months

		if not years and not months and (days := round(member_age / 86400)) > 0:
			text_list.append(f"{days} days")
			member_age -= 86400 * days
			# uage['days'] = days

		if not years and not months and not days and (hours := round(member_age / 3600)) > 0:
			text_list.append(f"{hours} hours")
			member_age -= 3600 * hours

			# uage['hours'] = hours

		if not years and not months and not days and not hours and (minutes := round(member_age / 60)) > 0:
			text_list.append(f"{minutes} minutes")
			member_age -= 60 * minutes
			# uage['minutes'] = minutes



		text = ' and '.join(text_list)
		text += ' ago'
		return text

	@commands.command()
	@commands.has_any_role(*[trial_mod_role_id, jr_mod_role_id, mod_role_id, admin_role_id, owner_role_id])
	async def snipe(self, ctx):
		'''
		(MOD) Snipes the last deleted message.
		'''
		message = last_deleted_message
		if message:
			message = message[0]
			embed = discord.Embed(title="Sniped", description=f"**>>** {message.content}", color=message.author.color, timestamp=message.created_at)
			embed.set_author(name=message.author,url=message.author.avatar_url, icon_url=message.author.avatar_url)
			await ctx.send(embed=embed)
		else:
			await ctx.send("**I couldn't snipe any messages!**")

	# Purge command
	@commands.command()
	@commands.has_any_role(*[jr_mod_role_id, mod_role_id, admin_role_id, owner_role_id])
	async def purge(self, ctx, amount=0, member: discord.Member = None):
		'''
		(MOD) Purges messages.
		:param amount: The amount of messages to purge.
		:param member: The member from whom to purge the messages. (Optional)
		'''

		perms = ctx.channel.permissions_for(ctx.author)
		if not perms.administrator:
			if amount > 30:
				return await ctx.send(f"**You cannot delete more than `30` messages at a time, {ctx.author.mention}!**")
		else:
			if amount > 200:
				return await ctx.send(f"**You cannot delete more than `200` messages at a time, {ctx.author.mention}!**")

		await ctx.message.delete()
		# global deleted
		deleted = 0
		if member:
			channel = ctx.channel
			msgs = list(filter(
				lambda m: m.author.id == member.id, 
				await channel.history(limit=200).flatten()
			))
			for _ in range(amount):
				await msgs.pop(0).delete()
				deleted += 1

			await ctx.send(f"**`{deleted}` messages deleted for `{member}`**",
				delete_after=5)
			
		else:
			await ctx.channel.purge(limit=amount)


	# Warns a member
	@commands.command()
	@commands.has_any_role(*[trial_mod_role_id, jr_mod_role_id, mod_role_id, admin_role_id, owner_role_id])
	async def warn(self, ctx, member: discord.Member = None, *, reason=None):
		'''
		(MOD) Warns a member.
		:param member: The @ or ID of the user to warn.
		:param reason: The reason for warning the user. (Optional)
		'''
		try:
			await ctx.message.delete()
		except Exception:
			pass

		if not member:
			await ctx.send("Please, specify a member!", delete_after=3)
		else:
			# # General embed
			general_embed = discord.Embed(description=f'**Reason:** {reason}', colour=discord.Colour.dark_gold())
			general_embed.set_author(name=f'{member} has been warned', icon_url=member.avatar_url)
			await ctx.send(embed=general_embed)
			# Moderation log embed
			moderation_log = discord.utils.get(ctx.guild.channels, id=mod_log_id)
			embed = discord.Embed(
				description=F"**Warned** {member.mention}\n**Reason:** {reason}\n**Location:** {ctx.channel.mention}",
				color=discord.Color.dark_gold(),
				timestamp=ctx.message.created_at)
			embed.set_author(name=f"{ctx.author} (ID {ctx.author.id})", icon_url=ctx.author.avatar_url)
			embed.set_thumbnail(url=member.avatar_url)
			await moderation_log.send(embed=embed)
			# Inserts a infraction into the database
			epoch = datetime.utcfromtimestamp(0)
			current_ts = (datetime.utcnow() - epoch).total_seconds()
			await self.insert_user_infraction(
				user_id=member.id, infr_type="warn", reason=reason,
				timestamp=current_ts , perpetrator=ctx.author.id)
			try:
				await member.send(embed=embed)
			except Exception as e:
				print(e)
				pass

			# user_infractions = await self.get_user_infractions(member.id)
			# user_warns = [w for w in user_infractions if w[1] == 'warn']
			# if len(user_warns) >= 3:
			# 	ctx.author = self.client.user
			# 	await self.mute(ctx=ctx, member=member, reason=reason)

	@commands.command()
	@commands.has_any_role(*[trial_mod_role_id, jr_mod_role_id, mod_role_id, admin_role_id, owner_role_id])
	async def mute(self, ctx, member: discord.Member = None, *, reason = None):
		'''
		(MOD) Mutes a member.
		:param member: The @ or the ID of the user to mute.
		:param reason: The reason for the mute.
		'''
		try:
			await ctx.message.delete()
		except:
			pass

		role = discord.utils.get(ctx.guild.roles, id=muted_role_id)
		if not member:
			return await ctx.send("**Please, specify a member!**")
		if role not in member.roles:
			await member.add_roles(role)
			await member.move_to(None)
			for mr in member.roles:
				if mr.id != role.id:
					try:
						await member.remove_roles(mr, atomic=True)
						await self.insert_in_muted(member.id, mr.id)
					except Exception:
						pass
			# General embed
			general_embed = discord.Embed(description=f'**Reason:** {reason}', colour=discord.Colour.dark_grey(), timestamp=ctx.message.created_at)
			general_embed.set_author(name=f'{member} has been muted', icon_url=member.avatar_url)
			await ctx.send(embed=general_embed)
			# Moderation log embed
			moderation_log = discord.utils.get(ctx.guild.channels, id=mod_log_id)
			embed = discord.Embed(
				description=F"**Muted** {member.mention}\n**Reason:** {reason}\n**Location:** {ctx.channel.mention}",
				color=discord.Color.dark_gray(),
				timestamp=ctx.message.created_at)
			embed.set_author(name=f"{ctx.author} (ID {ctx.author.id})", icon_url=ctx.author.avatar_url)
			embed.set_thumbnail(url=member.avatar_url)
			await moderation_log.send(embed=embed)
			# Inserts a infraction into the database
			epoch = datetime.utcfromtimestamp(0)
			current_ts = (datetime.utcnow() - epoch).total_seconds()
			await self.insert_user_infraction(
				user_id=member.id, infr_type="mute", reason=reason, 
				timestamp=current_ts , perpetrator=ctx.author.id)
			try:
				await member.send(embed=embed)
			except:
				pass
		
		else:
			await ctx.send(f'**{member} is already muted!**')


	async def get_mute_time(self, ctx: commands.Context, time: List[str]) -> Dict[str, int]:
		""" Gets the mute time in seconds.
		:param ctx: The context.
		:param time: The given time. """
		
		keys = ['d', 'h', 'm', 's']
		for k in keys:
			if k in time:
				break
		else:
			await ctx.send(f"**Inform a valid time, {ctx.author.mention}**", delete_after=3)
			return False

		the_time_dict = {
			'days': 0,
			'hours': 0,
			'minutes': 0,
			'seconds': 0,
		}

		seconds = 0

		for t in time.split():

			if (just_time := t[:-1]).isdigit():
				just_time = int(t[:-1])

			if 'd' in t and not the_time_dict.get('days'):

				seconds += just_time * 86400
				the_time_dict['days'] = just_time
				continue
			elif 'h' in t and not the_time_dict.get('hours'):
				seconds += just_time * 3600
				the_time_dict['hours'] = just_time
				continue
			elif 'm' in t and not the_time_dict.get('minutes'):
				seconds += just_time * 60
				the_time_dict['minutes'] = just_time
				continue
			elif 's' in t and not the_time_dict.get('seconds'):
				seconds += just_time
				the_time_dict['seconds'] = just_time
				continue

		if seconds <= 0:
			await ctx.send(f"**Something is wrong with it, {ctx.author.mention}!**", delete_after=3)
			return False, False
		else:
			return the_time_dict, seconds

	# Mutes a member temporarily
	@commands.command()
	@commands.has_any_role(*[trial_mod_role_id, jr_mod_role_id, mod_role_id, admin_role_id, owner_role_id])
	async def tempmute(self, ctx, member: discord.Member = None, reason: str =  None, *, time: str = None):
		"""
		Mutes a member for a determined amount of time.
		:param member: The @ or the ID of the user to tempmute.
		:param minutes: The amount of minutes that the user will be muted.
		:param reason: The reason for the tempmute.
		:param time: The time for the mute.
		"""
		await ctx.message.delete()

		role = discord.utils.get(ctx.guild.roles, id=muted_role_id)

		if not member:
			return await ctx.send("**Please, specify a member!**", delete_after=3)

		if not reason:
			return await ctx.send(f"**Specify a reason!**", delete_after=3)

		if not time:
			return await ctx.send('**Inform a time!**', delete_after=3)


		time_dict, seconds = await self.get_mute_time(ctx=ctx, time=time)
		if not seconds:
			return


		# print('ah')
		epoch = datetime.utcfromtimestamp(0)
		current_ts = int((datetime.utcnow() - epoch).total_seconds())

		# print(current_ts, seconds)

		if role not in member.roles:
			await member.add_roles(role)
			await member.move_to(None)
			for mr in member.roles:
				if mr.id != role.id:
					try:
						await member.remove_roles(mr, atomic=True)
						await self.insert_in_muted(member.id, mr.id, current_ts, seconds)
					except Exception:
						pass
			
			# General embed
			general_embed = discord.Embed(description=f"**For:** `{time_dict['days']}d` `{time_dict['hours']}h`, `{time_dict['minutes']}m`\n**Reason:** {reason}", colour=discord.Colour.dark_grey(), timestamp=ctx.message.created_at)
			general_embed.set_author(name=f"{member} has been tempmuted", icon_url=member.avatar_url)
			await ctx.send(embed=general_embed)
			# Moderation log embed
			moderation_log = discord.utils.get(ctx.guild.channels, id=mod_log_id)
			embed = discord.Embed(
				description=F"**Tempmuted** {member.mention} for `{time_dict['days']}d` `{time_dict['hours']}h`, `{time_dict['minutes']}m`\n**Reason:** {reason}\n**Location:** {ctx.channel.mention}",
				color=discord.Color.lighter_grey(),
				timestamp=ctx.message.created_at)
			embed.set_author(name=f"{ctx.author} (ID {ctx.author.id})", icon_url=ctx.author.avatar_url)
			embed.set_thumbnail(url=member.avatar_url)
			await moderation_log.send(embed=embed)
			# # Inserts a infraction into the database
			await self.insert_user_infraction(
				user_id=member.id, infr_type="mute", reason=reason, 
				timestamp=current_ts , perpetrator=ctx.author.id)
			try:
				await member.send(embed=general_embed)
			except:
				pass
		else:
			await ctx.send(f'**{member} is already muted!**', delete_after=5)

	# Unmutes a member
	@commands.command()
	@commands.has_any_role(*[trial_mod_role_id, jr_mod_role_id, mod_role_id, admin_role_id, owner_role_id])
	async def unmute(self, ctx, member: discord.Member = None, *, reason = None):
		'''
		(MOD) Unmutes a member.
		:param member: The @ or the ID of the user to unmute.
		'''
		await ctx.message.delete()
		role = discord.utils.get(ctx.guild.roles, id=muted_role_id)
		if not member:
			return await ctx.send("**Please, specify a member!**", delete_after=3)
		if role in member.roles:
			user_roles = await self.get_muted_roles(member.id)
			if user_roles:
				for mrole in user_roles:
					the_role = discord.utils.get(member.guild.roles, id=mrole[1])
					try:
						await member.add_roles(the_role, atomic=True)
						await self.remove_role_from_system(member.id, the_role.id)
					except Exception:
						pass
			await member.remove_roles(role)
			# General embed
			general_embed = discord.Embed(description=f'**Reason:** {reason}', colour=discord.Colour.light_gray(), timestamp=ctx.message.created_at)
			general_embed.set_author(name=f'{member} has been unmuted', icon_url=member.avatar_url)
			await ctx.send(embed=general_embed)
			# Moderation log embed
			moderation_log = discord.utils.get(ctx.guild.channels, id=mod_log_id)
			embed = discord.Embed(
				description=F"**Unmuted** {member.mention}\n**Reason:** {reason}\n**Location:** {ctx.channel.mention}",
				color=discord.Color.light_gray(),
				timestamp=ctx.message.created_at)
			embed.set_author(name=f"{ctx.author} (ID {ctx.author.id})", icon_url=ctx.author.avatar_url)
			embed.set_thumbnail(url=member.avatar_url)
			await moderation_log.send(embed=embed)
			try:
				await member.send(embed=embed)
			except:
				pass

		else:
			await ctx.send(f'**{member} is not even muted!**', delete_after=5)

	@commands.command()
	@commands.has_any_role(*[mod_role_id, admin_role_id, owner_role_id])
	async def kick(self, ctx, member: discord.Member = None, *, reason=None):
		'''
		(MOD) Kicks a member from the server.
		:param member: The @ or ID of the user to kick.
		:param reason: The reason for kicking the user. (Optional)
		'''
		await ctx.message.delete()
		if not member:
			await ctx.send('**Please, specify a member!**', delete_after=3)
		else:
			try:
				await member.kick(reason=reason)
			except Exception:
				await ctx.send('**You cannot do that!**', delete_after=3)
			else:
				# General embed
				general_embed = discord.Embed(description=f'**Reason:** {reason}', colour=discord.Colour.magenta())
				general_embed.set_author(name=f'{member} has been kicked', icon_url=member.avatar_url)
				await ctx.send(embed=general_embed)
				# Moderation log embed
				moderation_log = discord.utils.get(ctx.guild.channels, id=mod_log_id)
				embed = discord.Embed(
					description=F"**Kicked** {member.mention}\n**Reason:** {reason}\n**Location:** {ctx.channel.mention}",
					color=discord.Color.magenta(),
					timestamp=ctx.message.created_at)
				embed.set_author(name=f"{ctx.author} (ID {ctx.author.id})", icon_url=ctx.author.avatar_url)
				embed.set_thumbnail(url=member.avatar_url)
				await moderation_log.send(embed=embed)
				# Inserts a infraction into the database
				epoch = datetime.utcfromtimestamp(0)
				current_ts = (datetime.utcnow() - epoch).total_seconds()
				await self.insert_user_infraction(
					user_id=member.id, infr_type="kick", reason=reason, 
					timestamp=current_ts , perpetrator=ctx.author.id)
				try:
					await member.send(embed=general_embed)
				except:
					pass


	# Bans a member
	@commands.command()
	@commands.has_any_role(*[mod_role_id, admin_role_id, owner_role_id])
	async def ban(self, ctx, member: discord.Member = None, *, reason=None) -> None:
		""" Bans a member from the server.
		:param member: The @ or ID of the user to ban.
		:param reason: The reason for banning the user. (Optional) """

		await ctx.message.delete()
		if not member:
			return await ctx.send('**Please, specify a member!**', delete_after=3)


		channel = ctx.channel

		icon = ctx.author.avatar_url

		# Bans and logs
		try:
			await member.ban(delete_message_days=0, reason=reason)
		except Exception:
			await ctx.send('**You cannot do that!**', delete_after=3)
		else:
			# General embed
			general_embed = discord.Embed(description=f'**Reason:** {reason}', colour=discord.Colour.dark_red())
			general_embed.set_author(name=f'{member} has been banned', icon_url=member.avatar_url)
			await ctx.send(embed=general_embed)
			# Moderation log embed
			moderation_log = discord.utils.get(ctx.guild.channels, id=mod_log_id)
			embed = discord.Embed(
				description=F"**Banned** {member.mention}\n**Reason:** {reason}\n**Location:** {ctx.channel.mention}",
				color=discord.Color.dark_red(),
				timestamp=ctx.message.created_at)
			embed.set_author(name=f"{ctx.author} (ID {ctx.author.id})", icon_url=ctx.author.avatar_url)
			embed.set_thumbnail(url=member.avatar_url)
			await moderation_log.send(embed=embed)
			# Inserts a infraction into the database
			epoch = datetime.utcfromtimestamp(0)
			current_ts = (datetime.utcnow() - epoch).total_seconds()
			await self.insert_user_infraction(
				user_id=member.id, infr_type="ban", reason=reason, 
				timestamp=current_ts , perpetrator=ctx.author.id)
			try:
				await member.send(embed=general_embed)
			except:
				pass



	# Hardbans a member
	@commands.command()
	@commands.has_any_role(*[mod_role_id, admin_role_id, owner_role_id])
	async def hardban(self, ctx, member: discord.Member = None, *, reason=None) -> None:
		""" Hardbans a member from the server.
		=> Bans and delete messages from the last 7 days,
		:param member: The @ or ID of the user to ban.
		:param reason: The reason for banning the user. (Optional) """
		await ctx.message.delete()
		if not member:
			return await ctx.send('**Please, specify a member!**', delete_after=3)


		channel = ctx.channel

		icon = ctx.author.avatar_url

		# Bans and logs
		try:
			await member.ban(delete_message_days=1, reason=reason)
		except Exception:
			await ctx.send('**You cannot do that!**', delete_after=3)
		else:
			# General embed
			general_embed = discord.Embed(description=f'**Reason:** {reason}', colour=discord.Colour.dark_red())
			general_embed.set_author(name=f'{member} has been hardbanned', icon_url=member.avatar_url)
			await ctx.send(embed=general_embed)
			# Moderation log embed
			moderation_log = discord.utils.get(ctx.guild.channels, id=mod_log_id)
			embed = discord.Embed(
				description=F"**Hardbanned** {member.mention}\n**Reason:** {reason}\n**Location:** {ctx.channel.mention}",
				color=discord.Color.dark_red(),
				timestamp=ctx.message.created_at)
			embed.set_author(name=f"{ctx.author} (ID {ctx.author.id})", icon_url=ctx.author.avatar_url)
			embed.set_thumbnail(url=member.avatar_url)
			await moderation_log.send(embed=embed)
			# Inserts a infraction into the database
			epoch = datetime.utcfromtimestamp(0)
			current_ts = (datetime.utcnow() - epoch).total_seconds()
			await self.insert_user_infraction(
				user_id=member.id, infr_type="ban", reason=reason, 
				timestamp=current_ts , perpetrator=ctx.author.id)
			try:
				await member.send(embed=general_embed)
			except:
				pass

	# Unbans a member
	@commands.command()
	@commands.has_permissions(administrator=True)
	async def unban(self, ctx, *, member=None):
		'''
		(ADM) Unbans a member from the server.
		:param member: The full nickname and # of the user to unban.
		'''
		await ctx.message.delete()
		if not member:
			return await ctx.send('**Please, inform a member!**', delete_after=3)

		banned_users = await ctx.guild.bans()
		try:
			member_name, member_discriminator = str(member).split('#')
		except ValueError:
			return await ctx.send('**Wrong parameter!**', delete_after=3)

		for ban_entry in banned_users:
			user = ban_entry.user

			if (user.name, user.discriminator) == (member_name, member_discriminator):
				await ctx.guild.unban(user)
				# General embed
				general_embed = discord.Embed(colour=discord.Colour.red())
				general_embed.set_author(name=f'{user} has been unbanned', icon_url=user.avatar_url)
				await ctx.send(embed=general_embed)
				# Moderation log embed
				moderation_log = discord.utils.get(ctx.guild.channels, id=mod_log_id)
				embed = discord.Embed(
					description=F"**Unbanned** {user.display_name} (ID {user.id})\n**Location:** {ctx.channel.mention}",
					color=discord.Color.red(),
					timestamp=ctx.message.created_at)
				embed.set_author(name=f"{ctx.author} (ID {ctx.author.id})", icon_url=ctx.author.avatar_url)
				embed.set_thumbnail(url=user.avatar_url)
				await moderation_log.send(embed=embed)
				try:
					await user.send(embed=general_embed)
				except:
					pass
				return
		else:
			await ctx.send('**Member not found!**', delete_after=3)


	@commands.command()
	@commands.has_permissions(administrator=True)
	async def hackban(self, ctx, user_id: int = None, *, reason=None):
		"""
		(ADM) Bans a user that is currently not in the server.
		Only accepts user IDs.
		:param user_id: Member ID
		:param reason: The reason for hackbanning the user. (Optional)
		"""

		await ctx.message.delete()
		if not user_id:
			return await ctx.send("**Inform the user id!**", delete_after=3)
		member = discord.Object(id=user_id)
		if not member:
			return await ctx.send("**Invalid user id!**", delete_after=3)
		try:
			await ctx.guild.ban(member, reason=reason)
			# General embed
			general_embed = discord.Embed(description=f'**Reason:** {reason}', colour=discord.Colour.dark_teal(),
										  timestamp=ctx.message.created_at)
			general_embed.set_author(name=f'{self.client.get_user(user_id)} has been hackbanned')
			await ctx.send(embed=general_embed)

			# Moderation log embed
			moderation_log = discord.utils.get(ctx.guild.channels, id=mod_log_id)
			embed = discord.Embed(
				description=F"**Hackbanned** {self.client.get_user(user_id)} (ID {member.id})\n**Reason:** {reason}\n**Location:** {ctx.channel.mention}",
				color=discord.Color.dark_teal(),
				timestamp=ctx.message.created_at)
			embed.set_author(name=f"{ctx.author} (ID {ctx.author.id})", icon_url=ctx.author.avatar_url)
			await moderation_log.send(embed=embed)

			# Inserts a infraction into the database
			epoch = datetime.utcfromtimestamp(0)
			current_ts = (datetime.utcnow() - epoch).total_seconds()
			await self.insert_user_infraction(
				user_id=member.id, infr_type="hackban", reason=reason, 
				timestamp=current_ts , perpetrator=ctx.author.id)
			try:
				await member.send(embed=embed)
			except:
				pass

		except discord.errors.NotFound:
			return await ctx.send("**Invalid user id!**", delete_after=3)

	async def insert_in_muted(self, user_id: int, role_id: int, mute_ts: int = None, muted_for_seconds: int = None):
		mycursor, db = await the_database()
		await mycursor.execute("""
			INSERT INTO MutedMember (
			user_id, role_id, mute_ts, muted_for_seconds) VALUES (%s, %s, %s, %s)""", (user_id, role_id, mute_ts, muted_for_seconds)
		)
		await db.commit()
		await mycursor.close()

	async def get_muted_roles(self, user_id: int):
		mycursor, db = await the_database()
		await mycursor.execute("SELECT * FROM MutedMember WHERE user_id = %s", (user_id,))
		user_roles = await mycursor.fetchall()
		await mycursor.close()
		return user_roles

	async def remove_role_from_system(self, user_id: int, role_id: int):
		mycursor, db = await the_database()
		await mycursor.execute("DELETE FROM MutedMember WHERE user_id = %s AND role_id = %s", (user_id, role_id))
		await db.commit()
		await mycursor.close()


	@commands.command(hidden=True)
	@commands.has_permissions(administrator=True)
	async def create_table_mutedmember(self, ctx) -> None:
		""" (ADM) Creates the UserInfractions table. """

		if await self.check_table_mutedmember_exists():
			return await ctx.send("**Table __MutedMember__ already exists!**")
		
		await ctx.message.delete()
		mycursor, db = await the_database()
		await mycursor.execute("""CREATE TABLE MutedMember (
			user_id BIGINT NOT NULL, role_id BIGINT NOT NULL)""")
		await db.commit()
		await mycursor.close()

		return await ctx.send("**Table __MutedMember__ created!**", delete_after=3)

	@commands.command(hidden=True)
	@commands.has_permissions(administrator=True)
	async def drop_table_mutedmember(self, ctx) -> None:
		""" (ADM) Creates the UserInfractions table """
		if not await self.check_table_mutedmember_exists():
			return await ctx.send("**Table __MutedMember__ doesn't exist!**")
		await ctx.message.delete()
		mycursor, db = await the_database()
		await mycursor.execute("DROP TABLE MutedMember")
		await db.commit()
		await mycursor.close()

		return await ctx.send("**Table __MutedMember__ dropped!**", delete_after=3)

	@commands.command(hidden=True)
	@commands.has_permissions(administrator=True)
	async def reset_table_mutedmember(self, ctx):
		'''
		(ADM) Resets the MutedMember table.
		'''
		if not await self.check_table_mutedmember_exists():
			return await ctx.send("**Table __MutedMember__ doesn't exist yet**")

		await ctx.message.delete()
		mycursor, db = await the_database()
		await mycursor.execute("DELETE FROM MutedMember")
		await db.commit()
		await mycursor.close()

		return await ctx.send("**Table __MutedMember__ reset!**", delete_after=3)

	async def check_table_mutedmember_exists(self) -> bool:
		'''
		Checks if the MutedMember table exists
		'''
		mycursor, db = await the_database()
		await mycursor.execute("SHOW TABLE STATUS LIKE 'MutedMember'")
		table_info = await mycursor.fetchall()
		await mycursor.close()

		if len(table_info) == 0:
			return False

		else:
			return True
		

	# Infraction methods
	@commands.command(aliases=['infr', 'show_warnings', 'sw', 'show_bans', 'sb', 'show_muted', 'sm', 'punishements'])
	@commands.has_any_role(*[trial_mod_role_id, jr_mod_role_id, mod_role_id, admin_role_id, owner_role_id])
	async def infractions(self, ctx, member: discord.Member = None) -> None:
		'''
		Shows all infractions of a specific user.
		:param member: The member to show the infractions from.
		'''
		if not member:
			return await ctx.send("**Inform a member!**")
		
		# Try to get user infractions
		if user_infractions := await self.get_user_infractions(member.id):
			warns = len([w for w in user_infractions if w[1] == 'warn'])
			mutes = len([m for m in user_infractions if m[1] == 'mute'])
			kicks = len([k for k in user_infractions if k[1] == 'kick'])
			bans = len([b for b in user_infractions if b[1] == 'ban'])
			hackbans = len([hb for hb in user_infractions if hb[1] == 'hackban'])
		else:
			return await ctx.send(f"**{member.mention} doesn't have any existent infractions!**")

		# Makes the initial embed with their amount of infractions
		embed = discord.Embed(
			title=f"Infractions for {member}",
			# description=f"Warns: {warns} | Mutes: {mutes} | Kicks: {kicks} | Bans: {bans} | Hackbans: {hackbans}",
			color=member.color,
			timestamp=ctx.message.created_at)
		embed.set_thumbnail(url=member.avatar_url)
		embed.set_footer(text=f"Warns: {warns} | Mutes: {mutes} | Kicks: {kicks} | Bans: {bans} | Hackbans: {hackbans}", icon_url=ctx.author.avatar_url)

		# Loops through each infraction and adds a field to the embedded message
		## 0-user_id, 1-infraction_type, 2-infraction_reason, 3-infraction_ts, 4-infraction_id, 5-perpetrator
		for infr in user_infractions:
			# if (infr_type := infr[1]) in ['mute', 'warn']:
			infr_date = datetime.fromtimestamp(infr[3]).strftime('%Y/%m/%d at %H:%M:%S')
			perpetrator = discord.utils.get(ctx.guild.members, id=infr[5])
			embed.add_field(
				name=f"__**{infr[1]} ID: {infr[4]}**__", 
				value=f"**Given on:** {infr_date}\n**By:** {perpetrator}\n**Reason:** {infr[2]}",
				inline=False)

		# Shows the infractions
		await ctx.send(embed=embed)

	# Database methods

	async def insert_user_infraction(self, user_id: int, infr_type: str, reason: str, timestamp: int, perpetrator: int) -> None:
		""" Insert a warning into the system. """

		mycursor, db = await the_database()
		await mycursor.execute("""
			INSERT INTO UserInfractions (
			user_id, infraction_type, infraction_reason,
			infraction_ts, perpetrator)
			VALUES (%s, %s, %s, %s, %s)""",
			(user_id, infr_type, reason, timestamp, perpetrator))
		await db.commit()
		await mycursor.close()


	async def get_user_infractions(self, user_id: int) -> List[List[Union[str, int]]]:
		""" Gets all infractions from a user. """

		mycursor, db = await the_database()
		await mycursor.execute("SELECT * FROM UserInfractions WHERE user_id = %s", (user_id,))
		user_infractions = await mycursor.fetchall()
		await mycursor.close()
		return user_infractions


	async def get_user_infraction_by_infraction_id(self, infraction_id: int) -> List[List[Union[str, int]]]:
		""" Gets a specific infraction by ID. """

		mycursor, db = await the_database()
		await mycursor.execute("SELECT * FROM UserInfractions WHERE infraction_id = %s", (infraction_id,))
		user_infractions = await mycursor.fetchall()
		await mycursor.close()
		return user_infractions

	async def remove_user_infraction(self, infraction_id: int) -> None:
		""" Removes a specific infraction by ID. """

		mycursor, db = await the_database()
		await mycursor.execute("DELETE FROM UserInfractions WHERE infraction_id = %s", (infraction_id,))
		await db.commit()
		await mycursor.close()

	async def remove_user_infractions(self, user_id: int) -> None:
		""" Removes all infractions of a user by ID. """

		mycursor, db = await the_database()
		await mycursor.execute("DELETE FROM UserInfractions WHERE user_id = %s", (user_id,))
		await db.commit()
		await mycursor.close()

	@commands.command(aliases=['ri', 'remove_warn', 'remove_warning'])
	@commands.has_permissions(administrator=True)
	async def remove_infraction(self, ctx, infr_id: int = None):
		"""
		(MOD) Removes a specific infraction by ID.
		:param infr_id: The infraction ID.
		"""

		if not infr_id:
			return await ctx.send("**Inform the infraction ID!**")

		if user_infractions := await self.get_user_infraction_by_infraction_id(infr_id):
			await self.remove_user_infraction(infr_id)
			member = discord.utils.get(ctx.guild.members, id=user_infractions[0][0])
			await ctx.send(f"**Removed infraction with ID `{infr_id}` for {member}**")
		else:
			await ctx.send(f"**Infraction with ID `{infr_id}` was not found!**")

	@commands.command(aliases=['ris', 'remove_warns', 'remove_warnings'])
	@commands.has_permissions(administrator=True)
	async def remove_infractions(self, ctx, member: discord.Member = None):
		"""
		(MOD) Removes all infractions for a specific user.
		:param member: The member to get the warns from.
		"""

		if not member:
			return await ctx.send("**Inform a member!**")
		
		if user_infractions := await self.get_user_infractions(member.id):
			await self.remove_user_infractions(member.id)
			await ctx.send(f"**Removed all infractions for {member.mention}!**")
		else:
			await ctx.send(f"**{member.mention} doesn't have any existent infractions!**")

	@commands.command(hidden=True)
	@commands.has_permissions(administrator=True)
	async def create_table_user_infractions(self, ctx) -> None:
		""" (ADM) Creates the UserInfractions table. """

		if await self.check_table_user_infractions():
			return await ctx.send("**Table __UserInfractions__ already exists!**")
		
		await ctx.message.delete()
		mycursor, db = await the_database()
		await mycursor.execute("""CREATE TABLE UserInfractions (
			user_id BIGINT NOT NULL, 
			infraction_type VARCHAR(7) NOT NULL, 
			infraction_reason VARCHAR(250) DEFAULT NULL, 
			infraction_ts BIGINT NOT NULL, 
			infraction_id BIGINT NOT NULL AUTO_INCREMENT, 
			perpetrator BIGINT NOT NULL, 
			PRIMARY KEY(infraction_id)
			)""")
		await db.commit()
		await mycursor.close()

		return await ctx.send("**Table __UserInfractions__ created!**", delete_after=3)

	@commands.command(hidden=True)
	@commands.has_permissions(administrator=True)
	async def drop_table_user_infractions(self, ctx) -> None:
		""" (ADM) Creates the UserInfractions table """
		if not await self.check_table_user_infractions():
			return await ctx.send("**Table __UserInfractions__ doesn't exist!**")
		await ctx.message.delete()
		mycursor, db = await the_database()
		await mycursor.execute("DROP TABLE UserInfractions")
		await db.commit()
		await mycursor.close()

		return await ctx.send("**Table __UserInfractions__ dropped!**", delete_after=3)

	@commands.command(hidden=True)
	@commands.has_permissions(administrator=True)
	async def reset_table_user_infractions(self, ctx) -> None:
		""" (ADM) Creates the UserInfractions table """

		if not await self.check_table_user_infractions():
			return await ctx.send("**Table __UserInfractions__ doesn't exist yet!**")

		await ctx.message.delete()
		mycursor, db = await the_database()
		await mycursor.execute("DELETE FROM UserInfractions")
		await db.commit()
		await mycursor.close()

		return await ctx.send("**Table __UserInfractions__ reset!**", delete_after=3)

	async def check_table_user_infractions(self) -> bool:
		""" Checks if the UserInfractions table exists """

		mycursor, db = await the_database()
		await mycursor.execute("SHOW TABLE STATUS LIKE 'UserInfractions'")
		table_info = await mycursor.fetchall()
		await mycursor.close()

		if len(table_info) == 0:
			return False

		else:
			return True


	@commands.command()
	@commands.has_permissions(administrator=True)
	async def lockdown(self, ctx, channel: discord.TextChannel = None) -> None:
		""" Locksdown a channel. """

		if not ctx.guild:
			return await ctx.send("**It won't work here!**")

		channel = channel or ctx.channel


		embed = discord.Embed(
			description=f"**{channel.mention} is now on lockdown! 🔒**",
			color=discord.Color.red()
		)


		if ctx.guild.default_role not in channel.overwrites:
			overwrites = {
				ctx.guild.default_role: discord.PermissionOverwrite(send_messages=False)
			}
			await channel.edit(overwrites=overwrites)
			await ctx.send(embed=embed)

		elif channel.overwrites[ctx.guild.default_role].send_messages == True or channel.overwrites[ctx.guild.default_role].send_messages == None:
			overwrites = channel.overwrites[ctx.guild.default_role]
			overwrites.send_messages = False

			await channel.set_permissions(ctx.guild.default_role, overwrite=overwrites)
			await ctx.send(embed=embed)

		else:
			overwrites = channel.overwrites[ctx.guild.default_role]
			overwrites.send_messages = True
			await channel.set_permissions(ctx.guild.default_role, overwrite=overwrites)
			embed.description = f"**{channel.mention} is no longer on lockdown! 🔓**"
			embed.color = discord.Color.green()
			await ctx.send(embed=embed)
		

def setup(client) -> None:
	client.add_cog(Moderation(client))