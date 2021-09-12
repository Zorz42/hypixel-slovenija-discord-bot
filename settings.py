import os
import json


class Settings:
    def __init__(self):
        self.__filename = None
        self.__settings = {
            "discord_key": "insert your discord bot key here",
            "hypixel_key": "insert your hypixel api key here",
            "config": {
                "logging_channel_id": "insert logging channel ID",
                "officer_role_id": "insert Officer role ID",
                "hypixel_guild_id": "insert Hypixel guild ID",
                "admin_role_id": "insert admin role ID",
                "auto_update": "False",  # leave this line alone in settings.json
                "bot_channels": {
                    "1": "874233307238367299",
                    "2": "874233307238367299",
                    "3": "874233307238367299",
                    "4": "874233307238367299"
                }
            }
        }

    async def save(self):
        with open(self.__filename, "w+") as settings_file:
            json.dump(self.__settings, settings_file, indent=4)

    async def load(self, filename):
        self.__filename = filename

        if os.path.exists(filename):
            with open(filename, "r") as settings_file:
                self.__settings = {**self.__settings, **json.load(settings_file)}

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

