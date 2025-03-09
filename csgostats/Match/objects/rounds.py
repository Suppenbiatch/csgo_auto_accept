import warnings
from dataclasses import dataclass
from typing import Optional, Iterator


@dataclass
class RoundKill:
    attacker: int
    attacker_name: str
    victim: int
    victim_name: str
    assistant: int | None
    assistant_name: str | None
    weapon: str
    headshot: bool
    wallbang: bool
    ts: int
    tick: int


@dataclass
class RoundEconomy:
    equipment_value: int
    cash: int
    cash_spent: int


@dataclass
class Round:
    winner: int
    score: tuple[int, int]
    won_by: str

    team_1_size: int
    team_1_survived: int
    team_2_size: int
    team_2_survived: int

    kills: list[RoundKill]
    team_1_economy: RoundEconomy
    team_2_economy: RoundEconomy


    def kills_by(self, steam_id: int):
        kills = []
        for kill in self.kills:
            if kill.attacker == steam_id:
                kills.append(kill)
        return kills


@dataclass
class Rounds:
    rounds: list[Round]
    max_rounds: Optional[int]

    def __repr__(self):
        return f'Rounds(maxrounds=MR{self.max_rounds})'

    def reverse_rounds(self):
        for match_round in self.rounds:
            match_round.score = tuple(reversed(match_round.score))
            match_round.winner = 0 if match_round.winner == 1 else 1
            match_round.team_1_size, match_round.team_2_size = match_round.team_2_size, match_round.team_1_size
            match_round.team_1_survived, match_round.team_2_survived = match_round.team_2_survived, match_round.team_1_survived
            match_round.team_1_economy, match_round.team_2_economy = match_round.team_2_economy, match_round.team_1_economy
        return

    def score_after(self, rounds: int = None) -> tuple[int, int]:
        if rounds is None and self.max_rounds is None:
            raise ValueError(f'can not return half-time score since `max_rounds` is not set!')
        elif rounds is None:
            rounds = self.max_rounds // 2
        elif rounds > len(self.rounds):
            warnings.warn(f'only {len(self.rounds)} rounds where played but {rounds} were requested')

        """t1 = 0
        t2 = 0
        for round_ in self.rounds[:rounds]:
            if round_.winner == 0:
                t1 += 1
            else:
                t2 += 1
        return t1, t2"""
        round_ = self.rounds[rounds]
        return round_.score

    def __iter__(self) -> Iterator[Round]:
        for round_ in self.rounds:
            yield round_

    def __len__(self):
        return len(self.rounds)
