import discord
import asyncio
import time
import simplejson.errors
from mojang import MojangAPI
from discord.ext import commands

from settings import *
from hypixel_api import *


class StopAction(Enum):
    NONE = auto()
    SHUTDOWN = auto()
    RESTART = auto()
    UPDATE = auto()


# read & set config from settings.py
directory_path = os.getcwd()
with open(f"{directory_path}/settings.json") as f:
    json_config_data = json.load(f)["config"]
logging_channel = int(json_config_data["logging_channel_id"])  # int
verify_channel = int(json_config_data["verify_channel_id"])
bot_channels_id = json_config_data["bot_channels"]  # list
officer_role = int(json_config_data["officer_role_id"])  # int
hypixel_guild_id = str(json_config_data["hypixel_guild_id"])  # str
master_role_id = str(json_config_data["admin_role_id"])
bot_channels = []
count = 1
for item in json_config_data["bot_channels"]:
    bot_channels.append(int(json_config_data["bot_channels"][f"{count}"]))
    count += 1


def is_veteran(name):
    with open(f"{directory_path}/settings.json") as f:
        json_data = json.load(f)
    api_key = json_data["hypixel_key"]
    guild_id = str(json_data["config"]["hypixel_guild_id"])
    uuid = name_to_uuid(name)
    if uuid == "Error":
        return
    guild = requests.get("https://api.hypixel.net/guild?key=" + api_key + "&id=" + str(guild_id)).json()
    member_id = 0
    g_exp = []
    for i in range(len(guild['guild']['members'])):
        total = 0
        if guild['guild']['members'][i]["uuid"] == uuid:
            for x in range(7):
                f = list(guild['guild']['members'][i]['expHistory'].values())
                total += f[x]
            g_exp.append(total)
            member_id += i
    if int(g_exp[0]) >= 100000:
        if guild['guild']['members'][member_id]['rank'] == "Member":
            return 1
        else:
            return 2
    else:
        if guild['guild']['members'][member_id]['rank'] == "Veteran":
            return 3
        else:
            return 4


def name_to_uuid(name):
    try:
        return MojangAPI.get_uuid(name)
    except simplejson.errors.JSONDecodeError:
        return "Error"


def channel_suitable_for_commands(channel_id):
    if channel_id in bot_channels:
        return True


async def get_role_by_name(guild: discord.Guild, role_name):
    for role in guild.roles:
        if role.name == role_name:
            return role


async def is_officer(user):
    for role in user.roles:
        if role.id == officer_role:
            return True
    return False


async def member_has_role(member, role_name):
    for role in member.roles:
        if role.name == role_name:
            return True
    return False


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
        intents = discord.Intents.default()
        intents.members = True
        super().__init__(command_prefix=".", intents=intents,
                         activity=discord.Activity(type=discord.ActivityType.listening, name=".help"),
                         status=discord.Status.online)
        self.settings = Settings()
        self.hypixel_api = HypixelApi()
        self.addCommands()
        self.stop_action = StopAction.NONE
        self.channel_shutdown_id = channel_shutdown_id
        asyncio.set_event_loop(asyncio.new_event_loop())
        self.help_command = MyHelp()

    async def on_ready(self):
        print("Bot has started")
        if self.channel_shutdown_id:
            await self.get_channel(self.channel_shutdown_id).send("Bot has started")

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
        # update self or @user  Won't work if user doesn't have "Member" role
        @self.command(help="Posodobi rank in level.", pass_context=True, aliases=["u"])
        async def update(ctx: discord.ext.commands.context.Context, member: discord.Member = None):
            if not channel_suitable_for_commands(ctx.channel.id):
                return

            if member is None:
                member = ctx.author

            if member.id != ctx.author.id and not await is_officer(ctx.author):
                await ctx.send(f"Nimaš dovoljenja da posodabljaš druge uporabnike.")
                return

            display_name = member.display_name

            await self.update_member(ctx, display_name, member)

        # updates all users with "Member" role
        @self.command(pass_context=True)
        @commands.has_permissions(administrator=True)
        async def updateall(ctx: discord.ext.commands.context.Context):
            log_channel = self.get_channel(logging_channel)
            await log_channel.send("**Updateall started**")
            s = time.time()
            if not channel_suitable_for_commands(ctx.channel.id):
                return
            for member in ctx.guild.members:
                try:
                    await self.update_member(ctx, member.display_name, member)
                except Exception as exception:
                    await ctx.send(f"Python exception occurred for user {member.display_name}")
                    print(exception)
            await ctx.send(f"Updated all linked players!")
            await log_channel.send(f"**Updateall ended** *Porabil: {time.time() - s}*")

        # verify
        @self.command(help="Preveri se", pass_context=True, aliases=["p"])
        @commands.has_any_role(officer_role, "Nepreverjeni")
        async def preveri(ctx: discord.ext.commands.context.Context, minecraft_name, member: discord.Member = None):
            log_channel = self.get_channel(logging_channel)
            member_role = await get_role_by_name(ctx.guild, "Member")
            nepreverjeni_role = await get_role_by_name(ctx.guild, "Nepreverjeni")

            if ctx.channel.id != verify_channel:
                return

            if member is None:
                member = ctx.author
            if nepreverjeni_role not in member.roles:
                await ctx.send("Preveriš lahko samo uporabnike, ki niso preverjeni.")
                return

            try:
                uuid = name_to_uuid(minecraft_name)
                # if player doesn't exist
                if uuid == "Error":
                    await ctx.send(f"`{minecraft_name}` ne obstaja.")
                    return
                update_name = f"{minecraft_name} [0]"

                player = await self.hypixel_api.getPlayerByUUID(uuid)

                if player.discord is None:
                    # if player discord doesn't exist
                    if await is_officer(ctx.author):
                        await ctx.send(f"Preveril `{member}` kot `{minecraft_name}`!")
                        await member.add_roles(member_role)
                        await member.remove_roles(nepreverjeni_role)
                        await log_channel.send(f"**Preveril** `{member}` kot `{minecraft_name}`!")
                        await self.update_member(ctx, update_name, member)
                        return
                    else:
                        await ctx.send(f"`{minecraft_name}` nima registriranega discorda na Hypixlu. Počakaj na "
                                       f"<@&{officer_role}> da te preveri!")
                        return
                    # if player discord doesn't match
                elif player.discord != f"{member.name}#{member.discriminator}":
                    if await is_officer(ctx.author):
                        await ctx.send(f"Preveril `{member}` kot `{minecraft_name}`!")
                        await log_channel.send(f"**Preveril** `{member}` kot `{minecraft_name}`!")
                        await member.add_roles(member_role)
                        await member.remove_roles(nepreverjeni_role)
                        await self.update_member(ctx, update_name, member)
                        return
                    else:
                        await ctx.send(f"Tvoj discord se ne ujema počakaj na <@&{officer_role}>")
                        return
                    # if player discord matches
                elif player.discord == f"{member.name}#{member.discriminator}":
                    await ctx.send(f"Preveril `{member}` kot `{minecraft_name}`!")
                    await log_channel.send(f"**Preveril** `{member}` kot `{minecraft_name}`!")
                    await member.add_roles(member_role)
                    await member.remove_roles(nepreverjeni_role)
                    await self.update_member(ctx, update_name, member)

            except HypixelApiError as error:
                await ctx.send(f"Napaka: {error}")

        @self.command(help="Preimenuje osebo.", pass_context=True)
        @commands.has_role(officer_role)
        async def rename(ctx: discord.ext.commands.context.Context, minecraft_name, member: discord.Member = None):
            if not channel_suitable_for_commands(ctx.channel.id):
                return

            if member is None:
                member = ctx.author

            display_name = f"{minecraft_name} [0]"

            await self.update_member(ctx, display_name, member)

        @self.command(help="Počisti #preveri-se", pass_context=True, name="clear", aliases=["c"])
        @commands.has_role(officer_role)
        async def clear(ctx: discord.ext.commands.context.Context):
            if ctx.channel.id != verify_channel:
                return
            await ctx.message.delete()
            await ctx.channel.purge(limit=100, check=lambda msg: not msg.pinned)
            await ctx.send(f'Počistil #preveri-se', delete_after=5)

        @self.command(pass_context=True)
        @commands.has_permissions(administrator=True)
        async def shutdown(ctx: discord.ext.commands.context.Context):
            if not channel_suitable_for_commands(ctx.channel.id):
                return
            log_channel = self.get_channel(logging_channel)
            self.stop_action = StopAction.SHUTDOWN
            self.channel_shutdown_id = ctx.channel.id
            await ctx.send("Shutting down")
            await log_channel.send("Shutting down!")
            await ctx.bot.close()

        @self.command(pass_context=True)
        @commands.has_permissions(administrator=True)
        async def restart(ctx: discord.ext.commands.context.Context):
            log_channel = self.get_channel(logging_channel)
            if not channel_suitable_for_commands(ctx.channel.id):
                return
            self.stop_action = StopAction.RESTART
            self.channel_shutdown_id = ctx.channel.id
            await ctx.send("Restarting")
            await log_channel.send("Restarting")
            await ctx.bot.close()

    # function to update members   Won't work if user doesn't have "Member" role
    async def update_member(self, ctx, display_name, member):
        member_role = discord.utils.find(lambda r: r.name == 'Member', ctx.message.guild.roles)
        guild_role = discord.utils.find(lambda r: r.name == 'Guild Member', ctx.message.guild.roles)
        veteran_role = discord.utils.find(lambda r: r.name == 'Veteran', ctx.message.guild.roles)

        discord_nick = str(display_name)
        name_split = discord_nick.split()
        name = name_split[0]
        uuid = name_to_uuid(name)
        log_channel = self.get_channel(logging_channel)
        try:
            # check if user has member role
            if member_role not in member.roles:
                return
            # if name doesn't exist unverifyes user
            if uuid == "Error":
                await log_channel.send(f"`{name}` ne obstaja. Od-preveril `{member}`")
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
                embed.add_field(name="Kako se lahko spet preverim?", value=f"Sledi navodilom\nv <#{verify_channel}>",
                                inline=True)
                embed.set_footer(text="-Hypixel Slovenija ekipa")
                await dm.send(embed=embed)
                return
            # check & edit rank roles, nick and guild member role
            player = await self.hypixel_api.getPlayerByUUID(uuid)
            guild = await self.hypixel_api.getGuildByUUID(uuid)
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
                await member.remove_roles(await get_role_by_name(ctx.guild, role_name))

            if rank_name != "NON":
                await member.add_roles(await get_role_by_name(ctx.guild, rank_name))

            if player.rank == HypixelRank.MVP_PLUS_PLUS:
                await member.add_roles(await get_role_by_name(ctx.guild, "MVP++"))
            # check if member is in guild (check users without "Guild Member" role)
            if guild is not None and guild.guild_id == hypixel_guild_id:
                veteran_num = is_veteran(name)
                if guild_role not in member.roles:
                    await member.add_roles(await get_role_by_name(ctx.guild, "Guild Member"))
                    await log_channel.send(f"Dodal `Guild Member` `{player.username}`.")
                    await ctx.send(f"Dodal `Guild Member` `{player.username}`.")

                if veteran_role in member.roles:
                    if veteran_num in {3, 4}:
                        await member.remove_roles(await get_role_by_name(ctx.guild, "Veteran"))
                        await ctx.send(f"Odstranil `Veteran` od `{player.username}`.")
                        if veteran_num == 3:
                            await log_channel.send(
                                f"Odstranil `Veteran` od `{player.username}`. <@&{master_role_id}> ostrani mu ga na "
                                f"Hypixlu.")
                        if veteran_num == 4:
                            await log_channel.send(
                                f"Odstranil `Veteran` od `{player.username}`. Že ima Member ali višje na Hypixlu.")

                elif veteran_role not in member.roles and veteran_num in {1, 2}:
                    await member.add_roles(await get_role_by_name(ctx.guild, "Veteran"))
                    await ctx.send(f"Dodal `Veteran` `{player.username}`.")
                    if veteran_num == 1:
                        await log_channel.send(
                            f"Dodal `Veteran` `{player.username}`. <@&{master_role_id}> dodaj mu ga na Hypixlu.")
                    elif veteran_num == 2:
                        await log_channel.send(
                            f"Dodal `Veteran` `{player.username}`. Že ima Veteran ali višje na Hypixlu.")

            # check if someone with guild member role isn't in guild then remove all non moderator guild roles
            if guild_role in member.roles and guild is None or (
                    guild is not None and guild.guild_id != hypixel_guild_id):
                await member.remove_roles(await get_role_by_name(ctx.guild, "Guild Member"),
                                          await get_role_by_name(ctx.guild, "Veteran"),
                                          await get_role_by_name(ctx.guild, "Professional"))
                await log_channel.send(f"Odstranil use Guild role od `{player.username}`.")
                await ctx.send(f"Odstranil use Guild role od `{player.username}`.")

            await member.edit(nick=f"{player.username} [{player.network_level}]")

            await ctx.send(f"Posodobil `{player.username}` level na `{player.network_level}` in rank"
                           f" `{rank_name}`"
                           f"{' in `MVP++`' if player.rank == HypixelRank.MVP_PLUS_PLUS else ''}")

            await log_channel.send(f"Posodobil `{player.username}` level na `{player.network_level}` in rank"
                                   f" `{rank_name}`"
                                   f"{' in `MVP++`' if player.rank == HypixelRank.MVP_PLUS_PLUS else ''}")

        except HypixelApiError as error:
            # Un-Verify user if Minecraft account exists but never logged on Hypixel
            if str(error) == "This player does not exist":
                await log_channel.send(f"`{name}` ne obstaja(nikoli prijavljen na Hypixel). Od-preveril `{member}`")
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
                                                                           f"\nPotem pa sledi navodilom v <#{verify_channel}>",
                                inline=True)
                embed.set_footer(text="-Hypixel Slovenija ekipa")
                await dm.send(embed=embed)
            # Print error
            else:
                await ctx.send(f"Napaka: {error}")

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

        await ctx.send(message, delete_after=5)
        await ctx.message.delete(delay=5)
