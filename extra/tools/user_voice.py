import discord
from discord.ext import commands
from mysqldb import the_database
from typing import List, Union
from extra import utils
import os

afk_channel_id = int(os.getenv('AFK_CHANNEL_ID'))

class UserVoiceSystem(commands.Cog):
    """ Cog for the inner systems of UserVoice events. """

    def __init__(self, client: commands.Bot) -> None:
        """ Class init method. """

        self.client = client


    @commands.Cog.listener(name="on_voice_state_update")
    async def on_voice_state_update_join_leave(self, member, before, after) -> None:
        """ For when users join or leave the Voice Channel. """

        if member.bot:
            return

        current_ts: int = await utils.get_timestamp()

        # Get before/after channels and their categories
        bc = before.channel
        ac = after.channel

        # # Check voice states
        # if before.mute != after.mute:
        #     return
        # if before.deaf != before.deaf:
        #     return

        if before.self_stream != after.self_stream:
            if not before.self_stream and after.self_stream:
                return
            if bc == ac:
                return

        if before.self_video != after.self_video:
            if not before.self_video and after.self_video:
                return
            if bc == ac:
                return

        # Get before/after channels and their categories
        bc = before.channel
        ac = after.channel

        user_info = await self.get_user_voice(member.id)
        if not user_info and not after.self_mute:
            return await self.insert_user_voice(member.id, current_ts)


        # Join
        if ac and not bc:
            if not after.self_mute and not after.self_deaf and not after.mute and not after.deaf and after.channel.id != afk_channel_id:
                await self.update_user_voice_timestamp(member.id, current_ts)

        # Switch
        elif (ac and bc) and (bc.id != ac.id) and not after.self_mute and not after.mute and not after.deaf:

            people_in_vc: int = len([m for m in bc.members if not m.bot and m.id]) +1

            if people_in_vc < 2 or after.self_mute or after.mute or after.deaf or after.channel.id == afk_channel_id:
                return await self.update_user_voice_time(member.id, 0, current_ts)

            increment: int = current_ts - user_info[3]

            await self.update_user_voice_time(member.id, increment, current_ts)

        # Muted/unmuted
        elif (ac and bc) and (bc.id == ac.id) and before.self_mute != after.self_mute:

            if not after.self_mute and not after.self_deaf and not after.mute and not after.deaf and after.channel.id != afk_channel_id:
                return await self.update_user_voice_timestamp(member.id, current_ts)


            increment: int = current_ts - user_info[3]
            people_in_vc: int = len([m for m in bc.members if not m.bot and m.id])
            if people_in_vc < 2 or after.self_mute or after.self_deaf:
                return await self.update_user_voice_time(member.id, increment, None)


            await self.update_user_voice_time(member.id, increment, current_ts)

        # Deafened/undeafened
        elif (ac and bc) and (bc.id == ac.id) and before.self_deaf != after.self_deaf:

            if not after.self_mute and not after.self_deaf and not after.mute and not after.deaf and after.channel.id != afk_channel_id:
                return await self.update_user_voice_timestamp(member.id, current_ts)

            increment: int = current_ts - user_info[3] # Fix this, index out of range sometimes
            people_in_vc: int = len([m for m in bc.members if not m.bot and m.id])
            if people_in_vc < 2 or after.self_mute or after.self_deaf:
                return await self.update_user_voice_time(member.id, increment, None)

            await self.update_user_voice_time(member.id, increment, current_ts)

        # Server Muted/unmuted
        elif (ac and bc) and (bc.id == ac.id) and before.mute != after.mute:

            if not after.self_mute and not after.self_deaf and not after.mute and not after.deaf and after.channel.id != afk_channel_id:
                return await self.update_user_voice_timestamp(member.id, current_ts)


            increment: int = current_ts - user_info[3]
            people_in_vc: int = len([m for m in bc.members if not m.bot and m.id])
            if people_in_vc < 2 or after.mute or after.deaf:
                return await self.update_user_voice_time(member.id, increment, None)

            await self.update_user_voice_time(member.id, increment, current_ts)

        # Server Deafened/undeafened
        elif (ac and bc) and (bc.id == ac.id) and before.deaf != after.deaf:

            if not after.self_mute and not after.self_deaf and not after.mute and not after.deaf and after.channel.id != afk_channel_id:
                return await self.update_user_voice_timestamp(member.id, current_ts)


            increment: int = current_ts - user_info[3]
            people_in_vc: int = len([m for m in bc.members if not m.bot])
            if people_in_vc < 2 or after.mute or after.deaf:
                return await self.update_user_voice_time(member.id, increment, None)

            await self.update_user_voice_time(member.id, increment, current_ts)
        
        # Leave
        elif bc and not ac:

            people_in_vc: int = len([m for m in bc.members if not m.bot])
            if people_in_vc < 2 or before.self_mute or before.mute or before.deaf or before.channel.id == afk_channel_id:
                return await self.update_user_voice_timestamp(member.id, None)
        

            await self.update_user_voice_time(member.id, increment)


class UserVoiceTable(commands.Cog):
    """ Class for the UserVoice table in the database. """

    def __init__(self, client: commands.Bot) -> None:
        """ Class init method. """

        self.client = client

    # ===== Discord commands =====
    @commands.command(hidden=True)
    @commands.has_permissions(administrator=True)
    async def create_table_server_activity(self, ctx):
        """ (ADM) Creates the UserVoice table. """

        await ctx.message.delete()
        if await self.check_user_server_activity_table_exists():
            return await ctx.send("The `UserVoice` already exists!**")

        mycursor, db = await the_database()
        await mycursor.execute("""
            CREATE TABLE UserVoice (
                user_id BIGINT NOT NULL, 
                user_time BIGINT DEFAULT 0, 
                user_timestamp BIGINT DEFAULT NULL,
                PRIMARY KEY (user_id)
        )""")
        await db.commit()
        await mycursor.close()

        return await ctx.send("**Table `UserVoice` created!**")

    @commands.command(hidden=True)
    @commands.has_permissions(administrator=True)
    async def drop_table_server_activity(self, ctx):
        """ (ADM) Drops the UserVoice table. """

        await ctx.message.delete()

        if not await self.check_user_server_activity_table_exists():
            return await ctx.send("The `UserVoice` doesn't exist!**")

        mycursor, db = await the_database()
        await mycursor.execute("DROP TABLE UserVoice")
        await db.commit()
        await mycursor.close()

        return await ctx.send("**Table `UserVoice` dropped!**")

    @commands.command(hidden=True)
    @commands.has_permissions(administrator=True)
    async def reset_table_server_activity(self, ctx):
        """ (ADM) Resets the UserVoice table. """

        await ctx.message.delete()
        if not await self.check_user_server_activity_table_exists():
            return await ctx.send("The `UserVoice` doesn't exist yet!**")

        mycursor, db = await the_database()
        await mycursor.execute("DELETE FROM UserVoice")
        await db.commit()
        await mycursor.close()
        return await ctx.send("**Table `UserVoice` reset!**")

    # ===== SHOW =====

    async def check_user_server_activity_table_exists(self) -> bool:
        """ Checks whether the UserVoice table exists. """
        
        mycursor, _ = await the_database()
        await mycursor.execute("SHOW TABLE STATUS LIKE 'UserVoice'")
        exists = await mycursor.fetchone()
        await mycursor.close()
        if exists:
            return True
        else:
            return False

    # ===== INSERT =====
    async def insert_user_voice(self, user_id: int, new_ts: int = None) -> None:
        """ Inserts a user into the UserVoice table.
        :param user_id: The ID of the user to insert.
        :param new_ts: The current timestamp. """

        mycursor, db = await the_database()
        await mycursor.execute(
            "INSERT INTO UserVoice (user_id, user_timestamp) VALUES (%s, %s)",
            (user_id, new_ts))
        await db.commit()
        await mycursor.close()

    # ===== SELECT =====

    async def get_user_voice(self, user_id: int) -> List[int]:
        """ Gets a user from the UserVoice table.
        :param user_id: The ID of the user to get. """

        mycursor, _ = await the_database()
        await mycursor.execute("SELECT * FROM UserVoice WHERE user_id = %s", (user_id,))
        user_voice = await mycursor.fetchone()
        await mycursor.close()
        return user_voice

    # ===== UPDATE =====

    async def update_user_voice_time(self, user_id: int, increment: int, current_ts: int = None) -> None:
        """ Updates the user's voice time counter.
        :param user_id: The ID of the user to update.
        :param increment: The increment value in seconds to apply.
        :param current_ts: The current timestamp. [Optional] """

        mycursor, db = await the_database()
        await mycursor.execute("""
            UPDATE UserVoice SET user_time = user_time + %s, user_timestamp = %s WHERE user_id = %s
            """, (increment, current_ts, user_id))
        await db.commit()
        await mycursor.close()

    async def update_user_voice_timestamp(self, user_id: int, new_ts: int) -> None:
        """ Updates the user's voice timestamp.
        :param user_id: The ID of the user to update.
        :param new_ts: The new timestamp to set to. """

        mycursor, db = await the_database()
        await mycursor.execute("UPDATE UserVoice SET user_timestamp = %s WHERE user_id = %s", (new_ts, user_id))
        await db.commit()
        await mycursor.close()

