import discord
from discord.ext import commands, tasks, menus
from mysqldb import the_database

from typing import List, Dict, Union, Any
from datetime import date, datetime
import asyncio
import os

import emoji
from cogs.misc import Misc

from extra.menu import Confirm, SwitchPages
from extra.useful_variables import xp_levels
from extra import utils
from extra.level.level_roles import LevelRoleTable, VCLevelRoleTable
from extra.level.member_status import MemberStatusTable
from extra.tools.important_vars import ImportantVarsTable

owner_role_id: int = int(os.getenv('OWNER_ROLE_ID'))
admin_role_id: int = int(os.getenv('ADMIN_ROLE_ID'))
mod_role_id: int = int(os.getenv('MOD_ROLE_ID'))
jr_mod_role_id: int = int(os.getenv('JR_MOD_ROLE_ID'))
trial_mod_role_id: int = int(os.getenv('TRIAL_MOD_ROLE_ID'))
afk_channel_id: int = int(os.getenv('AFK_CHANNEL_ID'))
game_channel_id: int = int(os.getenv('GAME_VOICE_CHANNEL_ID'))

allowed_roles = [owner_role_id, admin_role_id, mod_role_id, jr_mod_role_id, trial_mod_role_id]

level_cogs: List[commands.Cog] = [
    LevelRoleTable, VCLevelRoleTable, MemberStatusTable,
    ImportantVarsTable
]

class LevelSystem(*level_cogs):
    """ A category for the Level System. """

    def __init__(self, client) -> None:
        self.client = client
        self.xp_rate = 20
        self.xp_multiplier = 1

        self.ticket_category_id: int = int(os.getenv('TICKET_CAT_ID'))

    @commands.Cog.listener()
    async def on_ready(self) -> None:

        self.check_weekend_boost.start()

        if await self.table_important_vars_exists():
            if multiplier := await self.get_important_var(label="xp_multiplier"):
                self.xp_multiplier = multiplier[2]

        print('LevelSystem cog is online')

    # In-game commands
    @commands.Cog.listener()
    async def on_message(self, message):

        if not message.guild:
            return
            
        if message.author.bot:
            return
        elif not await self.table_member_status_exists():
            return

        time_xp = await utils.get_timestamp()

        if not message.channel or not message.channel.category:
            return

        if message.channel.category.id == self.ticket_category_id:
            return

        if await self.get_important_var(label="xp_channel", value_int=message.channel.id):
            await self.update_data(message.author, time_xp, message.channel)
            
        await self.update_user_server_messages(message.author.id, 1)

    @commands.Cog.listener()
    async def on_voice_state_update(self, member, before, after):

        if member.bot:
            return

        if not await self.table_member_status_exists():
            return

        # After voice state
        if before.self_stream != after.self_stream: return
        if before.self_video != after.self_video: return

        current_ts = await utils.get_timestamp()

        bc = before.channel
        ac = after.channel

        user_info = await self.get_specific_user(member.id)
        if not user_info:
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

        if not ac and bc.id not in (game_channel_id, afk_channel_id):
            if addition is not None:
                await self.update_user_server_time(user_id=member.id, add_time=addition, reset_ts=True)
                await Misc.update_user_server_status_vc_time(status_ts=current_ts, addition=addition, label="daily-time", past_days=1, channel_id=bc.id)
                await Misc.update_user_server_status_vc_time(status_ts=current_ts, addition=addition, label="weekly-time", past_days=7, channel_id=bc.id)
        else:
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
            if time_xp - the_member[0][3] >= 20 or the_member[0][1] == 0:
                await self.update_user_xp_time(user.id, time_xp)
                new_xp = int(self.xp_rate + (self.xp_rate * self.xp_multiplier)/ 100)
                await self.update_user_xp(user.id, new_xp)
                return await self.level_up(user, channel)
        else:
            return await self.insert_user(user_id=user.id, xp=5, xp_time=time_xp)

    async def level_up(self, user: discord.Member, channel: discord.TextChannel) -> None:
        the_user = await self.get_specific_user(user.id)

        user_level = the_user[0][2]
        user_xp = the_user[0][1]

        if user_xp >= await self.get_xp(user_level):
            await self.check_user_perm_roles(user, user_level+1)
            await self.update_user_lvl(user.id, user_level+1)
            # await self.check_level_role(user, the_user[0][2]+1)
            await self.check_level_roles_deeply(user, user_level+1)
            return await channel.send(
                f"""🇬🇧 {user.mention} has reached level **{user_level + 1}!**\n🇫🇷 {user.mention} a atteint le niveau **{user_level + 1} !**""")

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

        special_roles = [862742944243253279, 862742944729268234]
        try:
            await member.add_roles(current_role)
        except Exception as e:
            print(e)
        if list_index and (previous_role_id := level_roles[list_index-1][1]):
            if previous_role := discord.utils.get(member.guild.roles, id=previous_role_id):
                if previous_role in member.roles and previous_role.id not in special_roles:
                    try:
                        await member.remove_roles(previous_role)
                    except Exception as ee:
                        print(ee)

        return role_id

    async def check_voice_level_role(self, member: discord.Member, level: int) -> Union[None, int]:
        """ Checks if the member voice level has a role attached to it
        and gives the role to the member if so.
        :param member: The member to check.
        :param level: The current level of the member. """

        role_id = None
        list_index = 0

        level_roles = await self.select_vc_level_role()
        for i, level_r in enumerate(level_roles):
            if level >= level_r[0]:
                role_id = level_r[1]
                list_index = i

        if not role_id or not (current_role := discord.utils.get(member.guild.roles, id=role_id)):
            return

        try:
            await member.add_roles(current_role)
        except Exception as e:
            print(e)
        if list_index and (previous_role_id := level_roles[list_index-1][1]):
            if previous_role := discord.utils.get(member.guild.roles, id=previous_role_id):
                if previous_role in member.roles:
                    try:
                        await member.remove_roles(previous_role)
                    except Exception as ee:
                        print(ee)

        return role_id

    @commands.command(aliases=['stats', 'statuses'])
    @Misc.check_whitelist()
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

        the_emojis = await Misc.get_top_emojis()

        the_emojis = [f"{emoji.emojize(emj[0])} ({emj[1]}x)" for emj in the_emojis]

        embed.add_field(
            name="__Top 3 Most Used Emojis__",
            value='\n'.join(the_emojis)
        )

        embed.add_field(
            name="__Most Active Message Channels__", 
            value=f"**🕖 Last 7 days:** {c_msg_7[0].mention if c_msg_7[0] else None}\n**🕛 Last 24 hours:** {c_msg_1[0].mention if c_msg_1[0] else None}", 
            inline=True)

        embed.add_field(
            name="__Most Active Voice Channels__", 
            value=f"**🕖 Last 7 days:** {c_time_7[0].mention if c_time_7[0] else None}\n**🕛 Last 24 hours:** {c_time_1[0].mention if c_time_1[0] else None}",
            inline=True)

        total_infractions = await self.client.get_cog('LevelSystem').get_important_var(label="t_infractions")
        monthly_infractions = await self.client.get_cog('LevelSystem').get_important_var(label="m_infractions")
        embed.add_field(name="📋 Total Infractions", value=f"{total_infractions[2] + monthly_infractions[2]} infractions in total.", inline=False)
        embed.add_field(name="🗓️ Monthly Infractions", value=f"{monthly_infractions[2]} infractions in this month..", inline=False)

        embed.set_thumbnail(url=ctx.guild.icon.url)
        embed.set_footer(text=member, icon_url=member.display_avatar)

        await ctx.send(embed=embed)

    @commands.command(aliases=['profile'])
    @Misc.check_whitelist()
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

        # Gets the user's Voice data from the database
        Tools = self.client.get_cog('Tools')
        if not (user_voice := await Tools.get_user_voice(member.id)):
            await Tools.insert_user_voice(member.id)
            await asyncio.sleep(0.3)
            user_voice = await Tools.get_user_voice(member.id)

        # Arranges the user's information into a well-formed embed
        all_users = await self.get_all_users_by_xp()
        position = [[i+1, u[1]] for i, u in enumerate(all_users) if u[0] == member.id]
        position = [it for subpos in position for it in subpos] if position else ['??', 0]

        all_vc_users = await Tools.get_all_user_voices_by_xp()
        vc_position = [[i+1, u[4]] for i, u in enumerate(all_vc_users) if u[0] == member.id]
        vc_position = [it for subpos in vc_position for it in subpos] if vc_position else ['??', 0]

        embed = discord.Embed(title="__Profile__", colour=member.color, timestamp=ctx.message.created_at)
        embed.add_field(name="**Chat Level**", value=f"{user[0][2]}.", inline=True)
        embed.add_field(name="**Chat Rank**", value=f"# {position[0]}.", inline=True)
        embed.add_field(name="**Chat EXP**", value=f"{user[0][1]} / {await self.get_xp(user[0][2])}.", inline=True)

        embed.add_field(name="**Messages**", value=f"{user[0][4]}.", inline=False)

        embed.add_field(name="**Voice Level**", value=f"{user_voice[3]}.", inline=True)
        embed.add_field(name="**Voice Rank**", value=f"# {vc_position[0]}.", inline=True)
        embed.add_field(name="**Voice EXP**", value=f"{user_voice[4]} / {await self.get_xp(user_voice[3])}.", inline=True)

        mall, sall = divmod(user[0][5], 60)
        hall, mall = divmod(mall, 60)
        dall, hall = divmod(hall, 24)
        text_all = ''
        if dall: text_all = f"{dall}d, {hall}h, {mall}m & {sall}s"
        elif hall: text_all = f"{hall}h, {mall}m & {sall}s"
        elif mall: text_all = f"{mall}m & {sall}s"
        elif sall: text_all = f"{sall}s"
        else: text_all = '0'

        embed.add_field(name="**Voice Time**", value=text_all, inline=True)

        if staff_member := await self.client.get_cog('Moderation').get_staff_member(member.id):
            try:
                joined_staff_at = datetime.utcfromtimestamp(int(staff_member[2])).strftime('%Y/%m/%d at %H:%M:%S')
            except:
                joined_staff_at = str(staff_member[2])

            embed.add_field(name="Joined Staff at:", value=joined_staff_at, inline=False)

            embed.add_field(name="Infractions Given:", value=f"{staff_member[1]} infractions.", inline=False)

        embed.set_thumbnail(url=member.display_avatar)
        embed.set_footer(text=f"{member}", icon_url=member.display_avatar)
        return await ctx.send(embed=embed)

    @commands.command(aliases=['score', 'level_board', 'levelboard', 'levels', 'level_score'])
    @Misc.check_whitelist()
    async def leaderboard(self, ctx):
        """ Shows the top ten members in the level leaderboard. """

        all_users = await self.get_all_users_by_xp()
        position = [[i+1, u[1]] for i, u in enumerate(all_users) if u[0] == ctx.author.id]
        position = [it for subpos in position for it in subpos] if position else ['??', 0]

        # Additional data:
        additional = {
            'change_embed': self._make_level_score_embed,
            'position': position
        }

        pages = menus.MenuPages(source=SwitchPages(all_users, **additional), clear_reactions_after=True)
        await pages.start(ctx)

    @commands.command(aliases=[
        'voice_score', 'voice_level_board', 'voice_levelboard', 'voice_levels', 'voice_level_score',
        'vscore', 'vlevel_board', 'vlevelboard', 'vlevels', 'vlevel_score'
    ])
    @Misc.check_whitelist()
    async def voice_leaderboard(self, ctx):
        """ Shows the top ten members in the voice level leaderboard. """

        Tools = self.client.get_cog('Tools')
        all_users = await Tools.get_all_user_voices_by_xp()
        position = [[i+1, u[4]] for i, u in enumerate(all_users) if u[0] == ctx.author.id]
        position = [it for subpos in position for it in subpos] if position else ['??', 0]

        # Additional data:
        additional = {
            'change_embed': self._make_voice_level_score_embed,
            'position': position
        }
        pages = menus.MenuPages(source=SwitchPages(all_users, **additional), clear_reactions_after=True)
        await pages.start(ctx)

    @commands.command()
    @commands.has_permissions(administrator=True)
    async def setlevel(self, ctx, member: discord.Member = None, level: int = None) -> None:
        """ Sets a level to a user.
        :param member: The member to whom the level is gonna be set.
        :param level: The new level to which the user's level is gonna be set. """

        if not member:
            return await ctx.send(f"**Please, inform a member to set a new level to, {ctx.author.mention}!**")

        if not level:
            return await ctx.send(f"**Please, inform the level that you want the user to have, {ctx.author.mention}!**")

        if level <= 0:
            return await ctx.send(f"**Please, inform a positive number greater than 0, {ctx.author.mention}!**")

        if not (the_user := await self.get_specific_user(member.id)):
            return await ctx.send(f"**Member is not in the system yet, {ctx.author.mention}!**")

        if level >= the_user[0][2]:
            await self.set_user_xp(member.id, await self.get_xp(level-1))
            await self.update_user_lvl(member.id, level)

        else:
            await self.set_user_xp(member.id, await self.get_xp(level-1))
            await self.update_user_lvl(member.id, level)

        await asyncio.sleep(0.1)
        await self.check_level_roles_deeply(member, level)
        await ctx.send(f"**The member {member.mention} is now level {level}!**")

    @commands.command()
    @commands.has_permissions(administrator=True)
    async def setvclevel(self, ctx, member: discord.Member = None, level: int = None) -> None:
        """ Sets a Voice Channel level to a user.
        :param member: The member to whom the level is gonna be set.
        :param level: The new level to which the user's level is gonna be set. """

        if not member:
            return await ctx.send(f"**Please, inform a member to set a new VC level to, {ctx.author.mention}!**")

        if not level:
            return await ctx.send(f"**Please, inform the VC level that you want the user to have, {ctx.author.mention}!**")

        if level <= 0:
            return await ctx.send(f"**Please, inform a positive number greater than 0, {ctx.author.mention}!**")

        Tools = self.client.get_cog('Tools')

        if not (the_user := await Tools.get_user_voice(member.id)):
            return await ctx.send(f"**Member is not in the system yet, {ctx.author.mention}!**")


        if level >= the_user[3]:
            await Tools.set_user_voice_xp(member.id, await self.get_xp(level-1))
            await Tools.update_user_voice_lvl(member.id, level)
            # await self.set_user_xp(member.id, ((level-1)** 5))

        else:
            # await self.set_user_xp(member.id, ((level-1)** 5))
            await Tools.set_user_voice_xp(member.id, await self.get_xp(level-1))
            await Tools.update_user_voice_lvl(member.id, level)

        await asyncio.sleep(0.1)
        await self.check_voice_level_roles_deeply(member, level)
        await ctx.send(f"**The member {member.mention} is now level {level}!**")

    async def check_level_roles_deeply(self, member: discord.Member, level: int) -> None:
        """ Checks the level role of the member deeply, involving all level roles.
        :param member: The member to check.
        :param level: The level of the member. """

        updated = await self.check_level_role(member, level)
        if updated:
            all_level_roles = await self.select_level_role()

            level_roles = set(
                [a_role for lvl_role in all_level_roles if (
                    a_role := discord.utils.get(member.guild.roles, id=lvl_role[1])
                    ) and lvl_role[1] != updated
                ]
            )

            special_roles = [862742944243253279, 862742944729268234]

            member_roles = member.roles
            excluded = level_roles & set(member_roles)
            if excluded:
                for ex in excluded:
                    if ex in member_roles and ex.id not in special_roles:
                        member_roles.remove(ex)
                await member.edit(roles=member_roles)

    async def check_voice_level_roles_deeply(self, member: discord.Member, level: int) -> None:
        """ Checks the voice level role of the member deeply, involving all voice level roles.
        :param member: The member to check.
        :param level: The voice level of the member. """

        updated = await self.check_voice_level_role(member, level)
        if updated:
            all_level_roles = await self.select_vc_level_role()

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

    async def check_user_perm_roles(self, member: discord.Member, level: int) -> None:
        """ Checks whether the member should get the user perm roles when leveling up. """

        if member.id == member.guild.owner_id:
            return

        if level >= 2:
            role: discord.Role = discord.utils.get(member.guild.roles, id=862742944729268234)
            try:
                await member.add_roles(role)
            except:
                pass

        if level >= 3:
            role: discord.Role = discord.utils.get(member.guild.roles, id=862742944243253279)
            try:
                await member.add_roles(role)
            except:
                pass

    async def _make_level_score_embed(self, ctx: commands.Context, entries, offset: int, lentries: int, kwargs) -> discord.Embed:
        """ Makes an embedded message for the level scoreboard. """

        position = kwargs.get('position')
        member = ctx.author

        leaderboard = discord.Embed(
            title="__Le Salon Français' Level Ranking Leaderboard__",
            description="All registered users and their levels and experience points.",
            colour=ctx.author.color, timestamp=ctx.message.created_at)

        leaderboard.description += f"\n**Your XP:** `{position[1]}` | **#**`{position[0]}`"
        leaderboard.set_thumbnail(url=ctx.guild.icon.url)
        leaderboard.set_author(name=ctx.author, icon_url=ctx.author.display_avatar)

        # Embeds each one of the top ten users.
        for i, sm in enumerate(entries, start=offset):
            member = discord.utils.get(ctx.guild.members, id=sm[0])
            leaderboard.add_field(name=f"[{i}]#", value=f"{member.mention if member else f'<@{sm[0]}>'} | Level: `{sm[2]}` | XP: `{sm[1]}`",
                                  inline=False)

        for i, v in enumerate(entries, start=offset):
            leaderboard.set_footer(text=f"({i} of {lentries})")

        return leaderboard

    async def _make_voice_level_score_embed(self, ctx: commands.Context, entries, offset: int, lentries: int, kwargs) -> discord.Embed:
        """ Makes an embedded message for the voice level scoreboard. """

        position = kwargs.get('position')
        member = ctx.author

        leaderboard = discord.Embed(
            title="__Le Salon Français' Voice Level Ranking Leaderboard__",
            description="All registered users and their voice levels and experience points.",
            colour=ctx.author.color, timestamp=ctx.message.created_at)

        leaderboard.description += f"\n**Your Voice XP:** `{position[1]}` | **#**`{position[0]}`"
        leaderboard.set_thumbnail(url=ctx.guild.icon.url)
        leaderboard.set_author(name=ctx.author, icon_url=ctx.author.display_avatar)

        # Embeds each one of the top ten users.
        for i, sm in enumerate(entries, start=offset):
            member = discord.utils.get(ctx.guild.members, id=sm[0])
            leaderboard.add_field(name=f"[{i}]#", value=f"{member.mention if member else f'<@{sm[0]}>'} | Level: `{sm[3]}` | XP: `{sm[4]}`",
                                  inline=False)

        for i, v in enumerate(entries, start=offset):
            leaderboard.set_footer(text=f"({i} of {lentries})")

        return leaderboard
    
    @commands.command(aliases=['setlevelrole', 'set_levelrole', 'set_lvlrole', 'set_lvl_role'])
    @commands.has_permissions(administrator=True)
    async def set_level_role(self, ctx, level: int = None, *, role: discord.Role = None) -> None:
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

    @commands.command(aliases=['setvclevelrole', 'set_vclevelrole', 'set_voice_level_role', 'set_vclvlrole', 'set_vc_lvl_role'])
    @commands.has_permissions(administrator=True)
    async def set_vc_level_role(self, ctx, level: int = None, *, role: discord.Role = None) -> None:
        """ Sets a level role to the level system.
        :param level: The level to set.
        :param role: The role to attach to the level. """

        member = ctx.author

        if not level:
            return await ctx.send(f"**Please, inform a level, {member.mention}!**")

        if not role:
            return await ctx.send(f"**Please, inform a role, {member.mention}!**")

        if await self.select_specific_vc_level_role(level=level):
            return await ctx.send(f"**There already is a role attached to the level `{level}`, {member.mention}!**")

        confirm = await Confirm(f"**Set level `{level}` to role `{role.name}`, {member.mention}?**").prompt(ctx)
        if not confirm:
            return

        try:
            await self.insert_vc_level_role(level, role.id)
        except Exception as e:
            print(e)
            await ctx.send(f"**Something went wrong with it, {member.mention}!**")
        else:
            await ctx.send(f"**Set level `{level}` to role `{role.name}`, {member.mention}!**")

    @commands.command(aliases=['unsetvclevelrole', 'unset_vclevelrole', 'delete_vclevelrole' 'unset_voice_level_role', 'delete_vc_level_role'])
    @commands.has_permissions(administrator=True)
    async def unset_vc_level_role(self, ctx, level: int = None) -> None:
        """ Sets a Voice Channel level role to the Voice level system.
        :param level: The level to set. """

        member = ctx.author

        if not level:
            return await ctx.send(f"**Please, inform a VC level, {member.mention}!**")

        if not (level_role := await self.select_specific_vc_level_role(level=level)):
            return await ctx.send(f"**There isn't a role attached to the VC level `{level}` yet, {member.mention}!**")

        role = discord.utils.get(ctx.guild.roles, id=level_role[1])

        confirm = await Confirm(f"**Unset VC level `{level}` from role `{role.name if role else level_role[1]}`, {member.mention}?**").prompt(ctx)
        if not confirm:
            return

        try:
            await self.delete_vc_level_role(level=level)
        except Exception as e:
            print(e)
            await ctx.send(f"**Something went wrong with it, {member.mention}!**")
        else:
            await ctx.send(f"**Unset level `{level}` from `{role.name if role else level_role[1]}`, {member.mention}!**")



    @commands.command(aliases=['showlevelroles', 'showlvlroles', 'show_lvlroles', 'level_roles', 'levelroles'])
    @Misc.check_whitelist()
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

    @commands.command(aliases=['showvclevelroles', 'showvclvlroles', 'show_vclvlroles', 'vc_level_roles', 'vclevelroles'])
    @Misc.check_whitelist()
    async def show_vc_level_roles(self, ctx) -> None:
        """ Shows the existing VC level roles. """

        member = ctx.author

        embed = discord.Embed(
            title="__VC Level Roles Menu__",
            description="All VC level roles that were set.",
            color=member.color,
            timestamp=ctx.message.created_at
        )

        level_roles = await self.select_vc_level_role()
        for lvl_role in level_roles:
            embed.add_field(name=f"Level {lvl_role[0]}", value=f"**Role:** <@&{lvl_role[1]}>", inline=True)

        await ctx.send(embed=embed)



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
            return await ctx.send(f"**No channels have been set yet, {member.mention}!**")

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
        await ctx.send(f"**{channel.mention} has been disabled for XP, {member.mention}!** ✅")

    @tasks.loop(minutes=1)
    async def check_weekend_boost(self) -> None:
        """ Checks whether its weekend to turn on or turn off the XP boost. """

        global_percentage: int = 50

        percentage: int = global_percentage

        current_time = await utils.get_time()
        weekday = current_time.weekday()
        hour = current_time.hour

        if not await self.table_important_vars_exists():
            return

        guild = self.client.get_guild(int(os.getenv('SERVER_ID')))

        # VC
        xp_boost_vc: discord.VoiceChannel = discord.utils.get(guild.voice_channels, id=int(os.getenv('XP_BOOST_VC_ID')))

        # Txt
        general_channel: discord.TextChannel = discord.utils.get(guild.text_channels, id=int(os.getenv('GENERAL_CHANNEL_ID')))
        if not general_channel:
            return

        if weekday != 0 and weekday != 4:
            return

        vc_name: str = f"🟢 {percentage}% Boost Active"
        text: str  = f"**Friday XP boost has been turned on; `{percentage}`%!**"
        if weekday == 0:
            percentage = 1
            text: str  = f"**Friday XP boost has been turned off; going back to `{percentage}`%!**"
            vc_name: str = f"🔴 {global_percentage}% Boost Inactive"
            

        if get_current := await self.get_important_var(label='xp_multiplier'):
            if weekday == 0 and get_current[2] != global_percentage:
                return

            if weekday == 4 and get_current[2] == global_percentage:
                return

            if weekday == 0 or weekday == 4 and hour == 19:
                await self.update_important_var(label='xp_multiplier', value_int=percentage)
                self.xp_multiplier = percentage
                await general_channel.send(text)
                await xp_boost_vc.edit(name=vc_name)

        else:

            await self.insert_important_var(label='xp_multiplier', value_int=percentage)
            self.xp_multiplier = percentage
            await general_channel.send(text)
            await xp_boost_vc.edit(name=vc_name)

""" 
Setup:
b!create_table_member_status
b!create_table_level_roles
b!create_table_important_vars
b!create_table_vc_level_roles
"""


def setup(client) -> None:
    client.add_cog(LevelSystem(client))