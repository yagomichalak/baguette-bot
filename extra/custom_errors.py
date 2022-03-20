from discord.ext import commands

class CommandNotReady(commands.CheckFailure):
    """ Error Class for denoting commands that are not ready. """
    
    pass
