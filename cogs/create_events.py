import discord
from discord.ext import commands

from extra import utils
from extra.prompt.menu import ConfirmButton

from mysqldb import the_database
from typing import Dict, List, Union, Optional, Any
import os

events_cat_id: int = 762396214721118228
lessons_cat_id: int = 763841725848092733

organizer_role_id: int = int(os.getenv("ORGANIZER_ROLE_ID"))
teacher_role_id: int = int(os.getenv("TEACHER_ROLE_ID"))
staff_role_id: int = int(os.getenv("STAFF_ROLE_ID"))

class CreateEvents(commands.Cog):
    """ Category for creating event channels. """

    def __init__(self, client: commands.Bot) -> None:
        """ Class init method. """

        self.client = client
        self.db = CreateEventDatabase()
        self.host_cache: Dict[int, int] = {}

    async def get_french_class_permissions(self, guild: discord.Guild) -> Dict[Any, Any]:
        """ Gets permissions for a French class.
        :param guild: The server from the context. """

        # Gets the teacher's role
        teacher_role = discord.utils.get(guild.roles, id=teacher_role_id)

        overwrites = {}

        # Everyone's permissions
        overwrites[guild.default_role] = discord.PermissionOverwrite(
            read_messages=True, send_messages=True, connect=True,
            speak=True, view_channel=True, attach_files=True, stream=False
        )

        # Teacher's permissions
        overwrites[teacher_role] = discord.PermissionOverwrite(
            manage_messages=True, manage_channels=True, mute_members=True, 
            stream=True, move_members=True, start_embedded_activities=True
        )

        return overwrites

    async def get_english_class_permissions(self, guild: discord.Guild) -> Dict[Any, Any]:
        """ Gets permissions for an English class.
        :param guild: The server from the context. """

        # Gets the teacher's role
        teacher_role = discord.utils.get(guild.roles, id=teacher_role_id)

        overwrites = {}

        # Everyone's permissions
        overwrites[guild.default_role] = discord.PermissionOverwrite(
            read_messages=True, send_messages=True, connect=True,
            speak=True, view_channel=True, attach_files=True, stream=False
        )

        # Teacher's permissions
        overwrites[teacher_role] = discord.PermissionOverwrite(
            manage_messages=True, manage_channels=True, mute_members=True, 
            stream=True, move_members=True, start_embedded_activities=True
        )

        return overwrites

    async def get_event_permissions(self, guild: discord.Guild) -> Dict[Any, Any]:
        """ Gets permissions for an event.
        :param guild: The server from the context. """

        # Gets the organizer's role
        organizer_role = discord.utils.get(guild.roles, id=organizer_role_id)

        overwrites = {}

        # Everyone's permissions
        overwrites[guild.default_role] = discord.PermissionOverwrite(
            read_messages=True, send_messages=True, connect=True,
            speak=True, view_channel=True, attach_files=True, stream=False
        )

        # Organizer's permissions
        overwrites[organizer_role] = discord.PermissionOverwrite(
            manage_messages=True, manage_channels=True, mute_members=True, 
            stream=True, move_members=True, start_embedded_activities=True
        )

        return overwrites

    # CREATE EVENT

    @commands.group(name="create", aliases=["create_event", "create_lesson"])
    @utils.not_ready()
    async def _create(self, ctx) -> None:
        """ Creates an event. """

        if ctx.invoked_subcommand:
            return

        prefix = self.client.command_prefix
        subcommands = [f"{prefix}{c.qualified_name}" for c in ctx.command.commands]

        subcommands = '\n'.join(subcommands)
        embed = discord.Embed(
          title="Subcommads",
          description=f"```apache\n{subcommands}```",
          color=ctx.author.color,
          timestamp=ctx.message.created_at
        )
        await ctx.send(embed=embed)

    @_create.command(name="event")
    @utils.is_allowed([organizer_role_id], throw_exc=True)
    @commands.cooldown(1, 60, commands.BucketType.user)
    async def _create_event(self, ctx) -> None:
        """ Creates a Movie Night voice and text channel. """

        member = ctx.author
        guild = ctx.guild
        room = await self.get_event_room_by_user_id(member.id)
        channel = discord.utils.get(guild.text_channels, id=room[2]) if room else None

        if room and channel:
            return await ctx.send(f"**{member.mention}, you already have an event room going on! ({channel.mention})**")
        elif room and not channel:
            await self.delete_event_room_by_txt_id(room[2])

        confirm_view = await ConfirmButton(member, timeout=60)
        msg = await ctx.send("Do you want to create an event?", view=confirm_view)

        if confirm_view is None:
            return await ctx.reply("**Timeout!**", delete_after=3)

        if not confirm_view:
            return await ctx.reply("**Not creating it, then!**", delete_after=3)

        await msg.delete()


        overwrites = await self.get_event_permissions(guild)

        events_category = discord.utils.get(guild.categories, id=events_cat_id)

        event_title = f"⭐ Event ⭐"

        try:
            # Creating text channel
            text_channel = await events_category.create_text_channel(
                name=event_title,
                overwrites=overwrites)
            # Creating voice channel
            voice_channel = await events_category.create_voice_channel(
                name=event_title,
                user_limit=None,
                overwrites=overwrites)
            # Inserts it into the database
            await self.insert_event_room(
                user_id=member.id, vc_id=voice_channel.id, txt_id=text_channel.id,
                event_title=event_title, event_type="event"
                )
        except Exception as e:
            print(e)
            await ctx.send(f"**{member.mention}, something went wrong, try again later!**")

        else:
            await ctx.send(f"**{member.mention}, {text_channel.mention} is up and running!**")

    @_create.command(name="english_lesson", aliases=["english_class", "englishlesson", "englishclas", "fc", "fl"])
    @utils.is_allowed([organizer_role_id], throw_exc=True)
    @commands.cooldown(1, 60, commands.BucketType.user)
    async def _create_english_lesson(self, ctx) -> None:
        """ Creates an English Lesson voice and text channel. """

        member = ctx.author
        guild = ctx.guild
        room = await self.get_event_room_by_user_id(member.id)
        channel = discord.utils.get(guild.text_channels, id=room[2]) if room else None

        if room and channel:
            return await ctx.send(f"**{member.mention}, you already have an open room! ({channel.mention})**")

        elif room and not channel:
            await self.delete_event_room_by_txt_id(room[2])

        confirm_view = await ConfirmButton(member, timeout=60)
        msg = await ctx.send("Do you want to create an event?", view=confirm_view)

        if confirm_view is None:
            return await ctx.reply("**Timeout!**", delete_after=3)

        if not confirm_view:
            return await ctx.reply("**Not creating it, then!**", delete_after=3)

        await msg.delete()


        overwrites = await self.get_english_class_permissions(guild)

        events_category = discord.utils.get(guild.categories, id=events_cat_id)

        event_title = f"🇫🇷 English Lesson 🇫🇷"

        try:
            # Creating text channel
            text_channel = await events_category.create_text_channel(
                name=event_title,
                overwrites=overwrites)
            # Creating voice channel
            voice_channel = await events_category.create_voice_channel(
                name=event_title,
                user_limit=None,
                overwrites=overwrites)
            # Inserts it into the database
            await self.insert_event_room(
                user_id=member.id, vc_id=voice_channel.id, txt_id=text_channel.id,
                event_title=event_title, event_type="english_lesson"
                )
        except Exception as e:
            print(e)
            await ctx.send(f"**{member.mention}, something went wrong, try again later!**")

        else:
            await ctx.send(f"**{member.mention}, {text_channel.mention} is up and running!**")

    @_create.command(name="french_lesson", aliases=["french_class", "frenchlesson", "frenchclas", "fc", "fl"])
    @utils.is_allowed([organizer_role_id], throw_exc=True)
    @commands.cooldown(1, 60, commands.BucketType.user)
    async def _create_french_lesson(self, ctx) -> None:
        """ Creates a Movie Night voice and text channel. """

        member = ctx.author
        guild = ctx.guild
        room = await self.get_event_room_by_user_id(member.id)
        channel = discord.utils.get(guild.text_channels, id=room[2]) if room else None

        if room and channel:
            return await ctx.send(f"**{member.mention}, you already have an open room! ({channel.mention})**")

        elif room and not channel:
            await self.delete_event_room_by_txt_id(room[2])

        confirm_view = await ConfirmButton(member, timeout=60)
        msg = await ctx.send("Do you want to create an event?", view=confirm_view)

        if confirm_view is None:
            return await ctx.reply("**Timeout!**", delete_after=3)

        if not confirm_view:
            return await ctx.reply("**Not creating it, then!**", delete_after=3)

        await msg.delete()


        overwrites = await self.get_french_class_permissions(guild)

        events_category = discord.utils.get(guild.categories, id=events_cat_id)

        event_title = f"🇫🇷 French Lesson 🇫🇷"

        try:
            # Creating text channel
            text_channel = await events_category.create_text_channel(
                name=event_title,
                overwrites=overwrites)
            # Creating voice channel
            voice_channel = await events_category.create_voice_channel(
                name=event_title,
                user_limit=None,
                overwrites=overwrites)
            # Inserts it into the database
            await self.insert_event_room(
                user_id=member.id, vc_id=voice_channel.id, txt_id=text_channel.id,
                event_title=event_title, event_type="french_lesson"
                )
        except Exception as e:
            print(e)
            await ctx.send(f"**{member.mention}, something went wrong, try again later!**")

        else:
            await ctx.send(f"**{member.mention}, {text_channel.mention} is up and running!**")

    # ==== Action Methods ====


    @commands.command(aliases=['close_event'])
    @utils.is_allowed([organizer_role_id], throw_exc=True)
    @utils.not_ready()
    async def delete_event(self, ctx) -> None:
        """ Deletes an event room. """
        member = ctx.author
        perms = ctx.channel.permissions_for(member)
        delete = False

        if not (room := await self.get_event_room_by_txt_id(ctx.channel.id)):
            return await ctx.send(f"**{member.mention}, this is not an event room, write this command in the event channel you created!**")

        # Checks whether member can delete room
        if room[0] == member.id:  # If it's the owner of the room
            delete = True

        elif perms.administrator or staff_role_id in [r.id for r in member.roles]:  # If it's a staff member
            delete = True

        if delete:
            confirm_view = await ConfirmButton(member, timeout=60)
            await ctx.send(f"**{member.mention}, are you sure you want to delete this event?**", viwe=confirm_view)

            await confirm_view.wait()

            if not confirm_view.value:
                return await ctx.send(f"**Not deleting them, then, {member.mention}!**")

            try:
                await self.delete_event_room_by_txt_id(ctx.channel.id)
                if (room_one := self.client.get_channel(room[1])): 
                    await room_one.delete()
                if (room_two := self.client.get_channel(room[2])): 
                    await room_two.delete()
            except Exception as e:
                print(e)
                await ctx.send(f"**Something went wrong with it, try again later, {member.mention}!**")

class CreateEventDatabase:
    """ Class for the CreateEvent system's database method. """

    @commands.command(hidden=True)
    @commands.has_permissions(administrator=True)
    async def create_event_table(self, ctx) -> None:
        """ Creates the Event table in the database. """

        member: discord.Member = ctx.author

        if await self.check_event_table_exists():
            return await ctx.send(f"**Table `Event` table already exists, {member.mention}!**")

        mycursor, db = await the_database()
        await mycursor.execute("""
            CREATE TABLE Event (
                user_id BIGINT NOT NULL,
                txt_id BIGINT DEFAULT NULL,
                vc_id BIGINT NOT NULL,
                event_type VARCHAR(5) NOT NULL,
                event_title VARCHAR(25) NOT NULL,
                PRIMARY KEY (user_id)
            )
        """)
        await db.commit()
        await mycursor.close()
        await ctx.send(f"**`Event` table created, {member.mention}!**")

    @commands.command(hidden=True)
    @commands.has_permissions(administrator=True)
    async def drop_event_table(self, ctx) -> None:
        """ Drops the Event table from the database. """

        member: discord.Member = ctx.author

        if not await self.check_event_table_exists():
            return await ctx.send(f"**Table `Event` table doesn't exist, {member.mention}!**")

        mycursor, db = await the_database()
        await mycursor.execute("DROP TABLE Event")
        await db.commit()
        await mycursor.close()
        await ctx.send(f"**`Event` table dropped, {member.mention}!**")

    @commands.command(hidden=True)
    @commands.has_permissions(administrator=True)
    async def reset_event_table(self, ctx) -> None:
        """ Resets the Event table in the database. """

        member: discord.Member = ctx.author

        if not await self.check_event_table_exists():
            return await ctx.send(f"**Table `Event` table doesn't exist yet, {member.mention}!**")

        mycursor, db = await the_database()
        await mycursor.execute("DELETE FROM Event")
        await db.commit()
        await mycursor.close()
        await ctx.send(f"**`Event` table reset, {member.mention}!**")

    async def check_event_table_exists(self) -> bool:
        """ Checks whether the Event table exists in the database. """

        mycursor, _ = await the_database()
        await mycursor.execute("SHOW TABLE STATUS LIKE 'Event'")
        exists = await mycursor.fetchone()
        await mycursor.close()
        if exists:
            return True
        else:
            return False


def setup(client: commands.Bot) -> None:
    """ Cog's setup function. """
    
    client.add_cog(CreateEvents(client))