from dataclasses import dataclass
from csgostats.Match.objects.player import MatchPlayer
import inspect
import logging

logger = logging.getLogger(__name__)


@dataclass
class Team:
    player_0: MatchPlayer = None
    player_1: MatchPlayer = None
    player_2: MatchPlayer = None
    player_3: MatchPlayer = None
    player_4: MatchPlayer = None

    def __post_init__(self):
        params = inspect.signature(self.__class__).parameters
        self.all_players = []
        for i, (param, _) in enumerate(params.items()):
            player: MatchPlayer = getattr(self, param)
            if player is not None:
                player.index = i
                self.all_players.append(player)

    def player_from_steam_id(self, steam_id):
        for i, player in enumerate(self.all_players):
            if player.steam_id == int(steam_id):
                if i != 0:
                    setattr(self, f'player_{i}', self.player_0)
                    self.player_0 = player
                    self.all_players.insert(0, self.all_players.pop(i))
                return player
        return None

    def __iter__(self):
        for player in self.all_players:
            yield player

    def __contains__(self, item):
        for player in self.all_players:
            if player.steam_id == int(item):
                return True
        return False

    def __getitem__(self, item):
        if 0 > item > len(self.all_players) - 1:
            raise ValueError(f'player index has to be between 0 and {len(self.all_players) - 1}')
        return self.all_players[item]

    def __len__(self):
        return len(self.all_players)
