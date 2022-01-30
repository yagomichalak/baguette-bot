import discord
from discord.ext import commands, tasks
import os
from mysqldb import the_database
from typing import List, Union
from extra import utils
import pytz

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
            birthday VARCHAR(5),
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
        """ (ADM) Drops the UserBirthday table """

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
        """ (ADM) Resets the UserBirthday table """

        if not await self.check_table_user_birthday():
            return await ctx.send("**Table __UserBirthday__ doesn't exist yet!**")

        await ctx.message.delete()
        mycursor, db = await the_database()
        await mycursor.execute("DELETE FROM UserBirthday")
        await db.commit()
        await mycursor.close()

        return await ctx.send("**Table __UserBirthday__ reset!**", delete_after=3)

    async def check_table_user_birthday(self) -> bool:
        """ Checks whether the UserBirthday table exists """

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
            ) VALUES (%s, '%s-%s', %s)
        """, (user_id, day, month, timezone))
        await db.commit()
        await mycursor.close()

    async def get_user_birthdays(self) -> List[List[Union[int, str]]]:
        """ Gets all user birthdays. """

        mycursor, _ = await the_database()
        await mycursor.execute("SELECT * FROM UserBirthday")
        user_birthdays = await mycursor.fetchall()
        await mycursor.close()
        return user_birthdays

    async def get_user_birthdays_by_date(self, the_date: str) -> List[List[Union[int, str]]]:
        """ Gets all user birthdays by a specific date. """

        mycursor, _ = await the_database()
        await mycursor.execute("SELECT * FROM UserBirthday WHERE birthday = %s", (the_date,))
        user_birthdays = await mycursor.fetchall()
        await mycursor.close()
        return user_birthdays

    async def get_user_no_longer_birthdays(self) -> List[List[Union[int, str]]]:
        """ Gets all user birthdays by a specific date. """

        mycursor, _ = await the_database()
        await mycursor.execute("SELECT * FROM UserBirthday WHERE is_birthday = 1")
        user_birthdays = await mycursor.fetchall()
        await mycursor.close()
        return user_birthdays

    async def get_user_birthdays_by_date(self, the_date: str) -> List[List[Union[int, str]]]:
        """ Gets all user birthdays by a specific date. """

        mycursor, _ = await the_database()
        await mycursor.execute("SELECT * FROM UserBirthday WHERE birthday = %s", (the_date,))
        user_birthdays = await mycursor.fetchall()
        await mycursor.close()
        return user_birthdays

    async def get_user_birthday(self, user_id: int) -> List[Union[int, str]]:
        """ Gets a user's birthday.
        :param user_id: The ID of the user to get. """

        mycursor, _ = await the_database()
        await mycursor.execute("SELECT * FROM UserBirthday WHERE user_id = %s", (user_id,))
        user_birthday = await mycursor.fetchone()
        await mycursor.close()
        return user_birthday

    async def update_user_birthday(self, user_id: int, the_date: str) -> None:
        """ Updates a user's birthday date.
        :param user_id: The ID of the user to update.
        :param the_date: The new updated date. """

        mycursor, db = await the_database()
        await mycursor.execute("UPDATE UserBirthday SET birthday = %s WHERE user_id = %s", (the_date, user_id))
        await db.commit()
        await mycursor.close()

    async def update_user_birthday_state(self, user_id: int, state: int = 0) -> None:
        """ Updates the user's birthday state.
        :param user_id: The ID of the user to update.
        :param state: Whether to set the state to true or false. (0-1) [DEFAULT=0] """

        mycursor, db = await the_database()
        await mycursor.execute("UPDATE UserBirthday SET is_birthday = %s WHERE user_id = %s", (state, user_id))
        await db.commit()
        await mycursor.close()

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

        current_date = await utils.get_time()
        the_date = current_date.strftime("%e-%#m")

        # Gets all people with today's date as birthday (DD-MM)
        user_birthdays = await self.get_user_birthdays_by_date(the_date)
        birthday_people: List[int] = []
        guild = self.client.get_guild(int(os.getenv('SERVER_ID')))
        birthday_role: discord.Role = discord.utils.get(guild.roles, id=int(os.getenv('BIRTHDAY_ROLE_ID')))

        # Checks whether it's really their birthday after converting the date to their timezone
        for ubd in user_birthdays:
            if ubd[3] == 1:
                continue

            # the_timezone = pytz.timezone(ubd[2])
            # converted_date = current_date.astimezone(the_timezone)
            # print(converted_date.strftime("%e-%#m %H:%M:%S"))
            birthday_people.append(ubd[0])

        # Gives the birthday role to the user
        for birthday_person in birthday_people:
            await self.update_user_birthday_state(birthday_people, 1)
            try:
                user = guild.get_member(birthday_person)
                await user.add_roles(birthday_role)
            except:
                pass

    @tasks.loop(minutes=1)
    async def check_user_no_longer_birthday(self) -> None:
        """ Checks whether today is no longer someone's birthday. """

        current_date = await utils.get_time()
        the_date = current_date.strftime("%e-%#m")
        guild = self.client.get_guild(int(os.getenv('SERVER_ID')))
        birthday_role: discord.Role = discord.utils.get(guild.roles, id=int(os.getenv('BIRTHDAY_ROLE_ID')))
        
        # Gets all people with the birthday mark
        nl_bd_people = await self.get_user_no_longer_birthdays()

        for person in nl_bd_people:

            # Converts the date to the person's timezone, to double check it
            # the_timezone = pytz.timezone(person[2])
            # converted_date = current_date.astimezone(the_timezone)

            # Checks whether it's really no longer their birthday after converting the date to their timezone
            if person[1] == the_date:
                continue

            try:
                await self.update_user_birthday_state(person[0])
                member = guild.get_member(person[0])
                # Removes the birthday role from the user
                await member.remove_roles(birthday_role)
            except:
                pass

    @commands.command(aliases=["add_birthday", "abd", "update_birthday", "ubd"])
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

        month = months[month.lower()]

        registered_timezone_roles = await self.get_timezone_roles()
        user_timezone_roles: List[List[Union[int, str]]] = [
            r_trole for r_trole in registered_timezone_roles
            if member.get_role(r_trole[0])
		]

        the_timezone = 'Etc/GMT+0' if not user_timezone_roles else user_timezone_roles[0][1]
        formatted_birthday = f"{day}-{month} {the_timezone}"

        if await self.get_user_birthday(member.id):
            await self.update_user_birthday(member.id, f"{day}-{month}")
            return await ctx.send(f"**Successfully updated your birthday, {member.mention}! (`{formatted_birthday}`)**")

        await self.insert_user_birthday(member.id, day, month, the_timezone)
        await ctx.send(f"**Successfully added your birthday, {member.mention}! (`{formatted_birthday}`)**")

    @commands.command(aliases=["delete_birthday", "rbd", "dbd"])
    @commands.cooldown(1, 5, commands.BucketType.user)
    async def remove_birthday(self, ctx) -> None:
        """ Removes your birthday from the system. """

        member: discord.Member = ctx.author
        if not await self.get_user_birthday(member.id):
            return await ctx.send(f"**You don't have a birthday saved, {member.mention}!**")

        await self.delete_user_birthday(member.id)
        await ctx.send(f"**Successfully deleted your birthday from the system, {member.mention}!**")