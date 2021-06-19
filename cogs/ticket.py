import discord
from discord.ext import commands
import aiomysql
from os import getenv
import asyncio
from typing import List, Union, Any, Dict
import time

from discord.ext.commands.core import check


class Ticket(commands.Cog):
  '''
  A class regarding the management of tickets and their channels.
  '''

  def __init__(self, client) -> None:
    '''
    An ordinary bot initialization method.
    '''
    self.client = client
    self.loop = asyncio.get_event_loop()
    self.ticket_message_id: int = int(getenv('TICKET_MESSAGE_ID'))
    self.ticket_category_id: int = int(getenv('TICKET_CAT_ID'))
    self.cache: Dict[int, int] = {}

  @commands.Cog.listener()
  async def on_ready(self) -> None:
    '''
    Fires when the bot loads the cog.
    '''
    print("Ticket cog is online!")

  @commands.Cog.listener()
  async def on_raw_reaction_add(self, payload) -> None:
    '''
    Checks whether the user reacted to the message, from which they can open a ticket channel.
    '''

    guild = self.client.get_guild(payload.guild_id)
    user = discord.utils.get(guild.members, id=payload.user_id)

    if not guild:
      return

    if user.bot:
      return

    if payload.message_id == self.ticket_message_id:
        if str(payload.emoji) != '❌':
            return

        channel = self.client.get_channel(payload.channel_id)
        message = await channel.fetch_message(payload.message_id)
        await message.remove_reaction('❌', user)

        member_ts = self.cache.get(payload.member.id)
        time_now = time.time()
        if member_ts:
            sub = time_now - member_ts
            if sub <= 60:
                return

        self.cache[payload.member.id] = time.time()

        try:
          msg = await payload.member.send(f"""🇬🇧 Please confirm by saying __**yes**__ that you need assistance. This will open a ticket notifying staff of your enquiry.

🇫🇷 Veuillez confirmer que vous avez besoin d'aide en écrivant __**oui**__. Un ticket sera alors ouvert et le staff sera informé.""")
          msg_resp = await self.client.wait_for('message', timeout=60, 
          check=lambda m: m.author.id == payload.member.id and not m.guild \
            and m.content.lower() in ['yes', 'oui', 'y', 'no', 'non', 'nope', 'non'])

        except asyncio.TimeoutError:
          await payload.member.send("**Timeout!**")
          self.cache[payload.member.id] = 0

        else:
          if msg_resp.content.lower() in ['yes', 'oui']:

            # Tries to open a ticket channel
            await self.open_ticket(user, guild)
          else:
            await payload.member.send("**Comprehensible, have a good day!**")
            self.cache[payload.member.id] = 0

  @commands.command(aliases=['close_ticket', 'cc', 'ct'])
  @commands.has_permissions(administrator=True)
  async def close_channel(self, ctx):
    '''
    Closes a Ticket-Channel.
    '''
    user_channel = await self.get_ticket_channel(ctx.channel.id)
    if user_channel:
      channel = discord.utils.get(ctx.guild.channels, id=user_channel[1])
      embed = discord.Embed(title="Confirmation",
        description="Are you sure that you want to delete this ticket channel?",
        color=ctx.author.color,
        timestamp=ctx.message.created_at)
      confirmation = await ctx.send(content=ctx.author.mention, embed=embed)
      await confirmation.add_reaction('✅')
      await confirmation.add_reaction('❌')
      try:
        reaction, user = await self.client.wait_for('reaction_add', timeout=20, 
          check=lambda r, u: u == ctx.author and r.message.channel == ctx.channel and str(r.emoji) in ['✅', '❌'])
      except asyncio.TimeoutError:
        embed = discord.Embed(title="Confirmation",
        description="You took too long to answer the question; not deleting it!",
        color=discord.Color.red(),
        timestamp=ctx.message.created_at)
        return await confirmation.edit(content=ctx.author.mention, embed=embed)
      else:
        if str(reaction.emoji) == '✅':
          embed.description = f"**Ticket-Channel {ctx.channel.mention} is being deleted...**"
          await confirmation.edit(content=ctx.author.mention, embed=embed)
          await asyncio.sleep(3)
          await channel.delete()
          await self.remove_ticket_channel(user_channel[0])
        else:
          embed.description = "Not deleting it!"
          await confirmation.edit(content='', embed=embed)
    else:
      await ctx.send(f"**What do you think that you are doing? You cannot delete this channel, {ctx.author.mention}!**")


  async def open_ticket(self, member, guild) -> None:
    if channel_id := await self.has_ticket_channel(member.id):
      channel = self.client.get_channel(channel_id)
      embed = discord.Embed(
        title="Error!", 
        description=f"**You already have an open channel! {channel.mention}**", color=discord.Color.red())
      return await member.send(embed=embed)

    counter = await self.get_ticket_number()

    # Gets the staff role
    staff = discord.utils.get(guild.roles, id=int(getenv('STAFF_ROLE_ID')))

    # Creates the Ticket channel
    case_cat = discord.utils.get(guild.categories, id=self.ticket_category_id)
    overwrites = {guild.default_role: discord.PermissionOverwrite(
      read_messages=False, send_messages=False, view_channel=False), 
    member: discord.PermissionOverwrite(
      read_messages=True, send_messages=True, view_channel=True),
    staff: discord.PermissionOverwrite(
      read_messages=True, send_messages=True, view_channel=True)
    }
    the_channel = await guild.create_text_channel(name=f"ticket-{counter}", category=case_cat, overwrites=overwrites)

    # Sends the DM embed
    created_embed = discord.Embed(
      title=f"Ticket channel created!", 
      description=f"Please, go to {the_channel.mention}!", 
      color=discord.Color.green()
    )
    await member.send(embed=created_embed)
    await self.insert_ticket_channel(member.id, the_channel.id)
    await self.increase_ticket_number()

    # Sends the server embed
    embed = discord.Embed(
      title=f"Ticket opened!", 
      description=f"Please, explain what's the problem or the situation.", 
      color=discord.Color.green()
    )
    await the_channel.send(content=f"{member.mention}, {staff.mention}", embed=embed)

 
  async def get_ticket_number(self) -> int:
    '''
    Gets the current ticket counting number.
    '''
    mycursor, db = await self.database()
    await mycursor.execute(f"SELECT * FROM TicketCounter")
    counter = await mycursor.fetchall()
    await mycursor.close()
    if len(counter) > 0:
      return counter[0][0]
    else:
      return 0

  async def get_ticket_channel(self, channel_id: int) -> Union[List[int], bool]:
    '''
    Gets a ticket channel with the given channel ID.
    '''
    mycursor, db = await self.database()
    await mycursor.execute("SELECT * FROM Ticket WHERE channel_id = %s", (channel_id,))
    the_channel = await mycursor.fetchall()
    await mycursor.close()
    if the_channel:
      return the_channel[0]
    else:
      return False

  async def increase_ticket_number(self) -> None:
    '''
    Increases the ticket counting number.
    '''
    mycursor, db = await self.database()
    await mycursor.execute("UPDATE TicketCounter SET counter = counter + 1")
    await db.commit()
    await mycursor.close()

  async def insert_ticket_channel(self, member_id: int, channel_id: int) -> None:
    '''
    Insert the ticket channel ID into the database.
    '''
    mycursor, db = await self.database()
    await mycursor.execute("INSERT INTO Ticket (member_id, channel_id) VALUES (%s, %s)", (member_id, channel_id))
    await db.commit()
    await mycursor.close()

  async def remove_ticket_channel(self, member_id: int) -> None:
    '''
    Removes a ticket channel from the system.
    '''
    mycursor, db = await self.database()
    await mycursor.execute("DELETE FROM Ticket WHERE member_id = %s", (member_id,))
    await db.commit()
    await mycursor.close()


  async def has_ticket_channel(self, member_id: int) -> Union[int, bool]:
    '''
    Checks whether the member has an open ticket channel.
    '''
    mycursor, db = await self.database()
    await mycursor.execute("SELECT * FROM Ticket WHERE member_id = %s", (member_id,))
    member_info = await mycursor.fetchall()
    await mycursor.close()
    if member_info:
      return member_info[0][1]
    else:
      return False

  async def database(self) -> Any:
    '''
    Database connection.
    '''

    pool = await aiomysql.create_pool(
      host=getenv('DB_HOST'), 
      user=getenv('DB_USER'), 
      password=getenv('DB_PASSWORD'), 
      db=getenv('DB_NAME'), 
      loop=self.loop
      )

    db = await pool.acquire()
    mycursor = await db.cursor()
    return mycursor, db


  # Create, drop, reset methods for the Tickets table.

  @commands.command(hidden=True)
  @commands.has_permissions(administrator=True)
  async def create_ticket_table(self, ctx) -> None:
    '''
    Creates the Ticket table.
    '''

    if await self.ticket_table_exists():
      return await ctx.send("**Table __Ticket__ already exists!**")

    mycursor, db = await self.database()
    await mycursor.execute("CREATE TABLE Ticket (member_id BIGINT NOT NULL, channel_id BIGINT NOT NULL)")
    await db.commit()
    await mycursor.close()
    await ctx.send("**Created __Ticket__ table!**")

  @commands.command(hidden=True)
  @commands.has_permissions(administrator=True)
  async def drop_ticket_table(self, ctx) -> None:
    '''
    Drops the Ticket table.
    '''
    if not await self.ticket_table_exists():
      return await ctx.send("**Table __Ticket__ doesn't exist!**")

    mycursor, db = await self.database()
    await mycursor.execute("DROP TABLE Ticket")
    await db.commit()
    await mycursor.close()
    await ctx.send("**Dropped __Ticket__ table!**")

  @commands.command(hidden=True)
  @commands.has_permissions(administrator=True)
  async def reset_ticket_table(self, ctx) -> None:
    '''
    Resets the Ticket table.
    '''
    if not await self.ticket_table_exists():
      return await ctx.send("**Table __Ticket__ doesn't exist yet!**")

    mycursor, db = await self.database()
    await mycursor.execute("DELETE FROM Ticket")
    await db.commit()
    await mycursor.close()
    await ctx.send("**Reset __Ticket__ table!**")

  async def ticket_table_exists(self) -> bool:
    '''
    Checks whether the Ticket table exists.
    '''

    mycursor, db = await self.database()
    await mycursor.execute(f"SHOW TABLE STATUS LIKE 'Ticket'")
    table_info = await mycursor.fetchall()
    await mycursor.close()
    if len(table_info) == 0:
      return False
    else:
      return True

  # Create, drop, reset methods for the TicketCounter table.

  @commands.command(hidden=True)
  @commands.has_permissions(administrator=True)
  async def create_ticket_counter_table(self, ctx):
    '''
    Creates the TicketCounter table.
    '''
    if await self.ticket_counter_table_exists():
      return await ctx.send("**Table __TicketCounter__ already exists!**")

    mycursor, db = await self.database()
    await mycursor.execute("CREATE TABLE TicketCounter (counter BIGINT DEFAULT 0)")
    await mycursor.execute("INSERT INTO TicketCounter (counter) VALUES (0)")
    await db.commit()
    await mycursor.close()
    await ctx.send("**Created __TicketCounter__ table!**")

  @commands.command(hidden=True)
  @commands.has_permissions(administrator=True)
  async def drop_ticket_counter_table(self, ctx):
    '''
    Drops the TicketCounter table.
    '''
    if not await self.ticket_counter_table_exists():
      return await ctx.send("**Table __TicketCounter__ doesn't exist!**")

    mycursor, db = await self.database()
    await mycursor.execute("DROP TABLE TicketCounter")
    await db.commit()
    await mycursor.close()
    return await ctx.send("**Dropped __TicketCounter__ table!**")

  @commands.command(hidden=True)
  @commands.has_permissions(administrator=True)
  async def reset_ticket_counter_table(self, ctx):
    '''
    Resets the TicketCounter table.
    '''
    if not await self.ticket_counter_table_exists():
      return await ctx.send("**Table __TicketCounter__ doesn't exist yet!**")

    mycursor, db = await self.database()
    await mycursor.execute("DELETE FROM TicketCounter")
    await mycursor.execute("INSERT INTO TicketCounter (counter) VALUES (0)")
    await db.commit()
    await mycursor.close()
    return await ctx.send("**Reset __TicketCounter__ table!**")

  async def ticket_counter_table_exists(self) -> bool:
    '''
    Checks whether the TicketCounter table exists.
    '''
    mycursor, db = await self.database()
    await mycursor.execute(f"SHOW TABLE STATUS LIKE 'TicketCounter'")
    table_info = await mycursor.fetchall()
    await mycursor.close()
    if len(table_info) == 0:
      return False
    else:
      return True 


"""
b!create_ticket_table
b!create_ticket_counter_table
"""

def setup(client):
  client.add_cog(Ticket(client))