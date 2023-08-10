import discord
from discord import Role, Member
from discord.ext.commands import Context
from mojang import MojangAPI

from hypixel_api import HypixelApi
from settings import Settings, DiscordRole
from structure.hypixel_guild import HypixelGuild
from structure.hypixel_player import HypixelPlayer
from structure.misc import GuildDiscordSyncStatus


def member_has_role(member: Member, role_name: str) -> bool:
    return any(role.name == role_name for role in member.roles)


async def get_role_by_name(guild: discord.Guild, role_name: str) -> Role:
    for role in guild.roles:
        if role.name == role_name:
            return role


def name_to_uuid(name: str) -> str:
    # TODO: Add file cache maybe?
    return MojangAPI.get_uuid(name)


async def remove_guild_roles(ctx: Context, log_channel: discord.TextChannel, member: Member):
    await member.remove_roles(await get_role_by_name(ctx.guild, "Guild Member"),
                              await get_role_by_name(ctx.guild, "Veteran"),
                              await get_role_by_name(ctx.guild, "Professional"))
    await log_channel.send(f"Odstranil use Guild role od `{member.mention}`.")
    await ctx.send(f"Odstranil use Guild role od {member.mention}.")


async def is_veteran(uuid: str, guild: HypixelGuild) -> GuildDiscordSyncStatus:
    guild_member = guild.members.get(uuid)

    total_weekly_xp = sum(xp for date, xp in guild_member.exp_history.items())

    VETERAN_WEEKLY_REQUIRED_XP = 100_000

    if total_weekly_xp >= VETERAN_WEEKLY_REQUIRED_XP:
        if guild_member.rank == "Member":
            return GuildDiscordSyncStatus.ADD_MC_DC
        return GuildDiscordSyncStatus.ADD_DISCORD
    else:
        if guild_member.rank == "Veteran":
            return GuildDiscordSyncStatus.REMOVE_MC_DC
        return GuildDiscordSyncStatus.REMOVE_DISCORD


async def is_professional(player: HypixelPlayer, guild: HypixelGuild) -> GuildDiscordSyncStatus:
    meets_criteria = player.duels_wins >= 1000 or player.bedwars_level >= 100 or player.skywars_level >= 10 or player.network_level >= 100
    guild_player = guild.members.get(player.uuid)
    lower_ranks = ["Member", "Veteran"]
    if meets_criteria:
        if guild_player.rank in lower_ranks:
            return GuildDiscordSyncStatus.ADD_MC_DC
        return GuildDiscordSyncStatus.ADD_DISCORD
    else:
        if guild_player.rank == "Professional":
            return GuildDiscordSyncStatus.REMOVE_MC_DC
        return GuildDiscordSyncStatus.REMOVE_DISCORD


class Utils:
    settings: Settings
    api: HypixelApi

    def __init__(self, settings: Settings, api: HypixelApi):
        self.settings = settings
        self.api = api

    def channel_suitable_for_commands(self, channel_id) -> bool:
        return channel_id in self.settings.get_bot_channels()

    async def is_officer(self, user):
        officer_role_id = self.settings.get_discord_role_id(DiscordRole.OFFICER)
        return any(role.id == officer_role_id for role in user.roles)
