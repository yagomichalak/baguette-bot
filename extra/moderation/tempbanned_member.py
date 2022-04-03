import discord
from discord.ext import commands

from mysqldb import the_database
from typing import List, Tuple

class TempbannedMemberTable(commands.Cog):
    """ Class for managing the TempbannedMember table in the database. """

    def __init__(self, client: commands.Bot) -> None:
        """ Class init method. """

        self.client = client

    @commands.command(hidden=True)
    @commands.has_permissions(administrator=True)
    async def create_table_tempbanned_member(self, ctx) -> None:
        """ (ADM) Creates the TempbannedMember table. """

        if await self.check_table_TempbannedMember_exists():
            return await ctx.send("**Table __TempbannedMember__ already exists!**")
        
        await ctx.message.delete()
        mycursor, db = await the_database()
        await mycursor.execute("""CREATE TABLE TempbannedMember (
            user_id BIGINT NOT NULL, 
            role_id BIGINT NOT NULL, 
            mute_ts BIGINT DEFAULT NULL, 
            tempbanned_for_seconds BIGINT DEFAULT NULL
        )""")
        await db.commit()
        await mycursor.close()

        return await ctx.send("**Table __TempbannedMember__ created!**", delete_after=3)

    @commands.command(hidden=True)
    @commands.has_permissions(administrator=True)
    async def drop_table_tempbanned_member(self, ctx) -> None:
        """ (ADM) Creates the TempbannedMember table """

        if not await self.check_table_TempbannedMember_exists():
            return await ctx.send("**Table __TempbannedMember__ doesn't exist!**")
        await ctx.message.delete()
        mycursor, db = await the_database()
        await mycursor.execute("DROP TABLE TempbannedMember")
        await db.commit()
        await mycursor.close()

        return await ctx.send("**Table __TempbannedMember__ dropped!**", delete_after=3)

    @commands.command(hidden=True)
    @commands.has_permissions(administrator=True)
    async def reset_table_tempbanned_member(self, ctx):
        """ (ADM) Resets the TempbannedMember table. """

        if not await self.check_table_TempbannedMember_exists():
            return await ctx.send("**Table __TempbannedMember__ doesn't exist yet**")

        await ctx.message.delete()
        mycursor, db = await the_database()
        await mycursor.execute("DELETE FROM TempbannedMember")
        await db.commit()
        await mycursor.close()

        return await ctx.send("**Table __TempbannedMember__ reset!**", delete_after=3)

    async def check_table_tempbanned_member_exists(self) -> bool:
        """ Checks if the TempbannedMember table exists. """

        mycursor, _ = await the_database()
        await mycursor.execute("SHOW TABLE STATUS LIKE 'TempbannedMember'")
        exists = await mycursor.fetchone()
        await mycursor.close()

        if exists:
            return True
        else:
            return False

    async def insert_in_tempbanned(self, user_role_ids: List[Tuple[int]]) -> None:
        """ Inserts a user into the database.
        :param use_role_ids: The list of the user's tempbanned roles IDs. """

        mycursor, db = await the_database()
        await mycursor.executemany("""
            INSERT INTO TempbannedMember (
            user_id, role_id, mute_ts, tempbanned_for_seconds) VALUES (%s, %s, %s, %s)""", user_role_ids
        )
        await db.commit()
        await mycursor.close()

    async def get_tempbanned_roles(self, user_id: int) -> List[Tuple[int, int]]:
        """ Gets the tempbanned roles from a specific tempbanned member.
        :param user_id: The user ID. """

        mycursor, _ = await the_database()
        await mycursor.execute("SELECT * FROM TempbannedMember WHERE user_id = %s", (user_id,))
        user_roles = await mycursor.fetchall()
        await mycursor.close()
        return user_roles

    async def remove_tempbanned_role_from_system(self, user_role_ids: List[Tuple[int, int]]) -> None:
        """ Removes all tempbanned roles from a specific user.
        :param user_role_ids: The list of the user's tempbanned roles IDs. """

        mycursor, db = await the_database()
        await mycursor.executemany("DELETE FROM TempbannedMember WHERE user_id = %s AND role_id = %s", user_role_ids)
        await db.commit()
        await mycursor.close()


    async def remove_all_tempbanned_roles_from_system(self, user_id: int) -> None:
        """ Removes all tempbanned-roles linked to a user from the system.
        :param user_id: The user ID. """

        mycursor, db = await the_database()
        await mycursor.execute("DELETE FROM TempbannedMember WHERE user_id = %s", (user_id,))
        await db.commit()
        await mycursor.close()

