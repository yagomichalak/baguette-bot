import discord
from discord.ext import commands

from mysqldb import the_database
from typing import List, Union

class UserInfractionsTable(commands.Cog):
    """ Class for managing the UserInfractionsTable table in the database. """

    def __init__(self, client: commands.Bot) -> None:
        """ Class init method. """

        self.client = client

    @commands.command(hidden=True)
    @commands.has_permissions(administrator=True)
    async def create_table_user_infractions(self, ctx) -> None:
        """ (ADM) Creates the UserInfractions table. """

        if await self.check_table_user_infractions():
            return await ctx.send("**Table __UserInfractions__ already exists!**")
        
        await ctx.message.delete()
        mycursor, db = await the_database()
        await mycursor.execute("""CREATE TABLE UserInfractions (
            user_id BIGINT NOT NULL, 
            infraction_type VARCHAR(7) NOT NULL, 
            infraction_reason VARCHAR(250) DEFAULT NULL, 
            infraction_ts BIGINT NOT NULL, 
            infraction_id BIGINT NOT NULL AUTO_INCREMENT, 
            perpetrator BIGINT NOT NULL, 
            PRIMARY KEY(infraction_id)
        )""")
        await db.commit()
        await mycursor.close()

        return await ctx.send("**Table __UserInfractions__ created!**", delete_after=3)

    @commands.command(hidden=True)
    @commands.has_permissions(administrator=True)
    async def drop_table_user_infractions(self, ctx) -> None:
        """ (ADM) Creates the UserInfractions table. """

        if not await self.check_table_user_infractions():
            return await ctx.send("**Table __UserInfractions__ doesn't exist!**")
        await ctx.message.delete()
        mycursor, db = await the_database()
        await mycursor.execute("DROP TABLE UserInfractions")
        await db.commit()
        await mycursor.close()

        return await ctx.send("**Table __UserInfractions__ dropped!**", delete_after=3)

    @commands.command(hidden=True)
    @commands.has_permissions(administrator=True)
    async def reset_table_user_infractions(self, ctx) -> None:
        """ (ADM) Creates the UserInfractions table. """

        if not await self.check_table_user_infractions():
            return await ctx.send("**Table __UserInfractions__ doesn't exist yet!**")

        await ctx.message.delete()
        mycursor, db = await the_database()
        await mycursor.execute("DELETE FROM UserInfractions")
        await db.commit()
        await mycursor.close()

        return await ctx.send("**Table __UserInfractions__ reset!**", delete_after=3)

    async def check_table_user_infractions(self) -> bool:
        """ Checks whether the UserInfractions table exists. """

        mycursor, _ = await the_database()
        await mycursor.execute("SHOW TABLE STATUS LIKE 'UserInfractions'")
        exists = await mycursor.fetchone()
        await mycursor.close()

        if exists:
            return True
        else:
            return False

    async def insert_user_infraction(self, user_id: int, infr_type: str, reason: str, timestamp: int, perpetrator: int) -> None:
        """ Insert a warning into the system.
        :param user_id: The user ID.
        :param infr_type: The infraction type.
        :param reason: The infraction reason.
        :param timestamp: The infraction action timestamp.
        :param perpetrator: The ID of the perpetrator of infraction action. """

        mycursor, db = await the_database()
        await mycursor.execute("""
            INSERT INTO UserInfractions (
            user_id, infraction_type, infraction_reason,
            infraction_ts, perpetrator)
            VALUES (%s, %s, %s, %s, %s)""",
            (user_id, infr_type, reason, timestamp, perpetrator))
        await db.commit()
        await mycursor.close()

    async def get_user_infractions(self, user_id: int) -> List[List[Union[str, int]]]:
        """ Gets all infractions from a user.
        :param user_id: The user ID. """

        mycursor, _ = await the_database()
        await mycursor.execute("SELECT * FROM UserInfractions WHERE user_id = %s", (user_id,))
        user_infractions = await mycursor.fetchall()
        await mycursor.close()
        return user_infractions

    async def get_user_infraction_by_infraction_id(self, infraction_id: int) -> List[List[Union[str, int]]]:
        """ Gets a specific infraction by ID.
        :param infraction_id: The infraction ID. """

        mycursor, _ = await the_database()
        await mycursor.execute("SELECT * FROM UserInfractions WHERE infraction_id = %s", (infraction_id,))
        user_infractions = await mycursor.fetchall()
        await mycursor.close()
        return user_infractions

    async def remove_user_infraction(self, infraction_id: int) -> None:
        """ Removes a specific infraction by ID.
        :param infraction_id: The infraction ID. """

        mycursor, db = await the_database()
        await mycursor.execute("DELETE FROM UserInfractions WHERE infraction_id = %s", (infraction_id,))
        await db.commit()
        await mycursor.close()

    async def remove_user_infractions(self, user_id: int) -> None:
        """ Removes all infractions of a user by ID.
        :parma user_id: The user ID. """

        mycursor, db = await the_database()
        await mycursor.execute("DELETE FROM UserInfractions WHERE user_id = %s", (user_id,))
        await db.commit()
        await mycursor.close()