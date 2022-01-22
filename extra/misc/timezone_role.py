import discord
from discord.ext import commands
from mysqldb import the_database
from typing import List, Union

class TimezoneRoleTable(commands.Cog):
    """ Table for managing the TimezoneRole table. """

    def __init__(self, client: commands.Bot) -> None:
        """ Class init method. """

        self.client = client

    @commands.command(hidden=True)
    @commands.has_permissions(administrator=True)
    async def create_table_timezone_role(self, ctx) -> None:
        """ (ADM) Creates the TimezoneRole table. """

        if await self.check_table_timezone_role():
            return await ctx.send("**Table __TimezoneRole__ already exists!**")

        await ctx.message.delete()
        mycursor, db = await the_database()
        await mycursor.execute("""CREATE TABLE TimezoneRole (
            role_id BIGINT NOT NULL,
            role_timezone VARCHAR(10) NOT NULL,
            PRIMARY KEY(role_id, role_timezone)
            )""")

        await db.commit()
        await mycursor.close()

        return await ctx.send("**Table __TimezoneRole__ created!**", delete_after=3)

    @commands.command(hidden=True)
    @commands.has_permissions(administrator=True)
    async def drop_table_timezone_role(self, ctx) -> None:
        """ (ADM) Creates the TimezoneRole table """

        if not await self.check_table_timezone_role():
            return await ctx.send("**Table __TimezoneRole__ doesn't exist!**")

        await ctx.message.delete()
        mycursor, db = await the_database()
        await mycursor.execute("DROP TABLE TimezoneRole")
        await db.commit()
        await mycursor.close()

        return await ctx.send("**Table __TimezoneRole__ dropped!**", delete_after=3)

    @commands.command(hidden=True)
    @commands.has_permissions(administrator=True)
    async def reset_table_timezone_role(self, ctx) -> None:
        """ (ADM) Creates the TimezoneRole table """

        if not await self.check_table_timezone_role():
            return await ctx.send("**Table __TimezoneRole__ doesn't exist yet!**")

        await ctx.message.delete()
        mycursor, db = await the_database()
        await mycursor.execute("DELETE FROM TimezoneRole")
        await db.commit()
        await mycursor.close()

        return await ctx.send("**Table __TimezoneRole__ reset!**", delete_after=3)

    async def check_table_timezone_role(self) -> bool:
        """ Checks whether the TimezoneRole table exists """

        mycursor, _ = await the_database()
        await mycursor.execute("SHOW TABLE STATUS LIKE 'TimezoneRole'")
        table_info = await mycursor.fetchone()
        await mycursor.close()

        if table_info:
            return True

        else:
            return False

    async def insert_timezone_role(self, role_id: int, role_timezone: str) -> None:
        """ Inserts a Timezone Role into the databse.
        :param role_id: The ID of the role.
        :param role_timezone: The timezone to attach to the role. """

        mycursor, db = await the_database()
        await mycursor.execute("""
            INSERT INTO TimezoneRole (role_id, role_timezone)
            VALUES (%s, %s)""", (role_id, role_timezone))
        await db.commit()
        await mycursor.close()

    async def get_timezone_role(self, role_timezone: str) -> List[Union[int, str]]:
        """ Gets a specific timezone role.
        :param role_timezone: The role timezone to get. """

        mycursor, _ = await the_database()
        await mycursor.execute("""
            SELECT * FROM TimezoneRole WHERE role_timezone = %s
        """, (role_timezone,))
        timezone_role = await mycursor.fetchone()
        await mycursor.close()
        return timezone_role

    async def get_timezone_roles(self) -> List[List[Union[int, str]]]:
        """ Gets all Timezone Roles registered. """

        mycursor, _ = await the_database()
        await mycursor.execute("SELECT * FROM TimezoneRole ORDER BY role_timezone")
        timezone_roles = await mycursor.fetchall()
        await mycursor.close()
        return timezone_roles

    async def update_timezone_role(self, role_id: int, role_timezone: str) -> None:
        """ Updates a role ID for a Timezone Role by role timezone.
        :param role_id: The new role ID to attach to the Timezone Role.
        :param role_timezone: The role timezone to update. """

        mycursor, db = await the_database()
        await mycursor.execute("""
            UPDATE TimezoneRole SET
            role_id = %s WHERE role_timezone = %s
        """, (role_id, role_timezone))
        await db.commit()
        await mycursor.close()
    
    async def delete_timezone_role(self, role_timezone: str) -> None:
        """ Deletes a Timezone Role by role timezone.
        :param role_timezone: The timezone of the role to delete. """

        mycursor, db = await the_database()
        await mycursor.execute("""
            DELETE FROM TimezoneRole 
            WHERE role_timezone =  %s
        """, (role_timezone,))
        await db.commit()
        await mycursor.close()
    