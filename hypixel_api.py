import requests
from structure.hypixel_guild import HypixelGuild
from structure.hypixel_player import HypixelPlayer


class HypixelApiError(Exception):
    pass


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

    async def __fetch_guild_from_id(self, guild_id):
        url = f"https://api.hypixel.net/guild?key={self.__key}&id={guild_id}"
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

    async def __save_guild_data(self, data, guild_id):
        if data["success"]:
            if data["guild"] is not None:
                self.__saved_guilds[data["guild"]["_id"]] = HypixelGuild(data)
        else:
            cause = data["cause"]
            if cause == "You have already looked up this name recently":
                if guild_id not in self.__saved_guilds.keys():
                    raise HypixelApiError("Cannot access guild data and there is no fallback data")
                else:
                    return
            else:
                raise HypixelApiError(cause)

    # TODO: Add cache
    async def get_player_by_name(self, name):
        data = await self.__fetch_player_data_from_name(name)

        await self.__save_player_data(data, None)

        return self.__saved_players[data["player"]["uuid"]]

    async def get_player_by_uuid(self, uuid) -> HypixelPlayer:
        data = await self.__fetch_player_data_from_uuid(uuid)

        await self.__save_player_data(data, uuid)

        return self.__saved_players[uuid]

    async def get_guild_by_player_uuid(self, uuid) -> HypixelGuild:
        data = await self.__fetch_guild_from_player_uuid(uuid)

        await self.__save_guild_data(data, uuid)
        try:
            return self.__saved_guilds[data["guild"]["_id"]]
        except TypeError:
            pass

    async def get_guild_by_id(self, guild_id: str) -> HypixelGuild:
        data = await self.__fetch_guild_from_id(guild_id)
        await self.__save_guild_data(data, guild_id)
        try:
            return self.__saved_guilds[data["guild"]["_id"]]
        except TypeError:
            pass