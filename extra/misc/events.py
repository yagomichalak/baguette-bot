import discord
from discord.ext import commands

from mysqldb import the_database
from typing import List, Union

class CreateEventDatabase(commands.Cog):
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
                event_type VARCHAR(15) NOT NULL,
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

    async def insert_event_room(self, 
        user_id: int, vc_id: int, txt_id: int, event_title: str, event_type: str) -> None:
        """ Inserts an Event into the database.
        :param user_id: The event host's ID.
        :param vc_id: The event's Voice Channel ID.
        :param txt_id: The event's Text Channel ID.
        :param event_title: The event title.
        :param event_type: The event type. """

        mycursor, db = await the_database()
        await mycursor.execute("""
            INSERT INTO Event (
                user_id, vc_id, txt_id, event_title, event_type
            ) VALUES (%s, %s, %s, %s, %s)
        """, (user_id, vc_id, txt_id, event_title, event_type))
        await db.commit()
        await mycursor.close()

    async def get_event_room_by_user_id(self, user_id: int) -> List[Union[int, str]]:
        """ Gets an event room by user ID.
        :param user_id: The ID of the user. """
        
        mycursor, _ = await the_database()
        await mycursor.execute("SELECT * FROM Event WHERE user_id = %s", (user_id,))
        event = await mycursor.fetchone()
        await mycursor.close()
        return event

    async def get_event_room_by_txt_id(self, txt_id: int) -> List[Union[int, str]]:
        """ Gets an event room by Text Channel ID.
        :param txt_id: The Text Channel ID. """
        
        mycursor, _ = await the_database()
        await mycursor.execute("SELECT * FROM Event WHERE txt_id = %s", (txt_id,))
        event = await mycursor.fetchone()
        await mycursor.close()
        return event

    async def delete_event_room_by_txt_id(self, txt_id: int) -> None:
        """ Deletes an Event by Text Channel ID.
        :param txt_id: The Text Channel ID. """

        mycursor, db = await the_database()
        await mycursor.execute("DELETE FROM Event WHERE txt_id = %s", (txt_id,))
        await db.commit()
        await mycursor.close()