from dataclasses import dataclass
from typing import List, Optional


@dataclass
class Round:
    winner: int
    score: tuple
    won_by: str
    team_1_size: int
    team_1_survived: int
    team_2_size: int
    team_2_survived: int


@dataclass
class Rounds:
    rounds: List[Round]
    max_rounds: Optional[int]

    def __repr__(self):
        return f'Rounds(maxrounds=MR{self.max_rounds})'

    def reverse_rounds(self):
        for match_round in self.rounds:
            match_round.score = tuple(reversed(match_round.score))
            match_round.winner = 0 if match_round.winner == 1 else 1
            match_round.team_1_size, match_round.team_2_size = match_round.team_2_size, match_round.team_1_size
            match_round.team_1_survived, match_round.team_2_survived = match_round.team_2_survived, match_round.team_1_survived
        return

    def __iter__(self):
        for round_ in self.rounds:
            yield round_

    def __len__(self):
        return len(self.rounds)
