import discord
from discord.ext import commands
from mysqldb import the_database

import os
from typing import List, Union, Any

class UserNotesTable(commands.Cog):
    """ Class for managing the UserNotes table in the database."""

    def __init__(self, client: commands.Bot) -> None:
        """ Class init method. """

        self.client = client

    @commands.command(hidden=True)
    @commands.has_permissions(administrator=True)
    async def create_table_user_notes(self, ctx) -> None:
        """ Creates the UserNotes table. """

        if await self.table_user_notes_exists():
            return await ctx.send("**The `UserNotes` table already exists!**")

        mycursor, db = await the_database()
        await mycursor.execute("""
            CREATE TABLE UserNotes (
                note_id INT NOT NULL AUTO_INCREMENT,
                user_id BIGINT NOT NULL,
                note VARCHAR(1000) NOT NULL,
                perpetrator_id BIGINT NOT NULL,
                created_at BIGINT NOT NULL,
                PRIMARY KEY (note_id)
            )""")
        await db.commit()
        await mycursor.close()
        await ctx.send("**Created `UserNotes` table!**")

    @commands.command(hidden=True)
    @commands.has_permissions(administrator=True)
    async def drop_table_user_notes(self, ctx) -> None:
        """ Drops the UserNotes table. """

        if not await self.table_user_notes_exists():
            return await ctx.send("**The `UserNotes` table doesn't exist!**")

        mycursor, db = await the_database()
        await mycursor.execute("DROP TABLE UserNotes")
        await db.commit()
        await mycursor.close()
        await ctx.send("**Dropped `UserNotes` table!**")

    @commands.command(hidden=True)
    @commands.has_permissions(administrator=True)
    async def reset_table_user_notes(self, ctx) -> None:
        """ Resets the UserNotes table. """

        if not await self.table_user_notes_exists():
            return await ctx.send("**The `UserNotes` table doesn't exist yet!**")

        mycursor, db = await the_database()
        await mycursor.execute("DELETE FROM UserNotes")
        await db.commit()
        await mycursor.close()
        await ctx.send("**Reset `UserNotes` table!**")

    async def table_user_notes_exists(self) -> bool:
        """ Checks whether the UserNotes table exists. """

        mycursor, _ = await the_database()
        await mycursor.execute("SHOW TABLE STATUS LIKE 'UserNotes'")
        exists = await mycursor.fetchone()
        await mycursor.close()
        if exists:
            return True
        else:
            return False

    async def insert_user_note(self, user_id: int, note: str, perpetrator_id: int, current_ts: int) -> None:
        """ Inserts a user note into the database.
        :param user_id: The ID of the user who's getting the note.
        :param note: The note text itself.
        :param perpetrator_id: The ID of the person who made the note.
        :param current_ts: The current timestamp. """

        mycursor, db = await the_database()
        await mycursor.execute("""
            INSERT INTO UserNotes (
                user_id, note, perpetrator_id, created_at
            ) VALUES (%s, %s, %s, %s)
        """, (user_id, note, perpetrator_id, current_ts))
        await db.commit()
        await mycursor.close()

    async def get_user_note(self, note_id: int) -> List[Union[int, str]]:
        """ Gets a specific note from a user.
        :param note_id: The ID of the note to get """

        mycursor, _ = await the_database()
        await mycursor.execute("SELECT * FROM UserNotes WHERE note_id = %s", (note_id,))
        note = await mycursor.fetchone()
        await mycursor.close()
        return note

    async def get_user_notes(self, user_id: int) -> List[List[Union[int, str]]]:
        """ Gets all notes from a user.
        :param user_id: The ID of the user from whom to get the notes """

        mycursor, _ = await the_database()
        await mycursor.execute("SELECT * FROM UserNotes WHERE user_id = %s", (user_id,))
        notes = await mycursor.fetchall()
        await mycursor.close()
        return notes

    async def update_user_note(self, note_id: int, new_note: str) -> None:
        """ Updates an existing note.
        :param note_id: The ID of the note to update.
        :param new_note: The new note text. """

        mycursor, db = await the_database()
        await mycursor.execute("""
            UPDATE UserNotes SET note = %s WHERE note_id = %s
        """, (new_note, note_id))
        await db.commit()
        await mycursor.close()

    async def delete_user_note(self, note_id: int) -> None:
        """ Deletes a user note.
        :param note_id: The ID of the note to delete. """

        mycursor, db = await the_database()
        await mycursor.execute("DELETE FROM UserNotes WHERE note_id = %s", (note_id,))
        await db.commit()
        await mycursor.close()

    async def delete_user_notes(self, user_id: int) -> None:
        """ Deletes all notes from a user.
        :param user_id: The ID of the user from whom to delete the notes. """

        mycursor, db = await the_database()
        await mycursor.execute("DELETE FROM UserNotes WHERE user_id = %s", (user_id,))
        await db.commit()
        await mycursor.close()