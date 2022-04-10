import discord
from discord.ext import commands
import os
from typing import List, Union

from extra import utils
from extra.tools.help_channel import HelpChannel
from extra.tools.scheduled_events import ScheduledEventsSystem, ScheduledEventsTable
from extra.tools.user_voice import UserVoiceTable, UserVoiceSystem
from extra.tools.user_notes import UserNotesTable
from extra.prompt.menu import ConfirmButton

tool_cogs: List[commands.Cog] = [
    HelpChannel, UserVoiceTable, UserVoiceSystem,
    ScheduledEventsSystem, ScheduledEventsTable, UserNotesTable
]

staff_role_id: int = int(os.getenv("STAFF_ROLE_ID"))

class Tools(*tool_cogs):
    """ Category for tool commands and features. """

    def __init__(self, client: commands.Bot) -> None:
        """ Class init method. """
        
        super().__init__(self)
        self.client = client

    @commands.Cog.listener()
    async def on_ready(self) -> None:
        """ Tells when the cog is ready to go. """

        self.advertise_patreon.start()
        self.solve_broken_roles.start()
        print('Tool cog is online!')


    @utils.is_allowed([staff_role_id], throw_exc=True)
    @commands.command(name="add_user_note", aliases=["create_user_note", "make_user_note"])
    async def _add_user_note(self, ctx, member: discord.Member = None, *, note: str = None) -> None:
        """ Adds a user note.
        :param member: The member to whom to add the note.
        :param note: The note text. """

        perpetrator: discord.Member = ctx.author
        if not member:
            return await ctx.send(f"**Please, inform the user to add the note to, {perpetrator.mention}!**")

        if not note:
            return await ctx.send(f"**Please, inform a note to add to the user, {perpetrator.mention}!**")

        if len(note) > 1000:
            return await ctx.send(f"**Please, inform a note that has a maximum of 1000 characters, {perpetrator.mention}!**")
        
        current_ts = await utils.get_timestamp()
        await self.insert_user_note(
            member.id, note, perpetrator.id, current_ts
        )
        await ctx.send(f"**Note has been successfully made for `{member}`, {perpetrator.mention}!**")

    @utils.is_allowed([staff_role_id], throw_exc=True)
    @commands.command(name="show_user_notes", aliases=["notes", "get_notes", "user_notes", "get_user_notes", "show_user_notes"])
    async def _show_user_notes(self, ctx, member: Union[discord.Member, discord.User] = None) -> None:
        """ Shows all notes from a specific user.
        :param member: The member from whom to show the notes. """

        perpetrator: discord.Member = ctx.author
        if not member:
            return await ctx.send(f"**Please, inform a member, {perpetrator.mention}!**")
        
        if not (user_notes := await self.get_user_notes(member.id)):
            return await ctx.send(f"**`{member}` doesn't have any notes, {perpetrator.mention}!**")

        embed = discord.Embed(
            title=f"__{member}'s Notes__",
            color=member.color,
            timestamp=ctx.message.created_at
        )
        for note in user_notes:
            embed.add_field(
                name=f"• Note: {note[0]}",
                value=f"""```{note[2]}```**Made by: <@{note[3]}>**\n**On:** <t:{note[4]}>""",
                inline=False
            )

        embed.set_thumbnail(url=member.display_avatar)
        embed.set_footer(text=f"Requested by: {perpetrator}", icon_url=perpetrator.display_avatar)
        
        await ctx.send(embed=embed)

    @utils.is_allowed([staff_role_id], throw_exc=True)
    @commands.command(name="delete_user_note", aliases=["remove_user_note", "del_user_note", "delete_note", "remove_note"])
    async def _delete_user_note(self, ctx, note_id: int = None) -> None:
        """ Deletes a user note.
        :param note_id: The ID of the note to delete. """

        perpetrator: discord.Member = ctx.author
        if not note_id:
            return await ctx.send(f"**Please, inform a note ID, {perpetrator.mention}!**")
        
        if not await self.get_user_note(note_id):
            return await ctx.send(f"**There doesn't exist any note with that ID, {perpetrator.mention}!**")

        confirm_view = ConfirmButton(perpetrator, timeout=60)
        msg = await ctx.send(
            f"**Are you sure you want to delete the note with the ID `{note_id}`, {perpetrator.mention}?**",
            view=confirm_view)
        await confirm_view.wait()

        await utils.disable_buttons(confirm_view)
        await msg.edit(view=confirm_view)

        if confirm_view.value is None:
            return await ctx.send(f"**Timeout, {perpetrator.mention}!**")

        if not confirm_view.value:
            return await ctx.send(f"**Canceled, {perpetrator.mention}!**")

        await self.delete_user_note(note_id)
        await ctx.send(f"**Note with ID `{note_id}` has been successfully deleted, {perpetrator.mention}!**")

    @utils.is_allowed([staff_role_id], throw_exc=True)
    @commands.command(name="delete_user_notes", aliases=["remove_user_notes", "del_user_notes", "delete_notes", "remove_notes"])
    async def _delete_user_notes(self, ctx, member: Union[discord.Member, discord.User] = None) -> None:
        """ Deletes all notes from a user.
        :param member: The member from whom to delete the notes. """

        perpetrator: discord.Member = ctx.author
        if not member:
            return await ctx.send(f"**Please, inform a member from whom to delete the notes, {perpetrator.mention}!**")
        
        if not (user_notes := await self.get_user_notes(member.id)):
            return await ctx.send(f"**`{member}` doesn't have any notes, {perpetrator.mention}!**")

        confirm_view = ConfirmButton(perpetrator, timeout=60)
        msg = await ctx.send(
            f"**Are you sure you want to delete `{len(user_notes)}` from `{member}`, {perpetrator.mention}?**",
            view=confirm_view)
        await confirm_view.wait()

        await utils.disable_buttons(confirm_view)
        await msg.edit(view=confirm_view)

        if confirm_view.value is None:
            return await ctx.send(f"**Timeout, {perpetrator.mention}!**")

        if not confirm_view.value:
            return await ctx.send(f"**Canceled, {perpetrator.mention}!**")

        await self.delete_user_notes(member.id)
        await ctx.send(f"**`{len(user_notes)}` has been successfully deleted from `{member}`, {perpetrator.mention}!**")

"""
b!create_table_user_notes
"""

def setup(client: commands.Bot) -> None:
    """ Cog's setup function. """

    client.add_cog(Tools(client))

