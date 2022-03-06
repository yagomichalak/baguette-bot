from datetime import datetime
import discord
from discord.ext import commands, tasks
from mysqldb import the_database
from extra import utils
import os
from typing import List, Union

dev_channel_id: int = int(os.getenv('DEV_CHANNEL_ID'))
general_channel_id: int = int(os.getenv('GENERAL_CHANNEL_ID'))

class ScheduledEventsSystem(commands.Cog):
    """ Class for managing the ScheduledEventsSystem table in the database. """

    def __init__(self, client: commands.Bot) -> None:
        """ Class init method. """

        self.client = client

    @tasks.loop(seconds=60)
    async def advertise_patreon(self) -> None:
        """ Checks the time for advertising Patreon. """

        current_ts = await utils.get_timestamp()
        # Checks whether the Patreon advertising event exists
        if not await self.get_advertising_event(event_label='patreon_ad'):
            # If not, creates it
            return await self.insert_advertising_event(event_label='patreon_ad', current_ts=current_ts-10800)

        # Checks whether advertising time is due
        if await self.check_advertising_time(
            current_ts=int(current_ts), event_label="patreon_ad", ad_time=10800):
            # Updates time and advertises.
            await self.update_advertising_time(event_label="patreon_ad", current_ts=current_ts)
            general_channel = self.client.get_channel(general_channel_id)

            text: str = ''
            with open('./media/texts/patreon_ad.txt', 'r', encoding="utf-8") as f:
                text = f.read()
            
            await general_channel.send(text)

    @tasks.loop(seconds=60)
    async def solve_broken_roles(self) -> None:
        """ Checks the time for advertising Patreon. """

        current_ts = await utils.get_timestamp()
        # Checks whether the SolveBrokenRoles event exists
        if not await self.get_advertising_event(event_label='solve_broken_roles'):
            # If not, creates it
            return await self.insert_advertising_event(event_label='solve_broken_roles', current_ts=current_ts-28800)

        # Checks whether event time is due
        if await self.check_advertising_time(
            current_ts=int(current_ts), event_label="solve_broken_roles", ad_time=28800):
            print("• Solving broken roles...")
            # Updates time and advertises.
            await self.update_advertising_time(event_label="solve_broken_roles", current_ts=current_ts)
            dev_channel = self.client.get_channel(dev_channel_id)


            mycursor, _ = await the_database()
            await mycursor.execute("SELECT user_id, user_lvl FROM MemberStatus")
            members = await mycursor.fetchall()
            await mycursor.close()

            sticky_roles = {
                2: 862742944729268234,
                5: 862742944243253279,
            }

            sticky_roles = {
                role_lvl:role for role_lvl, role_id in sticky_roles.items() 
                if (role := discord.utils.get(dev_channel.guild.roles, id=role_id))
            }

            await dev_channel.send(f"**Updating `{len(members)}` member role...**")
            counter = 0
            failed = 0
            async with dev_channel.typing():

                for member_db in members:

                    if not (member := discord.utils.get(dev_channel.guild.members, id=member_db[0])):
                        continue

                    for role_lvl, role in sticky_roles.items():
                        if member_db[1] >= role_lvl:
                            if role not in member.roles:
                                try:
                                    await member.add_roles(role)
                                except:
                                    failed += 1
                                else:
                                    counter += 1

            await dev_channel.send(f"**Successfully added {counter} lvl roles! Failed {failed} assignments!**")


    @tasks.loop(seconds=60)
    async def advertise_patreon_slots(self) -> None:
        """ Checks the time for advertising Patreon. """

        current_time = await utils.get_time()

        # Checks whether advertising time is due
        if not await self.check_advertising_slots(current_time):
            return

        # Gets text and advertises.
        general_channel = self.client.get_channel(general_channel_id)

        text: str = ''
        with open('./media/texts/patreon_ad.txt', 'r', encoding="utf-8") as f:
            text = f.read()
        
        await general_channel.send(text)

    async def check_advertising_slots(self, current_time: datetime) -> bool:
        """ Checks whether the current time is one of the pre-selected ones
        at which to advertise the Patreon ad. """

        return current_time.hour in (12, 17, 22) and current_time.minute == 0

class ScheduledEventsTable(commands.Cog):
    """ Class for managing the ScheduledEvents table in the database. """

    def __init__(self, client: commands.Bot) -> None:
        """ Class init method. """

        self.client = client

    @commands.command(hidden=True)
    @commands.has_permissions(administrator=True)
    async def create_table_scheduled_events(self, ctx: commands.Context) -> None:
        """ Creates the ScheduledEvents table. """

        member = ctx.author
        await ctx.message.delete()

        if await self.check_scheduled_events_exists():
            return await ctx.send(f"**Table `ScheduledEvents` already exists, {member.mention}!**")
        
        mycursor, db = await the_database()
        await mycursor.execute("""
            CREATE TABLE ScheduledEvents (
                event_label VARCHAR(100) NOT NULL,
                event_ts BIGINT NOT NULL,
                PRIMARY KEY (event_label)
            )""")
        await db.commit()
        await mycursor.close()

        await ctx.send(f"**Table `ScheduledEvents` created, {member.mention}!**")

    @commands.command(hidden=True)
    @commands.has_permissions(administrator=True)
    async def drop_table_scheduled_events(self, ctx: commands.Context) -> None:
        """ Creates the ScheduledEvents table. """

        member = ctx.author
        await ctx.message.delete()

        if not await self.check_scheduled_events_exists():
            return await ctx.send(f"**Table `ScheduledEvents` doesn't exist, {member.mention}!**")

        mycursor, db = await the_database()
        await mycursor.execute("DROP TABLE ScheduledEvents")
        await db.commit()
        await mycursor.close()

        await ctx.send(f"**Table `ScheduledEvents` dropped, {member.mention}!**")


    @commands.command(hidden=True)
    @commands.has_permissions(administrator=True)
    async def reset_table_scheduled_events(self, ctx: commands.Context) -> None:
        """ Creates the ScheduledEvents table. """

        member = ctx.author
        await ctx.message.delete()

        if not await self.check_scheduled_events_exists():
            return await ctx.send(f"**Table `ScheduledEvents` doesn't exist yet, {member.mention}!**")

        mycursor, db = await the_database()
        await mycursor.execute("DELETE FROM ScheduledEvents")
        await db.commit()
        await mycursor.close()

        await ctx.send(f"**Table `ScheduledEvents` reset, {member.mention}!**")

    async def check_scheduled_events_exists(self) -> bool:
        """ Checks whether the ScheduledEvents table exists. """

        mycursor, _ = await the_database()
        await mycursor.execute("SHOW TABLE STATUS LIKE 'ScheduledEvents'")
        exists = await mycursor.fetchone()
        await mycursor.close()
        if exists:
            return True
        else:
            return False

    async def check_advertising_time(self, current_ts: int, event_label: str, ad_time: int) -> bool:
        """ Checks whether the advertising time is due.
        :param current_ts: The current timestamp.
        :param event_label: The label of the event
        :param ad_time: Advertising time cooldown. """

        mycursor, _ = await the_database()
        await mycursor.execute("""
            SELECT * from ScheduledEvents
            WHERE event_label = %s AND %s - event_ts >= %s
        """, (event_label, current_ts, ad_time))
        
        due_event = await mycursor.fetchone()
        await mycursor.close()
        if due_event:
            return True
        else:
            return False

    async def get_advertising_event(self, event_label: str) -> List[Union[str, int]]:
        """ Gets an advertising event.
        :param event_label: The label of the advertising event. """

        mycursor, _ = await the_database()
        await mycursor.execute("SELECT * FROM ScheduledEvents WHERE event_label = %s", (event_label,))
        event = await mycursor.fetchone()
        await mycursor.close()
        return event

    async def insert_advertising_event(self, event_label: str, current_ts: int) -> None:
        """ Inserts an advertising event.
        :param event_label: The label of the advertising event.
        :param current_ts: The timestamp in which it was inserted. """

        mycursor, db = await the_database()
        await mycursor.execute("INSERT INTO ScheduledEvents (event_label, event_ts) VALUES (%s, %s)", (event_label, current_ts))
        await db.commit()
        await mycursor.close()

    async def update_advertising_time(self, event_label: str, current_ts: int) -> None:
        """ Updates the timestamp of the advertising event.
        :param event_label: The label of the advertising event.
        :param current_ts: The timestamp to update the event to. """

        mycursor, db = await the_database()
        await mycursor.execute("UPDATE ScheduledEvents SET event_ts = %s WHERE event_label = %s", (current_ts, event_label))
        await db.commit()
        await mycursor.close()