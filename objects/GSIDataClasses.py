from dataclasses import dataclass
from typing import Optional, Dict


@dataclass()
class Team:
    consecutive_round_losses: Optional[int]
    matches_won_this_series: Optional[int]
    score: Optional[int]
    timeouts_remaining: Optional[int]
    name: Optional[str] = None


@dataclass()
class MapInfo:
    round_wins: Optional[Dict[str, str]]
    current_spectators: Optional[int]
    mode: Optional[str]
    name: Optional[str]
    num_matches_to_win_series: Optional[int]
    phase: Optional[str]
    round: Optional[int]
    souvenirs_total: Optional[int]
    team_ct: Team
    team_t: Team
    
    def __post_init__(self):
        if isinstance(self.team_ct, dict):
            self.team_ct = Team(**self.team_ct)
        else:
            self.team_ct = Team(**vars(self.team_ct))
        if isinstance(self.team_t, dict):
            self.team_t = Team(**self.team_t)
        else:
            self.team_t = Team(**vars(self.team_t))
@dataclass()
class RoundInfo:
    phase: Optional[str]
    win_team: Optional[str]
    bomb: Optional[str]

@dataclass()
class State:
    armor: Optional[int]
    burning: Optional[int]
    equip_value: Optional[int]
    flashed: Optional[int]
    health: Optional[int]
    helmet: Optional[bool]
    money: Optional[int]
    round_killhs: Optional[int]
    round_kills: Optional[int]
    smoked: Optional[int]
    round_totaldmg: Optional[int] = 0
    defusekit: bool = False

@dataclass()
class MatchStats:
    assists: Optional[int]
    deaths: Optional[int]
    kills: Optional[int]
    mvps: Optional[int]
    score: Optional[int]

# needs Python 3.11
"""class WeaponType(StrEnum):
    Knife = auto()
    C4 = auto()
    Grenade = auto()
    Rifle = auto()
    MachineGun = auto()
    Shotgun = auto(),
    SniperRifle = auto()
    SubmachineGun = auto()

class WeaponState(StrEnum):
    active = auto()
    holstered = auto()"""
    
@dataclass()
class Weapon:
    name: str
    paintkit: str
    state: str
    type: str = None  # taser has no type
    ammo_reserve: int = None
    ammo_clip: int = None
    ammo_clip_max: int = None

    
@dataclass()
class PlayerInfo:
    name: str
    activity: str
    forward: None
    position: None
    observer_slot: None
    team: Optional[str]
    clan: Optional[str]
    steamid: str
    spectarget: Optional[str]
    state: State
    match_stats: MatchStats
    weapons: list[Weapon]
    opposing_team: Optional[str] = None
    
    def __post_init__(self):
        if isinstance(self.state, dict):
            self.state = State(**self.state)
        else:
            self.state = State(**vars(self.state))

        if isinstance(self.match_stats, dict):
            self.match_stats = MatchStats(**self.match_stats)
        else:
            self.match_stats = MatchStats(**vars(self.match_stats))

        if isinstance(self.weapons, dict):
            self.weapons = [Weapon(**weapon) for weapon in self.weapons.values()]

        if self.team:
            self.opposing_team = 'CT' if self.team == 'T' else 'T'