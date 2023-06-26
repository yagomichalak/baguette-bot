from pytz import timezone
import discord
from discord.ext import commands, tasks
from mysqldb import the_database
from datetime import datetime
import time
from typing import List, Union
import os

from extra.banned_things import chat_filter, website_filter
from extra.menu import Confirm
from extra.prompt.menu import ConfirmButton
from extra import utils

from extra.moderation.firewall import ModerationFirewallTable
from extra.moderation.muted_member import MutedMemberTable
from extra.moderation.tempbanned_member import TempbannedMemberTable
from extra.moderation.staff_member import StaffMemberTable
from extra.moderation.user_infractions import UserInfractionsTable

from typing import List, Dict, Tuple, Optional
import re
import emoji
from cogs.misc import Misc

# IDs
server_id = int(os.getenv('SERVER_ID'))

mod_log_id = int(os.getenv('MOD_LOG_CHANNEL_ID'))
nsfw_channel_id = int(os.getenv('NSFW_CHANNEL_ID'))
general_channel = int(os.getenv('GENERAL_CHANNEL_ID'))

muted_role_id = int(os.getenv('MUTED_ROLE_ID'))
banned_role_id = int(os.getenv('BANNED_ROLE_ID'))

last_deleted_message = []

mod_role_id = int(os.getenv('MOD_ROLE_ID'))
jr_mod_role_id = int(os.getenv('JR_MOD_ROLE_ID'))
trial_mod_role_id = int(os.getenv('TRIAL_MOD_ROLE_ID'))
admin_role_id = int(os.getenv('ADMIN_ROLE_ID'))
owner_role_id = int(os.getenv('OWNER_ROLE_ID'))
staff_role_id = int(os.getenv('STAFF_ROLE_ID'))
member_dot_role_id = int(os.getenv('MEMBER_DOT_ROLE_ID'))
teacher_role_id: int = int(os.getenv("TEACHER_ROLE_ID"))
organizer_role_id: int = int(os.getenv("ORGANIZER_ROLE_ID"))

allowed_roles = [owner_role_id, admin_role_id, mod_role_id, jr_mod_role_id, trial_mod_role_id]

moderation_cogs: List[commands.Cog] = [
	ModerationFirewallTable, MutedMemberTable, TempbannedMemberTable,
	StaffMemberTable, UserInfractionsTable,
]

class Moderation(*moderation_cogs):
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
		self.look_for_expired_tempbans.start()
		self.look_for_monthly_infractions_record_reset.start()
		print("Moderation cog is online!")

	@tasks.loop(minutes=1)
	async def look_for_expired_tempmutes(self) -> None:
		""" Looks for expired tempmutes and unmutes the users. """

		current_ts = await utils.get_timestamp()
		tempmutes = await self.get_expired_tempmutes(current_ts)
		guild = self.client.get_guild(server_id)

		for tm in tempmutes:
			member = discord.utils.get(guild.members, id=tm)
			if not member:
				continue

			try:
				role = discord.utils.get(guild.roles, id=muted_role_id)
				if role:
					if user_roles := await self.get_muted_roles(member.id):

						bot = discord.utils.get(guild.members, id=self.client.user.id)

						member_roles = list([
							a_role for the_role in user_roles if (a_role := discord.utils.get(guild.roles, id=the_role[1]))
							and a_role < bot.top_role
						])
						member_roles.extend(member.roles)

						member_roles = list(set(member_roles))
						if role in member_roles:
							member_roles.remove(role)

						await member.edit(roles=member_roles)
						try:
							await self.remove_all_roles_from_system(member.id)
						except Exception as e:
							print(e)
							pass

						else:
							# Moderation log embed
							moderation_log = discord.utils.get(guild.channels, id=mod_log_id)
							embed = discord.Embed(
								description=F"**Unmuted** {member.mention}\n**Reason:** Tempmute is over",
								color=discord.Color.light_gray())
							embed.set_author(name=f"{self.client.user} (ID {self.client.user.id})", icon_url=self.client.user.display_avatar)
							embed.set_thumbnail(url=member.display_avatar)
							await moderation_log.send(embed=embed)
							try:
								await member.send(embed=embed)
							except:
								pass

			except Exception as e:
				continue

	@tasks.loop(minutes=1)
	async def look_for_expired_tempbans(self) -> None:
		""" Looks for expired tempbans and unmutes the users. """

		current_ts = await utils.get_timestamp()
		tempbans = await self.get_expired_tempbans(current_ts)
		guild = self.client.get_guild(server_id)

		for tb in tempbans:
			member = discord.utils.get(guild.members, id=tb)
			if not member:
				continue

			try:
				role = discord.utils.get(guild.roles, id=banned_role_id)
				if role:
					if user_roles := await self.get_tempbanned_roles(member.id):

						bot = discord.utils.get(guild.members, id=self.client.user.id)

						member_roles = list([
							a_role for the_role in user_roles if (a_role := discord.utils.get(guild.roles, id=the_role[1]))
							and a_role < bot.top_role
						])
						member_roles.extend(member.roles)

						member_roles = list(set(member_roles))
						if role in member_roles:
							member_roles.remove(role)

						await member.edit(roles=member_roles)
						try:
							await self.remove_all_tempbanned_roles_from_system(member.id)
						except Exception as e:
							print(e)
							pass

						else:

							# Moderation log embed
							moderation_log = discord.utils.get(guild.channels, id=mod_log_id)
							embed = discord.Embed(
								description=F"**Untempbanned** {member.mention}\n**Reason:** Tempban is over",
								color=discord.Color.purple())
							embed.set_author(name=f"{self.client.user} (ID {self.client.user.id})", icon_url=self.client.user.display_avatar)
							embed.set_thumbnail(url=member.display_avatar)
							await moderation_log.send(embed=embed)
							try:
								await member.send(embed=embed)
							except:
								pass

			except Exception as e:
				continue

	@tasks.loop(minutes=1)
	async def look_for_monthly_infractions_record_reset(self):
		""" Resets monthly record of infractions given by Staff members, and adds it to the total amount. """

		LevelSystem = self.client.get_cog('LevelSystem')
		if not await LevelSystem.table_important_vars_exists():
			return

		tzone = timezone('Etc/GMT')
		month_today = datetime.now(tzone).month
		# Creates the Total-Infractions counter if it doesn't exist
		if not await LevelSystem.get_important_var(label="t_infractions"):
			await LevelSystem.insert_important_var(label="t_infractions", value_int=0)

		# Creates, updates and increments Monthly and Total Infractions counter respectively
		if (this_month := await LevelSystem.get_important_var(label="m_infractions")) is None:
			await LevelSystem.insert_important_var(label="m_infractions", value_int=0, value_str=str(month_today))
		elif this_month[1] != str(month_today):
			await LevelSystem.increment_important_var_int(label="t_infractions", increment=this_month[2])
			await LevelSystem.update_important_var(label="m_infractions", value_int=0, value_str=str(month_today))

	@commands.Cog.listener()
	async def on_member_join(self, member):
		if member.bot:
			return

		if await self.get_muted_roles(member.id):
			muted_role = discord.utils.get(member.guild.roles, id=muted_role_id)
			await member.add_roles(muted_role)
			# general = discord.utils.get(member.guild.channels, id=general_channel)
			await member.send(f"**{member.mention}, you were muted, left and rejoined the server, so you shall stay muted! 🔇**")
	
	@commands.Cog.listener()
	async def on_member_update(self, before, after):
		""" Checks whether the user got the Staff role. """

		if not after.guild:
			return

		# Get roles from now and then
		roles = before.roles
		roles2 = after.roles
		if len(roles2) < len(roles):
			return

		new_role = None

		for r2 in roles2:
			if r2 not in roles:
				new_role = r2
				break

		if new_role:
			# Checks ID of the new role and compares to the Staff role ID.
			if new_role.id == staff_role_id:
				if not await self.get_staff_member(after.id):
					staff_at = await utils.get_time()
					staff_at = staff_at.strftime('%Y/%m/%d at %H:%M:%S')
					# Creates a new Staff member entry in the database.
					await self.insert_staff_member(user_id=after.id, infractions_given=0, staff_at=staff_at)

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
		# await self.check_image_spam(ctx=ctx, message=message)

		# Checks mass mention
		if len(message.mentions) >= 10:
			await message.delete()
			await self.warn(context=ctx, member=message.author, reason="Mass Mention")

		# Invite tracker
		msg = str(message.content)
		if ('discord.gg/' in msg.lower() and '?event=' not in msg.lower()
			) or ('discord.com/invite/' in msg.lower() and '?event=' not in msg.lower()):
			invite_root = 'discord.gg/' if 'discord.gg/' in msg.lower() else 'discord.com/invite/'
			ctx = await self.client.get_context(message)
			if not await utils.is_allowed([*allowed_roles, organizer_role_id, teacher_role_id]).predicate(ctx):
				
				is_from_guild = await self.check_invite_guild(msg, message.guild, invite_root)

				if not is_from_guild:
					await message.delete()
					return await message.author.send("**Please, stop sending invites! (Invite Advertisement)**")
		
		if 'discord.com/events/' in msg.lower() or ('discord.gg/' in msg.lower() and '?event=' in msg.lower()):
			invite_root = 'discord.gg/' if 'discord.gg/' in msg.lower() else 'discord.com/events/'
			ctx = await self.client.get_context(message)
			if not await utils.is_allowed([*allowed_roles, organizer_role_id, teacher_role_id]).predicate(ctx):
				is_from_guild = await self.check_event_invite_guild(msg, message.guild, invite_root)

				if not is_from_guild:
					await message.delete()
					return await message.author.send("**Please, stop sending invites! (Invite Advertisement)**")

	async def check_invite_guild(self, msg, guild, invite_root: str):
		""" Checks whether it's a guild invite or not. """

		start_index = msg.index(invite_root)
		end_index = start_index + len(invite_root)
		invite_hash = ''
		for c in msg[end_index:]:
			if c == ' ':
				break

			invite_hash += c
		inv_code = discord.utils.resolve_invite(invite_root + invite_hash)
		guild_inv = discord.utils.get(await guild.invites(), code=inv_code)

		for char in ['!', '@', '.', '(', ')', '[', ']', '#', '?', ':', ';', '`', '"', "'", ',', '{', '}']:
			invite_hash = invite_hash.replace(char, '')
		invite = invite_root + invite_hash
		inv_code = discord.utils.resolve_invite(invite)
		if inv_code == 'lesalonfrancais':
			return True

		if inv_code in []:
			return True

		guild_inv = discord.utils.get(await guild.invites(), code=inv_code)
		if guild_inv:
			return True
		else:
			return False

	async def check_event_invite_guild(self, msg, guild, invite_root: str):
		""" Checks whether it's a guild invite or not. """

		start_index = msg.index(invite_root)
		end_index = start_index + len(invite_root)
		invite_hash = ''
		for c in msg[end_index:]:
			if c == ' ':
				break

			invite_hash += c
		is_from_guild: bool = False

		# Checks the event invite link pattern
		if invite_root == 'discord.gg/':
			event_id = int(invite_hash.split('?event=')[1])
			event = guild.get_scheduled_event(event_id)
			is_from_guild = False if not event else event.guild.id == guild.id
		else:
			event_guild_id = int(invite_hash.split('/')[0])
			is_from_guild = event_guild_id == guild.id
			
		# Checks whether the event invite is from the server
		if is_from_guild:
			return True
		else:
			return False

	async def check_cache_messages(self, ctx: commands.Context, message: discord.Message) -> None:
		""" Checks the user who used a banned word. 
		:param member: The user that is gonna be added to cache. """

		if ctx.channel.id == nsfw_channel_id:
			return

		contents = message.content.split()
		for word in contents:
			if word.lower() in chat_filter:
				await message.delete()

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

	async def check_banned_websites(self, ctx: commands.Context, message: discord.Message) -> None:
		""" Checks whether the user posted a banned website link. 
		:param ctx: The ctx of the user message.
		:param message: The user message. """

		for msg in message.content.lower().split():
			if msg in website_filter:
				await message.delete()
				try:
					await message.author.send("**Banned Website Link, please stop!**")
				except:
					pass
				return

	async def check_message_spam(self, ctx: commands.Context, message: discord.Message) -> None:
		""" Checks whether it is a message spam. 
		:param ctx: The context of the message.
		:param message: The user message. """

		member = message.author
		timestamp = time.time()

		# Substracts the amount of emojis from the length of the message
		lmsg = len(message.content)
		text_de= emoji.demojize(message.content)
		emojis_list_de= re.findall(r'(<[a]?:[!_\-\w]+:\d[^>][0-9].{,18}>)', text_de)
		lmsg -= len(''.join(emojis_list_de)) - len(emojis_list_de)

		if user_cache := self.message_cache.get(member.id):
			user_cache.append({'timestamp': timestamp, 'size': lmsg})
		else:
			self.message_cache[member.id] = [{'timestamp': timestamp, 'size': lmsg}]
			
		if len(user_cache := self.message_cache.get(member.id)) >= 10:
			sub = user_cache[-1]['timestamp'] - user_cache[-10]['timestamp']
			if sub <= 8:
				await message.delete()
				return await self.mute(context=ctx, member=member, reason="Message Spam¹")

		if lmsg >= 50:
			user_cache = self.message_cache.get(member.id)
			if len(self.message_cache[member.id]) >= 5:
				sub = user_cache[-1]['timestamp'] - user_cache[-5]['timestamp']
				if sub <= 10:
					if user_cache[-5]['size'] >= 50:
						message.delete()
						return await self.mute(context=ctx, member=member, reason="Message Spam²")

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
			message.delete()
			return await self.warn(context=ctx, member=member, reason="Image Spam")

		if len(self.image_cache[member.id]) >= 10:
			sub = user_cache[-1] - user_cache[-10]
			if sub <= 60:
				await message.delete()
				return await self.warn(context=ctx, member=member, reason="Image Spam")

	@commands.Cog.listener()
	async def on_message_delete(self, message):
		if message.author.bot:
			return
		last_deleted_message.clear()
		last_deleted_message.append(message)

	@commands.command(aliases=['userinfo', 'whois'])
	@Misc.check_whitelist()
	async def user(self, ctx, member: discord.Member = None):
		""" Shows all the information about a member.
		:param member: The member to show the info.
		:return: An embedded message with the user's information. """

		member = ctx.author if not member else member

		embed = discord.Embed(color=member.color, timestamp=ctx.message.created_at)

		embed.set_author(name=f"User Info: {member}")
		embed.set_thumbnail(url=member.display_avatar)
		embed.set_footer(text=f"Requested by {ctx.author}", icon_url=ctx.author.display_avatar)

		embed.add_field(name="ID:", value=member.id, inline=False)
		embed.add_field(name="Server name:", value=member.display_name, inline=False)

		sorted_time_create = f"<t:{int(member.created_at.timestamp())}:R>"
		sorted_time_join = f"<t:{int(member.joined_at.timestamp())}:R>"

		embed.add_field(name="Created at:", value=f"{member.created_at.strftime('%d/%m/%y')} ({sorted_time_create})",
						inline=False)
		embed.add_field(name="Joined at:", value=f"{member.joined_at.strftime('%d/%m/%y')} ({sorted_time_join})", inline=False)

		embed.add_field(name="Top role:", value=member.top_role.mention, inline=False)

		if last_seen := await self.client.get_cog('Misc').get_member_last_seen(member.id):
			last_seen_date = datetime.utcfromtimestamp(last_seen[1])
			last_seen_date = await self.sort_time(ctx.guild, last_seen_date)
			emoji_status = await self.get_status_emoji(str(member.status))
			embed.add_field(name="Last Seen:", value=f"{last_seen_date} | {emoji_status} **Current Status:** {member.status}", inline=False)

		await ctx.send(embed=embed)

	async def get_status_emoji(self, status: str) -> str:
		""" Gets an emoji for a status.
		:param status: The status to get the emoji for. """

		" :green_circle: :yellow_circle: :red_circle: :black_circle: ?"

		if status == "online": return ':green_circle:'
		if status == "idle": return ':yellow_circle:'
		if status == "dnd": return ':red_circle:'
		if status == "offline": return ':black_circle:'

	@commands.command(aliases=['si', 'server'])
	@Misc.check_whitelist()
	async def serverinfo(self, ctx):
		""" Shows some information about the server. """

		guild = ctx.guild

		em = discord.Embed(description=guild.description, color=ctx.author.color)
		online = len({m.id for m in guild.members if m.status is not discord.Status.offline})
		em.add_field(name="Server ID", value=guild.id, inline=True)
		em.add_field(name="Owner", value=guild.owner.mention, inline=True)

		staff_role = discord.utils.get(guild.roles, id=staff_role_id)
		staff_members = [m.mention for m in guild.members if staff_role in m.roles]
		staff = ', '.join(staff_members) if staff_members else None
		em.add_field(name="Staff Members", value=staff, inline=False)
		em.add_field(name="Members", value=f"🟢 {online} members ⚫ {len(guild.members)} members", inline=False)
		em.add_field(name="Channels", value=f"⌨️ {len(guild.text_channels)} | 🔈 {len(guild.voice_channels)}", inline=True)
		em.add_field(name="Roles", value=len(guild.roles), inline=False)
		em.add_field(name="Emojis", value=len(guild.emojis), inline=True)
		em.add_field(name="🌐 Region", value=str(guild.region).title() if guild.region else None, inline=False)
		em.add_field(name="🔨 Bans", value=len(await guild.bans()), inline=False)

		em.add_field(name="⚡ Boosts", value=f"{guild.premium_subscription_count} (Level {guild.premium_tier})", inline=False)
		features = '\n'.join(list(map(lambda f: f.replace('_', ' ').capitalize(), guild.features)))
		em.add_field(name="Server Features", value=features if features else None, inline=False)

		em.set_thumbnail(url=None or guild.icon.url)
		em.set_image(url=guild.banner_url)
		em.set_author(name=guild.name, icon_url=None or guild.icon.url)
		created_at = await self.sort_time(guild, guild.created_at)
		em.set_footer(text=f"Created: {guild.created_at.strftime('%d/%m/%y')} ({created_at})")
		await ctx.send(embed=em)

	async def sort_time(self, guild: discord.Guild, at: datetime) -> str:

		timedelta = await utils.get_time() - at.astimezone(timezone('Etc/GMT'))

		if type(timedelta) is not float:
			timedelta = timedelta.total_seconds()

		seconds = int(timedelta)

		periods = [
			('year', 60*60*24*365, 'years'),
			('months', 60*60*24*30, "months"),
			('day', 60*60*24, "days"),
			('hour', 60*60, "hours"),
			('minute', 60, "minutes"),
			('second', 1, "seconds")
		]

		strings = []
		for period_name, period_seconds, plural in periods:
			if seconds >= period_seconds:
				period_value, seconds = divmod(seconds, period_seconds)
				if period_value > 0:
					strings.append(
						f"{period_value} {plural if period_value > 1 else period_name}"
					)
					
		return ", ".join(strings[:2])

	def is_allowed_members():
		def predicate(ctx):
			return ctx.message.author.id == 442770329409159188

		return commands.check(predicate)

	@commands.command()
	@commands.check_any(is_allowed_members(), commands.has_any_role(*allowed_roles))
	async def snipe(self, ctx):
		""" (MOD) Snipes the last deleted message. """

		message = last_deleted_message
		if message:
			message = message[0]
			embed = discord.Embed(title="Sniped", description=f"**>>** {message.content}", color=message.author.color, timestamp=message.created_at)
			embed.set_author(name=message.author,url=message.author.display_avatar, icon_url=message.author.display_avatar)
			await ctx.send(embed=embed)
		else:
			await ctx.send("**I couldn't snipe any messages!**")

	@commands.command()
	@commands.check_any(is_allowed_members(), commands.has_any_role(*[jr_mod_role_id, mod_role_id, admin_role_id, owner_role_id]))
	async def purge(self, ctx, amount=0, member: discord.Member = None):
		""" (MOD) Purges messages.
		:param amount: The amount of messages to purge.
		:param member: The member from whom to purge the messages. (Optional) """

		perms = ctx.channel.permissions_for(ctx.author)
		if not perms.administrator:
			if amount > 100:
				return await ctx.send(f"**You cannot delete more than `100` messages at a time, {ctx.author.mention}!**")
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

	@commands.command()
	@commands.check_any(is_allowed_members(), commands.has_any_role(*allowed_roles))
	async def warn(self, ctx, member: discord.Member = None, *, reason=None):
		""" (MOD) Warns a member.
		:param member: The @ or ID of the user to warn.
		:param reason: The reason for warning the user. (Optional) """

		try:
			await ctx.message.delete()
		except Exception:
			pass

		if not member:
			await ctx.send("Please, specify a member!", delete_after=3)
		else:
			# # General embed
			general_embed = discord.Embed(description=f'**Reason:** {reason}', color=discord.Color.dark_gold())
			general_embed.set_author(name=f'{member} has been warned', icon_url=member.display_avatar)
			msg = await ctx.send(embed=general_embed)
			# Moderation log embed
			moderation_log = discord.utils.get(ctx.guild.channels, id=mod_log_id)
			embed = discord.Embed(
				description=f"**Warned** {member.mention}\n**Reason:** {reason}\n" \
					f"**Channel:** {ctx.channel.mention}\n**Location:** [Jump URL]({msg.jump_url})",
				color=discord.Color.dark_gold(),
				timestamp=ctx.message.created_at)
			embed.set_author(name=f"{ctx.author} (ID {ctx.author.id})", icon_url=ctx.author.display_avatar)
			embed.set_thumbnail(url=member.display_avatar)
			await moderation_log.send(embed=embed)
			# Inserts a infraction into the database
			current_ts = await utils.get_timestamp()
			await self.insert_user_infraction(
				user_id=member.id, infr_type="warn", reason=reason,
				timestamp=current_ts , perpetrator=ctx.author.id)
			try:
				await member.send(embed=embed)
			except Exception as e:
				print(e)
				pass

			await self.client.get_cog('LevelSystem').increment_important_var_int(label="m_infractions")
			
			if ctx.author.bot:
				return

			staff_member = ctx.author
			if not await self.get_staff_member(staff_member.id):
				staff_at = await utils.get_time()
				staff_at = staff_at.strftime('%Y/%m/%d at %H:%M:%S')
				return await self.insert_staff_member(
					user_id=staff_member.id, infractions_given=1, staff_at=staff_at)
			else:
				await self.update_staff_member_counter(
					user_id=staff_member.id, infraction_increment=1)

			user_infractions = await self.get_user_infractions(member.id)
			user_warns = [w for w in user_infractions if w[1] == 'warn' and 'Message Spam' in str(w[2])]
			if len(user_warns) >= 3:
				ctx.author = self.client.user
				await self.mute(context=ctx, member=member, reason=reason)

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

	@commands.command()
	@commands.check_any(is_allowed_members(), commands.has_any_role(*allowed_roles, member_dot_role_id))
	async def mute(self, ctx, member: discord.Member = None, reason: str =  None, *, time: str = None):
		""" Mutes a member for a determined amount of time or indefinitely.
		:param member: The @ or the ID of the user to tempmute.
		:param reason: The reason for the tempmute.
		:param time: The time for the mute (Optional). Default = Forever """

		try:
			await ctx.message.delete()
		except:
			pass

		if not member:
			return await ctx.send("**Please, specify a member!**", delete_after=3)

		if not reason:
			return await ctx.send(f"**Specify a reason!**", delete_after=3)

		if time:
			# return await ctx.send('**Inform a time!**', delete_after=3)

			time_dict, seconds = await self.get_mute_time(ctx=ctx, time=time)
			if not seconds:
				return

		current_ts = int(await utils.get_timestamp())

		role = discord.utils.get(ctx.guild.roles, id=muted_role_id)

		if role not in member.roles:
			await member.move_to(None)
			remove_roles = []
			keep_roles = [role]

			bot = discord.utils.get(ctx.guild.members, id=self.client.user.id)

			for i, member_role in enumerate(member.roles):
				if i == 0:
					continue

				if member_role.id == role.id:
					continue

				if member_role < bot.top_role:
					if not member_role.is_premium_subscriber():
						remove_roles.append(member_role)

				if member_role.is_premium_subscriber():
					keep_roles.append(member_role)

				if member_role >= bot.top_role:
					keep_roles.append(member_role)

			await member.edit(roles=keep_roles)
			if time:
				user_role_ids = [(member.id, rr.id, current_ts, seconds) for rr in remove_roles]
				await self.insert_in_muted(user_role_ids)

				# General embed
				general_embed = discord.Embed(description=f"**For:** `{time_dict['days']}d` `{time_dict['hours']}h`, `{time_dict['minutes']}m`\n**Reason:** {reason}", color=discord.Color.dark_gray(), timestamp=ctx.message.created_at)
				general_embed.set_author(name=f"{member} has been muted", icon_url=member.display_avatar)
				msg = await ctx.send(embed=general_embed)
				# Moderation log embed
				moderation_log = discord.utils.get(ctx.guild.channels, id=mod_log_id)
				embed = discord.Embed(
					description=f"**Muted** {member.mention} for `{time_dict['days']}d` `{time_dict['hours']}h`, `{time_dict['minutes']}m`\n**Reason:** {reason}\n" \
						f"**Channel:** {ctx.channel.mention}\n**Location:** [Jump URL]({msg.jump_url})",
					color=discord.Color.dark_gray(),
					timestamp=ctx.message.created_at)
				embed.set_author(name=f"{ctx.author} (ID {ctx.author.id})", icon_url=ctx.author.display_avatar)
				embed.set_thumbnail(url=member.display_avatar)
				await moderation_log.send(embed=embed)
			else:
				user_role_ids = [(member.id, rr.id, None, None) for rr in remove_roles]
				await self.insert_in_muted(user_role_ids)

				# General embed
				general_embed = discord.Embed(description=f'**Reason:** {reason}', color=discord.Color.dark_gray(), timestamp=ctx.message.created_at)
				general_embed.set_author(name=f'{member} has been muted', icon_url=member.display_avatar)
				await ctx.send(embed=general_embed)
				# Moderation log embed
				moderation_log = discord.utils.get(ctx.guild.channels, id=mod_log_id)
				embed = discord.Embed(
					description=F"**Muted** {member.mention}\n**Reason:** {reason}\n**Location:** {ctx.channel.mention}",
					color=discord.Color.dark_gray(),
					timestamp=ctx.message.created_at)
				embed.set_author(name=f"{ctx.author} (ID {ctx.author.id})", icon_url=ctx.author.display_avatar)
				embed.set_thumbnail(url=member.display_avatar)
				await moderation_log.send(embed=embed)

			# # Inserts a infraction into the database
			await self.insert_user_infraction(
				user_id=member.id, infr_type="mute", reason=reason, 
				timestamp=current_ts , perpetrator=ctx.author.id)
			try:
				await member.send(embed=general_embed)
			except:
				pass

			await self.client.get_cog('LevelSystem').increment_important_var_int(label="m_infractions")

			if ctx.author.bot:
				return

			staff_member = ctx.author
			if not await self.get_staff_member(staff_member.id):
				staff_at = await utils.get_time()
				staff_at = staff_at.strftime('%Y/%m/%d at %H:%M:%S')
				return await self.insert_staff_member(
					user_id=staff_member.id, infractions_given=1, staff_at=staff_at)
			else:
				await self.update_staff_member_counter(
					user_id=staff_member.id, infraction_increment=1)
		else:
			await ctx.send(f'**{member} is already tempbanned!**', delete_after=5)

	@commands.command()
	@commands.check_any(is_allowed_members(), commands.has_any_role(*allowed_roles, member_dot_role_id))
	async def unmute(self, ctx, member: discord.Member = None, *, reason: Optional[str] = None):
		""" (MOD) Unmutes a member.
		:param member: The @ or the ID of the user to unmute.
		:param reason: The reason for the unmute. [Optional] """

		await ctx.message.delete()
		role = discord.utils.get(ctx.guild.roles, id=muted_role_id)
		if not member:
			return await ctx.send("**Please, specify a member!**", delete_after=3)

		if not role:
			return

		if role in member.roles:
			if user_roles := await self.get_muted_roles(member.id):

				bot = discord.utils.get(ctx.guild.members, id=self.client.user.id)

				member_roles = list([
					a_role for the_role in user_roles if (a_role := discord.utils.get(member.guild.roles, id=the_role[1]))
					and a_role < bot.top_role
				])
				member_roles.extend(member.roles)

				member_roles = list(set(member_roles))
				if role in member_roles:
					member_roles.remove(role)

				await member.edit(roles=member_roles)
				user_role_ids = [(member.id, mrole[1]) for mrole in user_roles]
				try:
					await self.remove_role_from_system(user_role_ids)
				except Exception as e:
					print(e)
					pass

			# General embed
			general_embed = discord.Embed(description=f'**Reason:** {reason}', color=discord.Color.lighter_gray(), timestamp=ctx.message.created_at)
			general_embed.set_author(name=f'{member} has been unmuted', icon_url=member.display_avatar)
			msg = await ctx.send(embed=general_embed)
			# Moderation log embed
			moderation_log = discord.utils.get(ctx.guild.channels, id=mod_log_id)
			embed = discord.Embed(
				description=F"**Unmuted** {member.mention}\n**Reason:** {reason}\n" \
					f"**Channel:** {ctx.channel.mention}\n**Location:** [Jump URL]({msg.jump_url})",
				color=discord.Color.lighter_gray(),
				timestamp=ctx.message.created_at)
			embed.set_author(name=f"{ctx.author} (ID {ctx.author.id})", icon_url=ctx.author.display_avatar)
			embed.set_thumbnail(url=member.display_avatar)
			await moderation_log.send(embed=embed)
			try:
				await member.send(embed=general_embed)
			except:
				pass

		else:
			await ctx.send(f'**{member} is not even muted!**', delete_after=5)

	@commands.command()
	@commands.check_any(is_allowed_members(), commands.has_any_role(*[mod_role_id, admin_role_id, owner_role_id]))
	async def kick(self, ctx, member: discord.Member = None, *, reason: Optional[str] = None) -> None:
		""" (MOD) Kicks a member from the server.
		:param member: The @ or ID of the user to kick.
		:param reason: The reason for kicking the user. (Optional) """

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
				general_embed = discord.Embed(description=f'**Reason:** {reason}', color=discord.Color.magenta())
				general_embed.set_author(name=f'{member} has been kicked', icon_url=member.display_avatar)
				msg = await ctx.send(embed=general_embed)
				# Moderation log embed
				moderation_log = discord.utils.get(ctx.guild.channels, id=mod_log_id)
				embed = discord.Embed(
					description=f"**Kicked** {member.mention}\n**Reason:** {reason}\n" \
					f"**Channel:** {ctx.channel.mention}\n**Location:** [Jump URL]({msg.jump_url})",
					color=discord.Color.magenta(),
					timestamp=ctx.message.created_at)
				embed.set_author(name=f"{ctx.author} (ID {ctx.author.id})", icon_url=ctx.author.display_avatar)
				embed.set_thumbnail(url=member.display_avatar)
				await moderation_log.send(embed=embed)
				# Inserts a infraction into the database
				current_ts = await utils.get_timestamp()
				await self.insert_user_infraction(
					user_id=member.id, infr_type="kick", reason=reason, 
					timestamp=current_ts , perpetrator=ctx.author.id)
				try:
					await member.send(embed=general_embed)
				except:
					pass

				await self.client.get_cog('LevelSystem').increment_important_var_int(label="m_infractions")

				if ctx.author.bot:
					return

				staff_member = ctx.author
				if not await self.get_staff_member(staff_member.id):
					staff_at = await utils.get_time()
					staff_at = staff_at.strftime('%Y/%m/%d at %H:%M:%S')
					return await self.insert_staff_member(
						user_id=staff_member.id, infractions_given=1, staff_at=staff_at)
				else:
					await self.update_staff_member_counter(
						user_id=staff_member.id, infraction_increment=1)

	@commands.command()
	@commands.check_any(is_allowed_members(), commands.has_any_role(*[mod_role_id, admin_role_id, owner_role_id]))
	async def ban(self, ctx, *, reason: Optional[str] = None) -> None:
		""" Bans a member from the server.
		:param members: The @ or ID of one or more users to ban.
		:param reason: The reason for banning the user. [Optional] """

		await ctx.message.delete()


		members, reason = await utils.greedy_member_reason(ctx, reason)

		if not members:
			return await ctx.send('**Please, specify a member!**', delete_after=3)

		# Bans and logs
		current_ts = await utils.get_timestamp()
		staff_member = ctx.author
		if not (staff_member_info := await self.get_staff_member(staff_member.id)):
			staff_at = await utils.get_time()
			staff_at = staff_at.strftime('%Y/%m/%d at %H:%M:%S')
			return await self.insert_staff_member(
				user_id=staff_member.id, infractions_given=1, staff_at=staff_at, 
				bans_today=1, ban_timestamp=current_ts)
		else:
			LevelSystem = self.client.get_cog("LevelSystem")
			mod_default, adm_default = 30, 70

			staff_bans = staff_member_info[3]

			for member in members:

				if not (mod_ban_limit := await LevelSystem.get_important_var("mod_ban_limit")):
					await LevelSystem.insert_important_var(label="mod_ban_limit", value_int=mod_default)
					mod_ban_limit = mod_default
				if not (adm_ban_limit := await LevelSystem.get_important_var("adm_ban_limit")):
					await LevelSystem.insert_important_var(label="adm_ban_limit", value_int=mod_default)
					adm_ban_limit = adm_default

				if staff_bans and current_ts - staff_member_info[4] >= 86400 or staff_bans and not staff_member_info[4]:
					await self.update_staff_member_counter(
						user_id=staff_member.id, infraction_increment=1, reset_ban=True, timestamp=current_ts)

				elif staff_bans >= mod_ban_limit[2] and not ctx.channel.permissions_for(staff_member).administrator:
					try:
						await staff_member.send("**You have reached your daily ban limit. Please contact an admin.**")
					except:
						pass
					return
				elif staff_bans >= adm_ban_limit[2] and ctx.channel.permissions_for(staff_member).administrator:
					try:
						await staff_member.send("**You have reached your daily ban limit. Please contact the owner.**")
					except:
						pass
					return
				staff_bans += 1

				try:
					await member.ban(delete_message_days=0, reason=reason)
				except Exception:
					await ctx.send('**You cannot do that!**', delete_after=3)
				else:

					await self.update_staff_member_counter(
							user_id=staff_member.id, infraction_increment=1, ban_increment=1, timestamp=current_ts)

					# General embed
					general_embed = discord.Embed(description=f'**Reason:** {reason}', color=discord.Color.dark_red())
					general_embed.set_author(name=f'{member} has been banned', icon_url=member.display_avatar)
					msg = await ctx.send(embed=general_embed)
					# Moderation log embed
					moderation_log = discord.utils.get(ctx.guild.channels, id=mod_log_id)
					embed = discord.Embed(
						description=f"**Banned** {member.mention}\n**Reason:** {reason}\n" \
							f"**Channel:** {ctx.channel.mention}\n**Location:** [Jump URL]({msg.jump_url})",
						color=discord.Color.dark_red(),
						timestamp=ctx.message.created_at)
					embed.set_author(name=f"{ctx.author} (ID {ctx.author.id})", icon_url=ctx.author.display_avatar)
					embed.set_thumbnail(url=member.display_avatar)
					await moderation_log.send(embed=embed)
					# Inserts a infraction into the database
					await self.insert_user_infraction(
						user_id=member.id, infr_type="ban", reason=reason, 
						timestamp=current_ts , perpetrator=ctx.author.id)
					try:
						await member.send(embed=general_embed)
					except:
						pass

					await self.client.get_cog('LevelSystem').increment_important_var_int(label="m_infractions")

	@commands.command()
	@commands.check_any(is_allowed_members(), commands.has_any_role(*allowed_roles, member_dot_role_id))
	async def tempban(self, ctx, member: discord.Member = None, reason: str =  None, *, time: str = None):
		""" Tempbans a member from all channels for a determined amount of time or indefinitely.
		:param member: The @ or the ID of the user to tempban.
		:param reason: The reason for the tempban.
		:param time: The time for the tempban (Optional). Default = Forever """

		try:
			await ctx.message.delete()
		except:
			pass

		if not member:
			return await ctx.send("**Please, specify a member!**", delete_after=3)

		if not reason:
			return await ctx.send(f"**Specify a reason!**", delete_after=3)

		if time:

			time_dict, seconds = await self.get_mute_time(ctx=ctx, time=time)
			if not seconds:
				return

		current_ts = int(await utils.get_timestamp())

		role = discord.utils.get(ctx.guild.roles, id=banned_role_id)

		if role not in member.roles:
			await member.move_to(None)
			remove_roles = []
			keep_roles = [role]

			bot = discord.utils.get(ctx.guild.members, id=self.client.user.id)

			for i, member_role in enumerate(member.roles):
				if i == 0:
					continue

				if member_role.id == role.id:
					continue

				if member_role < bot.top_role:
					if not member_role.is_premium_subscriber():
						remove_roles.append(member_role)

				if member_role.is_premium_subscriber():
					keep_roles.append(member_role)

				if member_role >= bot.top_role:
					keep_roles.append(member_role)

			await member.edit(roles=keep_roles)
			if time:
				user_role_ids = [(member.id, rr.id, current_ts, seconds) for rr in remove_roles]
				await self.insert_in_tempbanned(user_role_ids)

				# General embed
				general_embed = discord.Embed(description=f"**For:** `{time_dict['days']}d` `{time_dict['hours']}h`, `{time_dict['minutes']}m`\n**Reason:** {reason}", color=discord.Color.dark_purple(), timestamp=ctx.message.created_at)
				general_embed.set_author(name=f"{member} has been tempbanned", icon_url=member.display_avatar)
				msg = await ctx.send(embed=general_embed)
				# Moderation log embed
				moderation_log = discord.utils.get(ctx.guild.channels, id=mod_log_id)
				embed = discord.Embed(
					description=f"**Tempbanned** {member.mention} for `{time_dict['days']}d` `{time_dict['hours']}h`, `{time_dict['minutes']}m`\n**Reason:** {reason}\n" \
						f"**Channel:** {ctx.channel.mention}\n**Location:** [Jump URL]({msg.jump_url})",
					color=discord.Color.dark_purple(),
					timestamp=ctx.message.created_at)
				embed.set_author(name=f"{ctx.author} (ID {ctx.author.id})", icon_url=ctx.author.display_avatar)
				embed.set_thumbnail(url=member.display_avatar)
				await moderation_log.send(embed=embed)
			else:
				user_role_ids = [(member.id, rr.id, None, None) for rr in remove_roles]
				await self.insert_in_tempbanned(user_role_ids)

				# General embed
				general_embed = discord.Embed(description=f'**Reason:** {reason}', color=discord.Color.dark_purple(), timestamp=ctx.message.created_at)
				general_embed.set_author(name=f'{member} has been tempbanned', icon_url=member.display_avatar)
				await ctx.send(embed=general_embed)
				# Moderation log embed
				moderation_log = discord.utils.get(ctx.guild.channels, id=mod_log_id)
				embed = discord.Embed(
					description=F"**Tempbanned** {member.mention}\n**Reason:** {reason}\n**Location:** {ctx.channel.mention}",
					color=discord.Color.dark_purple(),
					timestamp=ctx.message.created_at)
				embed.set_author(name=f"{ctx.author} (ID {ctx.author.id})", icon_url=ctx.author.display_avatar)
				embed.set_thumbnail(url=member.display_avatar)
				await moderation_log.send(embed=embed)

			# # Inserts a infraction into the database
			await self.insert_user_infraction(
				user_id=member.id, infr_type="tempban", reason=reason, 
				timestamp=current_ts , perpetrator=ctx.author.id)
			try:
				await member.send(embed=general_embed)
			except:
				pass

			await self.client.get_cog('LevelSystem').increment_important_var_int(label="m_infractions")

			if ctx.author.bot:
				return

			staff_member = ctx.author
			if not await self.get_staff_member(staff_member.id):
				staff_at = await utils.get_time()
				staff_at = staff_at.strftime('%Y/%m/%d at %H:%M:%S')
				return await self.insert_staff_member(
					user_id=staff_member.id, infractions_given=1, staff_at=staff_at)
			else:
				await self.update_staff_member_counter(
					user_id=staff_member.id, infraction_increment=1)
		else:
			await ctx.send(f'**{member} is already muted!**', delete_after=5)

	@commands.command()
	@commands.check_any(is_allowed_members(), commands.has_any_role(*allowed_roles, member_dot_role_id))
	async def untempban(self, ctx, member: discord.Member = None, *, reason: Optional[str] = None):
		""" (MOD) Untempbans a member.
		:param member: The @ or the ID of the user to untempban.
		:param reason: The reason for the untempban. [Optional] """

		await ctx.message.delete()
		role = discord.utils.get(ctx.guild.roles, id=banned_role_id)
		if not member:
			return await ctx.send("**Please, specify a member!**", delete_after=3)

		if not role:
			return

		if role in member.roles:
			if user_roles := await self.get_tempbanned_roles(member.id):

				bot = discord.utils.get(ctx.guild.members, id=self.client.user.id)

				member_roles = list([
					a_role for the_role in user_roles if (a_role := discord.utils.get(member.guild.roles, id=the_role[1]))
					and a_role < bot.top_role
				])
				member_roles.extend(member.roles)

				member_roles = list(set(member_roles))
				if role in member_roles:
					member_roles.remove(role)

				await member.edit(roles=member_roles)
				user_role_ids = [(member.id, mrole[1]) for mrole in user_roles]
				try:
					await self.remove_tempbanned_role_from_system(user_role_ids)
				except Exception as e:
					print(e)
					pass

			# General embed
			general_embed = discord.Embed(description=f'**Reason:** {reason}', color=discord.Color.purple(), timestamp=ctx.message.created_at)
			general_embed.set_author(name=f'{member} has been untempbanned', icon_url=member.display_avatar)
			msg = await ctx.send(embed=general_embed)
			# Moderation log embed
			moderation_log = discord.utils.get(ctx.guild.channels, id=mod_log_id)
			embed = discord.Embed(
				description=F"**Untempbanned** {member.mention}\n**Reason:** {reason}\n" \
					f"**Channel:** {ctx.channel.mention}\n**Location:** [Jump URL]({msg.jump_url})",
				color=discord.Color.purple(),
				timestamp=ctx.message.created_at)
			embed.set_author(name=f"{ctx.author} (ID {ctx.author.id})", icon_url=ctx.author.display_avatar)
			embed.set_thumbnail(url=member.display_avatar)
			await moderation_log.send(embed=embed)
			try:
				await member.send(embed=general_embed)
			except:
				pass

		else:
			await ctx.send(f'**{member} is not even muted!**', delete_after=5)

	@commands.command()
	@commands.check_any(is_allowed_members(), commands.has_any_role(*[mod_role_id, admin_role_id, owner_role_id]))
	async def hardban(self, ctx, *, reason: Optional[str] = None) -> None:
		""" Hardbans a member from the server.
		=> Bans and delete messages from the last day,
		:param member: The @ or ID of the user to ban.
		:param reason: The reason for banning the user. [Optional] """

		await ctx.message.delete()
		members, reason = await utils.greedy_member_reason(ctx, reason)

		if not members:
			return await ctx.send('**Please, specify a member!**', delete_after=3)


		# Bans and logs

		current_ts = await utils.get_timestamp()
		staff_member = ctx.author
		if not (staff_member_info := await self.get_staff_member(staff_member.id)):
			staff_at = await utils.get_time()
			staff_at = staff_at.strftime('%Y/%m/%d at %H:%M:%S')
			return await self.insert_staff_member(
				user_id=staff_member.id, infractions_given=1, staff_at=staff_at, 
				bans_today=1, ban_timestamp=current_ts)
		else:
			LevelSystem = self.client.get_cog("LevelSystem")
			mod_default, adm_default = 30, 70
			staff_bans = staff_member_info[3]

			for member in members:
				if not (mod_ban_limit := await LevelSystem.get_important_var("mod_ban_limit")):
					await LevelSystem.insert_important_var(label="mod_ban_limit", value_int=mod_default)
					mod_ban_limit = mod_default
				if not (adm_ban_limit := await LevelSystem.get_important_var("adm_ban_limit")):
					await LevelSystem.insert_important_var(label="adm_ban_limit", value_int=mod_default)
					adm_ban_limit = adm_default

				if staff_bans and current_ts - staff_member_info[4] >= 86400 or staff_bans and not staff_member_info[4]:
					await self.update_staff_member_counter(
						user_id=staff_member.id, infraction_increment=1, reset_ban=True, timestamp=current_ts)
				elif staff_bans >= mod_ban_limit[2] and not ctx.channel.permissions_for(staff_member).administrator:
					try:
						await staff_member.send("**You have reached your daily ban limit. Please contact an admin.**")
					except:
						pass
					return
				elif staff_bans >= adm_ban_limit[2] and ctx.channel.permissions_for(staff_member).administrator:
					try:
						await staff_member.send("**You have reached your daily ban limit. Please contact the owner.**")
					except:
						pass
					return

				staff_bans += 1				

				try:
					await member.ban(delete_message_days=1, reason=reason)
				except Exception:
					await ctx.send('**You cannot do that!**', delete_after=3)
				else:
					await self.update_staff_member_counter(
							user_id=staff_member.id, infraction_increment=1, ban_increment=1, timestamp=current_ts)

					# General embed
					general_embed = discord.Embed(description=f'**Reason:** {reason}', color=discord.Color.dark_red())
					general_embed.set_author(name=f'{member} has been hardbanned', icon_url=member.display_avatar)
					msg = await ctx.send(embed=general_embed)
					# Moderation log embed
					moderation_log = discord.utils.get(ctx.guild.channels, id=mod_log_id)
					embed = discord.Embed(
						description=F"**Hardbanned** {member.mention}\n**Reason:** {reason}\n" \
							f"**Channel:** {ctx.channel.mention}\n**Location:** [Jump URL]({msg.jump_url})",
						color=discord.Color.dark_red(),
						timestamp=ctx.message.created_at)
					embed.set_author(name=f"{ctx.author} (ID {ctx.author.id})", icon_url=ctx.author.display_avatar)
					embed.set_thumbnail(url=member.display_avatar)
					await moderation_log.send(embed=embed)
					# Inserts a infraction into the database
					await self.insert_user_infraction(
						user_id=member.id, infr_type="ban", reason=reason, 
						timestamp=current_ts , perpetrator=ctx.author.id)
					try:
						await member.send(embed=general_embed)
					except:
						pass

					await self.client.get_cog('LevelSystem').increment_important_var_int(label="m_infractions")

	@commands.command()
	@commands.has_permissions(administrator=True)
	async def unban(self, ctx, *, member = None):
		""" (ADM) Unbans a member from the server.
		:param member: The full nickname and # of the user to unban. """

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
				general_embed = discord.Embed(color=discord.Color.red())
				general_embed.set_author(name=f'{user} has been unbanned', icon_url=user.display_avatar)
				msg = await ctx.send(embed=general_embed)
				# Moderation log embed
				moderation_log = discord.utils.get(ctx.guild.channels, id=mod_log_id)
				embed = discord.Embed(
					description=F"**Unbanned** {user.display_name} (ID {user.id})\n" \
						f"**Channel:** {ctx.channel.mention}\n**Location:** [Jump URL]({msg.jump_url})",
					color=discord.Color.red(),
					timestamp=ctx.message.created_at)
				embed.set_author(name=f"{ctx.author} (ID {ctx.author.id})", icon_url=ctx.author.display_avatar)
				embed.set_thumbnail(url=user.display_avatar)
				await moderation_log.send(embed=embed)
				try:
					await user.send(embed=general_embed)
				except:
					pass

				return await self.client.get_cog('LevelSystem').increment_important_var_int(label="m_infractions")
		else:
			await ctx.send('**Member not found!**', delete_after=3)

	@commands.command()
	@commands.has_permissions(administrator=True)
	async def hackban(self, ctx, user_id: int = None, *, reason: Optional[str] = None):
		""" (ADM) Bans a user that is currently not in the server.
		Only accepts user IDs.
		:param user_id: Member ID
		:param reason: The reason for hackbanning the user. [Optional] """

		await ctx.message.delete()
		if not user_id:
			return await ctx.send("**Inform the user id!**", delete_after=3)
		member = discord.Object(id=user_id)
		if not member:
			return await ctx.send("**Invalid user id!**", delete_after=3)
		try:
			await ctx.guild.ban(member, reason=reason)
			# General embed
			general_embed = discord.Embed(description=f'**Reason:** {reason}', color=discord.Color.dark_teal(),
										  timestamp=ctx.message.created_at)
			general_embed.set_author(name=f'{self.client.get_user(user_id)} has been hackbanned')
			msg = await ctx.send(embed=general_embed)

			# Moderation log embed
			moderation_log = discord.utils.get(ctx.guild.channels, id=mod_log_id)
			embed = discord.Embed(
				description=F"**Hackbanned** {self.client.get_user(user_id)} (ID {member.id})\n**Reason:** {reason}\n" \
					f"**Channel:** {ctx.channel.mention}\n**Location:** [Jump URL]({msg.jump_url})",
				color=discord.Color.dark_teal(),
				timestamp=ctx.message.created_at)
			embed.set_author(name=f"{ctx.author} (ID {ctx.author.id})", icon_url=ctx.author.display_avatar)
			await moderation_log.send(embed=embed)

			# Inserts a infraction into the database
			current_ts = await utils.get_timestamp()
			await self.insert_user_infraction(
				user_id=member.id, infr_type="hackban", reason=reason, 
				timestamp=current_ts , perpetrator=ctx.author.id)
			try:
				await member.send(embed=embed)
			except:
				pass

			await self.client.get_cog('LevelSystem').increment_important_var_int(label="m_infractions")

		except discord.errors.NotFound:
			return await ctx.send("**Invalid user id!**", delete_after=3)
		
	@commands.command(aliases=['infr', 'show_warnings', 'sw', 'show_bans', 'sb', 'show_muted', 'sm', 'punishements'])
	@commands.check_any(is_allowed_members(), commands.has_any_role(*allowed_roles))
	async def infractions(self, ctx, member: Optional[discord.Member] = None) -> None:
		""" Shows all infractions of a specific user.
		:param member: The member to show the infractions from. [Optional] """

		if not member:
			return await ctx.send("**Inform a member!**")
		
		# Try to get user infractions
		if user_infractions := await self.get_user_infractions(member.id):
			warns = len([w for w in user_infractions if w[1] == 'warn'])
			mutes = len([m for m in user_infractions if m[1] == 'mute'])
			kicks = len([k for k in user_infractions if k[1] == 'kick'])
			tempbans = len([b for b in user_infractions if b[1] == 'tempban'])
			bans = len([b for b in user_infractions if b[1] == 'ban'])
			hackbans = len([hb for hb in user_infractions if hb[1] == 'hackban'])
		else:
			return await ctx.send(f"**{member.mention} doesn't have any existent infractions!**")

		# Makes the initial embed with their amount of infractions
		embed = discord.Embed(
			title=f"Infractions for {member}",
			color=member.color,
			timestamp=ctx.message.created_at)
		embed.set_thumbnail(url=member.display_avatar)
		embed.set_footer(text=f"Warns: {warns} | Mutes: {mutes} | Kicks: {kicks} | Tempbans: {tempbans} | Bans: {bans} | Hackbans: {hackbans}", icon_url=ctx.author.display_avatar)

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

	@commands.command(aliases=['ri', 'remove_warn', 'remove_warning'])
	@commands.has_permissions(administrator=True)
	async def remove_infraction(self, ctx, infr_id: int = None):
		""" (MOD) Removes a specific infraction by ID.
		:param infr_id: The infraction ID. """

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
	async def remove_infractions(self, ctx, member: Optional[discord.Member] = None):
		""" (MOD) Removes all infractions for a specific user.
		:param member: The member to get the warns from. """

		if not member:
			return await ctx.send("**Inform a member!**")
		
		if await self.get_user_infractions(member.id):
			await self.remove_user_infractions(member.id)
			await ctx.send(f"**Removed all infractions for {member.mention}!**")
		else:
			await ctx.send(f"**{member.mention} doesn't have any existent infractions!**")

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

	@commands.command(aliases=['bl_channels', 'blc'])
	@commands.has_permissions(administrator=True)
	async def blacklisted_channels(self, ctx) -> None:
		""" Shows the blacklisted channels that commands except moderation ones are not allowed to be used in. """

		LevelSystem = self.client.get_cog('LevelSystem')
		if not await LevelSystem.table_important_vars_exists():
			return await ctx.send(f"**This command is not ready to be used yet, {member.mention}!**")

		member = ctx.author

		if not (channels := await LevelSystem.get_important_var(label="bl_channel", multiple=True)):
			return await ctx.send(f"**No channels have been blacklisted yet, {member.mention}!**")

		guild = ctx.guild
		channels = ', '.join([cm.mention if (cm := discord.utils.get(guild.channels, id=c[2])) else str(c[2]) for c in channels])

		embed = discord.Embed(
			title="Blacklisted Channels",
			description=channels,
			color=member.color,
			timestamp=ctx.message.created_at
			)

		await ctx.send(embed=embed)

	@commands.command(aliases=['bl'])
	@commands.has_permissions(administrator=True)
	async def blacklist(self, ctx, channel: discord.TextChannel = None) -> None:
		""" Blacklists a channel for commands, except moderation ones.
		:param channel: The channel to blacklist. (Optional)
		Ps: If channel is not informed, it will use the context channel. """

		member = ctx.author

		LevelSystem = self.client.get_cog('LevelSystem')

		if not await LevelSystem.table_important_vars_exists():
			return await ctx.send(f"**This command is not ready to be used yet, {member.mention}!**")

		if not ctx.guild:
			return await ctx.send(f"**You cannot use this command in my DM's, {member.mention}!** ❌")

		if not channel:
			channel = ctx.channel

		if await LevelSystem.get_important_var(label='bl_channel', value_int=channel.id):
			return await ctx.send(f"**{channel.mention} is already blacklisted, {member.mention}!** ⚠️")

		await LevelSystem.insert_important_var(label='bl_channel', value_int=channel.id)

		await ctx.send(f"**{channel.mention} has been blacklisted, {member.mention}!** ✅")

	@commands.command(aliases=['ubl'])
	@commands.has_permissions(administrator=True)
	async def unblacklist(self, ctx, channel: discord.TextChannel = None) -> None:
		""" Unblacklists a channel for commands.
		:param channel: The channel. (Optional)
		Ps: If channel is not informed, it will use the context channel. """

		member = ctx.author

		LevelSystem = self.client.get_cog('LevelSystem')
		if not await LevelSystem.table_important_vars_exists():
			return await ctx.send(f"**This command is not ready to be used yet, {member.mention}!**")

		if not ctx.guild:
			return await ctx.send(f"**You cannot use this command in my DM's, {member.mention}!** ❌")

		if not channel:
			channel = ctx.channel

		if not await LevelSystem.get_important_var(label='bl_channel', value_int=channel.id):
			return await ctx.send(f"**{channel.mention} is not even blacklisted, {member.mention}!** ⚠️")

		await LevelSystem.delete_important_var(label='bl_channel', value_int=channel.id)
		await ctx.send(f"**{channel.mention} has been unblacklisted, {member.mention}!** ✅")
	
	@commands.command(aliases=['change_join_date', 'cjd', 'csjd'])
	@commands.has_permissions(administrator=True)
	async def change_staff_join_date(self, ctx: commands.Context, member: discord.Member = None, new_date: Optional[str] = None) -> None:
		""" Changes the Staff member's join date, if they are not in the table,
		it inserts them in there with the given joinin date.
		:param member: The Staff member to insert.
		:param new_date: The (new) joining date. [Optional]
		
		PS: If new_date is not informed, it'll prompt for the removal"""

		author: discord.Member = ctx.author

		if not member:
			return await ctx.send(f"**Please, inform a member, {ctx.author.mention}!**")

		if new_date and len(new_date) > 50:
			return await ctx.send(f"**Please, inform a date with a max. of 50 characters, {ctx.author.mention}!**")

		if not new_date:
			confirm_view = ConfirmButton(author, timeout=60)
			embed = discord.Embed(
				title="__Confirmation__",
				description=f"**Are you sure you wanna delete {member.mention}'s Staff join date, {author.mention}!**?",
				color=discord.Color.green(), timestamp=ctx.message.created_at)
			msg = await ctx.send(embed=embed, view=confirm_view)
			await confirm_view.wait()
			if confirm_view.value is None:
				await ctx.reply(f"**Timeout, {member.mention}!**")
			elif not confirm_view:
				await ctx.reply(f"**Declined, {member.mention}!**")
			else:
				await self.delete_staff_member(member.id)
				await ctx.send(f"**Successfully deleted Staff join date from `{member}`, {ctx.author.mention}!**")
			await utils.disable_buttons(confirm_view)
			await msg.edit(view=confirm_view)

		elif await self.get_staff_member(member.id):
			await self.update_staff_member_join_date(member.id, new_date)
			await ctx.send(f"**Successfully updated Staff join date for `{member}`, {ctx.author.mention}!**")
		else:
			await self.insert_staff_member(user_id=member.id, infractions_given=0, staff_at=new_date)
			await ctx.send(f"**Successfully inserted `{member}` with the given Staff join date, {ctx.author.mention}!**")

	@commands.command(aliases=['fire', 'wall', 'fire_wall'])
	@commands.has_permissions(administrator=True)
	async def firewall(self, ctx) -> None:
		""" (ADM) Turns on and off the firewall.
		When turned on, it'll kick new members having accounts created in less than 10 minutes. """

		member = ctx.author

		if not await self.check_table_firewall_exists():
			return await ctx.send(f"**It looks like the firewall is on maintenance, {member.mention}!**")

		if await self.get_firewall_state():
			confirm = await Confirm(f"The Firewall is activated, do you want to turn it off, {member.mention}?").prompt(ctx)
			if confirm:
				await self.set_firewall_state(0)
				await ctx.send(f"**Firewall deactivated, {member.mention}!**")
		else:
			confirm = await Confirm(f"The Firewall is deactivated, do you want to turn it on, {member.mention}?").prompt(ctx)
			if confirm:
				await self.set_firewall_state(1)
				await ctx.send(f"**Firewall activated, {member.mention}!**")

	@commands.command(aliases=["banlimit", "ban_limit", "bans_limit", "see_ban_limit", "see_bans_limit", "show_ban_limit"])
	@commands.has_permissions(administrator=True)
	async def show_bans_limit(self, ctx) -> None:
		""" Shows the daily bans limit for mods and admins. """

		member: discord.Member = ctx.author
		default_mod, default_adm = 30, 70

		LevelSystem = self.client.get_cog("LevelSystem")
		if not await LevelSystem.table_important_vars_exists():
			return await ctx.send(f"**This command is not ready to be used yet, {member.mention}!**")

		# Moderators
		if mod_limit := await LevelSystem.get_important_var(label="mod_ban_limit"):
			mod_limit = mod_limit[2]
		else:
			mod_limit = default_mod
		
		# Admins
		if adm_limit := await LevelSystem.get_important_var(label="adm_ban_limit"):
			adm_limit = adm_limit[2]
		else:
			adm_limit = default_adm

		await ctx.send(f"**Limits:\n• Mods: `{mod_limit}` daily bans;\n• Adms: `{adm_limit}` daily bans.\n{member.mention}**")
	
	@commands.command(aliases=['cdbl', 'change_ban_limit', 'change_bans_limit', 'edit_bans_limit'])
	@commands.has_permissions(administrator=True)
	async def change_daily_bans_limit(self, ctx, change_for: str = None, new_limit: str = None) -> None:
		""" Changes the daily bans limit for mods and admins.
		:param change_for: For whom to change it. (mod/adm) """

		member: discord.Member = ctx.author
		change_for_list: List[str] = ["mod", "adm"]

		if not change_for:
			return await ctx.send(
				f"**Please, inform who to change it to, {member.mention}!\n{', '.join(change_for_list)}**"
			)
		change_for = change_for.lower()

		if change_for not in change_for_list:
			return await ctx.send(f"**Please, inform a valid `change_for`, {member.mention}!\n{', '.join(change_for_list)}**")

		if not new_limit:
			return await ctx.send(f"**Please, inform a new limit ot set it to, {member.mention}!**")

		try:
			new_limit = int(new_limit)
		except ValueError:
			return await ctx.send(f"**Please, inform an integer value, {member.mention}!**")

		if new_limit < 0:
			return await ctx.send(f"**Please, inform a number greater than or equal to zero, {member.mention}!**")

		LevelSystem = self.client.get_cog('LevelSystem')
		if not await LevelSystem.table_important_vars_exists():
			return await ctx.send(f"**This command is not ready to be used yet, {member.mention}!**")

		if await LevelSystem.get_important_var(label=f"{change_for}_ban_limit"):
			# Update
			await LevelSystem.update_important_var(label=f"{change_for}_ban_limit", value_int=new_limit)
		else:
			# Insert
			await LevelSystem.insert_important_var(label=f"{change_for}_ban_limit", value_int=new_limit)

		await ctx.send(f"**Changed daily bans limit for `{change_for}` to `{new_limit}`!, {member.mention}!**")

"""
Setup:
b!create_table_mutedmembers
b!create_table_user_infractions
b!create_table_staff_member
b!create_table_firewall
"""
def setup(client) -> None:
	client.add_cog(Moderation(client))