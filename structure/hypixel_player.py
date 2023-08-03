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
