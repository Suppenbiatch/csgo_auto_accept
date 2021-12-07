from dataclasses import dataclass
import logging

logger = logging.getLogger(__name__)


@dataclass
class Score:
    score: int
    outcome: str

    def __post_init__(self):
        self.score_str = f'{self.score:02d}'

    def __repr__(self):
        return f'Score(score={self.score_str}, outcome={self.outcome})'
