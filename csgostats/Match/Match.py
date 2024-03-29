import base64
import hmac
import itertools
import logging
import pickle
from dataclasses import dataclass, field
from datetime import datetime
from typing import List, Optional, Tuple

from csgostats.Match.objects.duels import Duels
from csgostats.Match.objects.player import MatchPlayer
from csgostats.Match.objects.rounds import Rounds
from csgostats.Match.objects.score import Score
from csgostats.objects.Errors import PlayerNotFoundError
from csgostats.objects.rank import Rank

logger = logging.getLogger(__name__)
__all__ = ['Match', 'match_from_web_request', 'match_to_web_response']


@dataclass
class Match:
    map: str
    server: str
    timestamp: datetime
    average_rank: Rank
    surrendered: bool
    score: List[Score]
    teams: Tuple[List[MatchPlayer], List[MatchPlayer]]
    rounds: Rounds
    duels: Duels
    outcome: str = None
    match_id: int = None
    sharecode: str = None
    player: MatchPlayer = field(init=False, default=None)
    _all_players: List[MatchPlayer] = field(init=False, default=None)

    @property
    def all_players(self) -> List[MatchPlayer]:
        if self._all_players is not None:
            return self._all_players
        self._all_players = list(itertools.chain.from_iterable(self.teams))
        return self._all_players

    def score_str(self) -> str:
        return f'{self.score[0].score_str}:{self.score[1].score_str}'

    def get_player_sort(self, steam_id: int) -> MatchPlayer:
        for i, team in enumerate(self.teams):
            for ii, player in enumerate(team):
                if player.steam_id == steam_id:
                    if ii != 0:
                        self.teams[i][0], self.teams[i][ii] = self.teams[i][ii], self.teams[i][0]
                    self._sort_for_player(i)
                    self.player = player
                    return player
        else:
            logger.warning(f'did not find {steam_id} in {self.match_id}')
            raise PlayerNotFoundError(steam_id)

    def get_player(self, steam_id: int) -> MatchPlayer:
        for player in self.all_players:
            if player.steam_id == int(steam_id):
                return player
        raise PlayerNotFoundError(steam_id)

    def _sort_for_player(self, player_team_number: int):
        if player_team_number == 0:
            self.outcome = self.score[0].outcome
        elif player_team_number == 1:
            self.score = list(reversed(self.score))
            self.teams = (self.teams[1], self.teams[0])
            self.duels.reverse()
            self.rounds.reverse_rounds()
            self.outcome = self.score[0].outcome
        else:
            raise ValueError(f'expected number between 0 and 1 got {player_team_number}')

        for i, team in enumerate(self.teams):
            for player in team:
                player.team = i

    def players_without(self, steam_id: int):
        return list(
            filter(lambda player: filter_players(player, steam_id),
                   self.all_players)
        )

    def contains_player(self, steam_id: int):
        for player in self.all_players:
            if player.steam_id == int(steam_id):
                return True
        return False

    def match_url(self):
        if self.match_id is None:
            raise ValueError(f'missing Match ID')
        return f'https://www.csgostats.gg/match/{self.match_id}'

    def _pickle_me(self):
        return pickle.dumps(self, protocol=pickle.HIGHEST_PROTOCOL, fix_imports=False)

    def sql_tuple(self, steam_id):
        for player in self.teams[0]:
            if player.steam_id == steam_id:
                starting_team = 'T'
                break
        else:
            starting_team = 'CT'
        # starting_team = 'T' if steam_id in self.teams[0] else 'CT'
        player = self.get_player_sort(steam_id)
        return (self.match_id, self.map,
                self.score[0].score, self.score[1].score,
                self.score[0].outcome,
                starting_team,
                player.general.K, player.general.A, player.general.D,
                player.multi_kills.K5, player.multi_kills.K4, player.multi_kills.K3,
                player.multi_kills.K2, player.multi_kills.K1,
                player.general.KD,
                player.general.ADR, player.general.HS, player.general.KAST,
                player.general.HLTV1, player.general.HLTV2, player.rank.rank, player.rank.change, player.name,
                self.server, int(self.timestamp.timestamp()), self.sharecode)

    def __len__(self):
        return len(self.rounds)


def filter_players(player: MatchPlayer, steam_id: int):
    if player.steam_id is None:
        return True
    return player.steam_id != int(steam_id)


def match_to_web_response(match_bytes: bytes, secret: bytes):
    if isinstance(secret, str):
        secret = secret.encode()
    key = hmac.digest(secret, match_bytes, 'sha256')
    b64_object = base64.urlsafe_b64encode(match_bytes).decode('ascii')
    b64_key = base64.urlsafe_b64encode(key).decode('ascii')
    return {'object': b64_object, 'key': b64_key, 'status': 'complete'}


def match_from_web_request(retrieved_object: str, retrieved_key: str, secret: bytes) -> Optional[Match]:
    decoded_obj = base64.urlsafe_b64decode(retrieved_object)
    decoded_key = base64.urlsafe_b64decode(retrieved_key)
    if isinstance(secret, str):
        secret = secret.encode()
    check_obj = hmac.digest(secret, decoded_obj, 'sha256')
    if hmac.compare_digest(decoded_key, check_obj) is False:
        logger.error('retrieved bytes do not match digest, aborting')
        return None
    return pickle.loads(decoded_obj)


if __name__ == '__main__':
    pass
