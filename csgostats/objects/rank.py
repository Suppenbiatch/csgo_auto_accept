import re
from dataclasses import dataclass
from typing import Union, Optional


@dataclass
class Rank:
    rank: Union[int, str, None] = None
    change: Optional[str] = None

    def __post_init__(self):
        if self.rank is None:
            self.rank = 0
        if self.change is None:
            self.change = ''
        self.change = re.sub(r'[^+-]', '', self.change)

        self.rank = int(self.rank)
        if self.rank > 18:
            raise ValueError('Maximum of 18 Ranks')
        rank_names = ['None',
                      'S1', 'S2', 'S3', 'S4', 'SE', 'SEM',
                      'GN1', 'GN2', 'GN3', 'GNM',
                      'MG1', 'MG2', 'MGE', 'DMG',
                      'LE', 'LEM', 'SMFC', 'GE']
        self.name = rank_names[self.rank]

    def __repr__(self):
        return f'Rank({self.name}{self.change})'

    def __lt__(self, other):
        if isinstance(other, Rank):
            return self.rank < other.rank
        return self.rank < other
