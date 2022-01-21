import discord
from extra import utils
from discord.ext import commands
from typing import List, Union, Optional, Dict, Any
from functools import partial

class BasicUserCheckView(discord.ui.View):

    def __init__(self, member: Union[discord.User, discord.Member], timeout: int = 180) -> None:
        super().__init__(timeout=timeout)
        self.member = member

    async def interaction_check(self, interaction: discord.Interaction) -> bool:
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