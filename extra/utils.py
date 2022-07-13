from datetime import datetime
import re
from pytz import timezone
from typing import List, Optional
import discord
from discord.ext import commands
from .custom_errors import CommandNotReady
from collections import OrderedDict
import shlex

async def get_timestamp(tz: str = 'Etc/GMT') -> int:
    """ Gets the current timestamp.
    :param tz: The timezone to get the timstamp from. Default = Etc/GMT """

    tzone = timezone(tz)
    the_time = datetime.now(tzone)
    return the_time.timestamp()

async def get_time(tz: str = 'Etc/GMT') -> datetime:
    """ Gets the current timestamp.
    :param tz: The timezone to get the timstamp from. Default = Etc/GMT """

    tzone = timezone(tz)
    the_time = datetime.now(tzone)
    return the_time

async def parse_time(tz: str = 'Etc/GMT') -> str:
    """ Parses time from the current timestamp.
    :param tz: The timezone to get the timstamp from. Default = Etc/GMT """

    return datetime(*map(int, re.split(r'[^\d]', str(datetime.now(tz)).replace('+00:00', ''))))

def is_allowed(roles: List[int], check_adm: Optional[bool] = True, throw_exc: Optional[bool] = False) -> bool:
    """ Checks whether the member has adm perms or has an allowed role.
    :param roles: The roles to check if the user has.
    :param check_adm: Whether to check whether the user has adm perms or not. [Optional][Default=True]
    :param throw_exec: Whether to throw an exception if it returns false. [Optional][Default=False] """

    async def real_check(ctx: Optional[commands.Context] = None, channel: Optional[discord.TextChannel] = None, 
        member: Optional[discord.Member] = None) -> bool:

        member = member if not ctx else ctx.author
        channel = channel if not ctx else ctx.channel

        if check_adm:
            perms = channel.permissions_for(member)
            if perms.administrator:
                return True
                
        for rid in roles:
            if rid in [role.id for role in member.roles]:
                return True

        if throw_exc:
            raise commands.MissingAnyRole(roles)

    return commands.check(real_check)

def split_quotes(value: str) -> List[str]:
    """ Splits quotes.
    :param value: The value to split. """

    lex = shlex.shlex(value)
    lex.quotes = '"'
    lex.whitespace_split = True
    lex.commenters = ''
    return list(lex)

async def greedy_member_reason(ctx, message : str = None):
    """A converter that greedily member or users until it can't.
    The member search ends on the first member not found or when the string does not match a member identifier.
    Everything else is considered a reason."""

    users = []
    reason = None

    if not message:
        return users, reason

    message = split_quotes(message)

    for pos, word in enumerate(message):
        if '"' in word:
            word = word[1:-1]

        # Checks if it is an ID, a mention or name#discriminator
        if (len(word) >= 15 and len(word) <= 20 and word.isdigit()) or re.match(r'<@!?([0-9]{15,20})>$', word) or (len(word) > 5 and word[-5] == '#'):

            # Member search
            try:
                user = await commands.MemberConverter().convert(ctx, word)
                # Ignores member if found by username
                if user.name == word or user.nick == word:
                    del user

            except commands.errors.BadArgument:
                user = None
            # User search (if cannot found a member)
            if not user:
                try:
                    user = await commands.UserConverter().convert(ctx, word)
                    # Ignores member if found by username
                    if user.name == word:
                        del user

                except commands.errors.BadArgument:
                    user = None

            if not user:
                reason = ' '.join(message[pos:])
                return list(OrderedDict.fromkeys(users)), reason

            users.append(user)

        # When does not find a string in the member format
        else:
            reason = ' '.join(message[pos:])
            return list(OrderedDict.fromkeys(users)), reason

    return list(OrderedDict.fromkeys(users)), reason


async def disable_buttons(view: discord.ui.View) -> None:
    """ Disables all buttons from a view.
    :param view: The view from which to disable the buttons. """

    for child in view.children:
        child.disabled = True

def not_ready():
    """ Makes a command not be usable. """

    async def real_check(ctx):
        """ Performs the real check. """
        raise CommandNotReady()

    return commands.check(real_check)