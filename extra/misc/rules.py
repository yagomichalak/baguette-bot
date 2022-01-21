import discord
from discord.ext import commands
from mysqldb import the_database
from typing import List, Union

class RulesTable(commands.Cog):
    """ Category for managing the Rules table in the database. """

    def __init__(self, client: commands.Cog) -> None:
        """ Class init method. """

        self.client = client


    @commands.command(hidden=True)
    @commands.has_permissions(administrator=True)
    async def create_table_rules(self, ctx) -> None:
        """ (ADM) Creates the Rules table. """

        if await self.check_table_rules():
            return await ctx.send("**Table __Rules__ already exists!**")

        await ctx.message.delete()
        mycursor, db = await the_database()
        await mycursor.execute("""CREATE TABLE Rules (
            rule_number TINYINT(2) NOT NULL, 
            english_text VARCHAR(500) DEFAULT NULL, french_text VARCHAR(500) DEFAULT NULL)""")

        for i in range(15):
            await mycursor.execute("INSERT INTO Rules (rule_number) VALUES (%s)", (i+1,))

        await db.commit()
        await mycursor.close()

        return await ctx.send("**Table __Rules__ created!**", delete_after=3)

    @commands.command(hidden=True)
    @commands.has_permissions(administrator=True)
    async def drop_table_rules(self, ctx) -> None:
        """ (ADM) Creates the Rules table """

        if not await self.check_table_rules():
            return await ctx.send("**Table __Rules__ doesn't exist!**")

        await ctx.message.delete()
        mycursor, db = await the_database()
        await mycursor.execute("DROP TABLE Rules")
        await db.commit()
        await mycursor.close()

        return await ctx.send("**Table __Rules__ dropped!**", delete_after=3)

    @commands.command(hidden=True)
    @commands.has_permissions(administrator=True)
    async def reset_table_rules(self, ctx) -> None:
        """ (ADM) Creates the Rules table """

        if not await self.check_table_rules():
            return await ctx.send("**Table __Rules__ doesn't exist yet!**")

        await ctx.message.delete()
        mycursor, db = await the_database()
        await mycursor.execute("DELETE FROM Rules")
        await db.commit()
        await mycursor.close()

        return await ctx.send("**Table __Rules__ reset!**", delete_after=3)

    async def check_table_rules(self) -> bool:
        """ Checks if the Rules table exists """

        mycursor, _ = await the_database()
        await mycursor.execute("SHOW TABLE STATUS LIKE 'Rules'")
        table_info = await mycursor.fetchall()
        await mycursor.close()

        if len(table_info) == 0:
            return False

        else:
            return True

    async def update_rule(self, rule_number: int, english_text: str = None, french_text: str = None) -> None:
        """ Updates a rule in the database.
        :param rule_number: The number of the rule (1-15).
        :param english_text: The rule text in English.
        :param french_text: The rule text in French. """

        mycursor, db = await the_database()
        if english_text and french_text:
            await mycursor.execute(
                "UPDATE Rules SET english_text = %s, french_text = %s WHERE rule_number = %s", (
                    english_text, french_text, rule_number))

        elif english_text:
            await mycursor.execute("UPDATE Rules SET english_text = %s WHERE rule_number = %s", (english_text, rule_number))

        elif french_text:
            await mycursor.execute("UPDATE Rules SET french_text = %s WHERE rule_number = %s", (french_text, rule_number))
        await db.commit()
        await mycursor.close()

    async def get_rules(self) -> List[List[Union[int, str]]]:
        """ Get all rules from the database. """

        mycursor, _ = await the_database()
        await mycursor.execute("SELECT * FROM Rules")
        rules = await mycursor.fetchall()
        await mycursor.close()
        return rules

    async def get_rule(self, rule_number: int) -> List[Union[int, str]]:
        """ Get a specific rule from the database.
        :param rule_number: The number of the rule. """

        mycursor, _ = await the_database()
        await mycursor.execute("SELECT * FROM Rules WHERE rule_number = %s", (rule_number,))
        the_rule = await mycursor.fetchone()
        await mycursor.close()
        return the_rule