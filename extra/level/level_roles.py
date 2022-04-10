import discord
from discord.ext import commands
from mysqldb import the_database

from typing import List

class LevelRoleTable(commands.Cog):
    """ Class for managing the LevelRole table in the database."""

    def __init__(self, client: commands.Bot) -> None:
        """ Class init method. """

        self.client = client

    @commands.command(hidden=True)
    @commands.has_permissions(administrator=True)
    async def create_table_level_roles(self, ctx) -> None:
        """ Creates the LevelRoles table. """

        if await self.table_level_roles_exists():
            return await ctx.send("**The `LevelRoles` table already exists!**")

        mycursor, db = await the_database()
        await mycursor.execute("""
            CREATE TABLE LevelRoles (level int NOT NULL, role_id bigint NOT NULL)""")
        await db.commit()
        await mycursor.close()
        await ctx.send("**Created `LevelRoles` table!**")

    @commands.command(hidden=True)
    @commands.has_permissions(administrator=True)
    async def drop_table_level_roles(self, ctx) -> None:
        """ Drops the LevelRoles table. """

        if not await self.table_level_roles_exists():
            return await ctx.send("**The `LevelRoles` table doesn't exist!**")

        mycursor, db = await the_database()
        await mycursor.execute("DROP TABLE LevelRoles")
        await db.commit()
        await mycursor.close()
        await ctx.send("**Dropped `LevelRoles` table!**")

    @commands.command(hidden=True)
    @commands.has_permissions(administrator=True)
    async def reset_table_level_roles(self, ctx) -> None:
        """ Resets the LevelRoles table. """

        if not await self.table_level_roles_exists():
            return await ctx.send("**The `LevelRoles` table doesn't exist yet!**")

        mycursor, db = await the_database()
        await mycursor.execute("DELETE FROM LevelRoles")
        await db.commit()
        await mycursor.close()
        await ctx.send("**Reset `LevelRoles` table!**")

    async def table_level_roles_exists(self) -> bool:
        """ Checks whether the LevelRoles table exists. """

        mycursor, _ = await the_database()
        await mycursor.execute(f"SHOW TABLE STATUS LIKE 'LevelRoles'")
        exists = await mycursor.fetchall()
        await mycursor.close()
        if exists:
            return True
        else:
            return False

    async def insert_level_role(self, level: int, role_id: int) -> None:
        """ Inserts a level role into the database.
        :param level: The level to insert.
        :param role_id: The ID of the role to attach to the level. """

        mycursor, db = await the_database()
        await mycursor.execute("INSERT INTO LevelRoles (level, role_id) VALUES (%s, %s)", (level, role_id))
        await db.commit()
        await mycursor.close()

    async def select_specific_level_role(self, level: int = None, role_id: int = None) -> List[int]:
        """ Selects a specific level role from the database by level or role ID. """

        mycursor, _ = await the_database()
        if level:
            await mycursor.execute("SELECT * FROM LevelRoles WHERE level = %s", (level,))
        elif role_id:
            await mycursor.execute("SELECT * FROM LevelRoles WHERE role_id = %s", (role_id,))

        level_role = await mycursor.fetchone()
        await mycursor.close()
        return level_role

    async def select_level_role(self) -> List[List[int]]:
        """ Selects all level roles from the database. """

        mycursor, _ = await the_database()
        await mycursor.execute("SELECT * FROM LevelRoles ORDER BY level")
        level_roles = await mycursor.fetchall()
        await mycursor.close()
        return level_roles

    async def get_level_role_ids(self) -> List[int]:
        """ Gets all level roles IDs. """

        mycursor, _ = await the_database()
        await mycursor.execute("SELECT role_id FROM LevelRoles")
        level_roles = await mycursor.fetchall()
        await mycursor.close()
        return list(map(lambda lr: lr[0], level_roles))

    async def delete_level_role(self, level: int = None, role_id: int = None) -> None:
        """ Deletes a level role from the database by level or role ID.
        :param level: The level to delete. """

        mycursor, db = await the_database()
        if level:
            await mycursor.execute("DELETE FROM LevelRoles WHERE level = %s", (level,))
        elif role_id:
            await mycursor.execute("DELETE FROM LevelRoles WHERE role_id = %s", (role_id,))
        await db.commit()
        await mycursor.close()

class VCLevelRoleTable(commands.Cog):
    """ Class for managing the VC LevelRole table in the database."""

    def __init__(self, client: commands.Bot) -> None:
        """ Class init method. """

        self.client = client

    @commands.command(hidden=True)
    @commands.has_permissions(administrator=True)
    async def create_table_vc_level_roles(self, ctx) -> None:
        """ Creates the VCLevelRoles table. """

        if await self.table_vc_level_roles_exists():
            return await ctx.send("**The `VCLevelRoles` table already exists!**")

        mycursor, db = await the_database()
        await mycursor.execute("""
            CREATE TABLE VCLevelRoles (
                level INT NOT NULL, 
                role_id BIGINT NOT NULL
            )""")
        await db.commit()
        await mycursor.close()
        await ctx.send("**Created `VCLevelRoles` table!**")

    @commands.command(hidden=True)
    @commands.has_permissions(administrator=True)
    async def drop_table_vc_level_roles(self, ctx) -> None:
        """ Drops the VCLevelRoles table. """

        if not await self.table_vc_level_roles_exists():
            return await ctx.send("**The `VCLevelRoles` table doesn't exist!**")

        mycursor, db = await the_database()
        await mycursor.execute("DROP TABLE VCLevelRoles")
        await db.commit()
        await mycursor.close()
        await ctx.send("**Dropped `VCLevelRoles` table!**")

    @commands.command(hidden=True)
    @commands.has_permissions(administrator=True)
    async def reset_table_vc_level_roles(self, ctx) -> None:
        """ Resets the VCLevelRoles table. """

        if not await self.table_vc_level_roles_exists():
            return await ctx.send("**The `VCLevelRoles` table doesn't exist yet!**")

        mycursor, db = await the_database()
        await mycursor.execute("DELETE FROM VCLevelRoles")
        await db.commit()
        await mycursor.close()
        await ctx.send("**Reset `VCLevelRoles` table!**")

    async def table_vc_level_roles_exists(self) -> bool:
        """ Checks whether the VCLevelRoles table exists. """

        mycursor, _ = await the_database()
        await mycursor.execute(f"SHOW TABLE STATUS LIKE 'VCLevelRoles'")
        exists = await mycursor.fetchall()
        await mycursor.close()
        if exists:
            return True
        else:
            return False

    async def insert_vc_level_role(self, level: int, role_id: int) -> None:
        """ Inserts a VC level role into the database.
        :param level: The level to insert.
        :param role_id: The ID of the role to attach to the level. """

        mycursor, db = await the_database()
        await mycursor.execute("INSERT INTO VCLevelRoles (level, role_id) VALUES (%s, %s)", (level, role_id))
        await db.commit()
        await mycursor.close()

    async def select_specific_vc_level_role(self, level: int = None, role_id: int = None) -> List[int]:
        """ Selects a specific VC level role from the database by level or role ID. """

        mycursor, _ = await the_database()
        if level:
            await mycursor.execute("SELECT * FROM VCLevelRoles WHERE level = %s", (level,))
        elif role_id:
            await mycursor.execute("SELECT * FROM VCLevelRoles WHERE role_id = %s", (role_id,))

        level_role = await mycursor.fetchone()
        await mycursor.close()
        return level_role

    async def select_vc_level_role(self) -> List[List[int]]:
        """ Selects all VC level roles from the database. """

        mycursor, _ = await the_database()
        await mycursor.execute("SELECT * FROM VCLevelRoles ORDER BY level")
        level_roles = await mycursor.fetchall()
        await mycursor.close()
        return level_roles

    async def get_vc_level_role_ids(self) -> List[int]:
        """ Gets all level roles IDs. """

        mycursor, _ = await the_database()
        await mycursor.execute("SELECT role_id FROM VCLevelRoles")
        level_roles = await mycursor.fetchall()
        await mycursor.close()
        return list(map(lambda lr: lr[0], level_roles))

    async def delete_vc_level_role(self, level: int = None, role_id: int = None) -> None:
        """ Deletes a VC level role from the database by level or role ID.
        :param level: The level to delete. """

        mycursor, db = await the_database()
        if level:
            await mycursor.execute("DELETE FROM VCLevelRoles WHERE level = %s", (level,))
        elif role_id:
            await mycursor.execute("DELETE FROM VCLevelRoles WHERE role_id = %s", (role_id,))
        await db.commit()
        await mycursor.close()