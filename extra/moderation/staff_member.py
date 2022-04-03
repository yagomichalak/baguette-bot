import discord
from discord.ext import commands

from mysqldb import the_database
from typing import List

class StaffMemberTable(commands.Cog):
    """ Class for managing the StaffMember table in the database. """

    def __init__(self, client: commands.Bot) -> None:
        """ Class init method. """

        self.client = client

    @commands.command(hidden=True)
    @commands.has_permissions(administrator=True)
    async def create_table_staff_member(self, ctx) -> None:
        """ (ADM) Creates the StaffMember table. """

        if await self.check_table_staff_member():
            return await ctx.send("**Table __StaffMember__ already exists!**")

        await ctx.message.delete()
        mycursor, db = await the_database()
        await mycursor.execute("""CREATE TABLE StaffMember (
            user_id BIGINT NOT NULL,
            infractions_given INT NOT NULL DEFAULT 1,
            joined_staff_at VARCHAR(50) DEFAULT NULL,
            bans_today TINYINT(2) NOT NULL DEFAULT 0,
            first_ban_timestamp BIGINT DEFAULT NULL,
            PRIMARY KEY (user_id)
            )""")
        await db.commit()
        await mycursor.close()

        return await ctx.send("**Table __StaffMember__ created!**", delete_after=3)

    @commands.command(hidden=True)
    @commands.has_permissions(administrator=True)
    async def drop_table_staff_member(self, ctx) -> None:
        """ (ADM) Creates the StaffMember table """

        if not await self.check_table_staff_member():
            return await ctx.send("**Table __StaffMember__ doesn't exist!**")

        await ctx.message.delete()
        mycursor, db = await the_database()
        await mycursor.execute("DROP TABLE StaffMember")
        await db.commit()
        await mycursor.close()

        return await ctx.send("**Table __StaffMember__ dropped!**", delete_after=3)

    @commands.command(hidden=True)
    @commands.has_permissions(administrator=True)
    async def reset_table_staff_member(self, ctx) -> None:
        """ (ADM) Creates the StaffMember table """

        if not await self.check_table_staff_member():
            return await ctx.send("**Table __StaffMember__ doesn't exist yet!**")

        await ctx.message.delete()
        mycursor, db = await the_database()
        await mycursor.execute("DELETE FROM StaffMember")
        await db.commit()
        await mycursor.close()

        return await ctx.send("**Table __StaffMember__ reset!**", delete_after=3)

    async def check_table_staff_member(self) -> bool:
        """ Checks if the StaffMember table exists """

        mycursor, _ = await the_database()
        await mycursor.execute("SHOW TABLE STATUS LIKE 'StaffMember'")
        exists = await mycursor.fetchone()
        await mycursor.close()

        if exists:
            return True
        else:
            return False

    async def insert_staff_member(self, user_id: int, infractions_given: int, staff_at: str, bans_today: int = 0, ban_timestamp: int = None) -> None:
        """ Inserts a Staff member into the database.
        :param user_id: The ID of the Staff member.
        :param infractions_given: The infractions given by the Staff member.
        :param staff_at: Timestamp for the Staff joining time (not reliable for old Staff members).
        :param bans_today: First value to the bans_today counter. Default = 0.
        :param ban_timestamp: Timestamp for the first ban. """

        mycursor, db = await the_database()
        await mycursor.execute("""INSERT INTO StaffMember (
            user_id, infractions_given, joined_staff_at, bans_today, first_ban_timestamp
            ) VALUES (%s, %s, %s, %s, %s)""", (user_id, infractions_given, staff_at, bans_today, ban_timestamp))
        await db.commit()
        await mycursor.close()


    async def get_staff_member(self, user_id: int) -> List[int]:
        """ Gets a Staff member.
        :param user_id: The ID of the Staff member. """

        mycursor, db = await the_database()
        await mycursor.execute("SELECT * FROM StaffMember WHERE user_id = %s", (user_id,))
        staff_member = await mycursor.fetchone()
        await mycursor.close()
        return staff_member

    async def update_staff_member_counter(self, user_id: int, infraction_increment: int = 0, ban_increment: int = 0, timestamp: int = None, reset_ban: bool = False) -> None:
        """ Updates the Staff member's counters by a value.
        :param user_id: The ID of the Staff member.
        :param infraction_increment: The value to increment the infractions-given counter. Default = 0.
        :param ban_increment: The value to increment the bans-today counter. Default = 0.
        :param timestamp: The ban timestamp. Default = Null.
        :param reset_ban: Whether it should reset the bans-today counter. Default = False. """

        mycursor, db = await the_database()
        if timestamp and reset_ban:
            await mycursor.execute("""
                UPDATE StaffMember 
                SET bans_today = 1, infractions_given = infractions_given + %s, first_ban_timestamp = %s WHERE user_id = %s
                """, (infraction_increment, timestamp, user_id))

        elif timestamp:
            await mycursor.execute("""
                UPDATE StaffMember 
                SET bans_today = bans_today + %s, infractions_given = infractions_given + %s, first_ban_timestamp = %s WHERE user_id = %s
                """, (ban_increment, infraction_increment, timestamp, user_id))

        else:
            await mycursor.execute("""
                UPDATE StaffMember 
                SET infractions_given = infractions_given + %s, bans_today = bans_today + %s WHERE user_id = %s
                """, (infraction_increment, ban_increment, user_id))

        await db.commit()
        await mycursor.close()

    async def update_staff_member_join_date(self, user_id: int, joining_date: str) -> None:
        """ Updates a user's joining Staff date.
        :param user_id: The ID of the staff member.
        :param joining_date: The joining date in text. """

        mycursor, db = await the_database()
        await mycursor.execute("UPDATE StaffMember SET joined_staff_at = %s WHERE user_id = %s", (joining_date, user_id))
        await db.commit()
        await mycursor.close()

    async def delete_staff_member(self, user_id: int) -> None:
        """ Deletes a Staff member from the database.
        :param user_id: The ID of the Staff member. """

        mycursor, db = await the_database()
        await mycursor.execute("DELETE FROM StaffMember WHERE user_id = %s", (user_id,))
        await db.commit()
        await mycursor.close()