import re
import sqlite3
import time
from typing import List

import pyperclip
import requests

from csgostats.Match.Match import match_from_web_request
from csgostats.objects.Errors import PlayerNotFoundError

from write import *


class CSGOStatsUpdater:
    def __init__(self, cfg, account, db_path):
        self.cfg = cfg
        self.account = account
        self.db_path = db_path
        self.queue_difference = []
        self.last_retry = time.time()

    def new_account(self, account):
        self.account = account

    def check_status(self):
        try:
            r = requests.get(f'http://{self.cfg.server_ip}:{self.cfg.server_port}/', timeout=0.5)
            return r.status_code == 200
        except requests.ConnectionError:
            return False

    def update_csgo_stats(self, new_codes: List[dict], discord_output: bool = False):
        sharecodes = [match_dict['sharecode'] for match_dict in new_codes]
        try:
            r = requests.post(f'http://{self.cfg.server_ip}:{self.cfg.server_port}/matches', json={'sharecodes': sharecodes})
            if r.status_code != 200:
                write(red(f'ERROR: {r.status_code}, {r.text}'))
                return new_codes
        except requests.ConnectionError:
            write(red('CSGO Discord Bot OFFLINE'))
            return []
        data = r.json()

        completed_games = []
        not_completed_games = []
        corrupt_games = []
        for sharecode in sharecodes:
            try:
                raw_match: dict = data[sharecode]
            except KeyError:
                write(red(f'{repr(sharecode)} not in response!'))
                continue
            if raw_match['status'] == 'complete':
                match = match_from_web_request(raw_match['object'], raw_match['key'], self.cfg.secret)
                completed_games.append(match)
            elif raw_match['status'] == 'error':
                # un-completable sharecode
                raw_match['sharecode'] = sharecode
                corrupt_games.append(raw_match)
            else:
                raw_match['sharecode'] = sharecode
                not_completed_games.append(raw_match)

        if not_completed_games:
            temp_string = ''
            for i, val in enumerate(not_completed_games, start=1):
                if val['status'] != 'waiting':
                    queue_pos_obj = re.search(r'in Queue #(\d+)', val["msg"])
                    if queue_pos_obj is not None:
                        val["queue_pos"] = int(queue_pos_obj.group(1))
                    else:
                        val["queue_pos"] = 0
                    temp_string += f'#{i}: in Queue #{val["queue_pos"]} - '
                else:
                    temp_string += f'#{i}: Waiting - '
                    val['queue_pos'] = 0

            temp_string = temp_string.rstrip(' - ')
            write(temp_string, add_time=False, overwrite='4')

        self.last_retry = time.time()
        # new_codes = [game for game in corrupt_games]
        # new_codes.extend(csgostats_error)  # don't know yet when csgostats would error

        if corrupt_games:
            erred_games_string = 'An error occurred in one game' if len(corrupt_games) == 1 else f'An error occurred in {len(corrupt_games)} games'
            write(erred_games_string, overwrite='5')
            with sqlite3.connect(self.db_path) as db:
                for val in corrupt_games:
                    sql_str = """UPDATE matches SET error = 1 WHERE sharecode = ?"""
                    sharecode = val['sharecode']
                    db.execute(sql_str, (sharecode,))
                db.commit()

        if completed_games:
            with sqlite3.connect(self.db_path) as db:
                db.row_factory = sqlite3.Row
                for match in completed_games:
                    url = match.match_url()
                    write(green(f'URL: {url}'), add_time=True)
                    try:
                        sql_data = match.sql_tuple(int(self.account.steam_id))
                        sql_str = '''UPDATE matches SET id = ?,
                                                        map = ?,
                                                        team_score = ?,
                                                        enemy_score = ?,
                                                        outcome = ?,
                                                        start_team = ?,
                                                        kills = ?,
                                                        assists = ?,
                                                        deaths = ?,
                                                        [5k] = ?,
                                                        [4k] = ?,
                                                        [3k] = ?,
                                                        [2k] = ?,
                                                        [1k] = ?,
                                                        KD = ?,
                                                        ADR = ?,
                                                        HS = ?,
                                                        KAST = ?,
                                                        HLTV1 = ?,
                                                        HLTV2 = ?,
                                                        rank = ?,
                                                        rank_change = ?,
                                                        name = ?,
                                                        server = ?,
                                                        timestamp = ?,
                                                        cs2 = ?
                                                    WHERE sharecode = ?'''
                    except PlayerNotFoundError:
                        sql_str = '''UPDATE matches SET id = ?,
                                                        map = ?,
                                                        server = ?,
                                                        timestamp = ?
                                                    WHERE sharecode = ?'''
                        sql_data = (match.match_id, match.map, match.server, match.timestamp, match.sharecode)
                    db.execute(sql_str, sql_data)
                db.commit()

                if discord_output:
                    discord_matches = []
                    for match in completed_games:
                        sql_str = """SELECT id, match_time, wait_time, afk_time, mvps, points FROM matches WHERE sharecode = ? AND steam_id = ?"""
                        cur = db.execute(sql_str, (match.sharecode, int(self.account.steam_id)))
                        sql_match = dict(cur.fetchone())
                        sql_match['steam_id'] = int(self.account.steam_id)
                        discord_matches.append(sql_match)
                    r = requests.post(f'http://{self.cfg.server_ip}:{self.cfg.server_port}/discord_msg', json=discord_matches)
                    if r.status_code != 200:
                        write(f'failed to request discord message, {repr(r.text)}')

                if self.cfg.copy_to_clipboard:
                    try:
                        pyperclip.copy(url)
                    except (pyperclip.PyperclipWindowsException, pyperclip.PyperclipTimeoutException):
                        write('Failed to load URL in to clipboard', add_time=False)
        return not_completed_games
