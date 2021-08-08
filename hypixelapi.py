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
        if "newPackageRank" in data["player"]:
            self.rank = rank_names[data["player"]["newPackageRank"]]

        self.discord = None
        try:
            self.discord = data["player"]["socialMedia"]["links"]["DISCORD"]
        except KeyError or ValueError:
            pass

        self.uuid = data["player"]["uuid"]


class HypixelApi:
    def __init__(self, key: str):
        self.__key = key
        self.__saved_players = {}

    async def __fetchDataFromUUID(self, uuid):
        url = f"https://api.hypixel.net/player?key={self.__key}&uuid={uuid}"
        return requests.get(url).json()

    async def __fetchDataFromName(self, name):
        url = f"https://api.hypixel.net/player?key={self.__key}&name={name}"
        return requests.get(url).json()

    async def __savePlayerData(self, data, uuid):
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

    async def getPlayerByName(self, name):
        data = await self.__fetchDataFromName(name)

        await self.__savePlayerData(data, None)

        return self.__saved_players[data["player"]["uuid"]]

    async def getPlayerByUUID(self, uuid) -> HypixelPlayer:
        data = await self.__fetchDataFromUUID(uuid)

        await self.__savePlayerData(data, uuid)

        return self.__saved_players[uuid]
