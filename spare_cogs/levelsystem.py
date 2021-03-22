import discord
from discord.ext import commands, menus
from mysqldb import the_database
from extra.menu import Confirm, SwitchPages
from typing import List, Dict, Union, Any
import time
from datetime import datetime
import asyncio


class LevelSystem(commands.Cog):

	def __init__(self, client) -> None:
		self.client = client


	@commands.Cog.listener()
	async def on_ready(self) -> None:
		print('LevelSystem cog is online')



	# In-game commands
	@commands.Cog.listener()
	async def on_message(self, message):

		# return

		if not message.guild:
			return
			
		if message.author.bot:
			return
		elif not await self.table_member_status_exists():
			return


		# user_info = await self.get_user_activity_info(message.author.id)
		# if not user_info:
		# 	return await self.insert_user_server_activity(message.author.id, 1)

		# await self.update_user_server_messages(message.author.id, 1) 

		epoch = datetime.utcfromtimestamp(0)
		time_xp = (datetime.utcnow() - epoch).total_seconds()
		await self.update_data(message.author, time_xp, message.channel)

	async def update_data(self, user, time_xp, channel: discord.TextChannel):
		the_member = await self.get_specific_user(user.id)

		if the_member:
			if time_xp - the_member[0][3] >= 3 or the_member[0][1] == 0:
				await self.update_user_xp_time(user.id, time_xp)
				await self.update_user_xp(user.id, 5)
				return await self.level_up(user, channel)
		else:
			return await self.insert_user(user.id, 5, 1, time_xp)

	async def level_up(self, user: discord.Member, channel: discord.TextChannel) -> None:
		epoch = datetime.utcfromtimestamp(0)
		the_user = await self.get_specific_user(user.id)
		lvl_end = int(the_user[0][1] ** (1 / 5))
		if the_user[0][2] < lvl_end:
			await self.update_user_lvl(user.id, the_user[0][2]+1)
			await self.check_level_role(user, the_user[0][2]+1)
			return await channel.send(f"**{user.mention} has leveled up to lvl {the_user[0][2] + 1}!**")

	async def check_level_role(self, member: discord.Member, level: int) -> Union[None, int]:
		""" Checks if the member level has a role attached to it
		and gives the role to the member if so.
		:param member: The member to check.
		:param level: The current level of the member. """


		role_id = None
		list_index = 0


		level_roles = await self.select_level_role()
		for i, level_r in enumerate(level_roles):
			if level >= level_r[0]:
				role_id = level_r[1]
				list_index = i


		if not role_id or not (current_role := discord.utils.get(member.guild.roles, id=role_id)):
			return

		if current_role in member.roles:
			return

		try:
			await member.add_roles(current_role)
		except Exception as e:
			print(e)
		else:
			if list_index and (previous_role_id := level_roles[list_index-1][1]):
				if previous_role := discord.utils.get(member.guild.roles, id=previous_role_id):
					if previous_role in member.roles:
						try:
							await member.remove_roles(previous_role)
						except Exception as ee:
							print(ee)

			return role_id




	@commands.command(aliases=['profile'])
	async def level(self, ctx, member: discord.Member = None) -> None:
		""" Shows a user profile. 
		:param member: The member to show the profile. [Optional]
		PS: if a member is not passed as an argument, it will show the profile of the command's executor. """

		# Checks if the Ranking table exists.
		if not await self.table_member_status_exists():
			return await ctx.send("**This command may be on maintenance!**", delete_after=3)

		# If not specified a member - then it's you!
		if not member:
			member = ctx.author

		# Waits half of a second to avoid bugs
		await asyncio.sleep(0.5)
		
		# Tries to get the user's data from the database.
		if not (user := await self.get_specific_user(member.id)):
			return await ctx.send(f"**{member} is not in the system, maybe they have to use the command by themselves!**")


		# Arranges the user's information into a well-formed embed
		embed = discord.Embed(title="__Profile__", colour=member.color, timestamp=ctx.message.created_at)
		embed.add_field(name="__**Level**__", value=f"{user[0][2]}.", inline=True)
		embed.add_field(name="__**EXP**__", value=f"{user[0][1]} / {((user[0][2]+1)**5)}.", inline=True)
		embed.set_thumbnail(url=member.avatar_url)
		embed.set_footer(text=f"{member}", icon_url=member.avatar_url)
		return await ctx.send(embed=embed)

	@commands.command(aliases=['score', 'level_board', 'levelboard', 'levels', 'level_score'])
	async def leaderboard(self, ctx):
		""" Shows the top ten members in the level leaderboard. """

		# users = await self.get_users()

		all_users = await self.get_all_users_by_xp()
		position = [[i+1, u[1]] for i, u in enumerate(all_users) if u[0] == ctx.author.id]
		position = [it for subpos in position for it in subpos] if position else ['??', 0]

		# Additional data:
		additional = {
			'change_embed': self._make_level_score_embed,
			'position': position
		}

		pages = menus.MenuPages(source=SwitchPages(all_users, **additional), clear_reactions_after=True)
		await pages.start(ctx)


	@commands.command()
	@commands.has_permissions(administrator=True)
	async def setlevel(self, ctx, member: discord.Member = None, level: int = None) -> None:
		""" Sets a level to a user.
		:param member: The member to whom the level is gonna be set.
		:param level: The new level to which the user's level is gonna be set.
		"""

		if not member:
			return await ctx.send(f"**Please, inform a member to set a new level value, {ctx.author.mention}!**")

		if not level:
			return await ctx.send(f"**Please, inform the level that you want the user to have, {ctx.author.mention}!**")

		if level <= 0:
			return await ctx.send(f"**Please, inform a positive number greater than 0, {ctx.author.mention}!**")


		if not (the_user := await self.get_specific_user(member.id)):
			return await ctx.send(f"**Member is not in the system yet, {ctx.author.mention}!**")

		if level >= the_user[0][2]:
			await self.update_user_lvl(member.id, level)
			await asyncio.sleep(0.1)
			await self.set_user_xp(member.id, ((level-1)** 5))

		else:
			await self.set_user_xp(member.id, ((level-1)** 5))
			await asyncio.sleep(0.1)
			await self.update_user_lvl(member.id, level)

		print((level-1)** 5)
		print((level)** 5)
		await asyncio.sleep(0.1)
		updated = await self.check_level_role(member, level)
		if updated:
			all_level_roles = await self.select_level_role()
			# excluded = [lvl_role[1] for lvl_role in all_level_roles if lvl_role[1] != updated]

			# await member.remove_roles(excluded, atomic=True)




			level_roles = set(
				[a_role for lvl_role in all_level_roles if (
					a_role := discord.utils.get(member.guild.roles, id=lvl_role[1])
					) and lvl_role[1] != updated
				]
			)
			member_roles = member.roles
			excluded = level_roles & set(member_roles)
			if excluded:
				for ex in excluded:
					if ex in member_roles:
						member_roles.remove(ex)
				await member.edit(roles=member_roles)

		await ctx.send(f"**The member {member.mention} is now level {level}!**")

	async def set_user_xp(self, user_id: int, the_xp: int) -> None:
		""" Sets the user's XP with the given number. 
		:param user_id: The user's ID. 
		:param the_xp: The new XP value to which set the user's level. """

		mycursor, db = await the_database()
		await mycursor.execute("UPDATE MemberStatus SET user_xp = %s WHERE user_id = %s", (the_xp, user_id))
		await db.commit()
		await mycursor.close()

	async def _make_level_score_embed(self, ctx: commands.Context, entries, offset: int, lentries: int, kwargs) -> discord.Embed:
		""" Makes an embedded message for the level scoreboard. """

		position = kwargs.get('position')

		# tribe_embed.set_footer(text=f"Requested by {ctx.author}", icon_url=ctx.author.avatar_url)
		member = ctx.author

		leaderboard = discord.Embed(
			title="__The Language Sloth's Level Ranking Leaderboard__",
			description="All registered users and their levels and experience points.",
			colour=ctx.author.color, timestamp=ctx.message.created_at)


		leaderboard.description += f"\n**Your XP:** `{position[1]}` | **#**`{position[0]}`"
		leaderboard.set_thumbnail(url=ctx.guild.icon_url)
		leaderboard.set_author(name=ctx.author, icon_url=ctx.author.avatar_url)

		# Embeds each one of the top ten users.
		for i, sm in enumerate(entries, start=offset):
			member = discord.utils.get(ctx.guild.members, id=sm[0])
			leaderboard.add_field(name=f"[{i}]# - __**{member}**__", value=f"__**Level:**__ `{sm[2]}` | __**XP:**__ `{sm[1]}`",
								  inline=False)

		for i, v in enumerate(entries, start=offset):
			leaderboard.set_footer(text=f"({i} of {lentries})")


		return leaderboard
	

	@commands.has_permissions(administrator=True)
	@commands.command(hidden=True)
	async def create_table_member_status(self, ctx):
		""" (ADM) Creates the MemberStatus table. """

		if await self.table_member_status_exists():
			return await ctx.send("**The `MemberStatus` table already exists!**")

		mycursor, db = await the_database()
		await mycursor.execute(
			"CREATE TABLE MemberStatus (user_id bigint, user_xp bigint, user_lvl int, user_xp_time int)")
		await db.commit()
		await mycursor.close()
				
		await ctx.send("**Table `MemberStatus` created!**")

	@commands.has_permissions(administrator=True)
	@commands.command(hidden=True)
	async def drop_table_member_status(self, ctx):
		""" (ADM) Drops the MemberStatus table. """

		if not await self.table_member_status_exists():
			return await ctx.send("**The `MemberStatus` table doesn't exist!**")

		mycursor, db = await the_database()
		await mycursor.execute("DROP TABLE MemberStatus")
		await db.commit()
		await mycursor.close()

		await ctx.send("**Table `MemberStatus` dropped!**")

	@commands.has_permissions(administrator=True)
	@commands.command(hidden=True)
	async def reset_table_member_status(self, ctx):
		""" (ADM) Resets the MemberStatus table. """


		if not await self.table_member_status_exists():
			return await ctx.send("**The `MemberStatus` table doesn't exist yet!**")

		mycursor, db = await the_database()
		await mycursor.execute("DELETE FROM MemberStatus")
		await db.commit()
		await mycursor.close()

		await ctx.send("**Table `MemberStatus` reseted!**")

	async def table_member_status_exists(self) -> bool:
		""" Checks whether the LevelRoles table exists. """

		mycursor, db = await the_database()
		await mycursor.execute(f"SHOW TABLE STATUS LIKE 'MemberStatus'")
		table_info = await mycursor.fetchall()
		await mycursor.close()
		if len(table_info) == 0:
				return False
		else:
			return True

	async def insert_user(self, user_id: int, xp: int, lvl: int, xp_time: int):
		mycursor, db = await the_database()
		await mycursor.execute(
			"""INSERT INTO MemberStatus (user_id, user_xp, user_lvl, user_xp_time) VALUES (%s, %s, %s, %s)""", 
			(user_id, xp, lvl, xp_time))
		await db.commit()
		await mycursor.close()

	async def update_user_xp(self, user_id: int, xp: int):
		mycursor, db = await the_database()
		await mycursor.execute("UPDATE MemberStatus SET user_xp = user_xp + %s WHERE user_id = %s", (xp, user_id))
		await db.commit()
		await mycursor.close()

	async def update_user_lvl(self, user_id: int, level: int):
		mycursor, db = await the_database()
		await mycursor.execute("UPDATE MemberStatus set user_lvl = %s WHERE user_id = %s", (level, user_id))
		await db.commit()
		await mycursor.close()


	async def update_user_xp_time(self, user_id: int, time: int):
		mycursor, db = await the_database()
		await mycursor.execute("UPDATE MemberStatus SET user_xp_time = %s WHERE user_id = %s", (time, user_id))
		await db.commit()
		await mycursor.close()

	async def update_user_score_points(self, user_id: int, score_points: int):
		mycursor, db = await the_database()
		await mycursor.execute("UPDATE MemberStatus SET score_points = score_points + %s WHERE user_id = %s", (score_points, user_id))
		await db.commit()
		await mycursor.close()


	async def remove_user(self, user_id: int):
		mycursor, db = await the_database()
		await mycursor.execute("DELETE FROM MemberStatus WHERE user_id = %s", (user_id,))
		await db.commit()
		await mycursor.close()

	async def clear_user_lvl(self, user_id: int):
		mycursor, db = await the_database()
		await mycursor.execute("UPDATE MemberStatus SET user_xp = 0, user_lvl = 1 WHERE user_id = %s", (user_id,))
		await db.commit()
		await mycursor.close()

	async def get_users(self):
		mycursor, db = await the_database()
		await mycursor.execute("SELECT * FROM MemberStatus")
		members = await mycursor.fetchall()
		await mycursor.close()
		return members


	async def get_specific_user(self, user_id: int):
		mycursor, db = await the_database()
		await mycursor.execute("SELECT * FROM MemberStatus WHERE user_id = %s", (user_id,))
		member = await mycursor.fetchall()
		await mycursor.close()
		return member

	async def get_specific_user(self, user_id: int):
		mycursor, db = await the_database()
		await mycursor.execute("SELECT * FROM MemberStatus WHERE user_id = %s", (user_id,))
		member = await mycursor.fetchall()
		await mycursor.close()
		return member


	async def get_all_users_by_xp(self) -> List[List[int]]:
		""" Gets all users from the MembersScore table ordered by XP. """

		mycursor, db = await the_database()
		await mycursor.execute("SELECT * FROM MemberStatus ORDER BY user_xp DESC")
		users = await mycursor.fetchall()
		await mycursor.close()
		return users





	@commands.command(aliases=['setlevelrole', 'set_levelrole', 'set_lvlrole', 'set_lvl_role'])
	@commands.has_permissions(administrator=True)
	async def set_level_role(self, ctx, level: int = None, role: discord.Role = None) -> None:
		""" Sets a level role to the level system.
		:param level: The level to set.
		:param role: The role to attach to the level. """

		member = ctx.author

		if not level:
			return await ctx.send(f"**Please, inform a level, {member.mention}!**")

		if not role:
			return await ctx.send(f"**Please, inform a role, {member.mention}!**")

		if await self.select_specific_level_role(level=level):
			return await ctx.send(f"**There already is a role attached to the level `{level}`, {member.mention}!**")


		confirm = await Confirm(f"**Set level `{level}` to role `{role.name}`, {member.mention}?**").prompt(ctx)
		if not confirm:
			return

		try:
			await self.insert_level_role(level, role.id)
		except Exception as e:
			print(e)
			await ctx.send(f"**Something went wrong with it, {member.mention}!**")
		else:
			await ctx.send(f"**Set level `{level}` to role `{role.name}`, {member.mention}!**")

	@commands.command(aliases=['unsetlevelrole', 'unset_levelrole', 'delete_levelrole', 'delete_level_role'])
	@commands.has_permissions(administrator=True)
	async def unset_level_role(self, ctx, level: int = None) -> None:
		""" Sets a level role to the level system.
		:param level: The level to set. """

		member = ctx.author

		if not level:
			return await ctx.send(f"**Please, inform a level, {member.mention}!**")

		if not (level_role := await self.select_specific_level_role(level=level)):
			return await ctx.send(f"**There isn't a role attached to the level `{level}` yet, {member.mention}!**")

		role = discord.utils.get(ctx.guild.roles, id=level_role[1])

		confirm = await Confirm(f"**Unset level `{level}` from role `{role.name if role else level_role[1]}`, {member.mention}?**").prompt(ctx)
		if not confirm:
			return

		try:
			await self.delete_level_role(level=level)
		except Exception as e:
			print(e)
			await ctx.send(f"**Something went wrong with it, {member.mention}!**")
		else:
			await ctx.send(f"**Unset level `{level}` from `{role.name if role else level_role[1]}`, {member.mention}!**")



	@commands.command(aliases=['showlevelroles', 'showlvlroles', 'show_lvlroles', 'level_roles', 'levelroles'])
	@commands.has_permissions(administrator=True)
	async def show_level_roles(self, ctx) -> None:
		""" Shows the existing level roles. """

		member = ctx.author

		embed = discord.Embed(
			title="__Level Roles Menu__",
			description="All level roles that were set.",
			color=member.color,
			timestamp=ctx.message.created_at
		)

		level_roles = await self.select_level_role()
		for lvl_role in level_roles:
			embed.add_field(name=f"Level {lvl_role[0]}", value=f"**Role:** <@&{lvl_role[1]}>", inline=True)


		await ctx.send(embed=embed)


	# Database

	async def select_specific_level_role(self, level: int = None, role_id: int = None) -> List[int]:
		""" Selects a specific level role from the database by level or role ID. """

		mycursor, db = await the_database()
		if level:
			await mycursor.execute("SELECT * FROM LevelRoles WHERE level = %s", (level,))
		elif role_id:
			await mycursor.execute("SELECT * FROM LevelRoles WHERE role_id = %s", (role_id,))

		level_role = await mycursor.fetchone()
		await mycursor.close()
		return level_role

	async def select_level_role(self) -> List[List[int]]:
		""" Selects level roles from the database. """

		mycursor, db = await the_database()
		await mycursor.execute("SELECT * FROM LevelRoles ORDER BY level")
		level_roles = await mycursor.fetchall()
		await mycursor.close()
		return level_roles


	async def insert_level_role(self, level: int, role_id: int) -> None:
		""" Inserts a level role into the database.
		:param level: The level to insert.
		:param role_id: The ID of the role to attach to the level. """

		mycursor, db = await the_database()
		await mycursor.execute("INSERT INTO LevelRoles (level, role_id) VALUES (%s, %s)", (level, role_id))
		await db.commit()
		await mycursor.close()

	async def delete_level_role(self, level: int = None, role_id: int = None) -> None:
		""" Deletes a level role into the database by level or role ID.
		:param level: The level to delete. """

		mycursor, db = await the_database()
		if level:
			await mycursor.execute("DELETE FROM LevelRoles WHERE level = %s", (level,))
		elif role_id:
			await mycursor.execute("DELETE FROM LevelRoles WHERE role_id = %s", (role_id,))
		await db.commit()
		await mycursor.close()


	@commands.command(hidden=True)
	@commands.has_permissions(administrator=True)
	async def create_table_level_roles(self, ctx) -> None:
		""" Creates the LevelRoles table. """

		if await self.table_level_roles_exists():
			return await ctx.send("**The `LevelRoles` table already exists!**")

		mycursor, db = await the_database()
		await mycursor.execute("""
			CREATE TABLE LevelRoles (level int NOT NULL, role_id bigint NOT NULL)""")
		await db.commit()
		await mycursor.close()
		await ctx.send("**Created `LevelRoles` table!**")

	@commands.command(hidden=True)
	@commands.has_permissions(administrator=True)
	async def drop_table_level_roles(self, ctx) -> None:
		""" Drops the LevelRoles table. """

		if not await self.table_level_roles_exists():
			return await ctx.send("**The `LevelRoles` table doesn't exist!**")

		mycursor, db = await the_database()
		await mycursor.execute("DROP TABLE LevelRoles")
		await db.commit()
		await mycursor.close()
		await ctx.send("**Dropped `LevelRoles` table!**")

	@commands.command(hidden=True)
	@commands.has_permissions(administrator=True)
	async def reset_table_level_roles(self, ctx) -> None:
		""" Resets the LevelRoles table. """

		if not await self.table_level_roles_exists():
			return await ctx.send("**The `LevelRoles` table doesn't exist yet!**")

		mycursor, db = await the_database()
		await mycursor.execute("DELETE FROM LevelRoles")
		await db.commit()
		await mycursor.close()
		await ctx.send("**Reset `LevelRoles` table!**")

	async def table_level_roles_exists(self) -> bool:
		""" Checks whether the LevelRoles table exists. """

		mycursor, db = await the_database()
		await mycursor.execute(f"SHOW TABLE STATUS LIKE 'LevelRoles'")
		table_info = await mycursor.fetchall()
		await mycursor.close()
		if len(table_info) == 0:
				return False
		else:
			return True


def setup(client) -> None:
	client.add_cog(LevelSystem(client))