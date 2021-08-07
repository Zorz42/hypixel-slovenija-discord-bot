import math
import requests
import discord
import json
import os
from discord.ext import commands

intents = discord.Intents.default()
intents.members = True
client = commands.Bot(command_prefix='.', intents=intents)


async def getData(username: str):
    return requests.get(f"https://api.hypixel.net/player?key={settings['hypixel_key']}&name={username}").json()


async def getLevel(hypixel_data):
    network_experience = hypixel_data["player"]["networkExp"]
    network_level = (math.sqrt((2 * network_experience) + 30625) / 50) - 2.5
    return math.floor(network_level)


ranks = ["VIP", "VIP+", "MVP", "MVP+", "MVP++"]
roles = {}
rank_names = {
    "null": "NON",
    "VIP": "VIP",
    "VIP_PLUS": "VIP+",
    "MVP": "MVP",
    "MVP_PLUS": "MVP+",
}

settings = {
    "linked": {},
    "discord_key": "insert your discord bot key here",
    "hypixel_key": "insert your hypixel api key here",
}


def saveLinked():
    with open("settings.json", "w+") as settings_file:
        json.dump(settings, settings_file, indent=4, sort_keys=True)


def loadLinked():
    global settings
    if os.path.exists("settings.json"):
        with open("settings.json", "r") as settings_file:
            settings = json.load(settings_file)

    quit_ = False

    if settings["discord_key"] == "insert your discord bot key here":
        print("Insert discord_key into settings.json")
        quit_ = True

    if settings["hypixel_key"] == "insert your hypixel api key here":
        print("Insert hypixel_key into settings.json")
        quit_ = True

    with open("settings.json", "w+") as settings_file:
        json.dump(settings, settings_file, indent=4)

    if quit_:
        exit(0)


@client.event
async def on_ready():
    print("Bot has started")


async def updateMember(ctx, member):
    if roles == {}:
        for role in ctx.guild.roles:
            if role.name in ranks:
                roles[role.name] = role

    hypixel_data = await getData(member.display_name.split(" ")[0])
    if not hypixel_data["success"]:
        cause = hypixel_data["cause"]
        await ctx.send(f"Napaka: {cause}")
        return
    if hypixel_data["player"] is None:
        await ctx.send(f"Ta igralec ne obstaja!")
    username = hypixel_data["player"]["displayname"]

    level = await getLevel(hypixel_data)
    rank = "NON"
    try:
        rank = rank_names[hypixel_data["player"]["newPackageRank"]]
    except KeyError:
        pass
    for rank_name in ranks:
        await member.remove_roles(roles[rank_name])
    if rank != "NON":
        await member.add_roles(roles[rank])
    is_superstar = False
    try:
        if hypixel_data["player"]["monthlyPackageRank"] == "SUPERSTAR":
            await member.add_roles(roles["MVP++"])
            is_superstar = True
    except KeyError:
        pass
    await ctx.send(f"Posodobil {username} level na {level} in rank {rank}{' in MVP++' if is_superstar else ''}")
    await member.edit(nick=f"{username} [{level}]")


@client.command(pass_context=True, aliases=["u"])
async def update(ctx: discord.ext.commands.context.Context, name=None):
    if "bot" not in ctx.channel.name:
        return
    target_member = None
    if name is None:
        target_member = ctx.message.author
    elif name.startswith("<@!"):
        user_id = int(name[3:-1])
        for member in ctx.guild.members:
            if member.id == user_id:
                target_member = member
                break
    else:
        is_permitted = False
        author = ctx.message.author
        for role in author.roles:
            if role.name == "Officer":
                is_permitted = True
                break

        if not is_permitted:
            await ctx.send(f"No permission to update others")
            return

        for member in ctx.guild.members:
            if member.nick is not None:
                if member.nick.split(" ")[0].upper() == name.upper():
                    target_member = member
                    break

    if target_member is None:
        await ctx.send(f"Could not find that member")
    else:
        await updateMember(ctx, target_member)


@client.command(pass_context=True, aliases=["ua"])
@commands.has_permissions(administrator=True)
async def updateall(ctx: discord.ext.commands.context.Context):
    if "bot" not in ctx.channel.name:
        return
    for member in ctx.guild.members:
        for role in member.roles:
            if role.name == "Member":
                try:
                    await updateMember(ctx, member)
                except Exception as exception:
                    await ctx.send(f"Python exception occurred for user {member.display_name}")
                    print(exception)
    await ctx.send(f"Updated all members!")


@client.command(pass_context=True)
async def p(ctx: discord.ext.commands.context.Context, minecraft_name, user: discord.User = None):
    if "bot" not in ctx.channel.name:
        return

    target_user = ctx.author
    if user is not None:
        target_user = user

    hypixel_data = await getData(minecraft_name)
    if not hypixel_data["success"]:
        cause = hypixel_data["cause"]
        await ctx.send(f"Napaka: {cause}")
        return
    if hypixel_data["player"] is None:
        await ctx.send(f"Ta igralec ne obstaja!")

    try:
        discord_username = hypixel_data["player"]["socialMedia"]["links"]["DISCORD"]
    except KeyError or ValueError:
        await ctx.send(f"{minecraft_name} nima registriranega discorda na hypixlu!")
        return

    if discord_username != f"{target_user.name}#{target_user.discriminator}":
        await ctx.send("Discorda se na ujemata!")
        return

    settings["linked"][target_user.id] = hypixel_data["player"]["uuid"]

    with open("settings.json", "w+") as settings_file:
        json.dump(settings, settings_file, indent=4)

    for role in ctx.guild.roles:
        if role.name == "Povezan":
            await target_user.add_roles(role)

    await ctx.send("Povezava uspesna!")


@client.command(pass_context=True)
@commands.has_permissions(administrator=True)
async def shutdown(ctx: discord.ext.commands.context.Context):
    print("Shutdown")
    await ctx.send("Shutting down")
    await ctx.bot.close()


@client.command(pass_context=True)
@commands.has_permissions(administrator=True)
async def restart(ctx: discord.ext.commands.context.Context):
    print("Restart")
    await ctx.send("Restarting")
    await ctx.bot.close()


if __name__ == '__main__':
    loadLinked()
    client.run(settings["discord_key"])
