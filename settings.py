import os
import json


class Settings:
    def __init__(self):
        self.__filename = None
        self.__settings = {
            "linked": {},
            "discord_key": "insert your discord bot key here",
            "hypixel_key": "insert your hypixel api key here",
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

    async def getDiscordKey(self):
        return self.__settings["discord_key"]

    async def getHypixelKey(self):
        return self.__settings["hypixel_key"]

    async def getLinkedUser(self, user_id):
        return self.__settings["linked"][str(user_id)]

    async def isUserLinked(self, user_id):
        return str(user_id) in self.__settings["linked"]

    async def linkUser(self, user_id, uuid):
        self.__settings["linked"][user_id] = str(uuid)
        await self.save()
