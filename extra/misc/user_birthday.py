import discord
from discord.ext import commands, tasks
import os
from mysqldb import the_database
from typing import List, Union


class UserBirthdayTable(commands.Cog):
    """ Class for managing the Birthday """

    def __init__(self, client: commands.Bot) -> None:
        """ Class init method. """

        self.client = client

    @commands.command(hidden=True)
    @commands.has_permissions(administrator=True)
    async def create_table_user_birthday(self, ctx) -> None:
        """ (ADM) Creates the UserBirthday table. """

        if await self.check_table_user_birthday():
            return await ctx.send("**Table __UserBirthday__ already exists!**")

        await ctx.message.delete()
        mycursor, db = await the_database()
        await mycursor.execute("""CREATE TABLE UserBirthday (
            user_id BIGINT NOT NULL,
            birthday DATE,
            timezone VARCHAR(10),
            is_birthday TINYINT(1) DEFAULT 0,
            PRIMARY KEY (user_id)
            ) """)
        await db.commit()
        await mycursor.close()

        return await ctx.send("**Table __UserBirthday__ created!**", delete_after=3)

    @commands.command(hidden=True)
    @commands.has_permissions(administrator=True)
    async def drop_table_user_birthday(self, ctx) -> None:
        """ (ADM) Creates the UserBirthday table """

        if not await self.check_table_user_birthday():
            return await ctx.send("**Table __UserBirthday__ doesn't exist!**")

        await ctx.message.delete()
        mycursor, db = await the_database()
        await mycursor.execute("DROP TABLE UserBirthday")
        await db.commit()
        await mycursor.close()

        return await ctx.send("**Table __UserBirthday__ dropped!**", delete_after=3)

    @commands.command(hidden=True)
    @commands.has_permissions(administrator=True)
    async def reset_table_user_birthday(self, ctx) -> None:
        """ (ADM) Creates the UserBirthday table """

        if not await self.check_table_user_birthday():
            return await ctx.send("**Table __UserBirthday__ doesn't exist yet!**")

        await ctx.message.delete()
        mycursor, db = await the_database()
        await mycursor.execute("DELETE FROM UserBirthday")
        await db.commit()
        await mycursor.close()

        return await ctx.send("**Table __UserBirthday__ reset!**", delete_after=3)

    async def check_table_user_birthday(self) -> bool:
        """ Checks if the UserBirthday table exists """

        mycursor, _ = await the_database()
        await mycursor.execute("SHOW TABLE STATUS LIKE 'UserBirthday'")
        table_info = await mycursor.fetchall()
        await mycursor.close()

        if len(table_info) == 0:
            return False

        else:
            return True

    async def insert_user_birthday(self, user_id: int, day: int, month: int, timezone: str) -> None:
        """ Inserts a UserBirthday.
        :param user_id: The ID of the user to insert.
        :param day: The day of the user's birthday.
        :param day: The month of the user's birthday.
        :param timezone: The timezone to check. """

        mycursor, db = await the_database()
        await mycursor.execute("""
            INSERT INTO UserBirthday (
                user_id, birthday, timezone
            ) VALUES (%s, %s-%s, %s)
        """, (user_id, day, month, timezone))
        await db.commit()
        await mycursor.close()

    async def get_user_birthdays(self) -> List[List[Union[int, str]]]: pass

    async def get_user_birthday(self, user_id: int) -> List[Union[int, str]]: pass

    async def delete_user_birthday(self, user_id: int) -> None:
        """ Deletes the user's birthday.
        :param user_id: The ID of the user to delete. """

        mycursor, db = await the_database()
        await mycursor.execute("DELETE FROM UserBirthday WHERE user_id = %s", (user_id,))
        await db.commit()
        await mycursor.close()

class UserBirthdaySystem(commands.Cog):
    """ Class for the UserBirthday system. """

    def __init__(self, client: commands.Bot) -> None:
        self.client = client


    @tasks.loop(minutes=1)
    async def check_user_birthday(self) -> None:
        """ Checks whether today is someone's birthday. """
        print('Checking birthdays...')
        # Gets all people with today's date as birthday (DD-MM)

        # Checks whether it's really their birthday after converting the date to their timezone

        # Gives the birthday role to the user
        pass

    @tasks.loop(minutes=1)
    async def check_user_no_longer_birthday(self) -> None:
        """ Checks whether today is no longer someone's birthday. """
        print('Checking no-longer birthdays...')
        # Gets all people with the birthday mark

        # Checks whether it's really no longer their birthday after converting the date to their timezone

        # Removes the birthday role from the user
        pass


    @commands.command()
    @commands.cooldown(1, 5, commands.BucketType.user)
    async def set_birthday(self, ctx, day: str = None, month: str = None) -> None:
        """ Sets your birthday.
        :param day: The day of your birthday.
        :param month: The month of your birthday.
        
        Usage example:
        b!set_birthday 15 August """

        member: discord.Member = ctx.author

        if not day:
            ctx.command.reset_cooldown(ctx)
            return await ctx.send(f"**Please, inform a day, {member.mention}!**")
        
        try:
            day = int(day)
        except ValueError:
            ctx.command.reset_cooldown(ctx)
            return await ctx.send(f"**Please, inform an integer value, {member.mention}!**")

        if day <= 0 or day > 31:
            ctx.command.reset_cooldown(ctx)
            return await ctx.send(f"**Inform a day number between 1-31, {member.mention}!**")

        if not month:
            ctx.command.reset_cooldown(ctx)
            return await ctx.send(f"**Please, inform a month, {member.mention}!**")

        months = {
            "january": 1, "february": 2, "march": 3, 
            "april": 4, "may": 5, "june": 6,
            "july": 7, "august": 8, "september": 9, 
            "october": 10, "november": 11, "december": 12,
        }

        if month.lower() not in months:
            ctx.command.reset_cooldown(ctx)
            return await ctx.send(f"**Please, inform a valid month name, {member.mention}!**")

        print(day)
        print(month)
        month = months[month.lower()]



        registered_timezone_roles = await self.get_timezone_roles()
        user_timezone_roles: List[List[Union[int, str]]] = [
            r_trole for r_trole in registered_timezone_roles
            if member.get_role(r_trole[0])
		]

        the_timezone = 'Etc/GMT+0' if not user_timezone_roles else user_timezone_roles[0][1]



        print('INSERT', f"{day}-{month} tzinfo={the_timezone}")
        await self.insert_user_birthday(member.id, day, month, the_timezone)
        await ctx.send(f"**Successfully added your birthday, {member.mention}!**")
