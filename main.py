import discord
import json
import os
import asyncio
from discord.ext import commands

from hypixelapi import *

intents = discord.Intents.default()
intents.members = True
client = commands.Bot(command_prefix='.', intents=intents)

hypixel_api = None

settings = {
    "linked": {},
    "discord_key": "insert your discord bot key here",
    "hypixel_key": "insert your hypixel api key here",
}


async def saveLinked():
    with open("settings.json", "w+") as settings_file:
        json.dump(settings, settings_file, indent=4, sort_keys=True)


async def loadLinked():
    global settings
    if os.path.exists("settings.json"):
        with open("settings.json", "r") as settings_file:
            settings = json.load(settings_file)

    if settings["discord_key"] == "insert your discord bot key here":
        print("Insert discord_key into settings.json")
        return False

    if settings["hypixel_key"] == "insert your hypixel api key here":
        print("Insert hypixel_key into settings.json")
        return False

    await saveLinked()

    return True


async def getRoleByName(guild: discord.Guild, role_name):
    for role in guild.roles:
        if role.name == role_name:
            return role


@client.event
async def on_ready():
    print("Bot has started")


async def updateMember(ctx, member):
    try:
        player = await hypixel_api.getPlayer(member.display_name.split(" ")[0])
        rank_name = "NON"

        if player.rank == HypixelRank.VIP:
            rank_name = "VIP"
        elif player.rank == HypixelRank.VIP_PLUS:
            rank_name = "VIP+"
        elif player.rank == HypixelRank.MVP:
            rank_name = "MVP"
        elif player.rank == HypixelRank.MVP_PLUS or player.rank == HypixelRank.MVP_PLUS_PLUS:
            rank_name = "MVP+"

        for role_name in ["VIP", "VIP+", "MVP", "MVP+", "MVP++"]:
            await member.remove_roles(await getRoleByName(ctx.guild, role_name))

        if rank_name != "NON":
            await member.add_roles(await getRoleByName(ctx.guild, rank_name))

        if player.rank == HypixelRank.MVP_PLUS_PLUS:
            await member.add_roles(await getRoleByName(ctx.guild, "MVP++"))

        await member.edit(nick=f"{player.username} [{player.network_level}]")

        await ctx.send(f"Posodobil {player.username} level na {player.network_level} in rank {rank_name}"
                       f"{' in MVP++' if player.rank == HypixelRank.MVP_PLUS_PLUS else ''}")

    except HypixelApiError as error:
        await ctx.send(f"Napaka: {error}")


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

    try:
        player = await hypixel_api.getPlayer(minecraft_name)
        if player.discord is None:
            await ctx.send(f"{minecraft_name} nima registriranega discorda na hypixlu!")
        elif player.discord != f"{target_user.name}#{target_user.discriminator}":
            await ctx.send("Discorda se na ujemata!")
        else:
            settings["linked"][target_user.id] = player.uuid

            with open("settings.json", "w+") as settings_file:
                json.dump(settings, settings_file, indent=4)

            for role in ctx.guild.roles:
                if role.name == "Povezan":
                    await target_user.add_roles(role)

            await ctx.send("Povezava uspesna!")

    except HypixelApiError as error:
        await ctx.send(f"Napaka: {error}")


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
    if asyncio.get_event_loop().run_until_complete(loadLinked()):
        hypixel_api = HypixelApi(settings["hypixel_key"])
        client.run(settings["discord_key"])
    else:
        print("Shutdown")
