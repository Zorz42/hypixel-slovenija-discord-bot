import logging
import time

import discord
from discord import Member, Role
from discord.ext import commands
from discord.ext.commands import Context

from hypixel_api import *
from settings import *
from structure.hypixel_player import HypixelRank
from structure.misc import GuildDiscordSyncStatus
from util import Utils, get_role_by_name, name_to_uuid, remove_guild_roles, is_veteran, is_professional


class StopAction(Enum):
    NONE = auto()
    SHUTDOWN = auto()
    RESTART = auto()
    UPDATE = auto()


# TODO: fix fancy help
class MyHelp(commands.HelpCommand):
    def get_command_signature(self, command):
        return '%s%s %s' % (self.clean_prefix, command.qualified_name, command.signature)

    async def send_bot_help(self, mapping):
        embed = discord.Embed(title="Help", color=0xdcb824)
        for cog, commands in mapping.items():
            filtered = await self.filter_commands(commands, sort=True)
            command_signatures = [self.get_command_signature(c) for c in filtered]
            if command_signatures:
                cog_name = getattr(cog, "qualified_name", "Commands")
                embed.add_field(name=cog_name, value="\n".join(command_signatures), inline=False)

        channel = self.get_destination()
        await channel.send(embed=embed)


class HypixelSloveniaDiscordBot(commands.Bot):
    def __init__(self, channel_shutdown_id):
        self.log_channel = None
        intents = discord.Intents.default()
        intents.members = True
        intents.message_content = True
        super().__init__(command_prefix=".", intents=intents,
                         activity=discord.Activity(type=discord.ActivityType.listening, name=".help"),
                         status=discord.Status.online)
        logging.basicConfig(level=logging.DEBUG)
        self.settings = Settings()
        self.hypixel_api = HypixelApi()
        asyncio.get_event_loop().run_until_complete(self.init())
        self.utils = Utils(self.settings, self.hypixel_api)
        self.stop_action = StopAction.NONE
        self.channel_shutdown_id = channel_shutdown_id

        self.logging_channel_id = self.settings.get_discord_channel_id(DiscordChannel.LOGGING)
        self.verify_channel_id = self.settings.get_discord_channel_id(DiscordChannel.VERIFY)

        self.unverified_role_id = self.settings.get_discord_role_id(DiscordRole.UNVERIFIED)
        self.member_role_id = self.settings.get_discord_role_id(DiscordRole.MEMBER)
        self.guild_member_role_id = self.settings.get_discord_role_id(DiscordRole.GUILD_MEMBER)
        self.veteran_role_id = self.settings.get_discord_role_id(DiscordRole.VETERAN)
        self.professional_role_id = self.settings.get_discord_role_id(DiscordRole.PROFESSIONAL)
        self.officer_role_id = self.settings.get_discord_role_id(DiscordRole.OFFICER)
        self.admin_role_id = self.settings.get_discord_role_id(DiscordRole.ADMIN)

        self.hypixel_guild_id = self.settings.get_guild_id()

        self.bot_version = self.settings.get_bot_version()
        self.addCommands()
        asyncio.set_event_loop(asyncio.new_event_loop())

    async def on_ready(self):
        print("Bot has started")
        self.log_channel = self.get_channel(self.logging_channel_id)
        if self.channel_shutdown_id:
            await self.get_channel(self.channel_shutdown_id).send("Bot has started")

    async def init(self):
        if await self.settings.load("settings.json"):
            await self.hypixel_api.set_key(await self.settings.getHypixelKey())
            return True
        else:
            return False

    def runBot(self):
        if asyncio.get_event_loop().run_until_complete(self.init()):
            self.run(self.settings.getDiscordKey())
        else:
            self.stop_action = StopAction.SHUTDOWN

    def addCommands(self):
        # @self.command(pass_context=True)
        # @commands.is_owner()
        # async def test(ctx: Context, member: discord.Member = None):
        #     if not member:
        #         member = ctx.author
        #     msg = ""
        #     await ctx.send(msg)

        # update self or @user  Won't work if user doesn't have "Member" role
        @self.command(help="Posodobi rank in level.", pass_context=True, aliases=["u"])
        async def update(ctx: Context, member: discord.Member = None):
            if not self.utils.channel_suitable_for_commands(ctx.channel.id):
                return

            if member is None:
                member = ctx.author

            if member.id != ctx.author.id and not await self.utils.is_officer(ctx.author):
                await ctx.send(f"Nimaš dovoljenja da posodabljaš druge uporabnike.")
                return

            display_name = member.display_name

            await self.update_member(ctx, display_name, member)

        # updates all users with "Member" role
        @self.command(pass_context=True)
        @commands.has_permissions(administrator=True)
        async def updateall(ctx: Context):
            if not self.utils.channel_suitable_for_commands(ctx.channel.id):
                return
            await self.log_channel.send("**Updateall started**")
            start_time = time.time()
            for member in ctx.guild.members:
                try:
                    await self.update_member(ctx, member.display_name, member)
                except Exception as exception:
                    await ctx.send(f"Python exception occurred for user {member.display_name}. Error: {exception}")
            await ctx.send(f"Updated all linked players!")
            await self.log_channel.send(f"**Updateall ended** *Porabil: {time.time() - start_time}s*")

        # verify
        @self.command(help="Preveri se", pass_context=True, aliases=["p"])
        @commands.has_any_role(self.admin_role_id, self.officer_role_id, self.unverified_role_id)
        async def preveri(ctx: Context, minecraft_name, member: discord.Member = None):
            member_role = ctx.guild.get_role(self.member_role_id)
            unverified_role = ctx.guild.get_role(self.unverified_role_id)

            if ctx.channel.id != self.verify_channel_id:
                return

            if member is None:
                member = ctx.author
            if unverified_role not in member.roles:
                await ctx.send("Preveriš lahko samo uporabnike, ki niso preverjeni.")
                return

            try:
                uuid = name_to_uuid(minecraft_name)
                # if player doesn't exist
                if uuid == "Error":
                    await ctx.send(f"`{minecraft_name}` ne obstaja.")
                    return
                update_name = f"{minecraft_name} [0]"

                player = await self.hypixel_api.get_player_by_uuid(uuid)
                discriminator = f"#{member.discriminator}" if member.discriminator != "0" else ""
                is_linked = player.discord == member.name + discriminator
                if player.discord is None:
                    # if player discord doesn't exist
                    if await self.utils.is_officer(ctx.author):
                        await ctx.send(f"Preveril `{member}` kot `{minecraft_name}`!")
                        await member.add_roles(member_role)
                        await member.remove_roles(unverified_role)
                        await self.log_channel.send(f"**Preveril** `{member}` kot `{minecraft_name}`!")
                        await self.update_member(ctx, update_name, member)
                        return
                    else:
                        await ctx.send(f"`{minecraft_name}` nima registriranega discorda na Hypixlu. Počakaj na "
                                       f"<@&{self.officer_role_id}> da te preveri!")
                        return
                elif is_linked:
                    await ctx.send(f"Preveril `{member}` kot `{minecraft_name}`!")
                    await self.log_channel.send(f"**Preveril** `{member}` kot `{minecraft_name}`!")
                    await member.add_roles(member_role)
                    await member.remove_roles(unverified_role)
                    await self.update_member(ctx, update_name, member)
                else:
                    if await self.utils.is_officer(ctx.author):
                        await ctx.send(f"Preveril `{member}` kot `{minecraft_name}`!")
                        await self.log_channel.send(f"**Preveril** `{member}` kot `{minecraft_name}`!")
                        await member.add_roles(member_role)
                        await member.remove_roles(unverified_role)
                        await self.update_member(ctx, update_name, member)
                        return
                    else:
                        await ctx.send(f"Tvoj discord se ne ujema počakaj na <@&{self.officer_role_id}>")
                        return

            except HypixelApiError as error:
                await ctx.send(f"Napaka: {error}")

        @self.command(help="Preimenuje osebo.", pass_context=True)
        @commands.has_role(self.officer_role_id)
        async def rename(ctx: Context, minecraft_name, member: discord.Member = None):
            if not self.utils.channel_suitable_for_commands(ctx.channel.id):
                return

            if member is None:
                member = ctx.author

            display_name = f"{minecraft_name} [0]"

            await self.update_member(ctx, display_name, member)

        @self.command(help="Počisti #preveri-se", pass_context=True, name="clear", aliases=["c"])
        @commands.has_role(self.officer_role_id)
        async def clear(ctx: Context):
            if ctx.channel.id != self.verify_channel_id:
                return
            await ctx.message.delete()
            await ctx.channel.purge(limit=100, check=lambda msg: not msg.pinned)
            await ctx.send(f'Počistil #preveri-se', delete_after=5)

        @self.command(pass_context=True)
        @commands.has_permissions(administrator=True)
        async def shutdown(ctx: Context):
            if not self.utils.channel_suitable_for_commands(ctx.channel.id):
                return
            self.stop_action = StopAction.SHUTDOWN
            self.channel_shutdown_id = ctx.channel.id
            await ctx.send("Shutting down")
            await self.log_channel.send("Shutting down!")
            await ctx.bot.close()

        @self.command(pass_context=True)
        @commands.has_permissions(administrator=True)
        async def restart(ctx: Context):
            if not self.utils.channel_suitable_for_commands(ctx.channel.id):
                return
            self.stop_action = StopAction.RESTART
            self.channel_shutdown_id = ctx.channel.id
            await ctx.send("Restarting")
            await self.log_channel.send("Restarting")
            await ctx.bot.close()

        @self.command(pass_context=True)
        @commands.has_permissions(administrator=True)
        async def version(ctx: Context):
            if not self.utils.channel_suitable_for_commands(ctx.channel.id):
                return
            await ctx.send(f"Bot Version: `{self.bot_version}`")

    # function to update members   Won't work if user doesn't have "Member" role
    async def update_member(self, ctx: Context, discord_nick: str, member: Member):
        member_role = ctx.guild.get_role(self.member_role_id)
        member_is_owner = member.id == ctx.guild.owner_id

        name_split = discord_nick.split()
        name = name_split[0]
        uuid = name_to_uuid(name)
        try:
            # check if user has member role
            if member_role not in member.roles:
                return
            # if name doesn't exist unverifyes user
            if uuid == "Error":
                await self.log_channel.send(f"`{name}` ne obstaja. Od-preveril `{member}`")
                for role_name in ["VIP", "VIP+", "MVP", "MVP+", "MVP++", "Member", "Guild Member", "Veteran",
                                  "Professional"]:
                    await member.remove_roles(await get_role_by_name(ctx.guild, role_name))
                await member.add_roles(await get_role_by_name(ctx.guild, "Nepreverjeni"))
                await member.edit(nick="")
                dm = await member.create_dm()
                embed = discord.Embed(title="Bil si od-preverjen na Hypixel Slovenija", color=0x89ff00)
                embed.set_thumbnail(
                    url="https://cdn.discordapp.com/icons/794995068720119849/d4339c7041f4fe3b6473f0ab3ead56b1.webp?size=1024")
                embed.add_field(name="Zakaj?",
                                value="Očitno si si spremenil svoje Minecraft ime ali pa je prišlo do napake",
                                inline=True)
                embed.add_field(name="Kako se lahko spet preverim?", value=f"Sledi navodilom\nv <#{self.verify_channel_id}>",
                                inline=True)
                embed.set_footer(text="-Hypixel Slovenija ekipa")
                await dm.send(embed=embed)
                return

            # check & edit rank roles, nick and guild member role
            player = await self.hypixel_api.get_player_by_uuid(uuid)
            # TODO: Get rank roles form config
            for role_name in ["VIP", "VIP+", "MVP", "MVP+", "MVP++"]:
                await member.remove_roles(await get_role_by_name(ctx.guild, role_name))

            if player.rank.api_name:
                await member.add_roles(await get_role_by_name(ctx.guild, player.rank.display))

            if player.rank == HypixelRank.MVP_PLUS_PLUS:
                await member.add_roles(await get_role_by_name(ctx.guild, "MVP++"))

            await self.update_guild_roles(ctx, member, player)

            if not member_is_owner:
                await member.edit(nick=f"{player.username} [{player.network_level}]")
            else:
                await self.log_channel.send(f"Can't update nick {member.mention} is guild owner.")

            await ctx.send(f"Posodobil `{player.username}` level na `{player.network_level}` in rank"
                           f" `{player.rank.display}`"
                           f"{' in `MVP++`' if player.rank == HypixelRank.MVP_PLUS_PLUS else ''}")

            await self.log_channel.send(f"Posodobil `{player.username}` level na `{player.network_level}` in rank"
                                        f" `{player.rank.display}`"
                                        f"{' in `MVP++`' if player.rank == HypixelRank.MVP_PLUS_PLUS else ''}")

        except HypixelApiError as error:
            # Un-Verify user if Minecraft account exists but never logged on Hypixel
            if str(error) == "This player does not exist":
                await self.log_channel.send(f"`{name}` ne obstaja (nikoli se nisi prijavl na Hypixel). Od-preveril `{member}`")
                for role_name in ["VIP", "VIP+", "MVP", "MVP+", "MVP++", "Member", "Guild Member", "Veteran",
                                  "Professional"]:
                    await member.remove_roles(await get_role_by_name(ctx.guild, role_name))
                await member.add_roles(await get_role_by_name(ctx.guild, "Nepreverjeni"))
                await member.edit(nick="")
                dm = await member.create_dm()
                embed = discord.Embed(title="Bil si od-preverjen na Hypixel Slovenija", color=0x89ff00)
                embed.set_thumbnail(
                    url="https://cdn.discordapp.com/icons/794995068720119849/d4339c7041f4fe3b6473f0ab3ead56b1.webp"
                        "?size=1024")
                embed.add_field(name="Zakaj?",
                                value="Ker se še nikoli nisi povezal na Hypixel ali pa je prišlo do napake",
                                inline=True)
                embed.add_field(name="Kako se lahko spet preverim?", value=f"Poveši se na: `mc.hypixel.net`"
                                                                           f"\nPotem pa sledi navodilom v <#{self.verify_channel_id}>",
                                inline=True)
                embed.set_footer(text="-Hypixel Slovenija ekipa")
                await dm.send(embed=embed)
            # Print error
            else:
                await ctx.send(f"Napaka: {error}")

    async def update_guild_roles(self, ctx: Context, member: Member, player: HypixelPlayer):
        guild = await self.hypixel_api.get_guild_by_player_uuid(player.uuid)
        guild_member_role = ctx.guild.get_role(self.guild_member_role_id)
        veteran_role = ctx.guild.get_role(self.veteran_role_id)
        professional_role = ctx.guild.get_role(self.professional_role_id)

        if guild is None or guild.guild_id != self.hypixel_guild_id:
            await remove_guild_roles(ctx, self.log_channel, member)
            return

        veteran_status = await is_veteran(player.uuid, guild)
        professional_status = GuildDiscordSyncStatus.REMOVE_DISCORD

        if veteran_status.meets_requirements:
            professional_status = await is_professional(player, guild)

        if guild_member_role not in member.roles:
            await member.add_roles(guild_member_role)
            await self.log_channel.send(f"Dodal `Guild Member` {member.mention}.")
            await ctx.send(f"Dodal `Guild Member` {member.mention}`.")

        if veteran_role not in member.roles and veteran_status.meets_requirements:
            await member.add_roles(veteran_role)
            await ctx.send(f"Dodal `Veteran` {member.mention}.")
            await self.log_channel.send(f"Dodal `Veteran` {member.mention}.")
        if veteran_status.update_mc:
            await self.log_channel.send(
                f"Dodaj `Veteran` `{player.username}` na Hypixlu. <@&{self.admin_role_id}>")

        if professional_role not in member.roles and professional_status.meets_requirements:
            await member.add_roles(professional_role)
            await ctx.send(f"Dodal `Professional` {member.mention}.")
            await self.log_channel.send(f"Dodal `Professional` {member.mention}.")
        if professional_status.update_mc:
            await self.log_channel.send(
                f"Dodaj `Professional` `{player.username}` na Hypixlu. <@&{self.admin_role_id}>")

    # Error feedback
    @commands.Cog.listener()
    async def on_command_error(self, ctx: commands.Context, error: commands.CommandError):

        if isinstance(error, commands.CommandNotFound):
            return
        elif isinstance(error, commands.CommandOnCooldown):
            message = f"Ta ukaz lahko uporabiš vako minuto. Poiskusi ponovno po {round(error.retry_after, 1)} sekundah."
        elif isinstance(error, commands.MissingPermissions):
            message = "Nimaš dovoljenja za uporabo tega ukaza!"
        elif isinstance(error, commands.UserInputError):
            message = "Nisi napisal vseh argumentov ali pa so ti napačni"
        else:
            message = "Prišlo je do napake."

        await self.log_channel.send(f"Error {ctx.author}, {ctx.message.content}: {error}")
        await ctx.send(message, delete_after=5)
        await ctx.message.delete(delay=5)
