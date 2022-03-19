import discord
from discord.ext import commands

from typing import List, Union, Tuple
import asyncio

from .select import ReportSupportSelect
from .prompt.menu import ConfirmButton
from . import utils

class BasicUserCheckView(discord.ui.View):
    """ View fro basic user checking. """

    def __init__(self, member: Union[discord.User, discord.Member], timeout: int = 180) -> None:
        """ Class init method. """

        super().__init__(timeout=timeout)
        self.member = member

    async def interaction_check(self, interaction: discord.Interaction) -> bool:
        """ Checks whether the user who clicked on the button was the one who ran the command. """

        return self.member.id == interaction.user.id


class RulesView(discord.ui.View):
    """ View for showing a specific rule. """

    def __init__(self, member: discord.Member, rule: Union[int, str], rules: List[List[Union[int, str]]], timeout: int = 180) -> None:
        """ Class init method. """

        super().__init__(timeout=timeout)
        self.member = member
        self.rule = rule
        self.rules = rules


    @discord.ui.button(style=1, label="English", emoji="🇬🇧", custom_id=f"english_rule_translation")
    async def translate_english_rule_button(self, button: discord.ui.button, interaction: discord.Interaction) -> None:
        """ Button to translate the English rule(s). """


        await interaction.response.defer()

        if str(self.rule) == 'all':
            new_embed = await self.make_rules_embed(interaction.guild, 1)
        else:
            new_embed = await self.make_rule_embed(interaction.guild, 1)

        await interaction.followup.edit_message(message_id=interaction.message.id, embed=new_embed)

    @discord.ui.button(style=1, label="French", emoji="🇫🇷", custom_id=f"french_rule_translation")
    async def translate_french_rule_button(self, button: discord.ui.button, interaction: discord.Interaction) -> None:
        """ Button to translate the French rule(s). """

        await interaction.response.defer()

        if str(self.rule) == 'all':
            new_embed = await self.make_rules_embed(interaction.guild, 2)
        else:
            new_embed = await self.make_rule_embed(interaction.guild, 2)

        await interaction.followup.edit_message(message_id=interaction.message.id, embed=new_embed)


    async def make_rule_embed(self, guild, index: int = 1) -> discord.Embed:
        """ Makes an embed for a specific rule.
        :param number: The number of the rule.
        :param index: Whether it should be in English or French. Default = 1.
        1 - English; 2 - French. """

        embed = discord.Embed(
            title=f"Rule number {self.rule}",
            description=self.rules[self.rule-1][index], url='https://discordapp.com/guidelines', colour=1406210)

        embed.set_footer(text=guild.owner,
                            icon_url=guild.owner.display_avatar)
        embed.set_thumbnail(
            url=guild.icon.url)
        embed.set_author(name=guild.name, url='https://discordapp.com',icon_url=guild.icon.url)
        return embed

    async def make_rules_embed(self, guild, index: int = 1) -> discord.Embed:
        """ Makes an embed for the rules.
        :param index: Whether it should be in English or French. Default = 1.
        1 - English; 2 - French. """

        embed = discord.Embed(title="Discord’s Terms of Service and Community Guidelines",
                                description="Rules Of The Server", url='https://discordapp.com/guidelines',
                                colour=1406210)

        rules = self.rules
        rules = [r for r in rules if r[1] or r[2]]

        for rule in rules:
            embed.add_field(name=f"__{rule[0]}__:", value=rule[index], inline=False)

        embed.add_field(name="🇫🇷", value="Enjoy our Server!", inline=True)
        embed.add_field(name="🤖", value="Discover our Features!", inline=True)
        embed.add_field(name="🥖", value="We love chocolatine ~~and pain au chocolat~~!", inline=True)
        embed.set_footer(text=guild.owner,
                            icon_url=guild.owner.display_avatar)
        embed.set_thumbnail(
            url=guild.icon.url)
        embed.set_author(name=guild.name, url='https://discordapp.com',
                            icon_url=guild.icon.url)

        return embed


    async def interaction_check(self, interaction: discord.Interaction) -> bool:
        """ Checks whether the user who clicked on the button was the one who ran the command. """

        return self.member.id == interaction.user.id



class ReportSupportView(discord.ui.View):
    """ View for the ReportSupport functionality. """

    def __init__(self, client: commands.Bot) -> None:
        """ Class init method. """

        super().__init__(timeout=None)
        self.client = client
        self.cog = client.get_cog('Ticket')
        self.add_item(ReportSupportSelect(client))

    async def interaction_check(self, interaction: discord.Interaction) -> bool:
        """ Checks whether the checking should pass, based on the user who started
        the command and if they are on cooldown. """

        await interaction.message.edit(view=self)
        member = interaction.user
        member_ts = self.cog.report_cache.get(member.id)
        time_now = await utils.get_timestamp()
        if member_ts:
            sub = time_now - member_ts
            if sub <= 240:
                return await interaction.response.send_message(
                    f"**You are on cooldown to report, try again in {round(240-sub)} seconds**", ephemeral=True)

        return True

class ConvertTimeView(discord.ui.View):
    """ View for the converting time feature. """

    def __init__(self, client: commands.Bot, user_info: List[Union[int, str]], timeout: float = 60) -> None:
        super().__init__(timeout=timeout)
        self.client = client
        self.user_info = user_info


    @discord.ui.button(style=discord.ButtonStyle.blurple, label="Convert VC Time into XP!", custom_id="convert_vc_time_into_crumbs", emoji="💰")
    async def convert_activity(self, button: discord.ui.button, interaction: discord.Interaction) -> None:
        """ Exchanges the member's Voice Channel time into XP. """

        self.stop()
        member = interaction.user

        m, s = divmod(self.user_info[1], 60)
        h, m = divmod(m, 60)

        await interaction.response.defer()
        LevelSystem = self.client.get_cog('LevelSystem')
        converted_xp, time_times = await self.convert_time(self.user_info[1])

        if converted_xp == 0:
            return await interaction.followup.send(f"**You have nothing to exchange, {member.mention}!**")

        confirm_view =  ConfirmButton(member, timeout=60)
        msg = await interaction.followup.send(
            f"**{member.mention}, are you sure you want to convert `{h:d}h`, `{m:02d}m` to `{converted_xp}XP`?**",
            view=confirm_view
        )
        await confirm_view.wait()
        if confirm_view.value:
            pass
            await self.exchange(interaction, member, converted_xp, time_times)
            # Updates user Activity Status and Money
            # await LevelSystem.update_user_voice_xp(member.id, -time_times * 20)
        elif confirm_view.value is False:
            await confirm_view.interaction.followup.send(f"**{member.mention}, not exchanging, then!**")
        
        await utils.disable_buttons(confirm_view)
        await msg.edit(view=confirm_view)

    async def interaction_check(self, interaction: discord.Interaction) -> bool:
        """ Checks whether the user who clicked on the button was the one who ran the command. """

        return self.user_info[0] == interaction.user.id

    async def exchange(self, interaction: discord.Interaction, member: discord.Member, 
        converted_xp: int, time_times: int) -> discord.Message:
        """ Converts your Voice Channel time into Voice XP.
        :param interaction: The interaction that triggered this method.
        :param converted_xp: The amount of XP gotten after time conversion.
        :param time_times: The amount of loops it took to get to the time result. """
        

        current_time = await utils.get_time()
        embed = discord.Embed(title="Conversion", color=member.color, timestamp=current_time)
        embed.set_author(name=member, url=member.display_avatar)

        if converted_xp > 0:
            embed.add_field(
                name="__**Time:**__",
                value=f"Converted `{(time_times * 600) / 60}` minutes to `{converted_xp}`XP;", 
                inline=False)

        return await interaction.followup.send(embed=embed)

    async def convert_time(self, user_time: int) -> Tuple[int, int]:
        """ Converts the user's time counter to XP.
        :param user_time: The amount of time in seconds the user has. """

        time_left = user_time
        converted_xp = times = 0

        while True:
            if time_left >= 600: # Convertion Minute Rate
                times += 1
                time_left -= 60 #  Seconds conversion (= 1 minute)
                converted_xp += 20 # XP Obtained by the conversion
                await asyncio.sleep(0)
                continue
            else:
                return converted_xp, times

    
