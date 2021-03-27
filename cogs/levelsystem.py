import discord
from discord.ext import commands, tasks, menus
from mysqldb import the_database
from extra.menu import Confirm, SwitchPages
from typing import List, Dict, Union, Any
import time
from datetime import datetime
import asyncio
import os
from extra.useful_variables import xp_levels

owner_role_id = int(os.getenv('OWNER_ROLE_ID'))
admin_role_id = int(os.getenv('ADMIN_ROLE_ID'))
mod_role_id = int(os.getenv('MOD_ROLE_ID'))
jr_mod_role_id = int(os.getenv('JR_MOD_ROLE_ID'))
trial_mod_role_id = int(os.getenv('TRIAL_MOD_ROLE_ID'))

allowed_roles = [owner_role_id, admin_role_id, mod_role_id, jr_mod_role_id, trial_mod_role_id]


class LevelSystem(commands.Cog):
    """ A category for the Level System. """

    def __init__(self, client) -> None:
        self.client = client
        self.xp_rate = 20
        self.xp_multiplier = 1
        self.allowed_channel_ids: List[int] = []


    @commands.Cog.listener()
    async def on_ready(self) -> None:

        if await self.table_important_vars_exists():
            if multiplier := await self.get_important_var(label="xp_multiplier"):
                self.xp_multiplier = multiplier[2]


        if channel_ids := await self.get_important_var(label="xp_channel", multiple=True):
            self.allowed_channel_ids.extend([c[2] for c in channel_ids])




        print('LevelSystem cog is online')


    # In-game commands
    @commands.Cog.listener()
    async def on_message(self, message):

        # return

        if not message.guild:
            return
            
        if message.author.bot:
            return
        elif not await self.table_member_status_exists():
            return


        epoch = datetime.utcfromtimestamp(0)
        time_xp = (datetime.utcnow() - epoch).total_seconds()
        if message.channel.id in self.allowed_channel_ids:
            await self.update_data(message.author, time_xp, message.channel)
            
        await self.update_user_server_messages(message.author.id, 1)

    ###
    @commands.Cog.listener()
    async def on_voice_state_update(self, member, before, after):

        if member.bot:
            return

        if not await self.table_member_status_exists():
            return


        # After voice state
        # bm = before.mute
        # bsm = before.self_mute
        # if before.mute != after.mute: return
        # if before.deaf != before.deaf: return
        # if before.self_mute != after.self_mute: return
        # if before.self_deaf != after.self_deaf: return
        if before.self_stream != after.self_stream: return
        if before.self_video != after.self_video: return

        epoch = datetime.utcfromtimestamp(0)
        current_ts = (datetime.utcnow() - epoch).total_seconds()

        bc = before.channel
        ac = after.channel

        user_info = await self.get_specific_user(member.id)
        if not user_info:
            #user_id: int, xp_time: int, xp: int = 0, lvl: int = 1, messages: int = 0, vc_time: int = 0, vc_ts: int = None
            if ac:
                await self.insert_user(user_id=member.id, xp_time=current_ts, vc_ts=current_ts)
                user_info = await self.get_specific_user(member.id)
            else:
                return await self.insert_user(user_id=member.id, xp_time=current_ts)


        if not bc:
            if not after.mute and not after.self_mute:
                await self.update_user_server_timestamp(user_id=member.id, new_ts=current_ts)

            return

        addition = None
        old_time = user_info[0][6]

        if old_time is not None:
            addition = current_ts - old_time

        Misc = self.client.get_cog('Misc')

        if not ac: # and bc.id != afk_channel_id:
            if addition is not None:
                await self.update_user_server_time(user_id=member.id, add_time=addition, reset_ts=True)
                await Misc.update_user_server_status_vc_time(status_ts=current_ts, addition=addition, label="daily-time", past_days=1, channel_id=bc.id)
                await Misc.update_user_server_status_vc_time(status_ts=current_ts, addition=addition, label="weekly-time", past_days=7, channel_id=bc.id)
        else:
            # print('opa')
            if not before.mute and after.mute: # User muted
                if addition is not None:
                    await self.update_user_server_time(user_id=member.id, add_time=addition, reset_ts=True)
                    await Misc.update_user_server_status_vc_time(status_ts=current_ts, addition=addition, label="daily-time", past_days=1, channel_id=ac.id)
                    await Misc.update_user_server_status_vc_time(status_ts=current_ts, addition=addition, label="weekly-time", past_days=7, channel_id=ac.id)

            elif before.mute and not after.mute: # User unmuted
                await self.update_user_server_timestamp(user_id=member.id, new_ts=current_ts)

            elif not before.self_mute and after.self_mute: # User was muted
                if addition is not None:
                    await self.update_user_server_time(user_id=member.id, add_time=addition, reset_ts=True)
                    await Misc.update_user_server_status_vc_time(status_ts=current_ts, addition=addition, label="daily-time", past_days=1, channel_id=ac.id)
                    await Misc.update_user_server_status_vc_time(status_ts=current_ts, addition=addition, label="weekly-time", past_days=7, channel_id=ac.id)

            elif before.self_mute and not after.self_mute: # User was unmuted
                await self.update_user_server_timestamp(user_id=member.id, new_ts=current_ts)


    async def update_data(self, user, time_xp: int, channel: discord.TextChannel):
        the_member = await self.get_specific_user(user.id)

        if the_member:
            if time_xp - the_member[0][3] >= 3 or the_member[0][1] == 0:
                await self.update_user_xp_time(user.id, time_xp)
                new_xp = int(self.xp_rate + (self.xp_rate * self.xp_multiplier)/ 100)
                await self.update_user_xp(user.id, new_xp)
                return await self.level_up(user, channel)
        else:
            return await self.insert_user(user_id=user.id, xp=5, xp_time=time_xp)

    # async def level_up(self, user: discord.Member, channel: discord.TextChannel) -> None:
    #     epoch = datetime.utcfromtimestamp(0)
    #     the_user = await self.get_specific_user(user.id)
    #     lvl_end = int(the_user[0][1] ** (1 / 5))

    #     if the_user[0][2] < lvl_end:
    #         await self.update_user_lvl(user.id, the_user[0][2]+1)
    #         # await self.check_level_role(user, the_user[0][2]+1)
    #         await self.check_level_roles_deeply(user, the_user[0][2]+1)
    #         return await channel.send(
    #             f"""🇬🇧 {user.mention} has reached level **{the_user[0][2] + 1}!**\n🇫🇷 {user.mention} a atteint niveau **{the_user[0][2] + 1} !**""")

    async def level_up(self, user: discord.Member, channel: discord.TextChannel) -> None:
        epoch = datetime.utcfromtimestamp(0)
        the_user = await self.get_specific_user(user.id)
        # lvl_end = int(the_user[0][1] ** (1 / 5))

        user_level = the_user[0][2]
        user_xp = the_user[0][1]

        if user_xp >= await LevelSystem.get_xp(user_level):
            await self.update_user_lvl(user.id, user_level+1)
            # await self.check_level_role(user, the_user[0][2]+1)
            await self.check_level_roles_deeply(user, user_level+1)
            return await channel.send(
                f"""🇬🇧 {user.mention} has reached level **{user_level + 1}!**\n🇫🇷 {user.mention} a atteint niveau **{user_level + 1} !**""")


    @staticmethod
    async def get_xp(level: int) -> int:
        """ Gets the amount of XP to get to a level. """

        if xp := xp_levels.get(str(level)):
            return xp

        return level * 6000



    async def check_level_role(self, member: discord.Member, level: int) -> Union[None, int]:
        """ Checks if the member level has a role attached to it
        and gives the role to the member if so.
        :param member: The member to check.
        :param level: The current level of the member. """


        role_id = None
        list_index = 0


        level_roles = await self.select_level_role()
        for i, level_r in enumerate(level_roles):
            if level >= level_r[0]:
                role_id = level_r[1]
                list_index = i


        if not role_id or not (current_role := discord.utils.get(member.guild.roles, id=role_id)):
            return

        if current_role in member.roles:
            return

        try:
            await member.add_roles(current_role)
        except Exception as e:
            print(e)
        else:
            if list_index and (previous_role_id := level_roles[list_index-1][1]):
                if previous_role := discord.utils.get(member.guild.roles, id=previous_role_id):
                    if previous_role in member.roles:
                        try:
                            await member.remove_roles(previous_role)
                        except Exception as ee:
                            print(ee)

            return role_id


    @commands.command(aliases=['stats', 'statuses'])
    async def status(self, ctx) -> None:
        """ Shows server status related to time spent in VCs and messages sent. """

        
        member = ctx.author

        embed = discord.Embed(
            title="🌟 __Server Status__ 🌟",
            description="Server status related to overall time in Voice Channels and messages sent.",
            color=member.color,
            timestamp=ctx.message.created_at
        )


        Misc = self.client.get_cog('Misc')
        msgs_past_1 = await Misc.select_user_server_status_messages(label='daily-messages')
        msgs_past_7 = await Misc.select_user_server_status_messages(label='weekly-messages')

        total_messages = await self.get_total_messages()

        # total_messages = await self.get_total_messages_past_24_7()
        embed.add_field(
            name="⌨️ __Messages__",
            value=f"**Total:** {total_messages}\n**Past 7 days:** {msgs_past_7[1]}\n**Past 24 hours:** {msgs_past_1[1]}\n",
            inline=True)

        total_time = await self.get_total_time()
        time_past_1 = await Misc.select_user_server_status_time(label='daily-time')
        time_past_7 = await Misc.select_user_server_status_time(label='weekly-time')
        # print('time1', time_past_1)
        # print('time7', time_past_7)

        # All
        mall, sall = divmod(total_time, 60)
        hall, mall = divmod(mall, 60)
        dall, hall = divmod(hall, 24)
        text_all = ''
        if dall: text_all = f"{dall}d, {hall}h, {mall}m & {sall}s"
        elif hall: text_all = f"{hall}h, {mall}m & {sall}s"
        elif mall: text_all = f"{mall}m & {sall}s"
        elif sall: text_all = f"{sall}s"
        else: text_all = 0

        # Daily
        m1, s1 = divmod(time_past_1[1], 60)
        h1, m1 = divmod(m1, 60)
        text_1 = ''
        d1, h1 = divmod(h1, 24)
        if d1: text_1 = f"{d1}d, {h1}h, {m1}m & {s1}s"
        elif h1: text_1 = f"{h1}h, {m1}m & {s1}s"
        elif m1: text_1 = f"{m1}m & {s1}s"
        elif s1: text_1 = f"{s1}s"
        else: text_1 = 0

        # Weekly
        m7, s7 = divmod(time_past_7[1], 60)
        h7, m7 = divmod(m7, 60)
        d7, h7 = divmod(h7, 24)
        text_7 = ''
        if d7: text_7 = f"{d7}d, {h7}h, {m7}m & {s7}s"
        elif h7: text_7 = f"{h7}h, {m7}m & {s7}s"
        elif m7: text_7 = f"{m7}m & {s7}s"
        elif s7: text_7 = f"{s7}s"
        else: text_7 = 0


        embed.add_field(
            name="🗣️ __Overall Time in VCs__",
            value=f"**Total:** {text_all}\n**Past 7 days:** {text_7}\n**Past 24 hours:** {text_1}\n",
            inline=True)

        guild = ctx.guild

        # print(c_msg_1, await Misc.select_most_active_user_server_status(label='daily-messages', sublabel='messages'))
        # Weekly msg
        c_msg_7 = (guild.get_channel(c_msg_7[5]), c_msg_7[3]) if (
            c_msg_7 := await Misc.select_most_active_user_server_status(label='weekly-messages', sublabel='messages')) else (None, None)
        # Daily msg
        c_msg_1 = (guild.get_channel(c_msg_1[5]), c_msg_1[3]) if (
            c_msg_1 := await Misc.select_most_active_user_server_status(label='daily-messages', sublabel='messages')) else (None, None)
        # Weekly time
        c_time_7 = (guild.get_channel(c_time_7[5]), c_time_7[4]) if (
            c_time_7 := await Misc.select_most_active_user_server_status(label='weekly-time', sublabel='time')
            ) else (None, None)
        # Daily time
        c_time_1 = (guild.get_channel(c_time_1[5]), c_time_1[4]) if (
            c_time_1 := await Misc.select_most_active_user_server_status(label='daily-time', sublabel='time')
            ) else (None, None)

        embed.add_field(
            name="__Most Active Message Channels__", 
            value=f"**🕖 Last 7 days:** {c_msg_7[0].mention if c_msg_7[0] else None}\n**🕛 Last 24 hours:** {c_msg_1[0].mention if c_msg_1[0] else None}", 
            inline=False)

        embed.add_field(
            name="__Most Active Voice Channels__", 
            value=f"**🕖 Last 7 days:** {c_time_7[0].mention if c_time_7[0] else None}\n**🕛 Last 24 hours:** {c_time_1[0].mention if c_time_1[0] else None}",
            inline=True)

        embed.set_thumbnail(url=ctx.guild.icon_url)
        embed.set_footer(text=member, icon_url=member.avatar_url)



        await ctx.send(embed=embed)


    @commands.command(aliases=['profile'])
    async def level(self, ctx, member: discord.Member = None) -> None:
        """ Shows a user profile. 
        :param member: The member to show the profile. [Optional]
        PS: if a member is not passed as an argument, it will show the profile of the command's executor. """

        # Checks if the Ranking table exists.
        if not await self.table_member_status_exists():
            return await ctx.send("**This command may be on maintenance!**", delete_after=3)

        # If not specified a member - then it's you!
        if not member:
            member = ctx.author

        # Waits half of a second to avoid bugs
        await asyncio.sleep(0.5)
        
        # Tries to get the user's data from the database.
        if not (user := await self.get_specific_user(member.id)):
            return await ctx.send(f"**{member} is not in the system, maybe they have to use the command by themselves!**")


        # Arranges the user's information into a well-formed embed
        all_users = await self.get_all_users_by_xp()
        position = [[i+1, u[1]] for i, u in enumerate(all_users) if u[0] == ctx.author.id]
        position = [it for subpos in position for it in subpos] if position else ['??', 0]

        embed = discord.Embed(title="__Profile__", colour=member.color, timestamp=ctx.message.created_at)
        embed.add_field(name="__**Level**__", value=f"{user[0][2]}.", inline=True)
        embed.add_field(name="__**Rank**__", value=f"# {position[0]}.", inline=True)
        # embed.add_field(name="__**EXP**__", value=f"{user[0][1]} / {((user[0][2]+1)**5)}.", inline=False)
        embed.add_field(name="__**EXP**__", value=f"{user[0][1]} / {await LevelSystem.get_xp(user[0][2])}.", inline=False)
        embed.add_field(name="__**Messages**__", value=f"{user[0][4]}.", inline=True)



        mall, sall = divmod(user[0][5], 60)
        hall, mall = divmod(mall, 60)
        dall, hall = divmod(hall, 24)
        text_all = ''
        if dall: text_all = f"{dall}d, {hall}h, {mall}m & {sall}s"
        elif hall: text_all = f"{hall}h, {mall}m & {sall}s"
        elif mall: text_all = f"{mall}m & {sall}s"
        elif sall: text_all = f"{sall}s"
        else: text_all = '0'

        embed.add_field(name="__**Overall Time**__", value=text_all, inline=True)
        embed.set_thumbnail(url=member.avatar_url)
        embed.set_footer(text=f"{member}", icon_url=member.avatar_url)
        return await ctx.send(embed=embed)

    @commands.command(aliases=['score', 'level_board', 'levelboard', 'levels', 'level_score'])
    async def leaderboard(self, ctx):
        """ Shows the top ten members in the level leaderboard. """

        # users = await self.get_users()

        all_users = await self.get_all_users_by_xp()
        position = [[i+1, u[1]] for i, u in enumerate(all_users) if u[0] == ctx.author.id]
        print('p1', position)
        position = [it for subpos in position for it in subpos] if position else ['??', 0]
        print('p2', position)

        # Additional data:
        additional = {
            'change_embed': self._make_level_score_embed,
            'position': position
        }

        pages = menus.MenuPages(source=SwitchPages(all_users, **additional), clear_reactions_after=True)
        await pages.start(ctx)


    @commands.command()
    @commands.has_permissions(administrator=True)
    async def setlevel(self, ctx, member: discord.Member = None, level: int = None) -> None:
        """ Sets a level to a user.
        :param member: The member to whom the level is gonna be set.
        :param level: The new level to which the user's level is gonna be set.
        """

        if not member:
            return await ctx.send(f"**Please, inform a member to set a new level value, {ctx.author.mention}!**")

        if not level:
            return await ctx.send(f"**Please, inform the level that you want the user to have, {ctx.author.mention}!**")

        if level <= 0:
            return await ctx.send(f"**Please, inform a positive number greater than 0, {ctx.author.mention}!**")


        if not (the_user := await self.get_specific_user(member.id)):
            return await ctx.send(f"**Member is not in the system yet, {ctx.author.mention}!**")

        if level >= the_user[0][2]:
            await self.update_user_lvl(member.id, level)
            await asyncio.sleep(0.1)
            # await self.set_user_xp(member.id, ((level-1)** 5))
            await self.set_user_xp(member.id, await LevelSystem.get_xp(level-1))

        else:
            # await self.set_user_xp(member.id, ((level-1)** 5))
            await self.set_user_xp(member.id, await LevelSystem.get_xp(level-1))
            await asyncio.sleep(0.1)
            await self.update_user_lvl(member.id, level)

        # print((level-1)** 5)
        # print((level)** 5)
        await asyncio.sleep(0.1)
        await self.check_level_roles_deeply(member, level)
        await ctx.send(f"**The member {member.mention} is now level {level}!**")

    async def check_level_roles_deeply(self, member: discord.Member, level: int) -> None:
        """ Checks the level role of the member deeply, involving all level roles.
        :param member: The member to check.
        :param level: The level of the member. """

        updated = await self.check_level_role(member, level)
        if updated:
            all_level_roles = await self.select_level_role()
            # excluded = [lvl_role[1] for lvl_role in all_level_roles if lvl_role[1] != updated]

            # await member.remove_roles(excluded, atomic=True)


            level_roles = set(
                [a_role for lvl_role in all_level_roles if (
                    a_role := discord.utils.get(member.guild.roles, id=lvl_role[1])
                    ) and lvl_role[1] != updated
                ]
            )
            member_roles = member.roles
            excluded = level_roles & set(member_roles)
            if excluded:
                for ex in excluded:
                    if ex in member_roles:
                        member_roles.remove(ex)
                await member.edit(roles=member_roles)

    async def set_user_xp(self, user_id: int, the_xp: int) -> None:
        """ Sets the user's XP with the given number. 
        :param user_id: The user's ID. 
        :param the_xp: The new XP value to which set the user's level. """

        mycursor, db = await the_database()
        await mycursor.execute("UPDATE MemberStatus SET user_xp = %s WHERE user_id = %s", (the_xp, user_id))
        await db.commit()
        await mycursor.close()

    async def _make_level_score_embed(self, ctx: commands.Context, entries, offset: int, lentries: int, kwargs) -> discord.Embed:
        """ Makes an embedded message for the level scoreboard. """

        position = kwargs.get('position')

        # tribe_embed.set_footer(text=f"Requested by {ctx.author}", icon_url=ctx.author.avatar_url)
        member = ctx.author

        leaderboard = discord.Embed(
            title="__The Language Sloth's Level Ranking Leaderboard__",
            description="All registered users and their levels and experience points.",
            colour=ctx.author.color, timestamp=ctx.message.created_at)


        leaderboard.description += f"\n**Your XP:** `{position[1]}` | **#**`{position[0]}`"
        leaderboard.set_thumbnail(url=ctx.guild.icon_url)
        leaderboard.set_author(name=ctx.author, icon_url=ctx.author.avatar_url)

        # Embeds each one of the top ten users.
        for i, sm in enumerate(entries, start=offset):
            member = discord.utils.get(ctx.guild.members, id=sm[0])
            leaderboard.add_field(name=f"[{i}]# - __**{member}**__", value=f"Level: `{sm[2]}` | XP: `{sm[1]}`",
                                  inline=False)

        for i, v in enumerate(entries, start=offset):
            leaderboard.set_footer(text=f"({i} of {lentries})")


        return leaderboard
    

    @commands.has_permissions(administrator=True)
    @commands.command(hidden=True)
    async def create_table_member_status(self, ctx):
        """ (ADM) Creates the MemberStatus table. """

        if await self.table_member_status_exists():
            return await ctx.send("**The `MemberStatus` table already exists!**")

        mycursor, db = await the_database()
        await mycursor.execute(
            """CREATE TABLE MemberStatus (
            user_id BIGINT, user_xp BIGINT, user_lvl INT,
            user_xp_time INT, user_messages INT DEFAULT 0,
            vc_time BIGINT DEFAULT 0, vc_ts BIGINT
            )""")
        await db.commit()
        await mycursor.close()
                
        await ctx.send("**Table `MemberStatus` created!**")

    @commands.has_permissions(administrator=True)
    @commands.command(hidden=True)
    async def drop_table_member_status(self, ctx):
        """ (ADM) Drops the MemberStatus table. """

        if not await self.table_member_status_exists():
            return await ctx.send("**The `MemberStatus` table doesn't exist!**")

        mycursor, db = await the_database()
        await mycursor.execute("DROP TABLE MemberStatus")
        await db.commit()
        await mycursor.close()

        await ctx.send("**Table `MemberStatus` dropped!**")

    @commands.has_permissions(administrator=True)
    @commands.command(hidden=True)
    async def reset_table_member_status(self, ctx):
        """ (ADM) Resets the MemberStatus table. """


        if not await self.table_member_status_exists():
            return await ctx.send("**The `MemberStatus` table doesn't exist yet!**")

        mycursor, db = await the_database()
        await mycursor.execute("DELETE FROM MemberStatus")
        await db.commit()
        await mycursor.close()

        await ctx.send("**Table `MemberStatus` reseted!**")

    async def table_member_status_exists(self) -> bool:
        """ Checks whether the LevelRoles table exists. """

        mycursor, db = await the_database()
        await mycursor.execute(f"SHOW TABLE STATUS LIKE 'MemberStatus'")
        table_info = await mycursor.fetchall()
        await mycursor.close()
        if len(table_info) == 0:
                return False
        else:
            return True

    async def insert_user(self, user_id: int, xp_time: int, xp: int = 0, lvl: int = 1, messages: int = 0, vc_time: int = 0, vc_ts: int = None) -> None:
        mycursor, db = await the_database()
        await mycursor.execute("""
            INSERT INTO MemberStatus (user_id, user_xp, user_lvl, user_xp_time, user_messages, vc_time, vc_ts) 
            VALUES (%s, %s, %s, %s, %s, %s, %s)""", 
            (user_id, xp, lvl, xp_time, messages, vc_time, vc_ts))
        await db.commit()
        await mycursor.close()

    async def update_user_xp(self, user_id: int, xp: int) -> None:
        mycursor, db = await the_database()
        await mycursor.execute("UPDATE MemberStatus SET user_xp = user_xp + %s WHERE user_id = %s", (xp, user_id))
        await db.commit()
        await mycursor.close()

    async def update_user_lvl(self, user_id: int, level: int) -> None:
        mycursor, db = await the_database()
        await mycursor.execute("UPDATE MemberStatus set user_lvl = %s WHERE user_id = %s", (level, user_id))
        await db.commit()
        await mycursor.close()


    async def update_user_xp_time(self, user_id: int, time: int) -> None:
        mycursor, db = await the_database()
        await mycursor.execute("UPDATE MemberStatus SET user_xp_time = %s WHERE user_id = %s", (time, user_id))
        await db.commit()
        await mycursor.close()

    async def update_user_server_messages(self, user_id: int, add_msg: int) -> None:
        mycursor, db = await the_database()
        await mycursor.execute(
            "UPDATE MemberStatus SET user_messages = user_messages + %s WHERE user_id = %s", (add_msg, user_id))
        await db.commit()
        await mycursor.close()


    async def update_user_server_time(self, user_id: int, add_time: int, reset_ts: bool = False) -> None:
        mycursor, db = await the_database()
        if reset_ts:
            await mycursor.execute(
                "UPDATE MemberStatus SET vc_time = vc_time + %s, vc_ts = NULL WHERE user_id = %s", (add_time, user_id))
        else:
            await mycursor.execute(
                "UPDATE MemberStatus SET vc_time = vc_time + %s WHERE user_id = %s", (add_time, user_id))
        await db.commit()
        await mycursor.close()

    async def update_user_server_timestamp(self, user_id: int, new_ts: int) -> None:
        mycursor, db = await the_database()
        await mycursor.execute("UPDATE MemberStatus SET vc_ts = %s WHERE user_id = %s", (new_ts, user_id))
        await db.commit()
        await mycursor.close()


    async def remove_user(self, user_id: int) -> None:
        mycursor, db = await the_database()
        await mycursor.execute("DELETE FROM MemberStatus WHERE user_id = %s", (user_id,))
        await db.commit()
        await mycursor.close()

    async def clear_user_lvl(self, user_id: int) -> None:
        mycursor, db = await the_database()
        await mycursor.execute("UPDATE MemberStatus SET user_xp = 0, user_lvl = 1 WHERE user_id = %s", (user_id,))
        await db.commit()
        await mycursor.close()

    async def get_users(self) -> List[List[int]]:
        """ Gets all users from the MemberStatus system. """

        mycursor, db = await the_database()
        await mycursor.execute("SELECT * FROM MemberStatus")
        members = await mycursor.fetchall()
        await mycursor.close()
        return members


    async def get_specific_user(self, user_id: int) -> List[int]:
        """ Gets a specific user from the MemberStatus system. 
        :param user_id: The ID of the user to get. """

        mycursor, db = await the_database()
        await mycursor.execute("SELECT * FROM MemberStatus WHERE user_id = %s", (user_id,))
        member = await mycursor.fetchall()
        await mycursor.close()
        return member


    async def get_all_users_by_xp(self) -> List[List[int]]:
        """ Gets all users from the MembersScore table ordered by XP. """

        mycursor, db = await the_database()
        await mycursor.execute("SELECT * FROM MemberStatus ORDER BY user_xp DESC")
        users = await mycursor.fetchall()
        await mycursor.close()
        return users


    async def get_total_messages(self) -> int:
        """ Gets the total amount of messages sent in the server. """

        mycursor, db = await the_database()
        await mycursor.execute("SELECT SUM(user_messages) FROM MemberStatus")
        total = number[0] if (number := await mycursor.fetchone()) else 0
        await mycursor.close()
        return total

    async def get_total_time(self) -> int:
        """ Gets the total time spent in the server's VCs. """

        mycursor, db = await the_database()
        await mycursor.execute("SELECT SUM(vc_time) FROM MemberStatus")
        total = number[0] if (number := await mycursor.fetchone()) else 0
        await mycursor.close()
        return total


    @commands.command(aliases=['setlevelrole', 'set_levelrole', 'set_lvlrole', 'set_lvl_role'])
    @commands.has_permissions(administrator=True)
    async def set_level_role(self, ctx, level: int = None, role: discord.Role = None) -> None:
        """ Sets a level role to the level system.
        :param level: The level to set.
        :param role: The role to attach to the level. """

        member = ctx.author

        if not level:
            return await ctx.send(f"**Please, inform a level, {member.mention}!**")

        if not role:
            return await ctx.send(f"**Please, inform a role, {member.mention}!**")

        if await self.select_specific_level_role(level=level):
            return await ctx.send(f"**There already is a role attached to the level `{level}`, {member.mention}!**")


        confirm = await Confirm(f"**Set level `{level}` to role `{role.name}`, {member.mention}?**").prompt(ctx)
        if not confirm:
            return

        try:
            await self.insert_level_role(level, role.id)
        except Exception as e:
            print(e)
            await ctx.send(f"**Something went wrong with it, {member.mention}!**")
        else:
            await ctx.send(f"**Set level `{level}` to role `{role.name}`, {member.mention}!**")

    @commands.command(aliases=['unsetlevelrole', 'unset_levelrole', 'delete_levelrole', 'delete_level_role'])
    @commands.has_permissions(administrator=True)
    async def unset_level_role(self, ctx, level: int = None) -> None:
        """ Sets a level role to the level system.
        :param level: The level to set. """

        member = ctx.author

        if not level:
            return await ctx.send(f"**Please, inform a level, {member.mention}!**")

        if not (level_role := await self.select_specific_level_role(level=level)):
            return await ctx.send(f"**There isn't a role attached to the level `{level}` yet, {member.mention}!**")

        role = discord.utils.get(ctx.guild.roles, id=level_role[1])

        confirm = await Confirm(f"**Unset level `{level}` from role `{role.name if role else level_role[1]}`, {member.mention}?**").prompt(ctx)
        if not confirm:
            return

        try:
            await self.delete_level_role(level=level)
        except Exception as e:
            print(e)
            await ctx.send(f"**Something went wrong with it, {member.mention}!**")
        else:
            await ctx.send(f"**Unset level `{level}` from `{role.name if role else level_role[1]}`, {member.mention}!**")



    @commands.command(aliases=['showlevelroles', 'showlvlroles', 'show_lvlroles', 'level_roles', 'levelroles'])
    @commands.has_permissions(administrator=True)
    async def show_level_roles(self, ctx) -> None:
        """ Shows the existing level roles. """

        member = ctx.author

        embed = discord.Embed(
            title="__Level Roles Menu__",
            description="All level roles that were set.",
            color=member.color,
            timestamp=ctx.message.created_at
        )

        level_roles = await self.select_level_role()
        for lvl_role in level_roles:
            embed.add_field(name=f"Level {lvl_role[0]}", value=f"**Role:** <@&{lvl_role[1]}>", inline=True)


        await ctx.send(embed=embed)


    # Database

    async def select_specific_level_role(self, level: int = None, role_id: int = None) -> List[int]:
        """ Selects a specific level role from the database by level or role ID. """

        mycursor, db = await the_database()
        if level:
            await mycursor.execute("SELECT * FROM LevelRoles WHERE level = %s", (level,))
        elif role_id:
            await mycursor.execute("SELECT * FROM LevelRoles WHERE role_id = %s", (role_id,))

        level_role = await mycursor.fetchone()
        await mycursor.close()
        return level_role

    async def select_level_role(self) -> List[List[int]]:
        """ Selects level roles from the database. """

        mycursor, db = await the_database()
        await mycursor.execute("SELECT * FROM LevelRoles ORDER BY level")
        level_roles = await mycursor.fetchall()
        await mycursor.close()
        return level_roles


    async def insert_level_role(self, level: int, role_id: int) -> None:
        """ Inserts a level role into the database.
        :param level: The level to insert.
        :param role_id: The ID of the role to attach to the level. """

        mycursor, db = await the_database()
        await mycursor.execute("INSERT INTO LevelRoles (level, role_id) VALUES (%s, %s)", (level, role_id))
        await db.commit()
        await mycursor.close()

    async def delete_level_role(self, level: int = None, role_id: int = None) -> None:
        """ Deletes a level role into the database by level or role ID.
        :param level: The level to delete. """

        mycursor, db = await the_database()
        if level:
            await mycursor.execute("DELETE FROM LevelRoles WHERE level = %s", (level,))
        elif role_id:
            await mycursor.execute("DELETE FROM LevelRoles WHERE role_id = %s", (role_id,))
        await db.commit()
        await mycursor.close()


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

        mycursor, db = await the_database()
        await mycursor.execute(f"SHOW TABLE STATUS LIKE 'LevelRoles'")
        table_info = await mycursor.fetchall()
        await mycursor.close()
        if len(table_info) == 0:
                return False
        else:
            return True


    @commands.command(aliases=['show_multiplier', 'xp_multiplier', 'show_xp_multiplier', 'xpm', 'xp_rate', 'xprate'])
    @commands.has_any_role(*[trial_mod_role_id, jr_mod_role_id, mod_role_id, admin_role_id, owner_role_id])
    async def multiplier(self, ctx) -> None:
        """ Shows the current XP multiplier. """

        member = ctx.author

        if not await self.table_important_vars_exists():
            return await ctx.send(f"**This command is not ready to be used yet, {member.mention}!**")

        if self.xp_multiplier == 1:
            new_xp = int(self.xp_rate + (self.xp_rate * self.xp_multiplier)/ 100)
            await ctx.send(f"**The current XP multiplier is `{self.xp_multiplier}%`, making a total of `{new_xp}`XP per message**")

        else:
            if self.xp_multiplier:
                new_xp = int(self.xp_rate + (self.xp_rate * self.xp_multiplier)/ 100)
                await ctx.send(f"**The current XP multiplier is `{self.xp_multiplier}%`, making a total of `{new_xp}`XP per message**")
            elif xp_multiplier := await self.get_important_var(label='xp_multiplier'):
                xp_multiplier = xp_multiplier[2]
                new_xp = int(self.xp_rate + (self.xp_rate * xp_multiplier)/ 100)

            else:
                await ctx.send(f"**There isn't a XP multiplier set yet, so the XP rate still is `{self.xp_rate}`XP per message**")


    @commands.command(aliases=['xpboost', 'set_xp_boost', 'setpxpboost', 'setxprate'])
    @commands.has_permissions(administrator=True)
    async def xp_boost(self, ctx, percentage: int = 10):
        """ Sets the XP multiplier.
        :param percentage: The percentage of the multiplier.
        Ps: 
        ¹- Only positive integer numbers are allowed;
        ²- To reset it, use 1 as the percentage multiplier.
        ³- Maximum percentage of 200."""


        member = ctx.author

        if not await self.table_important_vars_exists():
            return await ctx.send(f"**This command is not ready to be used yet, {member.mention}!**")

        if percentage <= 0:
            return await ctx.author(f"**Only positive integer numbers are allowed, {member.mention}!**")

        if percentage > 200:
            return await ctx.send(f"**For safety, the maximum percentage is set to `200`, {member.mention}!**")

        if get_current := await self.get_important_var(label='xp_multiplier'):
            await self.update_important_var(label='xp_multiplier', value_int=percentage)
            self.xp_multiplier = percentage
            await ctx.send(f"**XP multiplier percentage has been updated from `{get_current[2]}`% to `{self.xp_multiplier}`%, {member.mention}!**")

        else:
            await self.insert_important_var(label='xp_multiplier', value_int=percentage)
            self.xp_multiplier = percentage
            await ctx.send(f"**XP multiplier percentage has been set to `{self.xp_multiplier}`%, {member.mention}!**")




    @commands.command(aliases=['xpchannels', 'xpc'])
    @commands.has_permissions(administrator=True)
    async def xp_channels(self, ctx) -> None:
        """ Shows the channels that XP are allowed to be earned in. """

        if not await self.table_important_vars_exists():
            return await ctx.send(f"**This command is not ready to be used yet, {member.mention}!**")


        member = ctx.author

        if not (channels := await self.get_important_var(label="xp_channel", multiple=True)):
            return await ctx.send(f"**No channels have seen set yet, {member.mention}!**")

        guild = ctx.guild
        channels = ', '.join([cm.mention if (cm := discord.utils.get(guild.channels, id=c[2])) else str(c[2]) for c in channels])

        embed = discord.Embed(
            title="XP Channels",
            description=channels,
            color=member.color,
            timestamp=ctx.message.created_at
            )

        await ctx.send(embed=embed)


    @commands.command(aliases=['set_xp_channel', 'setxpchannel', 'sxpc', 'enablexp'])
    @commands.has_permissions(administrator=True)
    async def enable_xp(self, ctx, channel: discord.TextChannel = None) -> None:
        """ Enables a channel for getting XP.
        :param channel: The channel. (Optional)
        Ps: If channel is not informed, it will use the current channel. """

        member = ctx.author

        if not await self.table_important_vars_exists():
            return await ctx.send(f"**This command is not ready to be used yet, {member.mention}!**")


        if not ctx.guild:
            return await ctx.send(f"**You cannot use this command in my DM's, {member.mention}!** ❌")


        if not channel:
            channel = ctx.channel

        if await self.get_important_var(label='xp_channel', value_int=channel.id):
            return await ctx.send(f"**{channel.mention} is already enabled for XP, {member.mention}!** ⚠️")

        await self.insert_important_var(label='xp_channel', value_int=channel.id)
        if channel.id not in self.allowed_channel_ids:
            try:
                self.allowed_channel_ids.append(channel.id)
            except:
                pass
        await ctx.send(f"**{channel.mention} has been enabled for XP, {member.mention}!** ✅")


    @commands.command(aliases=['unset_xp_channel', 'unsetxpchannel', 'uxpc','disablexp', 'disablexpchannel'])
    @commands.has_permissions(administrator=True)
    async def disable_xp(self, ctx, channel: discord.TextChannel = None) -> None:
        """ Enables a channel for getting XP.
        :param channel: The channel. (Optional)
        Ps: If channel is not informed, it will use the current channel. """

        member = ctx.author

        if not await self.table_important_vars_exists():
            return await ctx.send(f"**This command is not ready to be used yet, {member.mention}!**")

        if not ctx.guild:
            return await ctx.send(f"**You cannot use this command in my DM's, {member.mention}!** ❌")

        if not channel:
            channel = ctx.channel

        if not await self.get_important_var(label='xp_channel', value_int=channel.id):
            return await ctx.send(f"**{channel.mention} is not even enabled for XP, {member.mention}!** ⚠️")

        await self.delete_important_var(label='xp_channel', value_int=channel.id)
        if channel.id in self.allowed_channel_ids:
            try:
                self.allowed_channel_ids.remove(channel.id)
            except Exception as e:
                print(e)
                pass
        await ctx.send(f"**{channel.mention} has been disabled for XP, {member.mention}!** ✅")

    async def insert_important_var(self, label: str, value_str: str = None, value_int: int = None) -> None:
        """ Gets an important var.
        :param label: The label o that var. """

        mycursor, db = await the_database()
        await mycursor.execute("INSERT INTO ImportantVars (label, value_str, value_int) VALUES (%s, %s, %s)", (label, value_str, value_int))
        await db.commit()
        await mycursor.close()

    async def update_important_var(self, label: str, value_str: str = None, value_int: str = None) -> None:
        """ Gets an important var.
        :param label: The label o that var. """

        mycursor, db = await the_database()
        if value_str and value_int:
            await mycursor.execute("UPDATE ImportantVars SET value_str = %s, value_int = %s WHERE label = %s", (value_str, value_int, label))
        elif value_str:
            await mycursor.execute("UPDATE ImportantVars SET value_str = %s WHERE label = %s", (value_str, label))
        else:
            await mycursor.execute("UPDATE ImportantVars SET value_int = %s WHERE label = %s", (value_int, label))

        await db.commit()
        await mycursor.close()


    async def get_important_var(self, label: str, value_str: str = None, value_int: int = None, multiple: bool = False) -> Union[Union[str, int], List[Union[str, int]]]:
        """ Gets an important var.
        :param label: The label o that var.
        :param value_str: The string value. (Optional)
        :param value_int: The integer value. (Optional)
        :param multiple: Whether to get multiple values. """

        mycursor, db = await the_database()
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

        mycursor, db = await the_database()
        await mycursor.execute(f"SHOW TABLE STATUS LIKE 'ImportantVars'")
        table_info = await mycursor.fetchall()
        await mycursor.close()
        if len(table_info) == 0:
                return False
        else:
            return True


""" 
Setup:
b!create_table_member_status
b!create_table_level_roles
b!create_table_important_vars
"""


def setup(client) -> None:
    client.add_cog(LevelSystem(client))