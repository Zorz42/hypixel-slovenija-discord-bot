import discord
import requests
from mojang import MojangAPI

from settings import Settings, DiscordRole


async def member_has_role(member, role_name):
    for role in member.roles:
        if role.name == role_name:
            return True
    return False


async def get_role_by_name(guild: discord.Guild, role_name):
    for role in guild.roles:
        if role.name == role_name:
            return role


async def name_to_uuid(name):
    return MojangAPI.get_uuid(name)


class Utils:
    settings: Settings

    def __init__(self, settings: Settings):
        self.settings = settings

    async def is_veteran(self, name) -> int:
        api_key: str = await self.settings.getHypixelKey()
        guild_id: str = self.settings.get_guild_id()
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

    def channel_suitable_for_commands(self, channel_id) -> bool:
        return channel_id in self.settings.get_bot_channels()

    async def is_officer(self, user):
        for role in user.roles:
            if role.id == self.settings.get_discord_role_id(DiscordRole.OFFICER):
                return True
        return False
