import discord
from discord.ext import commands
from mysqldb import the_database
from typing import List, Union

class TicketTable(commands.Cog):
    """ Class for managing ticket in the database. """

    def __init__(self, client: commands.Bot) -> None:
        """ Class init method. """

        self.client = client


    async def get_ticket_number(self) -> int:
        """ Gets the current ticket counting number. """

        mycursor, _ = await the_database()
        await mycursor.execute("SELECT * FROM TicketCounter")
        counter = await mycursor.fetchone()
        await mycursor.close()
        if len(counter) > 0:
            return counter[0]
        else:
            return 0

    async def get_ticket_channel(self, channel_id: int) -> List[int]:
        """ Gets a ticket channel with the given channel ID. """

        mycursor, _ = await the_database()
        await mycursor.execute("SELECT * FROM Ticket WHERE channel_id = %s", (channel_id,))
        the_channel = await mycursor.fetchone()
        await mycursor.close()
        return the_channel

    async def increase_ticket_number(self) -> None:
        """ Increases the ticket counting number. """

        mycursor, db = await the_database()
        await mycursor.execute("UPDATE TicketCounter SET counter = counter + 1")
        await db.commit()
        await mycursor.close()

    async def insert_ticket_channel(self, member_id: int, channel_id: int) -> None:
        """ Insert the ticket channel ID into the database. """

        mycursor, db = await the_database()
        await mycursor.execute("INSERT INTO Ticket (member_id, channel_id) VALUES (%s, %s)", (member_id, channel_id))
        await db.commit()
        await mycursor.close()

    async def remove_ticket_channel(self, member_id: int) -> None:
        """ Removes a ticket channel from the system. """

        mycursor, db = await the_database()
        await mycursor.execute("DELETE FROM Ticket WHERE member_id = %s", (member_id,))
        await db.commit()
        await mycursor.close()


    async def has_ticket_channel(self, member_id: int) -> Union[int, bool]:
        """ Checks whether the member has an open ticket channel. """

        mycursor, _ = await the_database()
        await mycursor.execute("SELECT * FROM Ticket WHERE member_id = %s", (member_id,))
        member_info = await mycursor.fetchone()
        await mycursor.close()
        if member_info:
            return member_info[1]
        else:
            return False


    @commands.command(hidden=True)
    @commands.has_permissions(administrator=True)
    async def create_ticket_table(self, ctx) -> None:
        """ Creates the Ticket table. """

        if await self.ticket_table_exists():
            return await ctx.send("**Table __Ticket__ already exists!**")

        mycursor, db = await the_database()
        await mycursor.execute("CREATE TABLE Ticket (member_id BIGINT NOT NULL, channel_id BIGINT NOT NULL)")
        await db.commit()
        await mycursor.close()
        await ctx.send("**Created __Ticket__ table!**")

    @commands.command(hidden=True)
    @commands.has_permissions(administrator=True)
    async def drop_ticket_table(self, ctx) -> None:
        """ Drops the Ticket table. """

        if not await self.ticket_table_exists():
            return await ctx.send("**Table __Ticket__ doesn't exist!**")

        mycursor, db = await the_database()
        await mycursor.execute("DROP TABLE Ticket")
        await db.commit()
        await mycursor.close()
        await ctx.send("**Dropped __Ticket__ table!**")

    @commands.command(hidden=True)
    @commands.has_permissions(administrator=True)
    async def reset_ticket_table(self, ctx) -> None:
        """ Resets the Ticket table. """

        if not await self.ticket_table_exists():
            return await ctx.send("**Table __Ticket__ doesn't exist yet!**")

        mycursor, db = await the_database()
        await mycursor.execute("DELETE FROM Ticket")
        await db.commit()
        await mycursor.close()
        await ctx.send("**Reset __Ticket__ table!**")

    async def ticket_table_exists(self) -> bool:
        """ Checks whether the Ticket table exists. """

        mycursor, _ = await the_database()
        await mycursor.execute(f"SHOW TABLE STATUS LIKE 'Ticket'")
        table_info = await mycursor.fetchone()
        await mycursor.close()
        if len(table_info) == 0:
            return False
        else:
            return True

    # Create, drop, reset methods for the TicketCounter table.

    @commands.command(hidden=True)
    @commands.has_permissions(administrator=True)
    async def create_ticket_counter_table(self, ctx):
        """ Creates the TicketCounter table. """

        if await self.ticket_counter_table_exists():
            return await ctx.send("**Table __TicketCounter__ already exists!**")

        mycursor, db = await the_database()
        await mycursor.execute("CREATE TABLE TicketCounter (counter BIGINT DEFAULT 0)")
        await mycursor.execute("INSERT INTO TicketCounter (counter) VALUES (0)")
        await db.commit()
        await mycursor.close()
        await ctx.send("**Created __TicketCounter__ table!**")

    @commands.command(hidden=True)
    @commands.has_permissions(administrator=True)
    async def drop_ticket_counter_table(self, ctx):
        """ Drops the TicketCounter table. """

        if not await self.ticket_counter_table_exists():
            return await ctx.send("**Table __TicketCounter__ doesn't exist!**")

        mycursor, db = await the_database()
        await mycursor.execute("DROP TABLE TicketCounter")
        await db.commit()
        await mycursor.close()
        return await ctx.send("**Dropped __TicketCounter__ table!**")

    @commands.command(hidden=True)
    @commands.has_permissions(administrator=True)
    async def reset_ticket_counter_table(self, ctx):
        """ Resets the TicketCounter table. """

        if not await self.ticket_counter_table_exists():
            return await ctx.send("**Table __TicketCounter__ doesn't exist yet!**")

        mycursor, db = await the_database()
        await mycursor.execute("DELETE FROM TicketCounter")
        await mycursor.execute("INSERT INTO TicketCounter (counter) VALUES (0)")
        await db.commit()
        await mycursor.close()
        return await ctx.send("**Reset __TicketCounter__ table!**")

    async def ticket_counter_table_exists(self) -> bool:
        """ Checks whether the TicketCounter table exists. """

        mycursor, _ = await the_database()
        await mycursor.execute("SHOW TABLE STATUS LIKE 'TicketCounter'")
        table_info = await mycursor.fetchone()
        await mycursor.close()
        if len(table_info) == 0:
            return False
        else:
            return True