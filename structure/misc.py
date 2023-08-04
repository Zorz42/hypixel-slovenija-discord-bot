from enum import Enum


class VeteranStatus(Enum):
    ADD_MC_DC = (True, True)
    ADD_DISCORD = (True, False)
    REMOVE_MC_DC = (False, True)
    REMOVE_DISCORD = (False, False)

    def __init__(self, *dummy):
        self.is_veteran = self.value[0]
        self.update_mc = self.value[1]
