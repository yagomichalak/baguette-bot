import discord
from discord.ext import commands

from mysqldb import the_database
from typing import List, Dict, Optional
import os
from cogs.misc import Misc

booster_role_id: int = int(os.getenv('BOOSTER_ROLE_ID'))
booster_color_role_id: int = int(os.getenv('BOOSTER_COLOR_ROLE_ID'))

class ColourRoles(commands.Cog):
	""" Category for Colour Roles management and commands. """

	def __init__(self, client) -> None:
		self.client = client

	@commands.Cog.listener()
	async def on_ready(self) -> None:

		LevelSystem = self.client.get_cog('LevelSystem')
		txt_color_roles = await LevelSystem.get_level_role_ids()
		vc_color_roles = await LevelSystem.get_vc_level_role_ids()
		all_color_ids = list(set(txt_color_roles + vc_color_roles))
		self.colour_roles = all_color_ids
		print('ColourRoles cog is online!')

	@commands.Cog.listener(name="on_member_update")
	async def on_member_update_color_roles(self, before, after):
		""" Checks whether the user got the Staff role. """

		if not after.guild:
			return

		# Get roles from now and then
		roles = before.roles
		roles2 = after.roles
		if len(roles2) < len(roles):
			old_role = None

			for r in roles:
				if r not in roles2:
					old_role = r
					break

			if old_role:
				if old_role.id == booster_role_id:
					try:
						await self.delete_user_colour_role(after.id, old_role.id)
					except:
						pass
		else:
			new_role = None

			for r2 in roles2:
				if r2 not in roles:
					new_role = r2
					break

			if new_role:
				if new_role.id in self.colour_roles:
					try:
						await self.insert_user_colour_role(after.id, new_role.id)
					except:
						pass

	@commands.Cog.listener(name="on_member_update_roles")
	async def on_member_update_booster_role(self, before, after):
		""" Adds or removes the Booster role from people when they get or 
		get removed the Booster role from them. """

		if not after.guild:
			return
		

		roles = before.roles
		roles2 = after.roles
		if len(roles2) == len(roles):
			return

		old_role = new_role = None

		# Gets the added role
		for r2 in roles2:
			if r2 not in roles:
				new_role = r2
				break

		# Gets the removed role
		for r in roles:
			if r not in roles2:
				old_role = r
				break

		if new_role: # Became a Booster
			if new_role.id == booster_role_id:
				await self.insert_user_colour_role(after.id, booster_color_role_id)
				pass

		if old_role: # Not a Booster anymore
			if old_role.id == booster_role_id:
				await self.delete_user_colour_role(after.id, booster_color_role_id)
				pass
	
	@commands.command(aliases=['colour', 'colour_inventory', 'color', 'colors', 'color_inventory', 'inventory', 'inv'])
	@commands.cooldown(1, 5, commands.BucketType.user)
	@Misc.check_whitelist()
	async def colours(self, ctx, member: Optional[discord.Member] = None) -> None:
		""" Shows all colour roles that the user has.
		:param member: The member to show the colours from. [Optional].
		PS: If member not provided, it'll show from who ran the command. """

		if not member:
			member = ctx.author

		colour_roles = await self.get_user_colour_roles(member.id)
		if not colour_roles:
			return await ctx.send(f"**{member.mention} doesn't have any colour role in their inventory!**")

		colours = [colour.mention for colour_role in colour_roles if (colour := discord.utils.get(ctx.guild.roles, id=colour_role[1]))]
		embed = discord.Embed(
			title="__Colour Role Inventory__",
			description=', '.join(colours),
			colour=member.colour,
			timestamp=ctx.message.created_at,
			url=member.display_avatar
		)

		embed.set_thumbnail(url=member.display_avatar)
		embed.set_footer(text=f"Requested by: {ctx.author}", icon_url=ctx.author.display_avatar)

		await ctx.send(embed=embed)

	@commands.command(aliases=['switch_colour', 'switchcolour', 'switch_color', 'switchcolor'])
	@commands.cooldown(1, 5, commands.BucketType.user)
	@Misc.check_whitelist()
	async def switch(self, ctx, *, colour_role: discord.Role = None) -> None:
		""" Switches your current role colour to a given one from your inventory.
		:param colour_role: The name/id/tag of the colour role to switch to. """

		member = ctx.author

		if not colour_role:
			return await ctx.send(f"**Please, inform a colour role, {member.mention}!**")

		if not await self.get_user_colour_role(member.id, colour_role.id):
			return await ctx.send(f"**You don't have that colour role, {member.mention}!**")

		if colour_role.id in [862742944243253279, 862742944729268234]:
			return await ctx.send(f"**You cannot switch to this role!**")

		try:
			await member.add_roles(colour_role)
		except Exception as e:
			print(e)
			await ctx.send(f"**For some reason I couldn't give you that role, {member.mention}!** 😭")


		roles_to_check: List[discord.Role] = [
			crole for colour_id in self.colour_roles 
			if colour_id != colour_role.id and (crole := discord.utils.get(ctx.guild.roles, id=colour_id))
		]

		for crole in roles_to_check:
			if crole in member.roles:
				if crole.id in [862742944243253279, 862742944729268234]:
					continue
				try:
					await member.remove_roles(crole)
				except:
					pass

		else:
			await ctx.send(f"**{member.mention} has switched their colour role to `{colour_role}`!**")

	@commands.command(aliases=['removecolour', 'delete_colour', 'del_colour', 'delcolour', 'remove_color', 'deletecolor', 'del_color', 'delcolor'])
	@commands.has_permissions(administrator=True)
	async def remove_colour(self, ctx, member: discord.Member = None, *, colour_role: discord.Role = None) -> None:
		""" Removes a Colour Role from a given member.
		:param member: The member to remove the Colour Role from.
		:param colour_role: The name/id/tag of the colour role to remove from the user. """

		if not member:
			return await ctx.send(f"**Please, inform a member, {ctx.author.mention}!**")

		if not colour_role:
			return await ctx.send(f"**Please, inform a colour role, {ctx.author.mention}!**")

		if not await self.get_user_colour_role(member.id, colour_role.id):
			return await ctx.send(f"**{member.mention} doesn't have that role, {ctx.author.mention}!**")

		if colour_role in member.roles:
			await self.delete_user_colour_role(member.id, colour_role.id)
			try:
				await member.remove_roles(colour_role)
			except Exception as e:
				print(e)
				await ctx.send(f"**For some reason I couldn't")
			
			await ctx.send(f"**Removed Colour Role `{colour_role}` from {member.mention}, {ctx.author.mention}!**")

	@commands.command(aliases=['removecolours', 'delete_colours', 'removecolors', 'remove_colors', 'deletecolours', 'del_colosr', 'delcolours'])
	@commands.has_permissions(administrator=True)
	async def remove_colours(self, ctx, member: discord.Member = None) -> None:
		""" Removes a Colour Role from a given member.
		:param member: The member to remove the Colour Role from. """

		if not member:
			return await ctx.send(f"**Please, inform a member, {ctx.author.mention}!**")

		if not (colour_role_ids := await self.get_user_colour_roles(member.id)):
			return await ctx.send(f"**{member.mention} doesn't have roles, {ctx.author.mention}!**")

		colour_roles: List[discord.Role] = [
			crole for colour_id in colour_role_ids 
			if (crole := discord.utils.get(ctx.guild.roles, id=colour_id[1]))
		]

		await self.delete_user_colour_roles(member.id)
		for colour_role in colour_roles:
			if colour_role in member.roles:
				try:
					await member.remove_roles(colour_role)
				except:
					pass

		else:	
			await ctx.send(f"**Removed Colour Role `{colour_role}` from {member.mention}, {ctx.author.mention}!**")


	# ===== Database commands/methods =====


	@commands.command(hidden=True, aliases=['create_table_color_roles'])
	@commands.has_permissions(administrator=True)
	async def create_table_colour_roles(self, ctx) -> None:
		""" (ADM) Creates the ColourRoles table. """

		if await self.check_table_colour_roles_exists():
			return await ctx.send("**Table __ColourRoles__ already exists!**")
		
		await ctx.message.delete()
		mycursor, db = await the_database()
		await mycursor.execute("""
		CREATE TABLE ColorRoles (
			user_id BIGINT NOT NULL,
			role_id BIGINT NOT NULL,
			PRIMARY KEY (user_id, role_id)
		)""")
		await db.commit()
		await mycursor.close()

		return await ctx.send("**Table __ColourRoles__ created!**", delete_after=3)

	@commands.command(hidden=True, aliases=['drop_table_color_roles'])
	@commands.has_permissions(administrator=True)
	async def drop_table_colour_roles(self, ctx) -> None:
		""" (ADM) Creates the ColourRoles table """

		if not await self.check_table_colour_roles_exists():
			return await ctx.send("**Table __ColourRoles__ doesn't exist!**")
		await ctx.message.delete()
		mycursor, db = await the_database()
		await mycursor.execute("DROP TABLE ColorRoles")
		await db.commit()
		await mycursor.close()

		return await ctx.send("**Table __ColourRoles__ dropped!**", delete_after=3)

	@commands.command(hidden=True, aliases=['reset_table_color_roles'])
	@commands.has_permissions(administrator=True)
	async def reset_table_colour_roles(self, ctx):
		'''
		(ADM) Resets the ColourRoles table.
		'''
		if not await self.check_table_colour_roles_exists():
			return await ctx.send("**Table __ColourRoles__ doesn't exist yet**")

		await ctx.message.delete()
		mycursor, db = await the_database()
		await mycursor.execute("DELETE FROM ColorRoles")
		await db.commit()
		await mycursor.close()

		return await ctx.send("**Table __ColourRoles__ reset!**", delete_after=3)

	async def check_table_colour_roles_exists(self) -> bool:
		'''
		Checks if the ColourRoles table exists
		'''
		mycursor, db = await the_database()
		await mycursor.execute("SHOW TABLE STATUS LIKE 'ColorRoles'")
		table_info = await mycursor.fetchall()
		await mycursor.close()

		if len(table_info) == 0:
			return False

		else:
			return True


	async def insert_user_colour_role(self, user_id: int, role_id: int) -> None:
		""" Inserts a colour role for a user into the database.
		:param user_id: The ID of the user to insert.
		:param role_id: The ID of the role to attach to the user. """

		mycursor, db = await the_database()
		await mycursor.execute("INSERT INTO ColorRoles (user_id, role_id) VALUES (%s, %s)", (user_id, role_id))
		await db.commit()
		await mycursor.close()

	async def get_user_colour_role(self, user_id: int, role_id: int) -> List[int]:
		""" Gets the a user's colour role from the database.
		:param user_id: The ID of the user to get the role from.
		:param role_id: The ID of the role to get from the user. """

		mycursor, db = await the_database()
		await mycursor.execute("SELECT * FROM ColorRoles WHERE user_id = %s AND role_id = %s", (user_id, role_id))
		colour_role = await mycursor.fetchone()
		await mycursor.close()
		return colour_role


	async def get_user_colour_roles(self, user_id: int) -> List[List[int]]:
		""" Gets the user's colour roles from the database.
		:param user_id: The ID of the user to get the roles from. """

		mycursor, db = await the_database()
		await mycursor.execute("SELECT * FROM ColorRoles WHERE user_id = %s", (user_id,))
		colour_roles = await mycursor.fetchall()
		await mycursor.close()
		return colour_roles

	async def delete_user_colour_role(self, user_id: int, role_id: int) -> None:
		""" Deletes a user's colour role.
		:param user_id: The ID of the user to delete the role from.
		:param role_id: The ID of the role to remove from the user. """

		mycursor, db = await the_database()
		await mycursor.execute("DELETE FROM ColorRoles WHERE user_id = %s and role_id = %s", (user_id, role_id))
		await db.commit()
		await mycursor.close()

	async def delete_user_colour_roles(self, user_id: int) -> None:
		""" Deletes the user's colour roles
		:param user_id: The ID of the user to delete the role from. """

		mycursor, db = await the_database()
		await mycursor.execute("DELETE FROM ColorRoles WHERE user_id = %s", (user_id,))
		await db.commit()
		await mycursor.close()


def setup(client) -> None:
	client.add_cog(ColourRoles(client))