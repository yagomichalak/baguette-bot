import discord
from discord.ext import commands
import os
from mysqldb import the_database
from typing import List, Dict, Union, Any

class TemporaryVc(commands.Cog):
	""" Category for managing temporary voice channels. """

	def __init__(self, client) -> None:
		""" Class initializing method. """

		self.client = client

		self.temp_vc_cat_id = int(os.getenv('TEMP_VC_CAT_ID'))
		self.temp_vc_id = int(os.getenv('TEMP_VC_ID'))
		self.db = TemporaryVcDatabase()


	@commands.Cog.listener()
	async def on_ready(self) -> None:
		""" Tells when the cog is ready to use. """

		print('TemporaryVc is online!')


	@commands.Cog.listener()
	async def on_voice_state_update(self, member, before, after) -> None:
		""" Checks whether the user is leaving the VC and whether there still are people in there. """

		# Checks channel and category


		if before.channel and before.channel.category:
			if before.channel.category.id == self.temp_vc_cat_id:
				if before.channel.id != self.temp_vc_id:
					vc = discord.utils.get(member.guild.channels, id=before.channel.id)
					# Checks whether the VC is empty
					if vc and len(vc.members) == 0:
						if temp_vc := await self.db.get_temp_vc_by_vc_id(vc.id):
							try:
								await vc.delete()
							except Exception:
								pass
							else:
								await self.db.delete_temp_vc(temp_vc[0], temp_vc[1])


		if after.channel and after.channel.category:
			# Creates a voice channel and moves the user into there
			if after.channel.id == self.temp_vc_id:
				if not (user := await self.client.get_cog('LevelSystem').get_specific_user(member.id)):
					return await member.send(f"**{member}, you're not in the system yet, try again!**")

				if user[0][2] < 1:
					return await member.send(f"**You need to be at least level 1 to use this command!")


				# Checks whether user has an existing temp vc
				if (temp_vc := await self.db.get_temp_vc_by_user_id(member.id)):
					if (vc := discord.utils.get(member.guild.channels, id=temp_vc[1])):
						try:
							await member.move_to(vc)
						except:
							await member.send(f"**This is your temp vc: {vc.mention}**")

						return

				category = discord.utils.get(member.guild.categories, id=self.temp_vc_cat_id)
				overwrites = await self.get_channel_perms(member)
				if (vc := await self.try_to_create(kind='voice', category=category, name=f"{member.display_name}'s VC", overwrites=overwrites)):
					await self.db.insert_temp_vc(member.id, vc.id)
					try:
						await member.move_to(vc)
					except:
						await member.send(f"**I created your temp vc, click here to join: {vc.mention}!**")
				else:
					await member.send(f"**Something wrong happened and I couldn't create your temp vc!")


	@commands.group(aliases=['vc', 'voice_channel', 'voicechannel'])
	async def voice(self, ctx) -> None:
		""" A command for managing temporary voice channels. """

		if ctx.invoked_subcommand:
			return

		cmd = self.client.get_command('voice')
		prefix = self.client.command_prefix
		subcommands = [f"{prefix}{c.qualified_name}" for c in cmd.commands
		      ]

		subcommands = '\n'.join(subcommands)
		embed = discord.Embed(
		  title="Subcommads",
		  description=f"```apache\n{subcommands}```",
		  color=ctx.author.color,
		  timestamp=ctx.message.created_at
		)
		await ctx.send(embed=embed)


	@voice.command(aliases=['c', 'crt', 'make', 'build'])
	async def create(self, ctx) -> None:
		""" Creates a temporary voice channel. """

		member = ctx.author

		if not (user := await self.client.get_cog('LevelSystem').get_specific_user(member.id)):
			return await ctx.send(f"**{member}, you're not in the system yet, try again!**")

		if user[0][2] < 1:
			return await ctx.send(f"**You need to be at least level 1 to use this command!")

		if temp_vc := await self.db.get_temp_vc_by_user_id(member.id):
			return await ctx.send(f"**You already have a temp vc, {member.mention}! (<#{temp_vc[1]}>)**")

		overwrites = await self.get_channel_perms(member)
		category = discord.utils.get(ctx.guild.categories, id=self.temp_vc_cat_id)
		if (vc := await self.try_to_create(kind='voice', category=category, name=f"{member.display_name}'s VC", overwrites=overwrites)):
			await self.db.insert_temp_vc(member.id, vc.id)
			await ctx.send(f"**Temp VC created, {member.mention}!** ({vc.mention})")
		else:
			await ctx.send(f"**Something went wrong and I couldn't create your temp vc, {member.mention}!**")

	@voice.command(aliases=['remove', 'rm', 'dell', 'dlt'])
	async def delete(self, ctx) -> None:
		""" Deletes a temporary voice channel. """

		member = ctx.author
		voice = member.voice

		if not voice or not voice.channel:
			return await ctx.send(f"**You're not in a voice channel, {member.mention}!**")
		if not (temp_vc := await self.db.get_temp_vc_by_vc_id(voice.channel.id)):
			return await ctx.send(f"**{voice.channel.mention} is not a temp vc, {member.mention}!**")

		vc = discord.utils.get(ctx.guild.channels, id=temp_vc[1])
		
		try:
			await vc.delete()
		except:
			await ctx.send(f"**Couldn't delete it, try it later, {member.mention}!**")
		else:
			await self.db.delete_temp_vc(temp_vc[0], temp_vc[1])
			await ctx.send(f"**Temp VC deleted, {member.mention}!**")

	@voice.command(aliases=['permit'])
	async def allow(self, ctx, member: discord.Member = None) -> None:
		""" Allows a member into your temp VC.
		:param member: The member to allow. """

		author = ctx.author
		if member.id == author.id:
			return await ctx.send(f"**You cannot allow yourself, {author.mention}!**")

		voice = author.voice
		if not voice or not voice.channel:
			return await ctx.send(f"**You're not in a voice channel, {author.mention}!**")

		if not (temp_vc := await self.db.get_temp_vc_by_vc_id(voice.channel.id)):
			return await ctx.send(f"**{voice.channel.mention} is not a temp vc, {author.mention}!**")

		if temp_vc[0] != author.id:
			return await ctx.send(f"**You're not the owner of this temp vc, {author.mention}!**")

		await voice.channel.set_permissions(member, connect=True, speak=True, view_channel=True)
		await ctx.send(f"**{member.mention} has been allowed to {voice.channel.mention}, {author.mention}!**")

	@voice.command(aliases=['prohibit', 'reject'])
	async def forbid(self, ctx, member: discord.Member = None) -> None:
		""" Forbids a member from your temp VC.
		:param member: The member to forbid. """

		author = ctx.author
		if member.id == author.id:
			return await ctx.send(f"**You cannot forbid yourself, {author.mention}!**")

		voice = author.voice
		if not voice or not voice.channel:
			return await ctx.send(f"**You're not in a voice channel, {author.mention}!**")

		if not (temp_vc := await self.db.get_temp_vc_by_vc_id(voice.channel.id)):
			return await ctx.send(f"**{voice.channel.mention} is not a temp vc, {author.mention}!**")

		if temp_vc[0] != author.id:
			return await ctx.send(f"**You're not the owner of this temp vc, {author.mention}!**")

		member_voice = member.voice
		if member_voice and member_voice.channel:
			if member_voice.channel.id == voice.channel.id:
				try:
					await member.move_to(None)
				except:
					pass

		await voice.channel.set_permissions(member, connect=False, speak=False, view_channel=True)
		await ctx.send(f"**{member.mention} has been forbade from {voice.channel.mention}, {author.mention}!**")

	@voice.command()
	async def claim(self, ctx) -> None:
		""" Takes the possession of an abandonned temp vc. """

		member = ctx.author
		voice = member.voice
		if not voice or not voice.channel:
			return await ctx.send(f"**You're not in a voice channel, {member.mention}!**")

		if not (temp_vc := await self.db.get_temp_vc_by_vc_id(voice.channel.id)):
			return await ctx.send(f"**{voice.channel.mention} is not a temp vc, {member.mention}!**")

		if temp_vc[0] == member.id:
			return await ctx.send(f"**You're already the owner of this temp vc, {member.mention}!**")


		owner = discord.utils.get(ctx.guild.members, id=temp_vc[0])

		if not owner or owner not in voice.channel.members:
			await self.db.update_temp_vc_owner_id(owner.id, member.id, voice.channel.id)
			await voice.channel.set_permissions(owner, overwrite=None)
			await voice.channel.set_permissions(member, manage_channels=True)
			await ctx.send(f"**You just claimed {voice.channel.mention}, {member.mention}!**")
		else:
			await ctx.send(f"**{owner} is still in their temp vc, {member.mention}!**")

	@voice.command()
	async def limit(self, ctx, limit: int = None) -> None:
		""" Changes the user limit of your temp VC.
		:param limit: The new limit to set your temp vc to. """

		member = ctx.author
		voice = member.voice

		if not voice or not voice.channel:
			return await ctx.send(f"**You're not in a voice channel, {member.mention}!**")

		if limit is None:
			return await ctx.send(f"**Please, inform a `limit`, {member.mention}!**")

		if limit < 0 or limit > 99:
			return await ctx.send(f"**The `limit` must be between 0 and 99, {member.mention}!**")

		if not (temp_vc := await self.db.get_temp_vc_by_vc_id(voice.channel.id)):
			return await ctx.send(f"**{voice.channel.mention} is not a temp vc, {member.mention}!**")

		vc = discord.utils.get(ctx.guild.channels, id=temp_vc[1])
		try:
			await vc.edit(user_limit=limit)
		except:
			await ctx.send(f"**Something went wrong with it and I couldn't change the limit of it, {member.mention}!**")
		else:
			await ctx.send(f"**Your temp vc user limit has been set to `{limit}`, {member.mention}!**")

	@voice.command()
	@commands.cooldown(2, 600, commands.BucketType.user)
	async def name(self, ctx, *, name: str = None) -> None:
		""" Renames your temp VC.
		:param name: The new name to set your temp vc to. """


		member = ctx.author
		voice = member.voice

		if not voice or not voice.channel:
			return await ctx.send(f"**You're not in a voice channel, {member.mention}!**")
		
		if name is None:
			return await ctx.send(f"**Please, inform a `name`, {member.mention}!**")
		if len(name) > 100:
			return await ctx.send(f"**The `name` must have a maximum length of `100` characters, {member.mention}!**")

		if not (temp_vc := await self.db.get_temp_vc_by_vc_id(voice.channel.id)):
			return await ctx.send(f"**{voice.channel.mention} is not a temp vc, {member.mention}!**")

		vc = discord.utils.get(ctx.guild.channels, id=temp_vc[1])
		try:
			await vc.edit(name=name)
		except Exception as e:
			print('rename', e)
			await ctx.send(f"**Something went wrong with it and I couldn't rename it, {member.mention}!**")
		else:
			await ctx.send(f"**Your temp vc has been renamed to `{name}`, {member.mention}!**")





	async def try_to_create(self, kind: str, category: discord.CategoryChannel = None, guild: discord.Guild = None, **kwargs: Any) -> Union[bool, Any]:
		""" Try to create something.
		:param thing: The thing to try to create.
		:param kind: Kind of creation. (txt, vc, cat)
		:param category: The category in which it will be created. (Optional)
		:param guild: The guild in which it will be created in. (Required for categories)
		:param kwargs: The arguments to inform the creations. """

		try:
			if kind == 'text':
				the_thing = await category.create_text_channel(**kwargs)
			elif kind == 'voice':
				the_thing = await category.create_voice_channel(**kwargs)
			elif kind == 'category':
				the_thing = await guild.create_category(**kwargs)
		except Exception as e:
			print(e)
			return False
		else:
			return the_thing

	async def delete_things(self, things: List[Any]) -> None:
		""" Deletes a list of things.
		:param things: The things to delete. """

		for thing in things:
			try:
				await thing.delete()
			except:
				pass

	async def get_channel_perms(self, member: discord.Member) -> Dict[Union[discord.Role, discord.Member], discord.PermissionOverwrite]:
		""" Gets permissions for the temporary voice channel.
		:param member: The voice channel's owner. """

		muted_role = discord.utils.get(member.guild.roles, id=int(os.getenv('MUTED_ROLE_ID')))

		overwrites = {
			member.guild.default_role: discord.PermissionOverwrite(
				connect=None, speak=None, view_channel=True),

			muted_role: discord.PermissionOverwrite(
				connect=False, speak=None, view_channel=True),

			member: discord.PermissionOverwrite(
				connect=True, speak=True, view_channel=True, manage_channels=True)
		}

		return overwrites

	@commands.command(hidden=True)
	@commands.is_owner()
	async def create_table_temp_vc(self, ctx) -> None:
		""" Command for creating the TemporaryVc table. """

		member = ctx.author
		if await self.db.create_temp_vc_table():
			await ctx.send(f"**`TemporaryVc` table created, {member.mention}!**")
		else:
			await ctx.send(f"**`TemporaryVc` table already exists, {member.mention}!**")


	@commands.command(hidden=True)
	@commands.is_owner()
	async def drop_table_temp_vc(self, ctx) -> None:
		""" Command for creating the TemporaryVc table. """

		member = ctx.author
		if await self.db.drop_temp_vc_table():
			await ctx.send(f"**`TemporaryVc` table dropped, {member.mention}!**")
		else:
			await ctx.send(f"**`TemporaryVc` table doesn't exist, {member.mention}!**")

	@commands.command(hidden=True)
	@commands.is_owner()
	async def reset_table_temp_vc(self, ctx) -> None:
		""" Command for creating the TemporaryVc table. """

		member = ctx.author
		if await self.db.delete_temp_vc_table():
			await ctx.send(f"**`TemporaryVc` table reset, {member.mention}!**")
		else:
			await ctx.send(f"**`TemporaryVc` table doesn't exist yet, {member.mention}!**")


class TemporaryVcDatabase:
	""" A class for managing data in the database. """

	# ===== CREATE =====
	async def create_temp_vc_table(self) -> bool:
		""" Creates the TemporaryVc table. """

		mycursor, db = await the_database()
		try:
			await mycursor.execute("CREATE TABLE TemporaryVc (user_id BIGINT, vc_id BIGINT)")
		except:
			return False
		else:
			return True
		finally:
			await db.commit()
			await mycursor.close()

	async def insert_temp_vc(self, user_id: int, vc_id: int) -> None:
		""" Inserts a temp voice channel into the database.
		:param user_id: The voice channel's owner's ID.
		:param vc_id: The voice channel ID. """

		mycursor, db = await the_database()
		await mycursor.execute("INSERT INTO TemporaryVc (user_id, vc_id) VALUES (%s, %s)", (user_id, vc_id))
		await db.commit()
		await mycursor.close()

	# ===== READ =====
	async def get_temp_vc_by_user_id(self, user_id: int) -> List[int]:
		""" Gets a temporary VC by user ID.
		:param user_id: The user ID. """

		mycursor, db = await the_database()
		await mycursor.execute("SELECT * FROM TemporaryVc WHERE user_id = %s", (user_id,))
		temp_vc = await mycursor.fetchone()
		await mycursor.close()
		return temp_vc

	async def get_temp_vc_by_vc_id(self, vc_id: int) -> List[int]:
		""" Gets a temporary VC by voice channel ID.
		:param vc_id: The voice channel ID. """

		mycursor, db = await the_database()
		await mycursor.execute("SELECT * FROM TemporaryVc WHERE vc_id = %s", (vc_id,))
		temp_vc = await mycursor.fetchone()
		await mycursor.close()
		return temp_vc

	# ===== UPDATE =====
	async def update_temp_vc_owner_id(self, old_user_id: int, new_user_id: int, vc_id: int) -> None:
		""" Updates the owner of a given voice channel to a new one.
		:param old_user_id: The old owner's ID.
		:param new_user_id: The new onwer's ID.
		:param vc_id: The voice channel ID. """

		mycursor, db = await the_database()
		await mycursor.execute("UPDATE TemporaryVc SET user_id = %s WHERE user_id = %s AND vc_id = %s", (new_user_id, old_user_id, vc_id))
		await db.commit()
		await mycursor.close()

	# ===== DELETE =====
	async def drop_temp_vc_table(self) -> bool:
		""" Drops the TemporaryVc table. """

		mycursor, db = await the_database()
		try:
			await mycursor.execute("DROP TABLE TemporaryVc")
		except:
			return False
		else:
			return True
		finally:
			await db.commit()
			await mycursor.close()

	async def delete_temp_vc_table(self) -> bool:
		""" Deletes everything from the TemporaryVc table. """

		mycursor, db = await the_database()
		try:
			await mycursor.execute("DELETE FROM TemporaryVc")
		except:
			return False
		else:
			return True
		finally:
			await db.commit()
			await mycursor.close()

	async def delete_temp_vc(self, user_id: int, vc_id: int) -> None:
		""" Deletes a temporary VC.
		:param user_id: The voice channel's owner ID.
		:param vc_id: The voice channel ID. """

		mycursor, db = await the_database()
		await mycursor.execute("DELETE FROM TemporaryVc WHERE user_id = %s AND vc_id = %s", (user_id, vc_id))
		await db.commit()
		await mycursor.close()

	async def delete_temp_vcs(self, user_id: int) -> None:
		""" Deletes all temporary VC from a user.
		:param user_id: The user ID. """

		mycursor, db = await the_database()
		await mycursor.execute("DELETE FROM TemporaryVc WHERE user_id = %s", (user_id,))
		await db.commit()
		await mycursor.close()

"""
Setup:
b!create_table_temp_vc
"""
def setup(client) -> None:
	""" Cog's setup function. """

	client.add_cog(TemporaryVc(client))
