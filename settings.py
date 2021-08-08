import os
import json


class Settings:
    def __init__(self):
        self.__settings = {
            "linked": {},
            "discord_key": "insert your discord bot key here",
            "hypixel_key": "insert your hypixel api key here",
        }

    def load(self, file_name):
        if os.path.exists("settings.json"):
            with open("settings.json", "r") as settings_file:
                self.__settings = json.load(settings_file)
        else:

