from dataclasses import dataclass, field
from typing import List, Dict


@dataclass()
class Weapon:
    kills: int = 0
    HS: float = 0.0
    ACC: float = 0.0
    DMG: int = 0
    shots: int = 0
    is_set: bool = False
    hits: int = field(init=False)
    name: str = field(init=False)


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
    AK47: AK47 = AK47()
    AUG: AUG = AUG()
    AWP: AWP = AWP()
    Bizon: Bizon = Bizon()
    CZ75A: CZ75A = CZ75A()
    Deagle: Deagle = Deagle()
    Decoy: Decoy = Decoy()
    DualBerettas: DualBerettas = DualBerettas()
    Famas: Famas = Famas()
    FiveSeveN: FiveSeveN = FiveSeveN()
    Flashbang: Flashbang = Flashbang()
    G3SG1: G3SG1 = G3SG1()
    GalilAR: GalilAR = GalilAR()
    Glock: Glock = Glock()
    HE: HE = HE()
    Incendiary: Incendiary = Incendiary()
    Knife: Knife = Knife()
    M249: M249 = M249()
    M4A4: M4A4 = M4A4()
    M4A1S: M4A1S = M4A1S()
    M4A1: M4A1 = M4A1()
    MAC10: MAC10 = MAC10()
    MAG7: MAG7 = MAG7()
    Molotov: Molotov = Molotov()
    MolotovProjectile: MolotovProjectile = MolotovProjectile()
    MP5: MP5 = MP5()
    MP7: MP7 = MP7()
    MP9: MP9 = MP9()
    Negev: Negev = Negev()
    Nova: Nova = Nova()
    P2000: P2000 = P2000()
    P250: P250 = P250()
    P90: P90 = P90()
    Revolver: Revolver = Revolver()
    SawedOff: SawedOff = SawedOff()
    Scar20: Scar20 = Scar20()
    SG553: SG553 = SG553()
    Smoke: Smoke = Smoke()
    SSG: SSG = SSG()
    Taser: Taser = Taser()
    Tec9: Tec9 = Tec9()
    UMP45: UMP45 = UMP45()
    USPS: USPS = USPS()
    USP: USP = USP()
    XM1014: XM1014 = XM1014()

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
