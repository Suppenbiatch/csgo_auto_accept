import re
from dataclasses import dataclass
import inspect
from typing import Union
import logging
from csgostats.objects.rank import Rank
logger = logging.getLogger(__name__)

__all__ = ['MatchPlayer', 'GeneralStats', 'Utility', 'FirstKill', 'Trades', 'Clutches', 'MultiKills']


def dict_generator(cls, stats_lst):
    params = inspect.signature(cls).parameters
    stats = dict(zip(params, stats_lst))
    if len(params) != len(stats_lst):
        warning_string = f'expected {len(params)} items in {cls.__name__} got {len(stats_lst)}'
        if len(stats_lst) != 0:
            # more items then we expected, do we need to change a class?
            logger.warning(warning_string)
        else:
            # stats just not given
            logger.debug(warning_string)
        if len(params) > len(stats_lst):
            for param, _ in list(params.items())[len(stats_lst):]:
                stats[param] = None
                logger.debug(f'parameter "{param}" is missing and has been set to "None"')
    return stats


def missing_check(self):
    params = inspect.signature(self.__class__).parameters
    return all(getattr(self, param) is None for param in params)


@dataclass
class Utility:
    EF: int     # enemies flashed
    FA: int     # flash assists
    EBT: float  # enemies flashed time
    UD: int     # utility damage

    @classmethod
    def from_dict(cls, stats_lst):
        stats = dict_generator(cls, stats_lst)
        return cls(**stats)

    def __post_init__(self):
        # resolve seconds to float
        if isinstance(self.EBT, str):
            self.EBT = float(re.sub('[^\d.]', '', self.EBT))
        self.is_missing = missing_check(self)


@dataclass
class FirstKill:
    FKD: int    # first kill, first death difference
    FK: int     # first kill
    FD: int     # first death
    T_FK: int   # T  first kill
    T_FD: int   # T  first death
    CT_FK: int  # CT first kill
    CT_FD: int  # CT first death

    @classmethod
    def from_dict(cls, stats_lst):
        stats = dict_generator(cls, stats_lst)
        return cls(**stats)

    def __post_init__(self):
        self.is_missing = missing_check(self)


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

    @classmethod
    def from_dict(cls, stats_lst):
        stats = dict_generator(cls, stats_lst)
        return cls(**stats)

    def __post_init__(self):
        self.is_missing = missing_check(self)


@dataclass
class Clutches:
    VX: int
    V1: int
    V2: int
    V3: int
    V4: int
    V5: int

    @classmethod
    def from_dict(cls, stats_lst):
        stats = dict_generator(cls, stats_lst)
        return cls(**stats)

    def __post_init__(self):
        self.is_missing = missing_check(self)


@dataclass
class MultiKills:
    K3p: int
    K5: int
    K4: int
    K3: int
    K2: int
    K1: int

    @classmethod
    def from_dict(cls, stats_lst):
        stats = dict_generator(cls, stats_lst)
        return cls(**stats)

    def __post_init__(self):
        self.is_missing = missing_check(self)


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
    def from_dict(cls, stats_lst):
        stats = dict_generator(cls, stats_lst)
        return cls(**stats)

    def __post_init__(self):
        # resolve percentages
        if isinstance(self.HS, str):
            self.HS = round(float(re.sub('[^0-9.]', '', self.HS)) / 100, 4)
        if isinstance(self.KAST, str):
            self.KAST = round(float(re.sub('[^0-9.]', '', self.KAST)) / 100, 4)


@dataclass
class MatchPlayer:
    steam_id: Union[int, str, None]
    name: str
    rank: Rank
    general: GeneralStats
    utility: Utility
    first_kills: FirstKill
    trades: Trades
    clutches: Clutches
    multi_kills: MultiKills
    team: int = -1
    match = None

    def __post_init__(self):
        if not isinstance(self.steam_id, int):
            if self.steam_id is not None:
                self.steam_id = int(self.steam_id)

        self.index = None

    def profile_url(self):
        if self.steam_id is None:
            return None
        return f'https://steamcommunity.com/profiles/{self.steam_id}'

    def __hash__(self):
        return hash(self.steam_id if self.steam_id is not None else self.name)
