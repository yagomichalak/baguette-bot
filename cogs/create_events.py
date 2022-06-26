import discord
from discord.ext import commands

from extra import utils
from extra.prompt.menu import ConfirmButton, EventRoomTypeView
from extra.misc.events import CreateEventDatabase

from mysqldb import the_database
from typing import Dict, List, Union, Optional, Any
import os

events_cat_id: int = int(os.getenv("EVENTS_CAT_ID"))
lessons_cat_id: int = int(os.getenv("LESSONS_CAT_ID"))
french_lesson_role_id: int = int(os.getenv("FRENCH_LESSONS_ROLE_ID"))
english_lesson_role_id: int = int(os.getenv("ENGLISH_LESSONS_ROLE_ID"))

organizer_role_id: int = int(os.getenv("ORGANIZER_ROLE_ID"))
teacher_role_id: int = int(os.getenv("TEACHER_ROLE_ID"))
staff_role_id: int = int(os.getenv("STAFF_ROLE_ID"))

class CreateEvents(CreateEventDatabase):
    """ Category for creating event channels. """

    def __init__(self, client: commands.Bot) -> None:
        """ Class init method. """

        self.client = client
        self.host_cache: Dict[int, int] = {}

        self.french_roles: List[int] = [ # Native French roles
            824667329002209280,
            933873327653670922,
            933874570757308427,
            933874567150174209,
            933874559621402684,
            772182729101017098,
            895782147904913468,
            895783897487519784,
            895785379649695815,
        ]

        self.english_roles: List[int] = [ # Native English roles
            933878080165011476,
            933877674735198219,
            933877681005670400,
            933877682222034947,
            933877684356927548,
            909212571373010994,
            909213121527312385,
            909213451006644234,
            909214255121842248,
            948985481247457280,
        ]

    async def get_french_class_permissions(self, guild: discord.Guild) -> Dict[Any, Any]:
        """ Gets permissions for a French class.
        :param guild: The server from the context. """

        # Gets the teacher's role
        teacher_role = discord.utils.get(guild.roles, id=teacher_role_id)
        staff_role = discord.utils.get(guild.roles, id=staff_role_id)

        overwrites = {}

        # Everyone's permissions
        overwrites[guild.default_role] = discord.PermissionOverwrite(
            read_messages=True, send_messages=True, view_channel=True, 
            attach_files=True, stream=False, start_embedded_activities=False,
            connect=False, speak=False
        )

        # Teacher's permissions
        overwrites[teacher_role] = discord.PermissionOverwrite(
            manage_messages=True, manage_channels=True, mute_members=True, 
            stream=True, move_members=True, start_embedded_activities=True,
            manage_permissions=True
        )

        # Staff permissions
        overwrites[staff_role] = discord.PermissionOverwrite(
            connect=True, speak=True
        )

        if french_lessons_role := guild.get_role(french_lesson_role_id):
            overwrites[french_lessons_role] = discord.PermissionOverwrite(
                speak=True, connect=True
            )
        

        for role_id in self.french_roles:
            if role := guild.get_role(role_id):
                overwrites[role] = discord.PermissionOverwrite(connect=False)

        return overwrites

    async def get_english_class_permissions(self, guild: discord.Guild) -> Dict[Any, Any]:
        """ Gets permissions for an English class.
        :param guild: The server from the context. """

        # Gets the teacher's role
        teacher_role = discord.utils.get(guild.roles, id=teacher_role_id)
        staff_role = discord.utils.get(guild.roles, id=staff_role_id)

        overwrites = {}

        # Everyone's permissions
        overwrites[guild.default_role] = discord.PermissionOverwrite(
            read_messages=True, send_messages=True, connect=True,
            speak=True, view_channel=True, attach_files=True, stream=False,
            start_embedded_activities=False
        )

        # Teacher's permissions
        overwrites[teacher_role] = discord.PermissionOverwrite(
            manage_messages=True, manage_channels=True, mute_members=True, 
            stream=True, move_members=True, start_embedded_activities=True,
            manage_permissions=True
        )

        # Staff permissions
        overwrites[staff_role] = discord.PermissionOverwrite(
            connect=True, speak=True
        )
        
        if english_lessons_role := guild.get_role(english_lesson_role_id):
            overwrites[english_lessons_role] = discord.PermissionOverwrite(
                speak=True, connect=True
            )

        for role_id in self.english_roles:
            if role := guild.get_role(role_id):
                overwrites[role] = discord.PermissionOverwrite(connect=False)

        return overwrites

    async def get_event_permissions(self, guild: discord.Guild) -> Dict[Any, Any]:
        """ Gets permissions for an event.
        :param guild: The server from the context. """

        # Gets the organizer's role
        organizer_role = discord.utils.get(guild.roles, id=organizer_role_id)
        staff_role = discord.utils.get(guild.roles, id=staff_role_id)

        overwrites = {}

        # Everyone's permissions
        overwrites[guild.default_role] = discord.PermissionOverwrite(
            read_messages=True, send_messages=True, connect=True,
            speak=True, view_channel=True, attach_files=True, stream=False,
            start_embedded_activities=False
        )

        # Organizer's permissions
        overwrites[organizer_role] = discord.PermissionOverwrite(
            manage_messages=True, manage_channels=True, mute_members=True, 
            stream=True, move_members=True, start_embedded_activities=True,
            manage_permissions=True
        )

        # Staff permissions
        overwrites[staff_role] = discord.PermissionOverwrite(
            connect=True, speak=True
        )

        return overwrites

    def is_allowed_members(allowed_members: List[int]):
        def predicate(ctx):
            return ctx.message.author.id in allowed_members

        return commands.check(predicate)

    # CREATE EVENT

    @commands.group(name="create", aliases=["create_event", "create_lesson"])
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
    @commands.check_any(is_allowed_members([828674987141496923]), utils.is_allowed([organizer_role_id]))
    @commands.cooldown(1, 60, commands.BucketType.user)
    async def _create_event(self, ctx) -> None:
        """ Creates an event voice and text channel. """

        member = ctx.author
        guild = ctx.guild
        room = await self.get_event_room_by_user_id(member.id)
        channel = discord.utils.get(guild.text_channels, id=room[1]) if room else None

        if room and channel:
            return await ctx.send(f"**{member.mention}, you already have an event room going on! ({channel.mention})**")
        elif room and not channel:
            await self.delete_event_room_by_txt_id(room[2])

        event_room_prompt = EventRoomTypeView(member, timeout=60)
        msg = await ctx.send("What type is the main room for the event gonna be?", view=event_room_prompt)
        await event_room_prompt.wait()

        if event_room_prompt.value is None:
            return await ctx.reply("**Timeout!**", delete_after=3)

        if not event_room_prompt.value:
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
            if event_room_prompt.room_type == 'voice':
                # Creating voice channel
                voice_channel = await events_category.create_voice_channel(
                    name=event_title,
                    user_limit=None,
                    overwrites=overwrites)
            else:
                # Creating voice channel
                voice_channel = await events_category.create_stage_channel(
                    name=event_title,
                    topic=event_title,
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
            await ctx.send(f"**{member.mention}, {text_channel.mention}-{voice_channel.mention} are up and running!**")

    @_create.command(name="english_lesson", aliases=["english_class", "englishlesson", "englishclas", "ec", "el"])
    @commands.check_any(is_allowed_members([828674987141496923]), utils.is_allowed([organizer_role_id]))
    @commands.cooldown(1, 60, commands.BucketType.user)
    async def _create_english_lesson(self, ctx) -> None:
        """ Creates a Voice and Text Channel for an English class. """

        member = ctx.author
        guild = ctx.guild
        room = await self.get_event_room_by_user_id(member.id)
        channel = discord.utils.get(guild.text_channels, id=room[1]) if room else None

        if room and channel:
            return await ctx.send(f"**{member.mention}, you already have an open room! ({channel.mention})**")

        elif room and not channel:
            await self.delete_event_room_by_txt_id(room[2])

        event_room_prompt = EventRoomTypeView(member, timeout=60)
        msg = await ctx.send("What type is the main room for the English lesson gonna be?", view=event_room_prompt)
        await event_room_prompt.wait()

        if event_room_prompt.value is None:
            return await ctx.reply("**Timeout!**", delete_after=3)

        if not event_room_prompt.value:
            return await ctx.reply("**Not creating it, then!**", delete_after=3)

        await msg.delete()


        overwrites = await self.get_english_class_permissions(guild)

        events_category = discord.utils.get(guild.categories, id=events_cat_id)

        event_title = f"🇬🇧 English Lesson 🇬🇧"

        try:
            # Creating text channel
            text_channel = await events_category.create_text_channel(
                name=event_title,
                overwrites=overwrites)
            if event_room_prompt.room_type == 'voice':
                # Creating voice channel
                voice_channel = await events_category.create_voice_channel(
                    name=event_title,
                    user_limit=None,
                    overwrites=overwrites)
            else:
                # Creating voice channel
                voice_channel = await events_category.create_stage_channel(
                    name=event_title,
                    topic=event_title,
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
            await ctx.send(f"**{member.mention}, {text_channel.mention}-{voice_channel.mention} are up and running!**")

    @_create.command(name="french_lesson", aliases=["french_class", "frenchlesson", "frenchclas", "fc", "fl"])
    @utils.is_allowed([organizer_role_id], throw_exc=True)
    @commands.cooldown(1, 60, commands.BucketType.user)
    async def _create_french_lesson(self, ctx) -> None:
        """ Creates a Voice and Text channel for a French class. """

        member = ctx.author
        guild = ctx.guild
        room = await self.get_event_room_by_user_id(member.id)
        channel = discord.utils.get(guild.text_channels, id=room[1]) if room else None

        if room and channel:
            return await ctx.send(f"**{member.mention}, you already have an open room! ({channel.mention})**")

        elif room and not channel:
            await self.delete_event_room_by_txt_id(room[2])

        event_room_prompt = EventRoomTypeView(member, timeout=60)
        msg = await ctx.send("What type is the main room for the French lesson gonna be?", view=event_room_prompt)
        await event_room_prompt.wait()

        if event_room_prompt.value is None:
            return await ctx.reply("**Timeout!**", delete_after=3)

        if not event_room_prompt.value:
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
            if event_room_prompt.room_type == 'voice':
                # Creating voice channel
                voice_channel = await events_category.create_voice_channel(
                    name=event_title,
                    user_limit=None,
                    overwrites=overwrites)
            else:
                # Creating voice channel
                voice_channel = await events_category.create_stage_channel(
                    name=event_title,
                    topic=event_title,
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
            await ctx.send(f"**{member.mention}, {text_channel.mention}-{voice_channel.mention} are up and running!**")

    # ==== Action Methods ====


    @commands.command(aliases=['close_event'])
    @utils.is_allowed([organizer_role_id], throw_exc=True)
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
            confirm_view = ConfirmButton(member, timeout=60)
            await ctx.send(f"**{member.mention}, are you sure you want to delete this event?**", view=confirm_view)

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

"""
b!create_event_table
"""


def setup(client: commands.Bot) -> None:
    """ Cog's setup function. """
    
    client.add_cog(CreateEvents(client))