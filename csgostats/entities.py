class Rank(object):
    __slots__ = ['rank_int',
                 'rank_str',
                 'last_game',
                 'rank_age',
                 'comp_wins',
                 'rank_change']

    def __init__(self, rank_int: int = 0, last_game: str = 'U', rank_age: int = None, comp_wins: int = 0):
        self.rank_int: int = int(rank_int)
        self.rank_str: str = self.create_rank_str()
        self.last_game: str = last_game
        self.rank_age: int = rank_age
        self.comp_wins: int = comp_wins
        self.rank_change: str = ''

    def create_rank_str(self):
        rank_names = ['None',
                      'S1', 'S2', 'S3', 'S4', 'SE', 'SEM',
                      'GN1', 'GN2', 'GN3', 'GNM',
                      'MG1', 'MG2', 'MGE', 'DMG',
                      'LE', 'LEM', 'SMFC', 'GE']
        return rank_names[self.rank_int]

    def __repr__(self):
        return f'Rank(rank={self.rank_str}, last_game={self.rank_age})'


class CSSPlayer(object):
    def __init__(self, steam_id):
        self.steam_id = str(steam_id)
        self.username = ''
        self.rank = None
        self.avatar_url = None
        self.stats = None

    def __repr__(self):
        return f'CSSPlayer(steam_id={self.steam_id}, username={self.username}, rank={self.rank}, stats={self.stats}'

    def __eq__(self, other):
        if isinstance(other, CSSPlayer):
            return self.steam_id == other.steam_id
        return self.steam_id == str(other)


class Stats(object):
    def __init__(self, *stat_dict, **kwargs):
        self.K = None
        self.D = None
        self.A = None
        self.K_dif = None
        self.KD = None
        self.ADR = None
        self.HS = None
        self.KAST = None
        self.HLTV = None
        self.HLTV2 = None
        self.EF = None
        self.FA = None
        self.EBT = None
        self.UD = None
        self.FK_FD_DIF = None
        self.FK = None
        self.FD = None
        self.FK_T = None
        self.FD_T = None
        self.FK_CT = None
        self.FD_CT = None
        self.Trade_K = None
        self.Trade_D = None
        self.Trade_FK = None
        self.Trade_FD = None
        self.Trade_FK_T = None
        self.Trade_FD_T = None
        self.Trade_FK_CT = None
        self.Trade_FD_CT = None
        self.VX = None
        self.V5 = None
        self.V4 = None
        self.V3 = None
        self.V2 = None
        self.V1 = None
        self.K3plus = None
        self.K5 = None
        self.K4 = None
        self.K3 = None
        self.K2 = None
        self.K1 = None

        for dictionary in stat_dict:
            for key, value in dictionary.items():
                setattr(self, key, value)
        for key, value in kwargs.items():
            setattr(self, key, value)

    def __repr__(self):
        return f'Stats(kills={self.K}, assists={self.A}, deaths={self.D})'


class Match(object):
    def __init__(self, match_id):
        self.match_id = str(match_id)
        self.map = None
        self.score = None
        self.player = None
        self.players = None
        self.started_as = None
        self.outcome = None
        self.server = None
        self.timestamp = None

    def __repr__(self):
        return f'Match(map={self.map}, score={self.score[0]:02d}:{self.score[1]:02d}, match_id={self.match_id}'
