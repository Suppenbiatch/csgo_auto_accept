from dataclasses import dataclass, field
from typing import List, Dict


@dataclass()
class Weapon:
    kills: int = 0
    HS: float = 0.0
    ACC: float = 0.0
    DMG: int = 0
    shots: int = 0
    is_set: bool = field(default=False, repr=False)
    hits: int = field(init=False)
    name: str = field(init=False, repr=False)


@dataclass()
class Unknown(Weapon):
    def __post_init__(self):
        self.name = 'Unknown'
        self.hits = round(self.shots * self.ACC)


@dataclass
class AK47(Weapon):
    def __post_init__(self):
        self.name = 'AK47'
        self.hits = round(self.shots * self.ACC)


@dataclass
class AUG(Weapon):
    def __post_init__(self):
        self.name = 'AUG'
        self.hits = round(self.shots * self.ACC)


@dataclass
class AWP(Weapon):
    def __post_init__(self):
        self.name = 'AWP'
        self.hits = round(self.shots * self.ACC)


@dataclass
class Bizon(Weapon):
    def __post_init__(self):
        self.name = 'PP-Bizon'
        self.hits = round(self.shots * self.ACC)


@dataclass
class CZ75A(Weapon):
    def __post_init__(self):
        self.name = 'CZ75-Auto'
        self.hits = round(self.shots * self.ACC)


@dataclass
class Deagle(Weapon):
    def __post_init__(self):
        self.name = 'Desert Eagle'
        self.hits = round(self.shots * self.ACC)


@dataclass
class Decoy(Weapon):
    def __post_init__(self):
        self.name = 'Decoy Grenade'
        self.hits = round(self.shots * self.ACC)


@dataclass
class DualBerettas(Weapon):
    def __post_init__(self):
        self.name = 'Dual Berettas'
        self.hits = round(self.shots * self.ACC)


@dataclass
class Famas(Weapon):
    def __post_init__(self):
        self.name = 'Famas'
        self.hits = round(self.shots * self.ACC)


@dataclass
class FiveSeveN(Weapon):
    def __post_init__(self):
        self.name = 'Five-SeveN'
        self.hits = round(self.shots * self.ACC)


@dataclass
class Flashbang(Weapon):
    def __post_init__(self):
        self.name = 'Flashbang Grenade'
        self.hits = round(self.shots * self.ACC)


@dataclass
class G3SG1(Weapon):
    def __post_init__(self):
        self.name = 'G3SG1'
        self.hits = round(self.shots * self.ACC)


@dataclass
class GalilAR(Weapon):
    def __post_init__(self):
        self.name = 'Galil AR'
        self.hits = round(self.shots * self.ACC)


@dataclass
class Glock(Weapon):
    def __post_init__(self):
        self.name = 'Glock-18'
        self.hits = round(self.shots * self.ACC)


@dataclass
class HE(Weapon):
    def __post_init__(self):
        self.name = 'HE Grenade'
        self.hits = round(self.shots * self.ACC)


@dataclass()
class Incendiary(Weapon):
    def __post_init__(self):
        self.name = 'Incendiary Grenade'
        self.hits = round(self.shots * self.ACC)


@dataclass
class Knife(Weapon):
    def __post_init__(self):
        self.name = 'Knife'
        self.hits = round(self.shots * self.ACC)


@dataclass
class M249(Weapon):
    def __post_init__(self):
        self.name = 'M249'
        self.hits = round(self.shots * self.ACC)


@dataclass
class M4A4(Weapon):
    def __post_init__(self):
        self.name = 'M4A4'
        self.hits = round(self.shots * self.ACC)


@dataclass
class M4A1S(Weapon):
    def __post_init__(self):
        self.name = 'M4A1-S'
        self.hits = round(self.shots * self.ACC)


@dataclass
class M4A1(Weapon):
    def __post_init__(self):
        self.name = 'M4A1'
        self.hits = round(self.shots * self.ACC)


@dataclass
class MAC10(Weapon):
    def __post_init__(self):
        self.name = 'MAC-10'
        self.hits = round(self.shots * self.ACC)


@dataclass
class MAG7(Weapon):
    def __post_init__(self):
        self.name = 'MAG-7'
        self.hits = round(self.shots * self.ACC)


@dataclass
class Molotov(Weapon):
    def __post_init__(self):
        self.name = 'Molotov Grenade'
        self.hits = round(self.shots * self.ACC)


@dataclass
class MolotovProjectile(Weapon):
    def __post_init__(self):
        self.name = 'Molotov Projectile'
        self.hits = round(self.shots * self.ACC)


@dataclass
class MP5(Weapon):
    def __post_init__(self):
        self.name = 'MP5-SD'
        self.hits = round(self.shots * self.ACC)


@dataclass
class MP7(Weapon):
    def __post_init__(self):
        self.name = 'MP7'
        self.hits = round(self.shots * self.ACC)


@dataclass
class MP9(Weapon):
    def __post_init__(self):
        self.name = 'MP9'
        self.hits = round(self.shots * self.ACC)


@dataclass
class Negev(Weapon):
    def __post_init__(self):
        self.name = 'Negev'
        self.hits = round(self.shots * self.ACC)


@dataclass
class Nova(Weapon):
    def __post_init__(self):
        self.name = 'Nova'
        self.hits = round(self.shots * self.ACC)


@dataclass
class P2000(Weapon):
    def __post_init__(self):
        self.name = 'P2000'
        self.hits = round(self.shots * self.ACC)


@dataclass
class P250(Weapon):
    def __post_init__(self):
        self.name = 'P250'
        self.hits = round(self.shots * self.ACC)


@dataclass
class P90(Weapon):
    def __post_init__(self):
        self.name = 'P90'
        self.hits = round(self.shots * self.ACC)


@dataclass
class Revolver(Weapon):
    def __post_init__(self):
        self.name = 'R8 Revolver'
        self.hits = round(self.shots * self.ACC)


@dataclass
class SawedOff(Weapon):
    def __post_init__(self):
        self.name = 'Sawed-Off'
        self.hits = round(self.shots * self.ACC)


@dataclass
class Scar20(Weapon):
    def __post_init__(self):
        self.name = 'SCAR-20'
        self.hits = round(self.shots * self.ACC)


@dataclass
class SG553(Weapon):
    def __post_init__(self):
        self.name = 'SG 553'
        self.hits = round(self.shots * self.ACC)


@dataclass
class Smoke(Weapon):
    def __post_init__(self):
        self.name = 'Smoke Grenade'
        self.hits = round(self.shots * self.ACC)


@dataclass
class SSG(Weapon):
    def __post_init__(self):
        self.name = 'SSG 08'
        self.hits = round(self.shots * self.ACC)


@dataclass
class Taser(Weapon):
    def __post_init__(self):
        self.name = 'Zeus x27'
        self.hits = round(self.shots * self.ACC)


@dataclass
class Tec9(Weapon):
    def __post_init__(self):
        self.name = 'Tec-9'
        self.hits = round(self.shots * self.ACC)


@dataclass
class UMP45(Weapon):
    def __post_init__(self):
        self.name = 'UMP-45'
        self.hits = round(self.shots * self.ACC)


@dataclass
class USPS(Weapon):
    def __post_init__(self):
        self.name = 'USP-S'
        self.hits = round(self.shots * self.ACC)


@dataclass
class USP(Weapon):
    def __post_init__(self):
        self.name = 'USP'
        self.hits = round(self.shots * self.ACC)


@dataclass
class XM1014(Weapon):
    def __post_init__(self):
        self.name = 'XM1014'
        self.hits = round(self.shots * self.ACC)


@dataclass()
class Weapons:
    AK47: AK47 = field(default_factory=AK47)
    AUG: AUG = field(default_factory=AUG)
    AWP: AWP = field(default_factory=AWP)
    Bizon: Bizon = field(default_factory=Bizon)
    CZ75A: CZ75A = field(default_factory=CZ75A)
    Deagle: Deagle = field(default_factory=Deagle)
    Decoy: Decoy = field(default_factory=Decoy)
    DualBerettas: DualBerettas = field(default_factory=DualBerettas)
    Famas: Famas = field(default_factory=Famas)
    FiveSeveN: FiveSeveN = field(default_factory=FiveSeveN)
    Flashbang: Flashbang = field(default_factory=Flashbang)
    G3SG1: G3SG1 = field(default_factory=G3SG1)
    GalilAR: GalilAR = field(default_factory=GalilAR)
    Glock: Glock = field(default_factory=Glock)
    HE: HE = field(default_factory=HE)
    Incendiary: Incendiary = field(default_factory=Incendiary)
    Knife: Knife = field(default_factory=Knife)
    M249: M249 = field(default_factory=M249)
    M4A4: M4A4 = field(default_factory=M4A4)
    M4A1S: M4A1S = field(default_factory=M4A1S)
    M4A1: M4A1 = field(default_factory=M4A1)
    MAC10: MAC10 = field(default_factory=MAC10)
    MAG7: MAG7 = field(default_factory=MAG7)
    Molotov: Molotov = field(default_factory=Molotov)
    MolotovProjectile: MolotovProjectile = field(default_factory=MolotovProjectile)
    MP5: MP5 = field(default_factory=MP5)
    MP7: MP7 = field(default_factory=MP7)
    MP9: MP9 = field(default_factory=MP9)
    Negev: Negev = field(default_factory=Negev)
    Nova: Nova = field(default_factory=Nova)
    P2000: P2000 = field(default_factory=P2000)
    P250: P250 = field(default_factory=P250)
    P90: P90 = field(default_factory=P90)
    Revolver: Revolver = field(default_factory=Revolver)
    SawedOff: SawedOff = field(default_factory=SawedOff)
    Scar20: Scar20 = field(default_factory=Scar20)
    SG553: SG553 = field(default_factory=SG553)
    Smoke: Smoke = field(default_factory=Smoke)
    SSG: SSG = field(default_factory=SSG)
    Taser: Taser = field(default_factory=Taser)
    Tec9: Tec9 = field(default_factory=Tec9)
    UMP45: UMP45 = field(default_factory=UMP45)
    USPS: USPS = field(default_factory=USPS)
    USP: USP = field(default_factory=USP)
    XM1014: XM1014 = field(default_factory=XM1014)
    Unknown: Unknown = field(default_factory=Unknown)

    used_only: List[Weapon] = field(init=False, repr=False, default_factory=list)
    kills_only: List[Weapon] = field(init=False, repr=False, default_factory=list)
    _as_dict: Dict[str, Weapon] = field(init=False, repr=True, default=None)

    def populate_weapon_lists(self):
        as_dict = self._as_dict_val()
        used_only = list(filter(lambda x: x.is_set, as_dict.values()))
        kills_only = list(filter(lambda x: x.kills > 0, as_dict.values()))
        self.used_only = used_only
        self.kills_only = kills_only

    def _as_dict_val(self):
        _as_dict = vars(self)
        _as_dict.pop('used_only', None)
        _as_dict.pop('kills_only', None)
        _as_dict.pop('_as_dict', None)
        return _as_dict

    @property
    def as_dict(self):
        if self._as_dict is not None:
            return self._as_dict
        r = self._as_dict_val()
        self._as_dict = r
        return r
