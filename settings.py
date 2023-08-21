import asyncio
import os
import json
from enum import Enum, auto


class DiscordChannel(Enum):
    LOGGING = auto()
    VERIFY = auto()


class DiscordRole(Enum):
    ADMIN = auto()
    OFFICER = auto()
    PROFESSIONAL = auto()
    VETERAN = auto()
    GUILD_MEMBER = auto()
    MEMBER = auto()
    UNVERIFIED = auto()


class Settings:
    def __init__(self):
        self.__filename = None
        self.__settings = {
            "discord_key": "insert your discord bot key here",
            "hypixel_key": "insert your hypixel api key here",

            "hypixel_guild_id": "",  # insert Hypixel guild ID

            "logging_channel_id": 0,  # insert logging channel ID
            "verify_channel_id": 0,  # insert verification channel

            "unverified_role_id": 0,
            "member_role_id": 0,
            "guild_member_role_id": 0,
            "veteran_role_id": 0,
            "professional_role_id": 0,
            "officer_role_id": 0,  # insert Officer role ID
            "admin_role_id": 0,  # insert admin role ID

            "auto_update": False,  # leave this line alone in settings.json
            "bot_channel_ids": [],
            "discord_server_id": 0,

            "bot_version": "3.0",
        }

    async def save(self):
        with open(self.__filename, "w+") as settings_file:
            json.dump(self.__settings, settings_file, indent=4)

    async def load(self, filename):
        self.__filename = filename

        if os.path.exists(filename):
            with open(filename, "r") as settings_file:
                self.__settings = {**self.__settings, **json.load(settings_file)}
        else:
            with open(filename, "w") as fw:
                fw.write(json.dumps(self.__settings, indent=4))
            exit(f"Config file {filename} not found. Generated a new one.")

        if self.__settings["discord_key"] == "insert your discord bot key here":
            print("Insert discord_key into settings.json")
            return False

        if self.__settings["hypixel_key"] == "insert your hypixel api key here":
            print("Insert hypixel_key into settings.json")
            return False

        await self.save()

        return True

    def getDiscordKey(self):
        return self.__settings["discord_key"]

    async def getHypixelKey(self):
        return self.__settings["hypixel_key"]

    def get_bot_channels(self) -> list[str]:
        return self.__settings.get("bot_channel_ids")

    def get_discord_channel_id(self, channel: DiscordChannel) -> int:
        config_channel_name = channel.name.lower() + "_channel_id"
        return self.__settings.get(config_channel_name)

    def get_discord_role_id(self, channel: DiscordRole) -> int:
        config_role_name = channel.name.lower() + "_role_id"
        return self.__settings.get(config_role_name)

    def get_guild_id(self) -> str:
        return self.__settings.get("hypixel_guild_id")

    def get_bot_version(self) -> str:
        return self.__settings.get("bot_version")

    def get_discord_server_id(self) -> int:
        return self.__settings.get("discord_server_id")
