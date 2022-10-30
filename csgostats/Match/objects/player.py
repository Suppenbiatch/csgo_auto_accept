import re
from dataclasses import dataclass, field

from typing import Union, Any, List
import logging
from csgostats.objects.rank import Rank
from csgostats.Match.objects.weapons import Weapons
logger = logging.getLogger(__name__)

__all__ = ['MatchPlayer', 'GeneralStats', 'Utility', 'FirstKill', 'Trades', 'Clutches', 'MultiKills']


def list_check(stats_lst: list, expected_args: int) -> List[Union[int, float, str, None]]:
    if expected_args == len(stats_lst):
        return stats_lst

    warning_string = f'expected {expected_args} items in got {len(stats_lst)}'
    if len(stats_lst) != 0:
        # more items than we expected, do we need to change a class?
        logger.error(warning_string)
    else:
        # stats just not given
        logger.debug(warning_string)

    if expected_args > len(stats_lst):
        stats_lst.extend([None] * (expected_args - len(stats_lst)))
    else:
        stats_lst = stats_lst[:expected_args]
    return stats_lst


def missing_check(stat_values: list):
    stat_values.append(not any(val is not None for val in stat_values))
    return stat_values


@dataclass
class Utility:
    EF: int     # enemies flashed
    FA: int     # flash assists
    EBT: float  # enemies flashed time
    UD: int     # utility damage
    is_missing: bool

    @classmethod
    def from_list(cls, stats_lst: list):
        stats = list_check(stats_lst, 4)
        stats = missing_check(stats)
        return cls(*stats)

    def __post_init__(self):
        # resolve seconds to float
        if isinstance(self.EBT, str):
            self.EBT = float(re.sub('[^\d.]', '', self.EBT))


@dataclass
class FirstKill:
    FKD: int    # first kill, first death difference
    FK: int     # first kill
    FD: int     # first death
    T_FK: int   # T  first kill
    T_FD: int   # T  first death
    CT_FK: int  # CT first kill
    CT_FD: int  # CT first death
    is_missing: bool

    @classmethod
    def from_list(cls, stats_lst: list):
        stats = list_check(stats_lst, 7)
        stats = missing_check(stats)
        return cls(*stats)


@dataclass
class Trades:
    K: int      # trade kills
    D: int      # death was traded
    FK: int     # traded first kills
    FD: int     # traded first deaths
    T_FK: int   # traded first kills as T
    T_FD: int   # traded first deaths as T
    CT_FK: int  # traded first kills as CT
    CT_FD: int  # traded first deaths as CT
    is_missing: bool


    @classmethod
    def from_list(cls, stats_lst: list):
        stats = list_check(stats_lst, 8)
        stats = missing_check(stats)
        return cls(*stats)


@dataclass
class Clutches:
    VX: int
    V5: int
    V4: int
    V3: int
    V2: int
    V1: int
    is_missing: bool

    @classmethod
    def from_list(cls, stats_lst: list):
        stats = list_check(stats_lst, 6)
        stats = missing_check(stats)
        return cls(*stats)


@dataclass
class MultiKills:
    K3p: int
    K5: int
    K4: int
    K3: int
    K2: int
    K1: int
    is_missing: bool

    @classmethod
    def from_list(cls, stats_lst: list):
        stats = list_check(stats_lst, 6)
        stats = missing_check(stats)
        return cls(*stats)


@dataclass
class GeneralStats:
    K: int
    D: int
    A: int
    KD_Dif: int
    KD: float
    ADR: float
    HS: float
    KAST: float
    HLTV1: float
    HLTV2: float

    @classmethod
    def from_list(cls, stats_lst: list):
        stats = list_check(stats_lst, 10)
        return cls(*stats)

    def __post_init__(self):
        # resolve percentages
        if isinstance(self.HS, str):
            self.HS = round(float(re.sub(r'[^\d.]', '', self.HS)) / 100, 4)
        if isinstance(self.KAST, str):
            self.KAST = round(float(re.sub(r'[^\d.]', '', self.KAST)) / 100, 4)


@dataclass
class MatchPlayer:
    steam_id: Union[int, None]
    name: str
    rank: Rank
    general: GeneralStats
    utility: Utility
    first_kills: FirstKill
    trades: Trades
    clutches: Clutches
    multi_kills: MultiKills
    weapons: Weapons = field(init=False, default=None)
    team: int = field(init=False, default=-1)
    match: Any = field(init=False)
    index: int = field(init=False, default=None)

    def __post_init__(self):
        if not isinstance(self.steam_id, int):
            if self.steam_id is not None:
                self.steam_id = int(self.steam_id)

    def profile_url(self):
        if self.steam_id is None:
            return None
        return f'https://steamcommunity.com/profiles/{self.steam_id}'

    def __hash__(self):
        return hash(self.steam_id if self.steam_id is not None else self.name)
