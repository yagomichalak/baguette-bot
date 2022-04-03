import discord
from discord.ext import commands

from mysqldb import the_database
from typing import List, Tuple

class MutedMemberTable(commands.Cog):
    """ Class for managing the MutedMember table in the database. """

    def __init__(self, client: commands.Bot) -> None:
        """ Class init method. """

        self.client = client

    @commands.command(hidden=True)
    @commands.has_permissions(administrator=True)
    async def create_table_mutedmember(self, ctx) -> None:
        """ (ADM) Creates the UserInfractions table. """

        if await self.check_table_mutedmember_exists():
            return await ctx.send("**Table __MutedMember__ already exists!**")
        
        await ctx.message.delete()
        mycursor, db = await the_database()
        await mycursor.execute("""CREATE TABLE MutedMember (
            user_id BIGINT NOT NULL, 
            role_id BIGINT NOT NULL, 
            mute_ts BIGINT DEFAULT NULL, 
            muted_for_seconds BIGINT DEFAULT NULL,
            PRIMARY KEY(user_id, role_id)
        )""")
        await db.commit()
        await mycursor.close()

        return await ctx.send("**Table __MutedMember__ created!**", delete_after=3)

    @commands.command(hidden=True)
    @commands.has_permissions(administrator=True)
    async def drop_table_mutedmember(self, ctx) -> None:
        """ (ADM) Creates the UserInfractions table """
        if not await self.check_table_mutedmember_exists():
            return await ctx.send("**Table __MutedMember__ doesn't exist!**")
        await ctx.message.delete()
        mycursor, db = await the_database()
        await mycursor.execute("DROP TABLE MutedMember")
        await db.commit()
        await mycursor.close()

        return await ctx.send("**Table __MutedMember__ dropped!**", delete_after=3)

    @commands.command(hidden=True)
    @commands.has_permissions(administrator=True)
    async def reset_table_mutedmember(self, ctx):
        """ (ADM) Resets the MutedMember table. """

        if not await self.check_table_mutedmember_exists():
            return await ctx.send("**Table __MutedMember__ doesn't exist yet**")

        await ctx.message.delete()
        mycursor, db = await the_database()
        await mycursor.execute("DELETE FROM MutedMember")
        await db.commit()
        await mycursor.close()

        return await ctx.send("**Table __MutedMember__ reset!**", delete_after=3)

    async def check_table_mutedmember_exists(self) -> bool:
        """ Checks if the MutedMember table exists. """

        mycursor, _ = await the_database()
        await mycursor.execute("SHOW TABLE STATUS LIKE 'MutedMember'")
        exists = await mycursor.fetchone()
        await mycursor.close()

        if exists:
            return True
        else:
            return False

    async def insert_in_muted(self, user_role_ids: List[Tuple[int]]) -> None:
        """ Inserts a user into the database.
        :param use_role_ids: The list of the user's muted roles IDs. """

        mycursor, db = await the_database()
        await mycursor.executemany("""
            INSERT INTO MutedMember (
            user_id, role_id, mute_ts, muted_for_seconds) VALUES (%s, %s, %s, %s)""", user_role_ids
        )
        await db.commit()
        await mycursor.close()

    async def get_muted_roles(self, user_id: int) -> List[Tuple[int, int]]:
        """ Gets the muted roles from a specific muted member.
        :param user_id: The user ID. """

        mycursor, _ = await the_database()
        await mycursor.execute("SELECT * FROM MutedMember WHERE user_id = %s", (user_id,))
        user_roles = await mycursor.fetchall()
        await mycursor.close()
        return user_roles

    async def get_expired_tempmutes(self, current_ts: int) -> List[int]:
        """ Gets expired tempmutes. 
        :param current_ts: The current timestamp. """

        mycursor, _ = await the_database()
        await mycursor.execute("SELECT DISTINCT(user_id) FROM MutedMember WHERE (%s -  mute_ts) >= muted_for_seconds", (current_ts,))
        tempmutes = list(map(lambda m: m[0], await mycursor.fetchall()))
        await mycursor.close()
        return tempmutes

    async def remove_role_from_system(self, user_role_ids: List[Tuple[int, int]]) -> None:
        """ Removes all muted roles from a specific user.
        :param user_role_ids: The list of the user's muted roles IDs. """

        mycursor, db = await the_database()
        await mycursor.executemany("DELETE FROM MutedMember WHERE user_id = %s AND role_id = %s", user_role_ids)
        await db.commit()
        await mycursor.close()


    async def remove_all_roles_from_system(self, user_id: int) -> None:
        """ Removes all muted-roles linked to a user from the system.
        :param user_id: The user ID. """

        mycursor, db = await the_database()
        await mycursor.execute("DELETE FROM MutedMember WHERE user_id = %s", (user_id,))
        await db.commit()
        await mycursor.close()

