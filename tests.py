b!eval

import aiomysql
from mysqldb import the_database


mycursor, db = await the_database()
await mycursor.execute("SELECT user_id, user_lvl FROM MemberStatus")
members = await mycursor.fetchall()
await mycursor.close()

sticky_roles = {
    3: 732910493257302076,
    10: 732916589262798898,
    15: 733022810934607943,
    25: 733022972675227694,
    35: 740186380445024336,
    50: 770113783074783232,
    75: 740186445784023071,
    85: 740186469649350696,
    100: 740186498498035793
}

sticky_roles = {
    role_lvl:role for role_lvl, role_id in sticky_roles.items() 
    if (role := discord.utils.get(ctx.guild.roles, id=role_id))
}

await ctx.send(f"**Updating `{len(members)}` member role...**")
counter = 0
async with ctx.typing():

    for member_db in members:

        if not (member := discord.utils.get(ctx.guild.members, id=member_db[0])):
            continue

        for role_lvl, role in sticky_roles.items():
            if member_db[1] >= role_lvl:
                try:
                    await member.add_roles(role)
                except:
                    pass
                else:
                    counter += 1

await ctx.send(f"**Successfully added {counter} lvl roles!**")
