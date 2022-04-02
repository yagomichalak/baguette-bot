import discord
from discord.ext import commands
from mysqldb import the_database

import os
from typing import List, Union, Any

class MemberStatusTable(commands.Cog):
    """ Class for managing the MemberStatus table in the database."""

    def __init__(self, client: commands.Bot) -> None:
        """ Class init method. """

        self.client = client

    @commands.has_permissions(administrator=True)
    @commands.command(hidden=True)
    async def create_table_member_status(self, ctx):
        """ (ADM) Creates the MemberStatus table. """

        if await self.table_member_status_exists():
            return await ctx.send("**The `MemberStatus` table already exists!**")

        mycursor, db = await the_database()
        await mycursor.execute(
            """CREATE TABLE MemberStatus (
            user_id BIGINT, user_xp BIGINT, user_lvl INT,
            user_xp_time INT, user_messages INT DEFAULT 0,
            vc_time BIGINT DEFAULT 0, vc_ts BIGINT
            )""")
        await db.commit()
        await mycursor.close()
                
        await ctx.send("**Table `MemberStatus` created!**")

    @commands.has_permissions(administrator=True)
    @commands.command(hidden=True)
    async def drop_table_member_status(self, ctx):
        """ (ADM) Drops the MemberStatus table. """

        if not await self.table_member_status_exists():
            return await ctx.send("**The `MemberStatus` table doesn't exist!**")

        mycursor, db = await the_database()
        await mycursor.execute("DROP TABLE MemberStatus")
        await db.commit()
        await mycursor.close()

        await ctx.send("**Table `MemberStatus` dropped!**")

    @commands.has_permissions(administrator=True)
    @commands.command(hidden=True)
    async def reset_table_member_status(self, ctx):
        """ (ADM) Resets the MemberStatus table. """


        if not await self.table_member_status_exists():
            return await ctx.send("**The `MemberStatus` table doesn't exist yet!**")

        mycursor, db = await the_database()
        await mycursor.execute("DELETE FROM MemberStatus")
        await db.commit()
        await mycursor.close()

        await ctx.send("**Table `MemberStatus` reseted!**")

    async def table_member_status_exists(self) -> bool:
        """ Checks whether the LevelRoles table exists. """

        mycursor, _ = await the_database()
        await mycursor.execute(f"SHOW TABLE STATUS LIKE 'MemberStatus'")
        table_info = await mycursor.fetchall()
        await mycursor.close()
        if len(table_info) == 0:
                return False
        else:
            return True

    async def insert_user(self, user_id: int, xp_time: int, xp: int = 0, lvl: int = 1, messages: int = 0, vc_time: int = 0, vc_ts: int = None) -> None:
        mycursor, db = await the_database()
        await mycursor.execute("""
            INSERT INTO MemberStatus (user_id, user_xp, user_lvl, user_xp_time, user_messages, vc_time, vc_ts) 
            VALUES (%s, %s, %s, %s, %s, %s, %s)""", 
            (user_id, xp, lvl, xp_time, messages, vc_time, vc_ts))
        await db.commit()
        await mycursor.close()

    async def update_user_xp(self, user_id: int, xp: int) -> None:
        mycursor, db = await the_database()
        await mycursor.execute("UPDATE MemberStatus SET user_xp = user_xp + %s WHERE user_id = %s", (xp, user_id))
        await db.commit()
        await mycursor.close()

    async def update_user_lvl(self, user_id: int, level: int) -> None:
        mycursor, db = await the_database()
        await mycursor.execute("UPDATE MemberStatus set user_lvl = %s WHERE user_id = %s", (level, user_id))
        await db.commit()
        await mycursor.close()

    async def update_user_xp_time(self, user_id: int, time: int) -> None:
        mycursor, db = await the_database()
        await mycursor.execute("UPDATE MemberStatus SET user_xp_time = %s WHERE user_id = %s", (time, user_id))
        await db.commit()
        await mycursor.close()

    async def update_user_server_messages(self, user_id: int, add_msg: int) -> None:
        mycursor, db = await the_database()
        await mycursor.execute(
            "UPDATE MemberStatus SET user_messages = user_messages + %s WHERE user_id = %s", (add_msg, user_id))
        await db.commit()
        await mycursor.close()

    async def update_user_server_time(self, user_id: int, add_time: int, reset_ts: bool = False) -> None:
        mycursor, db = await the_database()
        if reset_ts:
            await mycursor.execute(
                "UPDATE MemberStatus SET vc_time = vc_time + %s, vc_ts = NULL WHERE user_id = %s", (add_time, user_id))
        else:
            await mycursor.execute(
                "UPDATE MemberStatus SET vc_time = vc_time + %s WHERE user_id = %s", (add_time, user_id))
        await db.commit()
        await mycursor.close()

    async def update_user_server_timestamp(self, user_id: int, new_ts: int) -> None:
        mycursor, db = await the_database()
        await mycursor.execute("UPDATE MemberStatus SET vc_ts = %s WHERE user_id = %s", (new_ts, user_id))
        await db.commit()
        await mycursor.close()

    async def remove_user(self, user_id: int) -> None:
        mycursor, db = await the_database()
        await mycursor.execute("DELETE FROM MemberStatus WHERE user_id = %s", (user_id,))
        await db.commit()
        await mycursor.close()

    async def clear_user_lvl(self, user_id: int) -> None:
        mycursor, db = await the_database()
        await mycursor.execute("UPDATE MemberStatus SET user_xp = 0, user_lvl = 1 WHERE user_id = %s", (user_id,))
        await db.commit()
        await mycursor.close()

    async def get_users(self) -> List[List[int]]:
        """ Gets all users from the MemberStatus system. """

        mycursor, _ = await the_database()
        await mycursor.execute("SELECT * FROM MemberStatus")
        members = await mycursor.fetchall()
        await mycursor.close()
        return members

    async def get_specific_user(self, user_id: int) -> List[int]:
        """ Gets a specific user from the MemberStatus system. 
        :param user_id: The ID of the user to get. """

        mycursor, db = await the_database()
        await mycursor.execute("SELECT * FROM MemberStatus WHERE user_id = %s", (user_id,))
        member = await mycursor.fetchall()
        await mycursor.close()
        return member

    async def get_all_users_by_xp(self) -> List[List[int]]:
        """ Gets all users from the MembersScore table ordered by XP. """

        mycursor, _ = await the_database()
        await mycursor.execute("SELECT * FROM MemberStatus ORDER BY user_xp DESC")
        users = await mycursor.fetchall()
        await mycursor.close()
        return users

    async def get_total_messages(self) -> int:
        """ Gets the total amount of messages sent in the server. """

        mycursor, _ = await the_database()
        await mycursor.execute("SELECT SUM(user_messages) FROM MemberStatus")
        total = number[0] if (number := await mycursor.fetchone()) else 0
        await mycursor.close()
        return total

    async def get_total_time(self) -> int:
        """ Gets the total time spent in the server's VCs. """

        mycursor, _ = await the_database()
        await mycursor.execute("SELECT SUM(vc_time) FROM MemberStatus")
        total = number[0] if (number := await mycursor.fetchone()) else 0
        await mycursor.close()
        return total

