import datetime
from dataclasses import dataclass


@dataclass
class HypixelGuildMember:
    uuid: str
    rank: str
    joined_date: datetime.datetime
    questParticipation: int
    exp_history: dict[datetime.date, int]

    def __init__(self, raw_member_data: dict):
        self.uuid = raw_member_data.get("uuid")
        self.rank = raw_member_data.get("rank")
        joined_timestamp = raw_member_data.get("joined") / 1000
        self.joined_date = datetime.datetime.fromtimestamp(joined_timestamp)
        self.questParticipation = raw_member_data.get("questParticipation")
        raw_exp_history: dict = raw_member_data.get("expHistory")
        self.exp_history = {datetime.datetime.strptime(raw_date, "%Y-%m-%d"): xp for raw_date, xp in raw_exp_history.items()}


@dataclass
class HypixelGuildRank:
    name: str
    default: bool
    tag: str
    created: datetime.datetime
    priority: int

    def __init__(self, raw_rank_data: dict):
        self.name = raw_rank_data.get("name")
        self.default = raw_rank_data.get("default")
        self.tag = raw_rank_data.get("tag")
        created_timestamp = raw_rank_data.get("created") / 1000
        self.created = datetime.datetime.fromtimestamp(created_timestamp)
        self.priority = raw_rank_data.get("priority")


@dataclass
class HypixelGuild:
    guild_id: str
    members: dict[str, HypixelGuildMember]

    def __init__(self, data: dict):
        guild_data: dict = data.get("guild")
        self.guild_id = guild_data.get("_id")
        self.members = {raw_member_data.get("uuid"): HypixelGuildMember(raw_member_data) for raw_member_data in guild_data.get("members")}
        self.ranks = [HypixelGuildRank(raw_rank_data) for raw_rank_data in guild_data.get("ranks")]
