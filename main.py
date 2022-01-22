import discord
from discord.ext import commands, tasks
import os
from datetime import datetime
from dotenv import load_dotenv
load_dotenv()

from cogs.misc import Misc


server_id = int(os.getenv('SERVER_ID'))
moderator_role_id = int(os.getenv('MOD_ROLE_ID'))
joins_and_leaves_log_id = int(os.getenv('JOIN_LEAVE_LOG_CHANNEL_ID'))
moderation_log_channel_id = int(os.getenv('MOD_LOG_CHANNEL_ID'))
message_log_id = int(os.getenv('MESSAGE_LOG_ID'))
counting_channel_id = int(os.getenv('COUNTING_CHANNEL_ID'))
faq_channel_id = int(os.getenv('FAQ_CHANNEL_ID'))


client = commands.Bot(command_prefix='b!', intents=discord.Intents.all(), help_command=None)

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

	elif isinstance(error, commands.MissingRole):
		role_name = f"{str(discord.utils.get(ctx.guild.roles, id=error.missing_role))}"
		await ctx.send(f"**You are missing the required role: `{role_name}`**")

	elif isinstance(error, commands.errors.RoleNotFound):
		await ctx.send(f"**{error}**")

	elif isinstance(error, commands.BadArgument):
		await ctx.send(f"**Bad argument!**")

	elif isinstance(error, commands.MemberNotFound):
		await ctx.send(f"**{error}**")

	elif isinstance(error, commands.ChannelNotFound):
		await ctx.send("**Channel not found!**")

	elif isinstance(error, commands.CheckAnyFailure):
		print('erroooooor', error.errors[0])
		await on_command_error(ctx, error.errors[0])

	print('='*10)
	print(f"ERROR: {error} | Class: {error.__class__} | Cause: {error.__cause__}")
	print('='*10)


@client.event
async def on_application_command_error(ctx, error) -> None:

    if isinstance(error, commands.MissingPermissions):
        await ctx.respond("**You can't do that!**")

    elif isinstance(error, commands.MissingRequiredArgument):
        await ctx.respond('**Please, inform all parameters!**')

    elif isinstance(error, commands.NotOwner):
        await ctx.respond("**You're not the bot's owner!**")

    elif isinstance(error, commands.CommandOnCooldown):
        await ctx.respond(error)

    elif isinstance(error, commands.errors.CheckAnyFailure):
        await ctx.respond("**You can't do that!**")

    elif isinstance(error, commands.MissingAnyRole):
        role_names = [f"**{str(discord.utils.get(ctx.guild.roles, id=role_id))}**" for role_id in error.missing_roles]
        await ctx.respond(f"You are missing at least one of the required roles: {', '.join(role_names)}")

    elif isinstance(error, commands.errors.RoleNotFound):
        await ctx.respond(f"**Role not found**")

    elif isinstance(error, commands.ChannelNotFound):
        await ctx.respond("**Channel not found!**")

    elif isinstance(error, discord.app.commands.errors.CheckFailure):
        await ctx.respond("**It looks like you can't run this command!**")


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



	sorted_time_create = await client.get_cog('Moderation').sort_time(member.guild, member.created_at)
	await join_log.send(f"{member.mention} joined.\n**Account creation date:** {member.created_at.strftime('%d/%m/%y')} ({sorted_time_create})")

	welcome_message = f"""
🇬🇧 **Welcome to: Le Salon Français!**

Please read the rules and report anything that is against the rules to any of the Moderators/Admins.
If there is anything you are unsure of, please first read the <#{faq_channel_id}> channel as this will have answers to some of your questions.

🇫🇷 **Bienvenue sur Le Salon Français !**

Veuillez lire les règles et signaler tout ce qui est contre les règles à n'importe quel membre du Staff. 
S'il y a quelque chose dont vous n'êtes pas sûr, veuillez d'abord lire le canal <#{faq_channel_id}> car vous y trouverez les réponses à la plupart de vos questions.

**Our affiliated servers / Nos serveurs affiliés**
For Italiano/English: https://discord.gg/mTCPdRsCdw
For Русский/English: https://discord.gg/7pamu9NNex"""

	await member.send(welcome_message)

@client.event
async def on_member_remove(member):
	roles = [role for role in member.roles]
	channel = discord.utils.get(member.guild.channels, id=joins_and_leaves_log_id)
	await channel.send(f"**{member.display_name}** (ID {member.id}) left.")


# Delete messages log
@client.event
async def on_message_delete(message):
	if not message.guild:
		return

	if message.author.bot:
		return

	if message.channel.id == counting_channel_id:
		return

	general_log = client.get_channel(message_log_id)
	embed = discord.Embed(
		description=f"**User:** {message.author.mention}\n**Channel:** {message.channel.mention}\n**Message:** {message.content}", 
		color=discord.Color.dark_grey(),
		timestamp=message.created_at)
	embed.set_footer(text=f"Message ID: {message.id}")
	embed.set_author(name="Message Deleted", icon_url=message.author.display_avatar)
	# if len(message.attachments)
	# if message.author != client.user and not message.author.bot:
	await general_log.send(embed=embed)

@client.event
async def on_bulk_message_delete(messages):
	
	general_log = client.get_channel(message_log_id)
	
	for message in messages:
		if not message.guild:
			continue

		if message.author.bot:
			continue

		if message.channel.id == counting_channel_id:
			continue

		embed = discord.Embed(
			description=f"**User:** {message.author.mention}\n**Channel:** {message.channel.mention}\n**Message:** {message.content}", 
			color=discord.Color.dark_grey(),
			timestamp=message.created_at)
		embed.set_footer(text=f"Message ID: {message.id}")
		embed.set_author(name="Message Deleted (Purge)", icon_url=message.author.display_avatar)
		# if len(message.attachments)
		# if message.author != client.user and not message.author.bot:
		await general_log.send(embed=embed)


@client.command()
@Misc.check_whitelist(client)
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