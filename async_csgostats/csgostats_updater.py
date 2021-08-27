import asyncio
import itertools
import json
import os.path
import re
import time
from datetime import timedelta
from typing import List

import pyperclip
import requests
from color import FgColor

import consts
import utils
from async_csgostats.add_match_id import add_match
from async_csgostats.csgostats_objects import Match, Stats, CSSPlayer
from async_csgostats.match_info import multiple_match_info
from write import write, pushbullet_dict


class CSGOStatsUpdater:
    def __init__(self, cfg, account):
        self.cfg = cfg
        self.account = account
        self.queue_difference = []
        self.last_retry = time.time()

    def new_account(self, account):
        self.account = account

    def update_csgo_stats(self, new_codes: List[dict], steam_id, discord_output: bool = False):
        sharecodes = [match_dict['sharecode'] for match_dict in new_codes]
        all_games = asyncio.run(add_match(sharecodes, use_signal=False))

        completed_games, not_completed_games, = [], []

        for game in all_games:
            if game['status'] == 'complete':
                completed_games.append(game)
            else:
                not_completed_games.append(game)

        queued_games = [game for game in not_completed_games if game['status'] != 'error']
        corrupt_games = [{'sharecode': game['sharecode'], 'queue_pos': None} for game in not_completed_games if game['status'] == 'error']

        if queued_games:
            temp_string = ''
            for i, val in enumerate(queued_games, start=1):
                queue_pos_obj = re.search(r'in Queue #(\d+)', val["msg"])
                if queue_pos_obj is not None:
                    val["queue_pos"] = int(queue_pos_obj.group(1))
                else:
                    val["queue_pos"] = 0
                temp_string += f'#{i}: in Queue #{val["queue_pos"]} - '

            current_queue_difference = utils.avg([last_game['queue_pos'] - game['queue_pos'] for game in queued_games for last_game in new_codes if last_game['sharecode'] == game['sharecode'] and last_game['queue_pos'] is not None])
            if current_queue_difference is not None:
                if current_queue_difference >= 0.0:
                    self.queue_difference.append(current_queue_difference / ((time.time() - self.last_retry) / 60))
                    queue_difference = self.queue_difference[-10:]
                    matches_per_min = round(utils.avg(queue_difference), 1)
                    if matches_per_min != 0.0:
                        time_till_done = timedelta(seconds=(queued_games[0]['queue_pos'] / matches_per_min) * 60)
                    else:
                        time_till_done = '∞:∞:∞'
                    temp_string += f'{matches_per_min} matches/min - #1 done in {time_till_done}'
            temp_string = temp_string.rstrip(' - ')
            write(temp_string, add_time=False, overwrite='4')

        self.last_retry = time.time()
        new_codes = [game for game in corrupt_games]
        # new_codes.extend(csgostats_error)  # don't know yet when csgostats would error

        if new_codes:
            erred_games_string = 'An error occurred in one game' if len(new_codes) == 1 else f'An error occurred in {len(new_codes)} games'
            write(erred_games_string, overwrite='5')

        new_codes.extend([game for game in queued_games if game['queue_pos'] < self.cfg['max_queue_position']])

        if completed_games:
            match_lst = [(match['id'], steam_id, match['sharecode']) for match in completed_games]
            matches: List[Match] = asyncio.run(multiple_match_info(match_lst, use_signal=False))
            for match in matches:
                game_url = f'https://csgostats.gg/match/{match.match_id}'

                write(f'URL: {game_url}', add_time=True, push=pushbullet_dict['urgency'], color=FgColor.Green)
                csv_match_data = add_match_id_to_csv(match, steam_id)
                add_players_to_db(match, steam_id)

                if discord_output and self.cfg['discord_url']:
                    discord_obj = generate_table(csv_match_data, self.account)
                    send_discord_msg(discord_obj, self.cfg['discord_url'], f'{match.player.username} - Match Stats')

                try:
                    pyperclip.copy(game_url)
                except (pyperclip.PyperclipWindowsException, pyperclip.PyperclipTimeoutException):
                    write('Failed to load URL in to clipboard', add_time=False)

            write(None, add_time=False, push=pushbullet_dict['urgency'], push_now=True, output=False)
        return new_codes


def add_match_id_to_csv(match: Match, _steam_id, match_id=None):
    csv_path = utils.csv_path_for_steamid(_steam_id)
    data = utils.get_csv_list(csv_path)
    m_index = None
    if match.sharecode is not None:
        m_index = utils.find_dict(data, 'sharecode', match.sharecode)
    if m_index is None and match_id is not None:
        m_index = utils.find_dict(data, 'match_id', match_id)
    if m_index is None:
        print('Failed to locate match in csv file')
        return

    match_data = data[m_index]

    if not match.player:
        write(f'Caller was not found in {match.match_id}', color=FgColor.Red)
        return
    else:
        match_data['match_id'] = match.match_id
        match_data['map'] = match.map
        match_data['server'] = match.server
        match_data['timestamp'] = match.timestamp
        match_data['team_score'] = match.score[0]
        match_data['enemy_score'] = match.score[1]
        match_data['outcome'] = match.outcome
        match_data['start_team'] = match.started_as

        player_stats: Stats = match.player.stats
        match_data['kills'] = player_stats.K
        match_data['assists'] = player_stats.A
        match_data['deaths'] = player_stats.D
        match_data['5k'] = player_stats.K5
        match_data['4k'] = player_stats.K4
        match_data['3k'] = player_stats.K3
        match_data['2k'] = player_stats.K2
        match_data['1k'] = player_stats.K1
        match_data['ADR'] = round(float(player_stats.ADR))
        match_data['HS%'] = re.sub(r'\D', '', player_stats.HS)
        match_data['KAST'] = re.sub(r'\D', '', player_stats.KAST)
        match_data['HLTV'] = round(float(player_stats.HLTV) * 100)
        match_data['rank'] = f'{match.player.rank.rank_int}{match.player.rank.rank_change}'
        match_data['username'] = match.player.username

        try:
            match_data['K/D'] = round((float(player_stats.K) / float(player_stats.D)) * 100)
        except (ZeroDivisionError, ValueError):
            match_data['K/D'] = '∞'

    utils.write_data_csv(csv_path, data, consts.csv_header)
    return match_data


def send_discord_msg(discord_data, webhook_url: str, username: str = 'Auto Acceptor'):
    discord_data['username'] = username
    r = requests.post(webhook_url, data=json.dumps(discord_data), headers={"Content-Type": "application/json"})
    try:
        remaining_requests = int(r.headers['x-ratelimit-remaining'])
    except KeyError:
        write(f'KeyError with status code {r.status_code}')
        remaining_requests = 1
    if remaining_requests == 0:
        ratelimit_wait = abs(int(r.headers['x-ratelimit-reset']) - time.time() + 0.2)
        print(f'sleeping {ratelimit_wait}s to prevent hitting the discord webhook rate limit')
        time.sleep(ratelimit_wait)


def add_players_to_list(match_data: Match, steam_id):
    player_list_path = os.path.join(os.getenv('APPDATA'), 'CSGO AUTO ACCEPT', f'player_list_{steam_id}.csv')
    data = utils.get_csv_list(player_list_path, consts.player_list_header)
    for i, _dict in enumerate(data):
        data[i]['seen_in'] = utils.convert_string_to_list(_dict['seen_in'])
    all_player = list(itertools.chain.from_iterable(match_data.players))
    players = [player for player in all_player if player != steam_id]

    for player in players:
        player: CSSPlayer
        i = utils.find_dict(data, 'steam_id', player.steam_id)

        if i is not None:
            data[i]['name'] = player.username
            data[i]['seen_in'].append(int(match_data.match_id))
            data[i]['seen_in'] = sorted(list(set(data[i]['seen_in'])))
            data[i]['timestamp'] = match_data.timestamp if int(data[i]['timestamp']) < int(match_data.timestamp) else data[i]['timestamp']
        else:
            data.append({'steam_id': player.steam_id, 'name': player.username, 'seen_in': [int(match_data.match_id)], 'timestamp': match_data.timestamp})

    data.sort(key=lambda x: (len(x['seen_in']), int(x['timestamp'])), reverse=True)
    utils.write_data_csv(player_list_path, data, consts.player_list_header)


def add_players_to_db(match_data: Match, steam_id):
    player_db_path = os.path.join(os.getenv('APPDATA'), 'CSGO AUTO ACCEPT', f'player_list_{steam_id}.db')
    utils.create_table(player_db_path)

    all_player = list(itertools.chain.from_iterable(match_data.players))
    players = [player for player in all_player if player != steam_id]

    seen_players = utils.get_players_from_db(player_db_path, [player.steam_id for player in players])
    new_players = []

    for player in players:
        player: CSSPlayer
        i = utils.find_dict(seen_players, 'steam_id', int(player.steam_id))

        if i is not None:
            seen_players[i]['name'] = player.username
            match_ids = seen_players[i]['match_ids']
            match_ids.append(match_data.match_id)
            match_ids = sorted(map(int, set(match_ids)))
            seen_players[i]['match_count'] = len(match_ids)
            seen_players[i]['match_ids'] = ';'.join(map(str, match_ids))

            seen_players[i]['timestamp'] = match_data.timestamp if int(seen_players[i]['timestamp']) < int(match_data.timestamp) else seen_players[i]['timestamp']
        else:
            new_players.append({'steam_id': player.steam_id, 'name': player.username, 'match_ids': match_data.match_id, 'match_count': 1, 'timestamp': match_data.timestamp})
    utils.add_and_update_players(player_db_path, seen_players, new_players)


def generate_table(match, account):
    def create_field(field: tuple):
        return {
            'name': field[0],
            'value': str(field[1]),
            'inline': field[2]
        }

    avatar_url = account['avatar_url']
    match_time = timedelta(seconds=int(match['match_time']) if match['match_time'] else 0)
    search_time = timedelta(seconds=int(match['wait_time']) if match['wait_time'] else 0)
    afk_time = timedelta(seconds=int(match['afk_time']) if match['afk_time'] else 0)
    afk_per_round = timedelta(seconds=int(int(match['afk_time']) / (int(match['team_score']) + int(match['enemy_score']))) if match['afk_time'] else 0)
    mvps = match['mvps'] if match['mvps'] else '0'
    points = match['points'] if match['points'] else '0'

    rank_names = ['None',
                  'S1', 'S2', 'S3', 'S4', 'SE', 'SEM',
                  'GN1', 'GN2', 'GN3', 'GNM',
                  'MG1', 'MG2', 'MGE', 'DMG',
                  'LE', 'LEM', 'SMFC', 'GE']

    rank_integer = int(re.sub(r'\D', '', match['rank']))
    rank_changed = re.sub(r'[\d ]', '', match['rank'])
    if '+' in rank_changed:
        rank_changed = 'up-ranked'
    elif '-' in rank_changed:
        rank_changed = 'de-ranked'

    rank_name = f'{rank_names[rank_integer]} ({rank_changed})' if rank_changed else rank_names[rank_integer]

    try:
        match_kd = f'{float(match["K/D"]) / 100:.2f}'
    except ValueError:
        match_kd = match["K/D"]

    url = 'https://csgostats.gg/match/' + match['match_id']

    field_values = [('Map', match['map'], True), ('Score', '{:02d} **:** {:02d}'.format(int(match['team_score']), int(match['enemy_score'])), True), ('Username', match['username'], True),
                    ('Kills', match['kills'], True), ('Assists', match['assists'], True), ('Deaths', match['deaths'], True),
                    ('MVPs', mvps, True), ('Points', points, True), ('\u200B', '\u200B', True),
                    ('K/D', match_kd, True), ('ADR', match['ADR'], True), ('HS%', f'{match["HS%"]}%', True),
                    ('5k', match['5k'], True), ('4k', match['4k'], True), ('3k', match['3k'], True),
                    ('2k', match['2k'], True), ('1k', match['1k'], True), ('HLTV-Rating', f'{float(match["HLTV"]) / 100:.2f}', True),
                    ('Rank', rank_name, True), ('Server', match['server'], True), ('AFK per round', afk_per_round, True),
                    ('Match Duration', match_time, True), ('Search Time', search_time, True), ('AFK Time', afk_time, True)
                    ]

    return {'embeds': [{'author': {'name': 'csgostats.gg', 'url': url, 'icon_url': ''}, 'color': account["color"],
                        'footer': {'text': 'CS:GO', 'icon_url': 'https://i.imgur.com/qlBV96I.png'}, 'timestamp': utils.epoch_to_iso(match['timestamp']),
                        'fields': [create_field(i) for i in field_values]}], 'avatar_url': avatar_url}
