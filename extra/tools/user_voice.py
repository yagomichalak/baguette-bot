import discord
from discord import slash_command, Option
from discord.ext import commands
from mysqldb import the_database

from typing import List, Union, Optional
from extra import utils
from extra.view import ConvertTimeView
import os
import asyncio

afk_channel_id: int = int(os.getenv('AFK_CHANNEL_ID'))
game_channel_id: int = int(os.getenv('GAME_VOICE_CHANNEL_ID'))
guild_ids: List[int] = [int(os.getenv('SERVER_ID'))]

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
            return

        if before.self_video != after.self_video:
            return

        # Get before/after channels and their categories
        bc = before.channel
        ac = after.channel

        user_info = await self.get_user_voice(member.id)
        if not user_info:
            if ac and not after.self_mute:
                return await self.insert_user_voice(member.id, current_ts)
            else:
                return await self.insert_user_voice(member.id)

        if not user_info:
            return

        # Join
        if ac and not bc:
            if not after.self_mute and not after.self_deaf and not after.mute and not after.deaf and after.channel.id not in (game_channel_id, afk_channel_id):
                await self.update_user_voice_timestamp(member.id, current_ts)

        # Switch
        elif (ac and bc) and (bc.id != ac.id) and not after.self_mute and not after.mute and not after.deaf:

            people_in_vc: int = len([m for m in bc.members if not m.bot and m.id]) +1

            if people_in_vc < 2 or after.self_mute or after.mute or after.deaf or after.channel.id in (game_channel_id, afk_channel_id):
                return await self.update_user_voice_time(member.id, 0, current_ts)

            if user_info[2]:
                increment: int = current_ts - user_info[2]
                await self.update_user_voice_time(member.id, increment, current_ts)

        # Muted/unmuted
        elif (ac and bc) and (bc.id == ac.id) and before.self_mute != after.self_mute:

            if not after.self_mute and not after.self_deaf and not after.mute and not after.deaf and after.channel.id not in (game_channel_id, afk_channel_id):
                return await self.update_user_voice_timestamp(member.id, current_ts)

            people_in_vc: int = len([m for m in bc.members if not m.bot and m.id])
            if people_in_vc < 2 or after.self_mute or after.self_deaf:
                return await self.update_user_voice_time(member.id, 0, None)

            if user_info[2]:
                increment: int = current_ts - user_info[2]
                await self.update_user_voice_time(member.id, increment, current_ts)

        # Deafened/undeafened
        elif (ac and bc) and (bc.id == ac.id) and before.self_deaf != after.self_deaf:

            if not after.self_mute and not after.self_deaf and not after.mute and not after.deaf and after.channel.id not in (game_channel_id, afk_channel_id):
                return await self.update_user_voice_timestamp(member.id, current_ts)

            people_in_vc: int = len([m for m in bc.members if not m.bot and m.id])
            if people_in_vc < 2 or after.self_mute or after.self_deaf:
                return await self.update_user_voice_time(member.id, 0, None)

            if user_info[2]:
                increment: int = current_ts - user_info[2] # Fix this, index out of range sometimes
                await self.update_user_voice_time(member.id, increment, current_ts)

        # Server Muted/unmuted
        elif (ac and bc) and (bc.id == ac.id) and before.mute != after.mute:

            if not after.self_mute and not after.self_deaf and not after.mute and not after.deaf and after.channel.id not in (game_channel_id, afk_channel_id):
                return await self.update_user_voice_timestamp(member.id, current_ts)

            people_in_vc: int = len([m for m in bc.members if not m.bot and m.id])
            if people_in_vc < 2 or after.mute or after.deaf:
                return await self.update_user_voice_time(member.id, 0, None)

            if user_info[2]:
                increment: int = current_ts - user_info[2]
                await self.update_user_voice_time(member.id, increment, current_ts)

        # Server Deafened/undeafened
        elif (ac and bc) and (bc.id == ac.id) and before.deaf != after.deaf:

            if not after.self_mute and not after.self_deaf and not after.mute and not after.deaf and after.channel.id not in (game_channel_id, afk_channel_id):
                return await self.update_user_voice_timestamp(member.id, current_ts)

            people_in_vc: int = len([m for m in bc.members if not m.bot])
            if people_in_vc < 2 or after.mute or after.deaf:
                return await self.update_user_voice_time(member.id, 0, None)

            if user_info[2]:
                increment: int = current_ts - user_info[2]
                await self.update_user_voice_time(member.id, increment, current_ts)
        
        # Leave
        elif bc and not ac:

            people_in_vc: int = len([m for m in bc.members if not m.bot])
            if people_in_vc < 2 or before.self_mute or before.mute or before.deaf or before.channel.id in (game_channel_id, afk_channel_id):
                return await self.update_user_voice_timestamp(member.id, None)
        
            if user_info[2]:
                increment: int = current_ts - user_info[2]
                await self.update_user_voice_time(member.id, increment)

    @slash_command(name="voice_time", guild_ids=guild_ids)
    @commands.cooldown(1, 5, commands.BucketType.user)
    async def _voice_time_slash_command(self, ctx, 
        member: Option(discord.Member, name="member", description="The member from whom to show the voice time.", required=False)
    ) -> None:
        """ Shows someone's voice time. """

        await ctx.defer()

        if not member:
            member = ctx.author

        await self._voice_time_callback(ctx, member)

    @commands.command(name="voice_time")
    @commands.cooldown(1, 5, commands.BucketType.user)
    async def _voice_time_command(self, ctx, member: Optional[Union[discord.Member, discord.User]] = None) -> None:
        """ Shows someone's voice time.
        :param member: The member from whom to show the voice time. [Optional][Default=You] """

        if not member:
            member = ctx.author

        await self._voice_time_callback(ctx, member)


    async def _voice_time_callback(self, ctx: discord.PartialMessageable, member: Union[discord.Member, discord.User]) -> None:
        """ Callback for the voice_time command.
        :param ctx: The context of the command.
        :param member: The member for whom to show the voice time. """

        answer: discord.PartialMessageable = ctx.send if isinstance(ctx, commands.Context) else ctx.respond

        current_time = await utils.get_time()

        if not (user_voice := await self.get_user_voice(member.id)):
            await self.insert_user_voice(member.id)
            await asyncio.sleep(0.3)
            user_voice = await self.get_user_voice(member.id)

        m, s = divmod(user_voice[1], 60)
        h, m = divmod(m, 60)

        embed = discord.Embed(
            description=f"**Voice Time:**\n{h:d} hours, {m:02d} minutes and {s:02d} seconds." \
            f"\n**Timestamp:** {f'<t:{user_voice[2]}:R>' if user_voice[2] else 'None.'}" \
            f"\n**Voice Level:** {user_voice[3]}" \
            f"\n**Voice XP:** {user_voice[4]}"
            ,
            color=member.color,
            timestamp=current_time
        )
        embed.set_author(name=member, icon_url=member.display_avatar)
        if ctx.author.id != member.id:
            embed.set_footer(text=f"Requested by: {ctx.author}", icon_url=ctx.author.display_avatar)

        view = ConvertTimeView(self.client, user_voice)

        await answer(embed=embed, view=view)


class UserVoiceTable(commands.Cog):
    """ Class for the UserVoice table in the database. """

    def __init__(self, client: commands.Bot) -> None:
        """ Class init method. """

        self.client = client

    # ===== Discord commands =====
    @commands.command(hidden=True)
    @commands.has_permissions(administrator=True)
    async def create_table_user_voice(self, ctx):
        """ (ADM) Creates the UserVoice table. """

        await ctx.message.delete()
        if await self.check_user_user_voice_table_exists():
            return await ctx.send("The `UserVoice` already exists!**")

        mycursor, db = await the_database()
        await mycursor.execute("""
            CREATE TABLE UserVoice (
                user_id BIGINT NOT NULL, 
                user_time BIGINT DEFAULT 0, 
                user_timestamp BIGINT DEFAULT NULL,
                user_lvl TINYINT(4) DEFAULT 1,
                user_xp BIGINT DEFAULT 0,
                PRIMARY KEY (user_id)
        )""")
        await db.commit()
        await mycursor.close()

        return await ctx.send("**Table `UserVoice` created!**")

    @commands.command(hidden=True)
    @commands.has_permissions(administrator=True)
    async def drop_table_user_voice(self, ctx):
        """ (ADM) Drops the UserVoice table. """

        await ctx.message.delete()

        if not await self.check_user_user_voice_table_exists():
            return await ctx.send("The `UserVoice` doesn't exist!**")

        mycursor, db = await the_database()
        await mycursor.execute("DROP TABLE UserVoice")
        await db.commit()
        await mycursor.close()

        return await ctx.send("**Table `UserVoice` dropped!**")

    @commands.command(hidden=True)
    @commands.has_permissions(administrator=True)
    async def reset_table_user_voice(self, ctx):
        """ (ADM) Resets the UserVoice table. """

        await ctx.message.delete()
        if not await self.check_user_user_voice_table_exists():
            return await ctx.send("The `UserVoice` doesn't exist yet!**")

        mycursor, db = await the_database()
        await mycursor.execute("DELETE FROM UserVoice")
        await db.commit()
        await mycursor.close()
        return await ctx.send("**Table `UserVoice` reset!**")

    # ===== SHOW =====

    async def check_user_user_voice_table_exists(self) -> bool:
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

    async def get_all_user_voices_by_xp(self) -> List[List[int]]:
        """ Gets all users from the MembersScore table ordered by XP. """

        mycursor, _ = await the_database()
        await mycursor.execute("SELECT * FROM UserVoice ORDER BY user_xp DESC")
        user_voices = await mycursor.fetchall()
        await mycursor.close()
        return user_voices

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

    async def update_user_voice_lvl(self, user_id: int, new_lvl: int) -> None:
        """ Updates the user's voice level.
        :param user_id: The ID of the user to update.
        :param new_lvl: The new level to set to. """

        mycursor, db = await the_database()
        await mycursor.execute("UPDATE UserVoice SET user_lvl = %s WHERE user_id = %s", (new_lvl, user_id))
        await db.commit()
        await mycursor.close()

    async def update_user_voice_xp(self, user_id: int, increment: int) -> None:
        """ Updates the user's voice XP.
        :param user_id: The ID of the user to update.
        :param increment: The increment value to apply to the XP counter. """

        mycursor, db = await the_database()
        await mycursor.execute("UPDATE UserVoice SET user_xp = user_xp + %s WHERE user_id = %s", (increment, user_id))
        await db.commit()
        await mycursor.close()

