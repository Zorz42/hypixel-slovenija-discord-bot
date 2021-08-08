import discord
import asyncio
from discord.ext import commands

from settings import *
from hypixel_api import *


class StopAction(Enum):
    NONE = auto()
    SHUTDOWN = auto()
    RESTART = auto()
    UPDATE = auto()


def channelSuitableForCommands(channel):
    return "bot" in channel.name


async def getRoleByName(guild: discord.Guild, role_name):
    for role in guild.roles:
        if role.name == role_name:
            return role


async def isOfficer(user):
    for role in user.roles:
        if role.name == "Officer":
            return True
    return False


async def memberHasRole(member, role_name):
    for role in member.roles:
        if role.name == role_name:
            return True
    return False


class HypixelSloveniaDiscordBot(commands.Bot):
    def __init__(self):
        intents = discord.Intents.default()
        intents.members = True
        super().__init__(command_prefix=".", intents=intents)
        self.settings = Settings()
        self.hypixel_api = HypixelApi()
        self.addCommands()
        self.stop_action = StopAction.NONE
        asyncio.set_event_loop(asyncio.new_event_loop())

    async def on_ready(self):
        print("Bot has started")

    async def init(self):
        if await self.settings.load("settings.json"):
            await self.hypixel_api.setKey(await self.settings.getHypixelKey())
            return True
        else:
            return False

    def runBot(self):
        if asyncio.get_event_loop().run_until_complete(self.init()):
            self.run(self.settings.getDiscordKey())
        else:
            self.stop_action = StopAction.SHUTDOWN

    def addCommands(self):
        @self.command(pass_context=True, aliases=["u"])
        async def update(ctx: discord.ext.commands.context.Context, member: discord.Member = None):
            if not channelSuitableForCommands(ctx.channel):
                return

            if member is None:
                member = ctx.author

            if member.id != ctx.author.id and not await isOfficer(ctx.author):
                await ctx.send(f"Nimas dovoljenja da updatas ostale")
                return

            await self.updateMember(ctx, member)

        @self.command(pass_context=True, aliases=["ua"])
        @commands.has_permissions(administrator=True)
        async def updateall(ctx: discord.ext.commands.context.Context):
            if not channelSuitableForCommands(ctx.channel):
                return

            for member in ctx.guild.members:
                if memberHasRole(member, "Linked"):
                    try:
                        await self.updateMember(ctx, member)
                    except Exception as exception:
                        await ctx.send(f"Python exception occurred for user {member.display_name}")
                        print(exception)
            await ctx.send(f"Updated all linked players!")

        @self.command(pass_context=True)
        async def p(ctx: discord.ext.commands.context.Context, minecraft_name, member: discord.Member = None):
            if not channelSuitableForCommands(ctx.channel):
                return

            try:
                if member is None:
                    member = ctx.author

                player = await self.hypixel_api.getPlayerByName(minecraft_name)

                if player.discord is None:
                    if await isOfficer(ctx.author):
                        await ctx.send(f"{minecraft_name} nima registriranega discorda na hypixlu vendar se bo se vseeno povezal")
                    else:
                        await ctx.send(f"{minecraft_name} nima registriranega discorda na hypixlu!")
                        return
                elif player.discord != f"{member.name}#{member.discriminator}":
                    await ctx.send("Discorda se na ujemata!")
                    return

                asyncio.ensure_future(self.settings.linkUser(member.id, player.uuid))
                await member.add_roles(await getRoleByName(ctx.guild, "Povezan"))
                await ctx.send("Povezava uspesna!")

            except HypixelApiError as error:
                await ctx.send(f"Napaka: {error}")

        @self.command(pass_context=True)
        @commands.has_permissions(administrator=True)
        async def shutdown(ctx: discord.ext.commands.context.Context):
            if not channelSuitableForCommands(ctx.channel):
                return
            self.stop_action = StopAction.SHUTDOWN
            await ctx.send("Shutting down")
            await ctx.bot.close()

        @self.command(pass_context=True)
        @commands.has_permissions(administrator=True)
        async def restart(ctx: discord.ext.commands.context.Context):
            if not channelSuitableForCommands(ctx.channel):
                return
            self.stop_action = StopAction.RESTART
            await ctx.send("Restarting")
            await ctx.bot.close()

    async def close(self):
        await super(HypixelSloveniaDiscordBot, self).close()
        self.stop_action = StopAction.SHUTDOWN

    async def updateMember(self, ctx, member):
        try:
            if not await self.settings.isUserLinked(member.id):
                await ctx.send("Ta uporabnik ni povezan z minecraft racunom")
                return
            uuid = await self.settings.getLinkedUser(member.id)
            player = await self.hypixel_api.getPlayerByUUID(uuid)
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
