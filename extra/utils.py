from datetime import datetime
import re
from pytz import timezone
from typing import List, Optional
import discord
from discord.ext import commands

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
