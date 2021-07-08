import discord
from discord.ext import commands
from typing import Dict
from mysqldb import the_database
from typing import List, Optional
from cogs.misc import Misc


class ColourRoles(commands.Cog):
	""" Category for Colour Roles management and commands. """

	def __init__(self, client) -> None:
		self.client = client
		self.colour_roles: Dict[str, int] = {
			"Kraken Purple": 838076939553603616,
			"Dark Aqua": 838076937787932672,
			"Royal Azure": 755573019526823967,
			"Mahogany": 755812366813364416,
			"Mint Blue": 755818573129318420,
			"Silent": 732910420037337118,
			"Shy": 732910493257302076,
			"Discreet": 732916420110712852,
			"Quiet": 732916589262798898,
			"Talkative": 733022810934607943,
			"Chatterbox": 733022972675227694,
			"Smooth Talker": 740186380445024336,
			"Charisma Bomb": 770113783074783232,
			"Tsunami of Charisma": 740186445784023071,
			"Charisma over 9000": 740186469649350696,
			"Charisma Superior": 740186498498035793,
			"Event Winner": 764120155428356107,
			"Patron Black": 862731111339393034 ,
			"Booster Pink": 862732594188648478 ,
		}


	@commands.Cog.listener()
	async def on_ready(self) -> None:
		print('ColourRoles cog is online!')

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
			if new_role.id in self.colour_roles.values():
				try:
					await self.insert_user_colour_role(after.id, new_role.id)
				except:
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
			url=member.avatar_url
		)

		embed.set_thumbnail(url=member.avatar_url)
		embed.set_footer(text=f"Requested by: {ctx.author}", icon_url=ctx.author.avatar_url)

		await ctx.send(embed=embed)

	@commands.command(aliases=['switch_colour', 'switchcolour', 'switch_color', 'switchcolor'])
	@commands.cooldown(1, 5, commands.BucketType.user)
	@Misc.check_whitelist()
	async def switch(self, ctx, colour_role: discord.Role = None) -> None:
		""" Switches your current role colour to a given one from your inventory.
		:param colour_role: The name/id/tag of the colour role to switch to. """

		member = ctx.author

		if not colour_role:
			return await ctx.send(f"**Please, inform a colour role, {member.mention}!**")

		if not await self.get_user_colour_role(member.id, colour_role.id):
			return await ctx.send(f"**You don't have that colour role, {member.mention}!**")

		if colour_role in member.roles:
			await ctx.send(f"**You are already using that colour role, {member.mention}!**")
		else:
			try:
				await member.add_roles(colour_role)
			except Exception as e:
				print(e)
				await ctx.send(f"**For some reason I couldn't give you that role, {member.mention}!** 😭")
			else:
				previous_role = None

				roles_to_check: List[discord.Role] = [
					crole for colour_id in self.colour_roles.values() 
					if colour_id != colour_role.id and (crole := discord.utils.get(ctx.guild.roles, id=colour_id))
				]

				for crole in roles_to_check:
					if crole in member.roles:
						try:
							await member.remove_roles(crole)
						except:
							pass


				if previous_role:
					await ctx.send(f"**{member.mention} has switched their colour role from `{previous_role}` to `{colour_role}`!**")
				else:
					await ctx.send(f"**{member.mention} has switched their colour role to `{colour_role}`!**")
		
	@commands.command(aliases=['removecolour', 'delete_colour', 'del_colour', 'delcolour', 'remove_color', 'deletecolor', 'del_color', 'delcolor'])
	@commands.has_permissions(administrator=True)
	async def remove_colour(self, ctx, member: discord.Member = None, colour_role: discord.Role = None) -> None:
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
			except:
				pass
			
			await ctx.send(f"**Removed Colour Role `{colour_role}` from {member.mention}, {ctx.author.mention}!**")

	@commands.command(aliases=['removecolours', 'delete_colours', 'removecolors', 'remove_colors', 'deletecolours', 'del_colosr', 'delcolours'])
	@commands.has_permissions(administrator=True)
	async def remove_colours(self, ctx, member: discord.Member = None) -> None:
		""" Removes a Colour Role from a given member.
		:param member: The member to remove the Colour Role from. """

		if not member:
			return await ctx.send(f"**Please, inform a member, {ctx.author.mention}!**")

		if not (colour_role_ids := await self.get_user_colour_roles(member.id)):
			return await ctx.send(f"**{member.mention} doesn't have that role, {ctx.author.mention}!**")

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