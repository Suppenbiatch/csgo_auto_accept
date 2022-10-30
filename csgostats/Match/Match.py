import asyncio
import base64
import hmac
import itertools
import logging
import pickle
import re
from dataclasses import dataclass
from datetime import datetime
from functools import partial
from typing import List, Optional, Union

import aiosqlite
from pytz import utc

from csgostats.Match.objects.player import MatchPlayer
from csgostats.Match.objects.rounds import Rounds
from csgostats.Match.objects.score import Score
from csgostats.Match.objects.team import Team
from csgostats.objects.Errors import PlayerNotFoundError
from csgostats.objects.rank import Rank
from csgostats.objects.utils import grouped, uniq
from csgostats.Match.Serializer import rebuild_match, serialize_match

logger = logging.getLogger(__name__)
__all__ = ['Match', 'DBPlayer', 'match_from_db', 'get_n_matches',
           'matches_for_player', 'match_for_players', 'match_ids_for_player',
           'all_unique_players', 'match_from_web_request', 'match_to_web_response',
           'dump_all_players', 'get_leaderboard_solutions']


@dataclass
class Match:
    map: str
    server: str
    timestamp: datetime
    average_rank: Rank
    surrendered: bool
    score: List[Score]
    teams: List[Team]
    rounds: Rounds
    outcome: str = None
    match_id: int = None
    sharecode: str = None

    def __post_init__(self):
        for player in self.all_players():
            player.match = self

    def score_str(self) -> str:
        return f'{self.score[0].score_str}:{self.score[1].score_str}'

    def get_player_sort(self, steam_id: int) -> MatchPlayer:
        for i, team in enumerate(self.teams):
            player = team.player_from_steam_id(int(steam_id))
            if player is not None:
                self._sort_for_player(i)
                return player
        else:
            logger.warning(f'did not find {steam_id} in {self.match_id}')
            raise PlayerNotFoundError(steam_id)

    def get_player(self, steam_id: int) -> MatchPlayer:
        for player in self.all_players():
            if player.steam_id == int(steam_id):
                return player
        raise PlayerNotFoundError(steam_id)

    def _sort_for_player(self, player_team_number: int):
        if player_team_number == 0:
            self.outcome = self.score[0].outcome
        elif player_team_number == 1:
            self.score = list(reversed(self.score))
            self.teams = list(reversed(self.teams))
            self.rounds.reverse_rounds()
            self.outcome = self.score[0].outcome
        else:
            raise ValueError(f'expected number between 0 and 1 got {player_team_number}')

        for i, team in enumerate(self.teams):
            for player in team:
                player.team = i

    def all_players(self) -> List[MatchPlayer]:
        return list(itertools.chain.from_iterable(self.teams))

    def players_without(self, steam_id: int):
        return list(
            filter(lambda player: filter_players(player, steam_id),
                   self.all_players())
        )

    def contains_player(self, steam_id: int):
        for player in self.all_players():
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
        starting_team = 'T' if steam_id in self.teams[0] else 'CT'
        player = self.get_player_sort(steam_id)
        return (self.sharecode, self.match_id, self.map,
                self.score[0].score, self.score[1].score, self.score[0].outcome,
                starting_team, player.general.K, player.general.A, player.general.D,
                player.multi_kills.K5, player.multi_kills.K4, player.multi_kills.K3,
                player.multi_kills.K2, player.multi_kills.K1, player.general.KD,
                player.general.ADR, player.general.HS, player.general.KAST,
                player.general.HLTV1, player.general.HLTV2, player.rank.rank, player.name,
                self.server, int(self.timestamp.timestamp()))

    async def save_to_db(self, path: str):
        loop = asyncio.get_running_loop()
        pickled_me = await loop.run_in_executor(None, self._pickle_me)
        async with aiosqlite.connect(path) as db:
            await db.execute("""INSERT OR REPLACE INTO matches (id, sharecode, object) VALUES (?, ?, ?)""",
                             (self.match_id, self.sharecode, pickled_me))
            steam_ids = [player.steam_id for player in self.all_players() if player.steam_id is not None]
            async with db.execute(f"""SELECT * FROM players WHERE steam_id IN ({', '.join(['?'] * len(steam_ids))})""",
                                  steam_ids) as cur:
                db.row_factory = aiosqlite.Row
                seen_players = [DBPlayer(*row) for row in await cur.fetchall()]

            [seen_player.add_match(self) for seen_player in seen_players]
            missing_steam_ids = [steam_id for steam_id in steam_ids if
                                 all(steam_id != seen_player.steam_id for seen_player in seen_players)]

            new_players = [DBPlayer(steam_id, [self.match_id], self.match_id, self.timestamp, 1, set(steam_ids), len(steam_ids)) for steam_id in
                           missing_steam_ids]
            player_data = [player.sql_tuple() for player in [*new_players, *seen_players]]
            await db.executemany(
                """INSERT OR REPLACE INTO players (steam_id, ids, newest_id, timestamp, count, seen, seen_count) VALUES (?, ?, ?, ?, ?, ?, ?)""",
                player_data)
            await db.commit()
        logger.info(f'saved Match(id={self.match_id}) into database')
        return

    @classmethod
    def from_serial(cls, id: int, sharecode: str | None, json_string: str):
        data = rebuild_match(id, sharecode, json_string)
        return cls(**data)

    def serialized(self):
        return serialize_match(self)

    def __len__(self):
        return len(self.rounds)


@dataclass
class DBPlayer:
    steam_id: int
    ids: List[int]
    newest_id: int
    timestamp: datetime
    count: int
    seen: set[int]
    seen_count: int
    match: Match = None
    player: MatchPlayer = None

    def __post_init__(self):
        if isinstance(self.ids, str):
            self.ids = list(map(int, self.ids.split(';')))
        if isinstance(self.timestamp, (int, float)):
            self.timestamp = datetime.fromtimestamp(int(self.timestamp), tz=utc)
        if isinstance(self.seen, str):
            if self.seen:
                self.seen = set(int(steam_id) + 76561197960265728 for steam_id in self.seen.split(';'))
            else:
                self.seen = set()

    def add_match(self, match: Match):
        self.ids.append(match.match_id)
        self.ids = sorted(set(self.ids))
        if self.timestamp < match.timestamp:
            self.newest_id = match.match_id
            self.timestamp = match.timestamp
        self.count = len(self.ids)
        for player in match.all_players():
            if player.steam_id is not None:
                self.seen.add(player.steam_id)
        self.seen_count = len(self.seen)

    def sql_tuple(self):
        seen = ';'.join([str(steam_id - 76561197960265728) for steam_id in self.seen])
        return (self.steam_id, ';'.join(map(str, self.ids)),
                self.newest_id, int(self.timestamp.timestamp()),
                self.count, seen, self.seen_count)

    async def fetch_newest_match(self, db: aiosqlite.Connection):
        async with db.execute("""SELECT object FROM matches WHERE id = ?""", (self.newest_id,)) as cur:
            match_bytes, = await cur.fetchone()
        self.match = await _match_from_pickle(match_bytes)
        self.player = self.match.get_player_sort(self.steam_id)


def filter_players(player: MatchPlayer, steam_id: int):
    if player.steam_id is None:
        return True
    return player.steam_id != int(steam_id)


async def match_from_db(match_id: Union[int, List[int]] = None, sharecode: Union[str, List[str]] = None,
                        path: str = 'matches.db') -> List[Optional[Match]]:
    if match_id is None and sharecode is None:
        raise AttributeError(f'match_id and sharecode can not be both None')
    if match_id is not None and sharecode is not None:
        raise AttributeError(f'match_id and sharecode can not be both set')

    if isinstance(match_id, int):
        match_id = [match_id]
    elif isinstance(sharecode, str):
        sharecode = [sharecode]

    if match_id is not None:
        search_ids = match_id
        row = 'id'
    else:
        search_ids = sharecode
        row = 'sharecode'

    all_matches: List[Match] = []
    async with aiosqlite.connect(path) as db:
        for ids in grouped(search_ids, 500):
            async with db.execute(
                    f"""SELECT object FROM matches WHERE {row} IN ({','.join(['?'] * len(ids))}) ORDER BY ID ASC""",
                    ids) as cur:
                match_objects = await cur.fetchall()
            matches = await asyncio.gather(*[_match_from_pickle(match_bytes) for match_bytes, in match_objects],
                                           return_exceptions=False)
            all_matches.extend(matches)
    return all_matches


async def _match_from_pickle(pickled_bytes: bytes) -> Match:
    fetch_function = partial(pickle.loads, pickled_bytes, fix_imports=False, encoding='ascii', errors='strict')
    loop = asyncio.get_running_loop()
    match = await loop.run_in_executor(None, fetch_function)
    return match


def _sync_match_from_pickle(pickled_bytes: bytes) -> Match:
    return pickle.loads(pickled_bytes, fix_imports=False, encoding='ascii', errors='strict')


async def get_n_matches(n: int = None, reverse: bool = False, path: str = 'matches.db') -> List[Match]:
    if n is None:
        n = -1
    else:
        n = int(n)
    if bool(reverse):
        order = 'DESC'
    else:
        order = 'ASC'
    async with aiosqlite.connect(path) as db:
        async with db.execute(f'SELECT object from matches ORDER BY id {order} LIMIT ?', (n,)) as cur:
            objects = await cur.fetchall()
    return await asyncio.gather(*[_match_from_pickle(match_bytes) for match_bytes, in objects], return_exceptions=False)


async def match_for_players(steam_ids: List[int], path: str = 'matches.db') -> List[DBPlayer]:
    players = []
    async with aiosqlite.connect(path) as db:
        chunked = grouped(steam_ids, 500)
        for ids in chunked:
            async with db.execute(
                    f"""SELECT steam_id, 0, newest_id, timestamp, count, '', seen_count FROM players WHERE steam_id IN ({','.join(['?'] * len(ids))})""",
                    ids) as cur:
                player_objects = await cur.fetchall()
                if len(player_objects) == 0:
                    continue
                sub_players = [DBPlayer(*player) for player in player_objects]
            players.extend(sub_players)
        await asyncio.gather(*[player.fetch_newest_match(db) for player in players])
    return players


async def match_ids_for_player(steam_id: int, path: str = 'matches.db') -> DBPlayer:
    async with aiosqlite.connect(path) as db:
        db.row_factory = aiosqlite.Row
        async with db.execute("""SELECT * FROM players WHERE steam_id = ? LIMIT 1""", (steam_id,)) as cur:
            db_item = await cur.fetchone()
            if db_item is None:
                raise PlayerNotFoundError(steam_id)
            player = DBPlayer(**db_item)
    return player


async def matches_for_player(steam_id: int, limit: int = None, raw: bool = False, path: str = 'matches.db') -> List[
    Union[Match, bytes]]:
    if steam_id is None:
        return []
    async with aiosqlite.connect(path) as db:
        db.row_factory = aiosqlite.Row
        async with db.execute("""SELECT * FROM players WHERE steam_id = ? LIMIT 1""", (steam_id,)) as cur:
            db_item = await cur.fetchone()
            if db_item is None:
                raise PlayerNotFoundError(steam_id)
            player = DBPlayer(**db_item)
            ids = player.ids

            if limit is not None:
                if limit < 0:
                    match_ids = ids[limit:]
                elif limit > 0:
                    match_ids = ids[:limit]
                else:
                    raise ValueError('can not return no match')
            else:
                match_ids = ids
        db.row_factory = None
        all_matches = []
        for ids in grouped(match_ids, 500):
            async with db.execute(
                    f"""SELECT object FROM matches WHERE id IN ({','.join(['?'] * len(ids))}) ORDER BY ID ASC""",
                    ids) as cur:
                match_objects = await cur.fetchall()
            if not raw:
                matches = await asyncio.gather(*[_match_from_pickle(match_bytes) for match_bytes, in match_objects],
                                               return_exceptions=False)
            else:
                matches = [match_bytes for match_bytes, in match_objects]
            all_matches.extend(matches)

    return all_matches


async def dump_all_players(path: str = 'matches.db') -> List[tuple]:
    async with aiosqlite.connect(path) as db:
        async with db.execute(f"""SELECT * FROM players ORDER BY count DESC""") as cur:
            data = await cur.fetchall()
    return data


async def all_unique_players(newest_first: bool = False, path: str = 'matches.db') -> List[MatchPlayer]:
    matches = await get_n_matches(None, path=path)
    matches.sort(key=lambda m: m.timestamp, reverse=newest_first)

    return uniq(player for match in matches for player in match.all_players() if player.steam_id is not None)


async def get_leaderboard_solutions(steam_id: int, history: str, db_path: str) -> list[list[Match]]:
    matches: list[Match] = await matches_for_player(steam_id, path=db_path)
    for match in matches:
        match.get_player_sort(steam_id)

    matches.sort(key=lambda m: m.timestamp)

    outcome_pattern = re.compile(rf'(?=({history.upper()}))')
    outcome_lst = ''.join(match.outcome for match in matches)

    solutions = outcome_pattern.finditer(outcome_lst)
    match_solutions = []
    for solution in solutions:
        start, _ = solution.span()
        stop = start + len(history)
        match_solutions.append(matches[start:stop])
    return match_solutions


def match_to_web_response(match_bytes: bytes, secret: bytes):
    key = hmac.digest(secret, match_bytes, 'sha256')
    b64_object = base64.urlsafe_b64encode(match_bytes).decode('ascii')
    b64_key = base64.urlsafe_b64encode(key).decode('ascii')
    return {'object': b64_object, 'key': b64_key, 'status': 'complete'}


def match_from_web_request(retrieved_object: str, retrieved_key: str, secret: bytes) -> Optional[Match]:
    decoded_obj = base64.urlsafe_b64decode(retrieved_object)
    decoded_key = base64.urlsafe_b64decode(retrieved_key)
    check_obj = hmac.digest(secret, decoded_obj, 'sha256')
    if hmac.compare_digest(decoded_key, check_obj) is False:
        logger.error('retrieved bytes do not match digest, aborting')
        return None
    return pickle.loads(decoded_obj)


if __name__ == '__main__':
    async def main():
        path = '../../matches.db'
        matches = await get_n_matches(None, path=path)


    asyncio.run(main())
