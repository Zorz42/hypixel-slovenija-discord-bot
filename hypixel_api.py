import requests
import math
from enum import Enum, auto


class HypixelRank(Enum):
    NON = auto()
    VIP = auto()
    VIP_PLUS = auto()
    MVP = auto()
    MVP_PLUS = auto()
    MVP_PLUS_PLUS = auto()


rank_names = {
    "VIP": HypixelRank.VIP,
    "VIP_PLUS": HypixelRank.VIP_PLUS,
    "MVP": HypixelRank.MVP,
    "MVP_PLUS": HypixelRank.MVP_PLUS,
    "SUPERSTAR": HypixelRank.MVP_PLUS_PLUS,
}


class HypixelApiError(Exception):
    pass


class HypixelPlayer:
    def __init__(self, data: dict):
        self.username = data["player"]["displayname"]
        network_experience = data["player"]["networkExp"]
        network_level = (math.sqrt((2 * network_experience) + 30625) / 50) - 2.5
        self.network_level = math.floor(network_level)

        self.rank = HypixelRank.NON
        try:
            if "newPackageRank" in data["player"]:
                self.rank = rank_names[data["player"]["newPackageRank"]]
                self.rank = rank_names[data["player"]["monthlyPackageRank"]]
        except KeyError or ValueError:
            pass

        self.discord = None
        try:
            self.discord = data["player"]["socialMedia"]["links"]["DISCORD"]
        except KeyError or ValueError:
            pass

        self.uuid = data["player"]["uuid"]


class Guild:
    def __init__(self, data: dict):
        self.guild_id = data["guild"]["_id"]


class HypixelApi:
    def __init__(self):
        self.__key = ""
        self.__saved_players = {}
        self.__saved_guilds = {}

    async def set_key(self, key: str):
        self.__key = key

    async def __fetch_player_data_from_uuid(self, uuid):
        url = f"https://api.hypixel.net/player?key={self.__key}&uuid={uuid}"
        return requests.get(url).json()

    async def __fetch_player_data_from_name(self, name):
        url = f"https://api.hypixel.net/player?key={self.__key}&name={name}"
        return requests.get(url).json()

    async def __fetch_guild_from_player_uuid(self, uuid):
        url = f"https://api.hypixel.net/guild?key={self.__key}&player={uuid}"
        return requests.get(url).json()

    async def __save_player_data(self, data, uuid):
        if data["success"]:
            if data["player"] is None:
                raise HypixelApiError("This player does not exist")
            self.__saved_players[data["player"]["uuid"]] = HypixelPlayer(data)
        else:
            cause = data["cause"]
            if cause == "You have already looked up this name recently":
                if uuid not in self.__saved_players.keys():
                    raise HypixelApiError("Cannot access player data and there is no fallback data")
                else:
                    return
            else:
                raise HypixelApiError(cause)

    async def __save_guild_data(self, data, uuid):
        if data["success"]:
            if data["guild"] is None:
                self.__saved_guilds["null"] = "null"
            else:
                self.__saved_guilds[data["guild"]["_id"]] = Guild(data)
        else:
            cause = data["cause"]
            if cause == "You have already looked up this name recently":
                if uuid not in self.__saved_guilds.keys():
                    raise HypixelApiError("Cannot access player data and there is no fallback data")
                else:
                    return
            else:
                raise HypixelApiError(cause)

    async def get_player_by_name(self, name):
        data = await self.__fetch_player_data_from_name(name)

        await self.__save_player_data(data, None)

        return self.__saved_players[data["player"]["uuid"]]

    async def get_player_by_uuid(self, uuid) -> HypixelPlayer:
        data = await self.__fetch_player_data_from_uuid(uuid)

        await self.__save_player_data(data, uuid)

        return self.__saved_players[uuid]

    async def get_guild_by_player_uuid(self, uuid) -> Guild:
        data = await self.__fetch_guild_from_player_uuid(uuid)

        await self.__save_guild_data(data, uuid)
        try:
            return self.__saved_guilds[data["guild"]["_id"]]
        except TypeError:
            pass
