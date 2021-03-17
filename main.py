import discord
from discord.ext import commands, tasks
import os
import datetime
from dotenv import load_dotenv
load_dotenv()


server_id = int(os.getenv('SERVER_ID'))
moderator_role_id = int(os.getenv('MOD_ROLE_ID'))
joins_and_leaves_log_id = int(os.getenv('JOIN_LEAVE_LOG_CHANNEL_ID'))
moderation_log_channel_id = int(os.getenv('MOD_LOG_CHANNEL_ID'))
message_log_id = int(os.getenv('MESSAGE_LOG_ID'))

client = commands.Bot(command_prefix='!', intents=discord.Intents.all(), help_command=None)

@client.event
async def on_ready() -> None:
	change_status.start()
	print("Bot is ready!")

# Handles the errors
@client.event
async def on_command_error(ctx, error):
	if isinstance(error, commands.MissingPermissions):
		await ctx.send("You can't do that!")

	elif isinstance(error, commands.MissingRequiredArgument):
		await ctx.send('Please, inform all parameters!')

	elif isinstance(error, commands.CommandOnCooldown):
		await ctx.send(error)
		
	elif isinstance(error, commands.MissingAnyRole):
		role_names = [f"**{str(discord.utils.get(ctx.guild.roles, id=role_id))}**" for role_id in error.missing_roles]
		await ctx.send(f"You are missing at least one of the required roles: {', '.join(role_names)}")

	elif isinstance(error, commands.errors.RoleNotFound):
		await ctx.send(f"**{error}**")

	elif isinstance(error, commands.ChannelNotFound):
		await ctx.send("**Channel not found!**")

	print('='*10)
	print(f"ERROR: {error} | Class: {error.__class__} | Cause: {error.__cause__}")
	print('='*10)


# Members status update
@tasks.loop(seconds=10)
async def change_status():
	guild = client.get_guild(server_id)
	await client.change_presence(activity=discord.Activity(type=discord.ActivityType.watching, name=f'{len(guild.members)} members.'))


@client.event
async def on_member_join(member) -> None:
	""" Greets newcomers as soon as they join the server. """

	# Discards bot joinings
	if member.bot:
		return

	join_log = discord.utils.get(member.guild.channels, id=joins_and_leaves_log_id)

	# Embedded message to send into the chat
	embed = discord.Embed(
		title=f"Welcome to {member.guild}!",
		description="We hope you have a nice stay in here and meet new people.",
		color=discord.Color.green()
	)
	embed.set_author(name=member, icon_url=member.avatar_url)
	embed.set_image(url=member.guild.icon_url)
	embed.set_footer(text=member.guild, icon_url=member.guild.icon_url)
	await join_log.send(content=f"**Nice to see you, {member.mention}! Have a nice welcome.**", embed=embed)

@client.event
async def on_member_remove(member):
	roles = [role for role in member.roles]
	channel = discord.utils.get(member.guild.channels, id=joins_and_leaves_log_id)
	embed = discord.Embed(title=member.name, description=f"User has left the server.", colour=discord.Colour.dark_red())
	embed.set_thumbnail(url=member.avatar_url)
	embed.set_author(name=f"User Info: {member}")
	embed.add_field(name="ID:", value=member.id, inline=False)
	embed.add_field(name="Guild name:", value=member.display_name, inline=False)
	embed.add_field(name="Created at:", value=member.created_at.strftime("%a, %d %B %y, %I %M %p UTC"), inline=False)
	embed.add_field(name="Joined at:", value=member.joined_at.strftime("%a, %d %B %y, %I %M %p UTC"), inline=False)
	embed.add_field(name="Left at:", value=datetime.utcnow().strftime("%a, %d %B %y, %I %M %p UTC"), inline=False)
	embed.add_field(name=f"Roles: {len(roles)}", value=" ".join([role.mention for role in roles]), inline=False)
	embed.add_field(name="Top role:", value=member.top_role.mention, inline=False)
	embed.add_field(name="Bot?", value=member.bot)
	#cosmos = discord.utils.get(member.guild.members, id=user_cosmos_id)
	await channel.send(embed=embed)


# Delete messages log
@client.event
async def on_message_delete(message):
	if not message.guild:
		return

	general_log = client.get_channel(message_log_id)
	embed = discord.Embed(description=f'Message deleted in {message.channel.mention}', colour=discord.Colour.dark_grey())
	embed.add_field(name='Content', value=f'```{message.content}```', inline=False)
	embed.add_field(name='ID', value=f'```py\nUser = {message.author.id}\nMessage = {message.id}```')
	embed.set_footer(text=f"Guild name: {message.author.guild.name}")
	embed.set_author(name=message.author.name, icon_url=message.author.avatar_url)
	if message.author != client.user and not message.author.bot:
		await general_log.send(embed=embed)


# Edit messages log
@client.event
async def on_message_edit(before, after):
	if not after.guild:
		return

	general_log = client.get_channel(message_log_id)
	embed = discord.Embed(description=f'Message edited in {before.channel.mention}', colour=discord.Colour.greyple())
	embed.add_field(name='Before:', value=f'```{before.content}```', inline=False)
	embed.add_field(name='After:', value=f'```{after.content}```', inline=False)
	embed.add_field(name='ID', value=f'```py\nUser = {before.author.id}\nMessage = {before.id}```')
	embed.set_footer(text=f"Guild name: {before.author.guild.name}")
	embed.set_author(name=before.author.name, icon_url=before.author.avatar_url)
	if before.author != client.user and not before.author.bot:
		await general_log.send(embed=embed)


@client.command()
async def help(ctx, cmd: str = None):
	'''
	Shows some information about commands and categories.
	'''
	if not cmd:
		embed = discord.Embed(
			title="All commands and categories", 
			description=f"```ini\nUse {client.command_prefix}help command or {client.command_prefix}help category to know more about a specific command or category\n\n[Examples]\n[1] Category: {client.command_prefix}help Moderation\n[2] Command : {client.command_prefix}help snipe```", 
			timestamp=ctx.message.created_at, 
			color=ctx.author.color
			)

		for cog in client.cogs:
			cog = client.get_cog(cog)
			commands = [c.name for c in cog.get_commands() if not c.hidden]
			if commands:
				embed.add_field(
					name=f"__{cog.qualified_name}__", 
					value=f"`Commands:` {', '.join(commands)}", 
					inline=False
					)

		cmds = []
		for y in client.walk_commands():
			if not y.cog_name and not y.hidden:
				cmds.append(y.name)
		embed.add_field(
			name='__Uncategorized Commands__', 
			value=f"`Commands:` {', '.join(cmds)}", 
			inline=False)
		await ctx.send(embed=embed)

	else:
		# Checks if it's a command
		if command := client.get_command(cmd.lower()):
			command_embed = discord.Embed(title=f"__Command:__ {command.name}", description=f"__**Description:**__\n```{command.help}```", color=ctx.author.color, timestamp=ctx.message.created_at)
			return await ctx.send(embed=command_embed)

		# Checks if it's a cog
		for cog in client.cogs:
			if str(cog).lower() == str(cmd).lower():
				cog = client.get_cog(cog)
				cog_embed = discord.Embed(title=f"__Cog:__ {cog.qualified_name}", description=f"__**Description:**__\n```{cog.description}```", color=ctx.author.color, timestamp=ctx.message.created_at)
				for c in cog.get_commands():
					if not c.hidden:
						cog_embed.add_field(name=c.name,value=c.help,inline=False)

				return await ctx.send(embed=cog_embed)

		# Otherwise, it's an invalid parameter (Not found)
		else:
			await ctx.send(f"**Invalid parameter! `{cmd}` is neither a command nor a cog!**")



@client.command(hidden=True)
@commands.has_permissions(administrator=True)
async def load(ctx, extension: str = None):
	'''
	Loads a cog.
	:param extension: The cog.
	'''
	if not extension:
		return await ctx.send("**Inform the cog!**")
	client.load_extension(f'cogs.{extension}')
	return await ctx.send(f"**{extension} loaded!**")


@client.command(hidden=True)
@commands.has_permissions(administrator=True)
async def unload(ctx, extension: str = None):
	'''
	Unloads a cog.
	:param extension: The cog.
	'''
	if not extension:
		return await ctx.send("**Inform the cog!**")
	client.unload_extension(f'cogs.{extension}')
	return await ctx.send(f"**{extension} unloaded!**")


@client.command(hidden=True)
@commands.has_permissions(administrator=True)
async def reload(ctx, extension: str = None):
	'''
	Reloads a cog.
	:param extension: The cog.
	'''
	if not extension:
		return await ctx.send("**Inform the cog!**")
	client.unload_extension(f'cogs.{extension}')
	client.load_extension(f'cogs.{extension}')
	return await ctx.send(f"**{extension} reloaded!**")



for filename in os.listdir('./cogs'):
	if filename.endswith('.py'):
		client.load_extension(f"cogs.{filename[:-3]}")

client.run(os.getenv('TOKEN'))