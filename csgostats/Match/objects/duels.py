import hashlib
from dataclasses import dataclass, field

from csgostats.Match.objects.player import MatchPlayer


@dataclass()
class Duels:
    _data: list[tuple[str, list[tuple[int, int]]]] = field(repr=False)
    _team_length: int = field(repr=False)

    @staticmethod
    def hash(_str: str):
        encoded_str = _str.encode('utf-8')
        gen = hashlib.md5(encoded_str, usedforsecurity=False)
        return gen.hexdigest()

    def __repr__(self):
        return f'Duels(players={len(self._data)})'

    def total_disconnects(self) -> int:
        suicides = 0
        for i, (_, val) in enumerate(self._data):
            suicides += val[i][0]
        return suicides

    def disconnects_by_team(self, team_index: int) -> int:
        if team_index not in (0, 1):
            raise ValueError(f'team_index must be between 0 and 1 not {team_index}')
        if team_index == 0:
            team = self._data[:self._team_length]
            offset = 0
        else:
            team = self._data[self._team_length:]
            offset = self._team_length

        suicides = 0
        for i, (_, player) in enumerate(team):
            suicides += player[i + offset][0]
        return suicides

    def disconnects_by(self, player: MatchPlayer) -> int:
        player_hash = self.hash(f'{player.name}-{player.avatar_hash}')
        for i, (target_hash, item) in enumerate(self._data):
            if player_hash != target_hash:
                continue
            return item[i][0]
        raise ValueError(f'Player {player.name} not found in DuelData')

    def total_teamkills(self) -> int:
        team_kills = 0
        team_split = self._team_length - 1
        for i, (_, val) in enumerate(self._data):
            for ii, (k, d) in enumerate(val):
                if i == ii:
                    continue  # disconnects
                if i <= team_split and ii <= team_split:
                    team_kills += k
                if i > team_split and ii > team_split:
                    team_kills += k
        return team_kills

    def teamkills_by_team(self, team_index: int) -> int:
        if team_index not in (0, 1):
            raise ValueError(f'Unsupported team_index: "{team_index}"')
        if team_index == 0:
            team = self._data[:self._team_length]
            offset = (0, self._team_length)
        else:
            team = self._data[self._team_length:]
            offset = (self._team_length, len(self._data))

        team_kills = 0
        for i, (_, player) in enumerate(team):
            for ii in range(*offset):
                if i + offset[0] == ii:
                    continue  # remove disconnects
                team_kills += player[ii][0]
        return team_kills

    def teamkills_by(self, player: MatchPlayer) -> int:
        player_hash = self.hash(f'{player.name}-{player.avatar_hash}')
        for i, (hash_, item) in enumerate(self._data):
            if player_hash != hash_:
                continue
            if i >= self._team_length:
                data = item[self._team_length:]
                data.pop(i - self._team_length)  # remove disconnects
            else:
                data = item[:self._team_length]
                data.pop(i)  # remove disconnects
            return sum(k for k, _ in data)
        raise ValueError(f'Player {player.name} not found in DuelData')

    def teamkilled(self, player: MatchPlayer) -> int:
        player_hash = self.hash(f'{player.name}-{player.avatar_hash}')
        for i, (hash_, item) in enumerate(self._data):
            if hash_ != player_hash:
                continue
            if i >= self._team_length:
                data = item[self._team_length:]
                data.pop(i - self._team_length)  # remove disconnects
            else:
                data = item[:self._team_length]
                data.pop(i)  # remove disconnects
            return sum(d for _, d in data)
        raise ValueError(f'Player {player.name} not found in DuelData')

    def duel_by(self, player_1: MatchPlayer, player_2: MatchPlayer) -> tuple[int, int]:
        player_1_hash = self.hash(f'{player_1.name}-{player_1.avatar_hash}')
        player_2_hash = self.hash(f'{player_2.name}-{player_2.avatar_hash}')
        p1_data = None
        p2_idx = None
        for i, (hash_, player) in enumerate(self._data):
            if p1_data is None and hash_ == player_1_hash:
                p1_data = player
            elif p2_idx is None and hash_ == player_2_hash:
                p2_idx = i
            if p1_data is not None and p2_idx is not None:
                break
        else:
            if p1_data is None:
                raise ValueError(f'failed to find {player_1.name} in DuelData')
            raise ValueError(f'failed to find {player_2.name} in DuelData')
        return p1_data[p2_idx]

    def duels_from(self, player: MatchPlayer, all_players: list[MatchPlayer]):
        player_hash = self.hash(f'{player.name}-{player.avatar_hash}')
        for hash_, duels in self._data:
            if hash_ != player_hash:
                continue
            break
        else:
            raise ValueError(f'failed to find {player.name} in DuelData')
        sort_by_idx = []

        for hash_, _ in self._data:
            for new_player in all_players:
                player_hash = self.hash(f'{new_player.name}-{new_player.avatar_hash}')
                if player_hash == hash_:
                    sort_by_idx.append(new_player)
        matched_data = []
        for i, (k, d) in enumerate(duels):
            dueled_player = sort_by_idx[i]
            matched_data.append((dueled_player, k, d))

        teamed_data = matched_data[:self._team_length], matched_data[self._team_length:]
        for i, team in enumerate(teamed_data):
            for new_player, _, _ in team:
                if new_player.steam_id == player.steam_id:
                    if i == 0:
                        return teamed_data
                    return list(reversed(teamed_data))

    def reverse(self):
        for i, (hash_, player) in enumerate(self._data):
            block_1 = player[:self._team_length]
            block_2 = player[self._team_length:]
            new_player = block_2 + block_1
            self._data[i] = (hash_, new_player)
        team_1 = self._data[:self._team_length]
        team_2 = self._data[self._team_length:]
        self._data = team_2 + team_1
        self._team_length = len(self._data) - self._team_length
