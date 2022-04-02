import discord
from discord.ext import commands
from mysqldb import the_database

import os
from typing import List, Union, Any

class ImportantVarsTable(commands.Cog):
    """ Class for managing the ImportantVars table in the database."""

    def __init__(self, client: commands.Bot) -> None:
        """ Class init method. """

        self.client = client

    @commands.command(hidden=True)
    @commands.has_permissions(administrator=True)
    async def create_table_important_vars(self, ctx) -> None:
        """ Creates the ImportantVars table. """

        if await self.table_important_vars_exists():
            return await ctx.send("**The `ImportantVars` table already exists!**")

        mycursor, db = await the_database()
        await mycursor.execute("""
            CREATE TABLE ImportantVars (label VARCHAR(15), value_str VARCHAR(30), value_int BIGINT DEFAULT 0)""")
        await db.commit()
        await mycursor.close()
        await ctx.send("**Created `ImportantVars` table!**")

    @commands.command(hidden=True)
    @commands.has_permissions(administrator=True)
    async def drop_table_important_vars(self, ctx) -> None:
        """ Drops the ImportantVars table. """

        if not await self.table_important_vars_exists():
            return await ctx.send("**The `ImportantVars` table doesn't exist!**")

        mycursor, db = await the_database()
        await mycursor.execute("DROP TABLE ImportantVars")
        await db.commit()
        await mycursor.close()
        await ctx.send("**Dropped `ImportantVars` table!**")

    @commands.command(hidden=True)
    @commands.has_permissions(administrator=True)
    async def reset_table_important_vars(self, ctx) -> None:
        """ Resets the ImportantVars table. """

        if not await self.table_important_vars_exists():
            return await ctx.send("**The `ImportantVars` table doesn't exist yet!**")

        mycursor, db = await the_database()
        await mycursor.execute("DELETE FROM ImportantVars")
        await db.commit()
        await mycursor.close()
        await ctx.send("**Reset `ImportantVars` table!**")

    async def table_important_vars_exists(self) -> bool:
        """ Checks whether the ImportantVars table exists. """

        mycursor, _ = await the_database()
        await mycursor.execute(f"SHOW TABLE STATUS LIKE 'ImportantVars'")
        exists = await mycursor.fetchall()
        await mycursor.close()
        if exists:
            return True
        else:
            return False

    async def insert_important_var(self, label: str, value_str: str = None, value_int: int = None) -> None:
        """ Gets an important var.
        :param label: The label o that var. """

        mycursor, db = await the_database()
        await mycursor.execute("INSERT INTO ImportantVars (label, value_str, value_int) VALUES (%s, %s, %s)", (label, value_str, value_int))
        await db.commit()
        await mycursor.close()

    async def get_important_var(self, label: str, value_str: str = None, value_int: int = None, multiple: bool = False) -> Union[Union[str, int], List[Union[str, int]]]:
        """ Gets an important var.
        :param label: The label o that var.
        :param value_str: The string value. (Optional)
        :param value_int: The integer value. (Optional)
        :param multiple: Whether to get multiple values. """

        mycursor, _ = await the_database()
        if value_str and value_int:
            await mycursor.execute("SELECT * FROM ImportantVars WHERE label = %s AND value_str = %s AND value_int = %s", (label, value_str, value_int))
        elif value_str:
            await mycursor.execute("SELECT * FROM ImportantVars WHERE label = %s AND value_str = %s", (label, value_str))
        elif value_int:
            await mycursor.execute("SELECT * FROM ImportantVars WHERE label = %s AND value_int = %s", (label, value_int))
        else:
            await mycursor.execute("SELECT * FROM ImportantVars WHERE label = %s", (label,))

        important_var = None
        if multiple:
            important_var = await mycursor.fetchall()
        else:
            important_var = await mycursor.fetchone()
        await mycursor.close()
        return important_var

    async def update_important_var(self, label: str, value_str: str = None, value_int: str = None) -> None:
        """ Gets an important var.
        :param label: The label o that var.
        :param value_str: The string value.
        :param value_int: The integer value. """
        
        mycursor, db = await the_database()
        if value_str is not None and value_int is not None:
            await mycursor.execute("UPDATE ImportantVars SET value_str = %s, value_int = %s WHERE label = %s", (value_str, value_int, label))
        elif value_str is not None:
            await mycursor.execute("UPDATE ImportantVars SET value_str = %s WHERE label = %s", (value_str, label))
        else:
            await mycursor.execute("UPDATE ImportantVars SET value_int = %s WHERE label = %s", (value_int, label))

        await db.commit()
        await mycursor.close()

    async def increment_important_var_int(self, label: str, increment: int = 1) -> None:
        """ Increments an integer value of an important var by a value.
        :param label: The lable of the important var.
        :param increment: Ther increment value to apply. Default = 1. """

        mycursor, db = await the_database()
        await mycursor.execute("UPDATE ImportantVars SET value_int = value_int + %s WHERE label = %s", (increment, label))
        await db.commit()
        await mycursor.close()

    async def delete_important_var(self, label: str, value_str: str = None, value_int: int = None) -> None:
        """ Deletes an important var.
        :param label: The label o that var.
        :param value_str: The string value. (Optional)
        :param value_int: The integer value. (Optional) """

        mycursor, db = await the_database()

        if value_str and value_int:
            await mycursor.execute("DELETE FROM ImportantVars WHERE label = %s and value_str = %s and value_int = %s", (label, value_str, value_int))
        elif value_str:
            await mycursor.execute("DELETE FROM ImportantVars WHERE label = %s and value_str = %s", (label, value_str))
        elif value_int:
            await mycursor.execute("DELETE FROM ImportantVars WHERE label = %s and value_int = %s", (label, value_int))
        else:
            await mycursor.execute("DELETE FROM ImportantVars WHERE label = %s", (label,))

        await db.commit()
        await mycursor.close()

