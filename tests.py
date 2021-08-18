b!eval

import aiomysql
from mysqldb import the_database


mycursor, db = await the_database()
await mycursor.execute("SELECT user_id, user_lvl FROM MemberStatus")
members = await mycursor.fetchall()
await mycursor.close()

sticky_roles = {
    2: 862742944729268234,
    # 3: 732910493257302076,
    5: 862742944243253279,
    # 10: 732916589262798898,
    # 15: 733022810934607943,
    # 25: 733022972675227694,
    # 35: 740186380445024336,
    # 50: 770113783074783232,
    # 75: 740186445784023071,
    # 85: 740186469649350696,
    # 100: 740186498498035793
}

sticky_roles = {
    role_lvl:role for role_lvl, role_id in sticky_roles.items() 
    if (role := discord.utils.get(ctx.guild.roles, id=role_id))
}

await ctx.send(f"**Updating `{len(members)}` member role...**")
counter = 0
failed = 0
async with ctx.typing():

    for member_db in members:

        if not (member := discord.utils.get(ctx.guild.members, id=member_db[0])):
            continue

        for role_lvl, role in sticky_roles.items():
            if member_db[1] >= role_lvl:
                if role not in member.roles:
                    try:
                        await member.add_roles(role)
                    except:
                        failed += 1
                    else:
                        counter += 1

await ctx.send(f"**Successfully added {counter} lvl roles! Failed {failed} assignments!**")




b!eval
from mysqldb import the_database

member_role = discord.utils.get(ctx.guild.roles, id=726222316174049280)
members = [(m.id, member_role.id) for m.id in ctx.guild.members if member_role in m.roles]

try:
    mycursor, db = await the_database()
    await mycursor.executemany("INSERT IGNORE INTO ColorRoles (user_id, role_id) VALUES (%s, %s)", members)
    await db.commit()
except Exception as e:
    await ctx.send(f"error! {e}",)
else:
    await ctx.send(f"**Successful!**")
finally:
    await mycursor.close()