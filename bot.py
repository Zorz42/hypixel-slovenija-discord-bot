import discord
import asyncio
from discord.ext import commands, tasks
from datetime import datetime
import simplejson.errors

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
    gExp = []
    for i in range(len(guild['guild']['members'])):
        total = 0
        if guild['guild']['members'][i]["uuid"] == uuid:
            for x in range(7):
                f = list(guild['guild']['members'][i]['expHistory'].values())
                total += f[x]
            gExp.append(total)
            member_id += i
    if int(gExp[0]) >= 100000:
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
    url = f"https://api.mojang.com/users/profiles/minecraft/{name}"
    try:
        return requests.get(url).json()["id"]
    except simplejson.errors.JSONDecodeError:
        return "Error"


def channelSuitableForCommands(channel_id):
    if channel_id in bot_channels:
        return True


async def getRoleByName(guild: discord.Guild, role_name):
    for role in guild.roles:
        if role.name == role_name:
            return role


async def isOfficer(user):
    for role in user.roles:
        if role.id == officer_role:
            return True
    return False


async def memberHasRole(member, role_name):
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
            if not channelSuitableForCommands(ctx.channel.id):
                return

            if member is None:
                member = ctx.author

            if member.id != ctx.author.id and not await isOfficer(ctx.author):
                await ctx.send(f"Nimaš dovoljenja da posodabljaš druge uporabnike.")
                return

            display_name = member.display_name

            await self.updateMember(ctx, display_name, member)

        # updates all users with "Member" role
        @self.command(pass_context=True)
        @commands.has_permissions(administrator=True)
        async def updateall(ctx: discord.ext.commands.context.Context):
            log_channel = self.get_channel(logging_channel)
            await log_channel.send("**Updateall started**")
            if not channelSuitableForCommands(ctx.channel.id):
                return
            for member in ctx.guild.members:
                try:
                    await self.updateMember(ctx, member.display_name, member)
                except Exception as exception:
                    await ctx.send(f"Python exception occurred for user {member.display_name}")
                    print(exception)
            await ctx.send(f"Updated all linked players!")
            await log_channel.send("**Updateall ended**")

        # verify
        @self.command(help="Preveri se", pass_context=True, aliases=["p"])
        @commands.has_any_role(officer_role, "Nepreverjeni")
        async def preveri(ctx: discord.ext.commands.context.Context, minecraft_name, member: discord.Member = None):
            log_channel = self.get_channel(logging_channel)
            member_role = await getRoleByName(ctx.guild, "Member")
            nepreverjeni_role = await getRoleByName(ctx.guild, "Nepreverjeni")

            if not channelSuitableForCommands(ctx.channel.id):
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
                    if await isOfficer(ctx.author):
                        await ctx.send(f"Preveril `{member}` kot `{minecraft_name}`!")
                        await member.add_roles(member_role)
                        await member.remove_roles(nepreverjeni_role)
                        await log_channel.send(f"**Preveril** `{member}` kot `{minecraft_name}`!")
                        await self.updateMember(ctx, update_name, member)
                        return
                    else:
                        await ctx.send(f"`{minecraft_name}` nima registriranega discorda na Hypixlu. Počakaj na "
                                       f"<@&{officer_role}> da te preveri!")
                        return
                    # if player discord doesn't match
                elif player.discord != f"{member.name}#{member.discriminator}":
                    if await isOfficer(ctx.author):
                        await ctx.send(f"Preveril `{member}` kot `{minecraft_name}`!")
                        await log_channel.send(f"**Preveril** `{member}` kot `{minecraft_name}`!")
                        await member.add_roles(member_role)
                        await member.remove_roles(nepreverjeni_role)
                        await self.updateMember(ctx, update_name, member)
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
                    await self.updateMember(ctx, update_name, member)

            except HypixelApiError as error:
                await ctx.send(f"Napaka: {error}")

        @self.command(help="Preimenuje osebo.", pass_context=True)
        @commands.has_role(officer_role)
        async def rename(ctx: discord.ext.commands.context.Context, minecraft_name, member: discord.Member = None):
            if not channelSuitableForCommands(ctx.channel.id):
                return

            if member is None:
                member = ctx.author

            display_name = f"{minecraft_name} [0]"

            await self.updateMember(ctx, display_name, member)

        @self.command(help="Uklopi ali izklopi auto-updateall.", pass_context=True)
        @commands.has_permissions(administrator=True)
        async def autoupdate(ctx: discord.ext.commands.context.Context, args="status"):
            if not channelSuitableForCommands(ctx.channel.id):
                return
            args.lower()
            with open(f"{directory_path}/settings.json") as f:
                json_data = json.load(f)
            if args == "on":
                json_data["config"]["auto_update"] = "True"
                await ctx.send("```diff\n+ Auto Update enabled```")
            if args == "off":
                json_data["config"]["auto_update"] = "False"
                await ctx.send("```diff\n- Auto Update disabled```")
            if args == "status":
                await ctx.send("`AutoUpdate status:` " + str(json_data["config"]["auto_update"]))

            json_object = json.dumps(json_data, indent=4)
            with open(f"{directory_path}/settings.json", "w") as outfile:
                outfile.write(json_object)

        @self.command(pass_context=True)
        @commands.has_permissions(administrator=True)
        async def shutdown(ctx: discord.ext.commands.context.Context):
            if not channelSuitableForCommands(ctx.channel.id):
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
            if not channelSuitableForCommands(ctx.channel.id):
                return
            self.stop_action = StopAction.RESTART
            self.channel_shutdown_id = ctx.channel.id
            await ctx.send("Restarting")
            await log_channel.send("Restarting")
            await ctx.bot.close()

        #
        # @self.command(pass_context=True)
        # @commands.has_permissions(administrator=True)
        # async def ping(ctx: discord.ext.commands.context.Context):
        #    if not channelSuitableForCommands(ctx.channel.id):
        #        return
        #    await ctx.send("Pong")

        # checkes every 1h if it's between 3-4am and if it is then updates all users
        @tasks.loop(minutes=60.0)
        async def task(ctx: discord.ext.commands.context.Context):
            log_channel = self.get_channel(logging_channel)
            with open(f"{directory_path}/settings.json") as f:
                json_data = json.load(f)
            # sam da vidm če ta srane dela dej stran če js nism
            if datetime.now().hour == 3:
                if json_data["config"]["auto_update"] == "True":
                    await log_channel.send("**Updateall started** *autoupdate*")
                    if not channelSuitableForCommands(ctx.channel.id):
                        return
                    for member in ctx.guild.members:
                        try:
                            await self.updateMember(ctx, member.display_name, member)
                        except Exception as exception:
                            await log_channel.send(f"Python exception occurred for user {member.display_name}")
                            print(exception)
                    await log_channel.send("**Updateall ended** *autoupdate*")
                else:
                    return

    # function to update members   Won't work if user doesn't have "Member" role
    async def updateMember(self, ctx, display_name, member):
        member_role = discord.utils.find(lambda r: r.name == 'Member', ctx.message.guild.roles)
        guild_role = discord.utils.find(lambda r: r.name == 'Guild Member', ctx.message.guild.roles)
        veteran_role = discord.utils.find(lambda r: r.name == 'Veteran', ctx.message.guild.roles)

        log_channel = self.get_channel(logging_channel)
        try:
            # check if user has member role
            if member_role not in member.roles:
                return
            discord_nick = str(display_name)
            name_split = discord_nick.split()
            name = name_split[0]
            uuid = name_to_uuid(name)
            veteran_num = is_veteran(name)
            # if name doesn't exist unverifyes user
            if uuid == "Error":
                await log_channel.send(f"`{name}` ne obstaja. Od-preveril `{member}`")
                for role_name in ["VIP", "VIP+", "MVP", "MVP+", "MVP++", "Member", "Guild Member"]:
                    await member.remove_roles(await getRoleByName(ctx.guild, role_name))
                await member.add_roles(await getRoleByName(ctx.guild, "Nepreverjeni"))
                await member.edit(nick="")
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
                await member.remove_roles(await getRoleByName(ctx.guild, role_name))

            if rank_name != "NON":
                await member.add_roles(await getRoleByName(ctx.guild, rank_name))

            if player.rank == HypixelRank.MVP_PLUS_PLUS:
                await member.add_roles(await getRoleByName(ctx.guild, "MVP++"))
            # check if member is in guild (check users without "Guild Member" role)
            if guild.guild_id == hypixel_guild_id:
                await member.add_roles(await getRoleByName(ctx.guild, "Guild Member"))
                await log_channel.send(f"Dodal `Guild Member` `{player.username}`.")
                await ctx.send(f"Dodal `Guild Member` `{player.username}`.")
            if not memberHasRole(member, veteran_role):
                if veteran_num in {3, 4}:
                    await member.remove_roles(await getRoleByName(ctx.guild, "Veteran"))
                    await ctx.send(f"Odstranil `Veteran` od `{player.username}`.")
                    if veteran_num == 3:
                        await log_channel.send(
                            f"Odstranil `Veteran` od `{player.username}`. <@&{master_role_id}> ostrani mu ga na Hypixlu.")
                    if veteran_num == 4:
                        await log_channel.send(
                            f"Odstranil `Veteran` od `{player.username}`. Že ima Member ali višje na Hypixlu.")

                if veteran_num in {1, 2}:
                    await member.add_roles(await getRoleByName(ctx.guild, "Veteran"))
                    await ctx.send(f"Dodal `Veteran` `{player.username}`.")
                    if veteran_num == 1:
                        await log_channel.send(
                            f"Dodal `Veteran` `{player.username}`. <@&{master_role_id}> dodaj mu ga na Hypixlu.")
                    if veteran_num == 2:
                        await log_channel.send(
                            f"Dodal `Veteran` `{player.username}`. Že ima Veteran ali višje na Hypixlu.")

            # check if someone with guild member role isn't in guild then remove all non moderator guild roles
            if not memberHasRole(member, guild_role):
                if guild.guild_id != hypixel_guild_id:
                    await member.remove_roles(await getRoleByName(ctx.guild, "Guild Member"),
                                              await getRoleByName(ctx.guild, "Veteran"),
                                              await getRoleByName(ctx.guild, "Professional"))
                    await log_channel.send(f"Odstranil use Guild role od `{player.username}`.")
                    await ctx.send(f"Odstranil use Guild role od `{player.username}`.")

            await member.edit(nick=f"{player.username} [{player.network_level}]")

            await ctx.send(f"Posodobil {player.username} level na {player.network_level} in rank {rank_name}"
                           f"{' in MVP++' if player.rank == HypixelRank.MVP_PLUS_PLUS else ''}")

            await log_channel.send(f"Posodobil `{player.username}` level na `{player.network_level}` in rank"
                                   f" `{rank_name}`"
                                   f"{' in `MVP++`' if player.rank == HypixelRank.MVP_PLUS_PLUS else ''}")

        except HypixelApiError as error:
            await ctx.send(f"Napaka: {error}")
