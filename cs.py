import configparser
import csv
import glob
import hashlib
import json
import operator
import os
import queue
import random
import re
import sqlite3
import subprocess
import threading
import time
import winreg
from dataclasses import dataclass
from datetime import datetime
from datetime import timedelta as td
from enum import Enum
from pathlib import Path
from shutil import copyfile
from typing import List, Union

import playsound
import requests
import win32api
import win32con
import win32gui
import win32process
from PIL import ImageGrab, Image
from pytz import utc

from ConsoleInteraction import TelNetConsoleReader
from GSI import server
from csgostats.Log import LogReader
from objects.Account import get_accounts_from_cfg
from utils import *
from write import *
from ConfigValidator import fix_config


def mute_csgo(lvl: int):
    global path_vars

    subprocess.run(f'{path_vars.mute_csgo} {lvl}')
    if lvl == 2:
        write('Mute toggled!', add_time=False)


def timedelta(then=None, seconds=None):
    if seconds is not None:
        return str(td(seconds=abs(int(seconds))))
    else:
        now = time.time()
        return str(td(seconds=abs(int(now - then))))


# noinspection PyShadowingNames
def click(location: tuple, lmb: bool = True):
    x = location[0]
    y = location[1]
    set_mouse_position(location)
    if lmb:
        win32api.mouse_event(win32con.MOUSEEVENTF_LEFTDOWN, x, y, 0, 0)
        win32api.mouse_event(win32con.MOUSEEVENTF_LEFTUP, x, y, 0, 0)
    else:
        win32api.mouse_event(win32con.MOUSEEVENTF_RIGHTDOWN, x, y, 0, 0)
        win32api.mouse_event(win32con.MOUSEEVENTF_RIGHTUP, x, y, 0, 0)


def set_mouse_position(location: tuple):
    position = (int(location[0] * 65536 / win32api.GetSystemMetrics(win32con.SM_CXSCREEN)),
                int(location[1] * 65535 / win32api.GetSystemMetrics(win32con.SM_CYSCREEN)))
    win32api.mouse_event(win32con.MOUSEEVENTF_MOVE | win32con.MOUSEEVENTF_ABSOLUTE, position[0], position[1])


def minimize_csgo(window_id: int):
    try:
        win32gui.PostMessage(window_id, win32con.WM_SYSKEYDOWN, 0x1B, 0)
        win32gui.PostMessage(window_id, win32con.WM_SYSKEYUP, 0x1B, 0)
    except BaseException as e:
        if e.args[0] == 1400:
            pass
        else:
            raise e


def anti_afk_tel(tl: TelNetConsoleReader, is_active: bool):
    if is_active:
        tl.send('-right')
        tl.send('-forward')
    else:
        tl.send('+right')
        tl.send('+forward')


# noinspection PyShadowingNames
def relate_list(l_org, compare_list, relate: operator = operator.le):
    if not l_org:
        return False
    compared = [list(map(relate, l_part, compare_list)) for l_part in l_org]
    compared = any(all(compare_part) for compare_part in compared)
    return compared


# noinspection PyShadowingNames
def color_average(image: Image, compare_list: list):
    avg_image = image.resize((1, 1))
    rgb = list(avg_image.getpixel((0, 0)))
    compared = [list(map(operator.sub, rgb, compare_rgb)) for compare_rgb in compare_list]
    compared = [list(map(abs, compare_part)) for compare_part in compared]
    return compared


# noinspection PyShadowingNames
def get_screenshot(window_id: int, area: tuple = (0, 0, 0, 0)):
    area = list(area)
    win32gui.ShowWindow(window_id, win32con.SW_MAXIMIZE)
    scaled_area = [win32api.GetSystemMetrics(0) / 2560, win32api.GetSystemMetrics(1) / 1440]
    scaled_area = 2 * scaled_area
    for i, _ in enumerate(area[-2:], start=len(area) - 2):
        area[i] += 1
    for i, val in enumerate(area, start=0):
        scaled_area[i] = scaled_area[i] * val
    scaled_area = list(map(int, scaled_area))
    image = ImageGrab.grab(scaled_area)
    return image


# noinspection PyShadowingNames
def get_current_steam_user():
    try:
        steam_reg_key = winreg.OpenKey(winreg.HKEY_CURRENT_USER, r'Software\Valve\Steam\ActiveProcess')
        current_user = winreg.QueryValueEx(steam_reg_key, 'ActiveUser')[0]
        if not current_user:
            return ''
        return str(current_user + 76561197960265728)
    except OSError:
        return ''


# noinspection PyShadowingNames
def check_userdata_autoexec(steam_id_3: str):
    global path_vars, cfg
    userdata_path = os.path.join(path_vars.steam, 'userdata', steam_id_3, '730', 'local', 'cfg')
    str_in_autoexec = ['sv_max_allowed_developer 1', 'developer 1', 'con_allownotify 0']
    os.makedirs(userdata_path, exist_ok=True)
    with open(os.path.join(userdata_path, 'autoexec.cfg'), 'a+') as autoexec:
        autoexec.seek(0)
        lines = autoexec.readlines()
        for autoexec_str in str_in_autoexec:
            if not any(autoexec_str.lower() in line.rstrip('\n').lower() for line in lines):
                write(yellow(f'Added "{autoexec_str}" to "autoexec.cfg"'), add_time=False)
                write(red('RESTART Counter-Strike for the script to work'), add_time=False)
                autoexec.write(f'\n{autoexec_str}\n')

    if os.path.exists(os.path.join(path_vars.csgo, 'cfg', 'autoexec.cfg')):
        write(
            red(f'YOU HAVE TO DELETE THE "autoexec.cfg" in {os.path.join(path_vars.csgo, "cfg")} AND MERGE IT WITH THE ONE IN {userdata_path}'),
            add_time=False)
        write(red(f'THE SCRIPT WONT WORK UNTIL THERE IS NO "autoexec.cfg" in {os.path.join(path_vars.csgo, "cfg")}'),
              add_time=False)


# noinspection PyShadowingNames
def get_avg_match_time(steam_id: int):
    with sqlite3.connect(path_vars.db) as db:
        cur = db.execute(
            """SELECT AVG(match_time), SUM(match_time), AVG(wait_time), SUM(wait_time) FROM matches WHERE steam_id = ?""",
            (steam_id,))
        match_avg, match_sum, search_avg, search_sum = cur.fetchone()
        cur = db.execute(
            """SELECT SUM(afk_time), COUNT(afk_time), SUM(team_score + enemy_score) FROM matches WHERE steam_id = ? AND afk_time NOT NULL""",
            (steam_id,))
        afk_sum, afk_count, rounds_sum = cur.fetchone()

    data = {}
    if match_avg is not None and match_sum is not None:
        data['match_time'] = (round(match_avg, 0), match_sum)
    else:
        data['match_time'] = (0, 0)

    if search_avg is not None and search_sum is not None:
        data['search_time'] = (round(search_avg, 0), search_sum)
    else:
        data['search_time'] = (0, 0)

    if afk_sum is not None and afk_count != 0:
        data['afk_time'] = round(afk_sum / afk_count), afk_sum, round(afk_sum / rounds_sum, 0)
    else:
        data['afk_time'] = 0, 0, 0

    return data


def add_first_match(path):
    if not account.match_token:
        raise ValueError('Missing Match Token in Config')
    create_table(path, account.match_token, account.steam_id)
    return [account.match_token]


# noinspection PyShadowingNames
def get_old_sharecodes(last_x: int):
    if last_x >= 0:
        return []
    path = path_vars.db
    if os.path.isfile(path):
        with sqlite3.connect(path) as db:
            cur = db.execute("""SELECT sharecode FROM matches WHERE steam_id = ? ORDER BY timestamp DESC LIMIT ?""",
                             (steam_id, abs(last_x)))
            games = [sharecode for sharecode, in cur.fetchall()]
        if len(games) == 0:
            # table already exists, but its the first match for a user
            games = add_first_match(path)
    else:
        games = add_first_match(path)

    return games


# noinspection PyShadowingNames
def get_new_sharecodes(game_id: str, stats=None):
    sharecodes = [game_id]
    stats_error = True
    while True:
        steam_url = f'https://api.steampowered.com/ICSGOPlayers_730/GetNextMatchSharingCode/v1?key={cfg.steam_api_key}&steamid={steam_id}&steamidkey={account.auth_code}&knowncode={game_id}'
        try:
            r = requests.get(steam_url, timeout=2)
            next_code = r.json()['result']['nextcode']
        except (
        KeyError, requests.exceptions.ConnectionError, requests.exceptions.Timeout, json.decoder.JSONDecodeError) as e:
            write(red(f'STEAM API ERROR! Error: "{e}"'))
            break
        if r.status_code == 200:  # new match has been found
            sharecodes.append(next_code)
            game_id = next_code
            time.sleep(0.5)
        elif r.status_code == 202:  # no new match has been found
            if stats is None or len(sharecodes) > 1:
                if stats_error is False:
                    write(green('got a match code for the given stats'))
                break
            else:
                if stats_error is True:
                    write(yellow('new match stats were given, yet steam api gave no new sharecode'))
                    stats_error = False
                time.sleep(2)

    path = path_vars.db
    with sqlite3.connect(path) as db:
        if len(sharecodes) > 1:
            # > 1 is true if there is a new sharecode, first sharecode is the last supplied one

            # add all matches expect the newest one without any extra data
            db_data = [(sharecode, int(steam_id), 0.0) for sharecode in sharecodes[:-1]]
            db.executemany("""INSERT OR IGNORE INTO matches (sharecode, steam_id, timestamp) VALUES (?, ?, ?)""",
                           db_data)

            if stats is None:
                stats = {'map': None, 'match_time': None, 'wait_time': None, 'afk_time': None, 'mvps': None,
                         'score': None}
            if 'mvps' not in stats:
                stats = {'map': None, 'match_time': None, 'wait_time': None, 'afk_time': None, 'mvps': None,
                         'score': None}

            now = datetime.now(tz=utc).timestamp()
            match_data = (
            sharecodes[-1], int(steam_id), stats['match_time'], stats['wait_time'], stats['afk_time'], stats['mvps'],
            stats['score'], now)
            db.execute(
                """INSERT OR IGNORE INTO matches (sharecode, steam_id, match_time, wait_time, afk_time, mvps, points, timestamp) VALUES (?, ?, ?, ?, ?, ?, ?, ?)""",
                match_data)
            db.commit()

        # Test if any tracked match has missing info
        cur = db.execute(
            """SELECT sharecode FROM matches WHERE map IS NULL AND error = 0 and steam_id = ? ORDER BY timestamp ASC""",
            (int(steam_id),))
        sharecodes = cur.fetchall()

    return [{'sharecode': code, 'queue_pos': None} for code, in sharecodes]


def check_for_forbidden_programs(process_list):
    if cfg.forbidden_programs == 'None':
        return False

    titles = [i[1].lower() for i in process_list]
    forbidden_programs = [i.lstrip(' ').lower() for i in cfg.forbidden_programs.split(',')]
    if forbidden_programs[0]:
        return any(name for name in titles for forbidden_name in forbidden_programs if forbidden_name == name)
    else:
        return False


@dataclass()
class ConsoleLog:
    msg: List[str] = None
    update: List[str] = None
    players_accepted: List[str] = None
    lobby_data: List[str] = None
    server_abandon: List[str] = None
    map: List[str] = None
    server_settings: List[str] = None
    server_found: bool = False
    server_ready: bool = False

    @classmethod
    def from_log(cls, log_str: List[str]):
        replace_items = {}
        bool_items = {}

        replace_checks = [('msg', 'Matchmaking message: '),
                          ('update', 'Matchmaking update: '),
                          ('players_accepted', 'Server reservation2 is awaiting '),
                          ('lobby_data', 'LobbySetData: '),
                          ('server_abandon', ['Closing Steam Net Connection to =', 'Kicked by Console']),
                          ('map', 'Map: '),
                          ('server_settings', 'SetConVar: mp_')]

        bool_checks = [('server_found', 'Matchmaking reservation confirmed: '),
                       ('server_ready', 'ready-up!')]

        for _str in log_str:
            for key, item in replace_checks:
                if not isinstance(item, (list, tuple)):
                    item = [item]
                try:
                    for check in item:
                        if check in _str:
                            if key not in replace_items:
                                replace_items[key] = []
                            replace_items[key].append(_str.replace(item[0], ''))
                            raise ItemFound()
                except ItemFound:
                    break

            for key, check in bool_checks:
                if check in _str:
                    bool_items[key] = True
                    break

        return cls(**{**replace_items, **bool_items})


def activate_afk_message():
    global afk_message
    if not cfg.discord_user_id:
        write(red('No User ID set in config'))
        return
    afk_message = not afk_message
    if afk_message is True:
        write(green('Sending AFK Messages'), overwrite='2')
    else:
        write(magenta('NOT sending AFK Messages'), overwrite='2')


def round_start_msg(msg: str, round_phase: str, freezetime_start: float, current_window_status: bool, scoreboard,
                    overwrite_key: str = '7'):
    if round_phase == 'freezetime':
        # timer_stopped = ''
        old_window_status = True
    elif current_window_status:
        old_window_status = True
        # timer_stopped = ' - ' + green('stopped')
    else:
        old_window_status = False

    freeze_time = scoreboard.freeze_time
    buy_time = scoreboard.buy_time

    if round_phase == 'freezetime':
        time_str = green(timedelta(seconds=time.time() - (freezetime_start + freeze_time)))
    elif time.time() - freezetime_start > freeze_time + buy_time:
        time_str = red(timedelta(then=freezetime_start))
    else:
        time_str = yellow(timedelta(seconds=time.time() - (freezetime_start + freeze_time + buy_time)))

    msg += f' - {time_str}'
    write(msg, overwrite=overwrite_key)
    scoreboard.round_message = msg
    return old_window_status


def time_output(current: Union[float, int], average: Union[float, int]):
    difference = abs(current - average)
    if current <= average:
        return f'{timedelta(seconds=current)}, {timedelta(seconds=difference)} {green("shorter")} than average of {timedelta(seconds=average)}'
    else:
        return f'{timedelta(seconds=current)}, {timedelta(seconds=difference)} {red("longer")}  than average of {timedelta(seconds=average)}'


def is_program_alive(exe_name: str = 'csgo.exe'):
    r = subprocess.check_output(f'tasklist /FI "IMAGENAME EQ {exe_name}" /FO "CSV"', shell=False)
    procs = [line.decode('utf-8', errors='ignore') for line in r.splitlines()]
    data = list(csv.DictReader(procs))
    return len(data) >= 1


class ProcessNotFoundError(BaseException):
    def __init__(self, name):
        super().__init__(f'no process found for "{name}"')


class WindowNotFoundError(BaseException):
    def __init__(self, name):
        super().__init__(f'no window found for "{name}"')


class ItemFound(BaseException):
    def __init__(self):
        super().__init__()


class MatchRequest(threading.Thread):
    """Using a thread, so we are not blocking the script while performing the request"""

    def __init__(self):
        super().__init__()
        self.name = 'MatchRequester'
        self.daemon = True

    def run(self) -> None:
        match_log = None
        start = time.time()
        while match_log is None:
            match_log = log_reader.get_log_info()
            if time.time() - start > 7.5:
                write(yellow('found no match log after 7.5s'))
                return
            time.sleep(0.5)
        data = match_log.to_web_request(cfg.secret, steam_id)
        url = f"http://{cfg.server_ip}:{cfg.server_port}/check"
        try:
            r = requests.post(url, json=data)
            if r.status_code != 200:
                write(
                    f'failed to send check match message to {repr(cfg.server_ip)} with status {r.status_code} - {r.text}')
        except requests.ConnectionError:
            write(red('CSGO Discord Bot OFFLINE'))
        return


def round_wins_since_reset(_steam_id: int) -> int:
    last_wednesday = datetime.now(tz=utc).replace(hour=0, minute=1, second=0, microsecond=0)
    while last_wednesday.weekday() != 2:
        last_wednesday -= td(days=1)

    with sqlite3.connect(path_vars.db) as db:
        cur = db.execute("""SELECT SUM(team_score) FROM matches WHERE steam_id = ? and timestamp > ?""",
                         (_steam_id, int(last_wednesday.timestamp())))
    r, = cur.fetchone()
    return r or 0


def match_win_list(number_of_matches: int, _steam_id, time_difference: int = 7_200, replace_chars: bool = False):
    with sqlite3.connect(path_vars.db) as db:
        cur = db.execute(
            """SELECT outcome, timestamp, team_score, enemy_score FROM matches WHERE steam_id = ? ORDER BY timestamp DESC LIMIT ?""",
            (_steam_id, abs(number_of_matches)))
        items = cur.fetchall()
    outcome_lst = []
    short_match_intro = datetime(year=2021, month=9, day=21, hour=1, tzinfo=utc).timestamp()
    for outcome, timestamp, score_1, score_2 in items:
        if not outcome:
            outcome = 'U'
        if not timestamp:
            timestamp = datetime.now(tz=utc).timestamp() - (60 * 60)

        if replace_chars:
            char = ''
        elif not score_1 or not score_2:
            char = '\u2588'  # unknown
        elif score_1 == 16 or score_2 == 16:
            char = '\u2588'  # long match win
        elif score_1 + score_2 == 30:
            char = '\u2588'  # long match draw
        elif timestamp < short_match_intro and (score_1 != 16 and score_2 != 16):
            char = '\u2593'  # surrender
        elif score_1 == 9 or score_2 == 9:
            char = '\u2584'  # short match win (might be surrender)
        elif score_1 == 8 and score_2 == 8 and outcome == 'D':
            char = '\u2584'  # short match draw
        else:
            char = '\u2593'  # surrender

        if outcome == 'W':
            if not char:
                char = 'W'
            outcome_lst.append((timestamp, green(char)))
        elif outcome == 'L':
            if not char:
                char = 'L'
            outcome_lst.append((timestamp, red(char)))
        elif outcome == 'D':
            if not char:
                char = 'D'
            outcome_lst.append((timestamp, blue(char)))
        else:
            if not char:
                char = 'U'
            outcome_lst.append((timestamp, magenta(char)))

    start = outcome_lst[0][0]
    group = 0
    outcome_groups = [[]]
    for timestamp, outcome in outcome_lst:
        if start - timestamp > time_difference:
            outcome_groups.append([])
            group += 1
        start = timestamp
        outcome_groups[group].append(outcome)
    return '\u007c \u007c'.join(['\u007c'.join(group) for group in outcome_groups])


# noinspection PyShadowingNames
class WindowEnumerator(threading.Thread):
    def __init__(self, exe_name: str, window_name: str, sleep_interval: float = 0.75):
        super().__init__(name='WindowEnumerator', daemon=True)
        self._interval = sleep_interval
        self._exe_name = exe_name
        self._window_name = window_name.lower()

        self.window_ids = []
        self.hwnd: int = 0

    def get_hwnd(self):
        win32gui.EnumWindows(self.enum_cb, self.window_ids)
        r = subprocess.check_output(f'tasklist /FI "IMAGENAME EQ {self._exe_name}" /FO "CSV"', shell=False)
        procs = [line.decode('utf-8', errors='ignore') for line in r.splitlines()]
        data = list(csv.DictReader(procs))
        if len(data) <= 0:
            self.hwnd = 0
            return self.hwnd

        pid = int(data[0]["PID"])
        for window_id, title, cpid in self.window_ids:
            if cpid != pid:
                continue
            if self._window_name in title.lower():
                self.hwnd = window_id
                break
        else:
            self.hwnd = 0
        return self.hwnd

    def run(self):
        while True:
            self.get_hwnd()
            time.sleep(self._interval)

    @staticmethod
    def enum_cb(hwnd: int, results: list):
        _, cpid = win32process.GetWindowThreadProcessId(hwnd)
        name = win32gui.GetWindowText(hwnd)
        results.append((hwnd, name, cpid))

    def restart_gsi_server(self, gsi_server: server.GSIServer = None):
        if gsi_server is None:
            gsi_server = server.GSIServer(('127.0.0.1', 3000), "IDONTUSEATOKEN")
        elif gsi_server.running:
            gsi_server.shutdown()
            if self.get_hwnd() != 0:
                gsi_server = server.GSIServer(('127.0.0.1', 3000), "IDONTUSEATOKEN")
                gsi_server.start_server()
            else:
                gsi_server = server.GSIServer(('127.0.0.1', 3000), "IDONTUSEATOKEN")
        else:
            gsi_server.start_server()
        return gsi_server


@dataclass()
class PathVars:
    appdata: str = os.path.join(os.getenv('APPDATA'), 'CSGO AUTO ACCEPT')
    mute_csgo: str = f'"{os.path.abspath(os.path.expanduser("sounds/nircmdc.exe"))}" muteappvolume csgo.exe'
    db: str = os.path.join(os.path.join(os.getenv('APPDATA'), 'CSGO AUTO ACCEPT', 'matches.db'))
    csgo: str = None
    steam: str = None

    def __post_init__(self):
        steam_reg_key = winreg.OpenKey(winreg.HKEY_LOCAL_MACHINE, r'SOFTWARE\WOW6432Node\Valve\Steam')
        steam_path = winreg.QueryValueEx(steam_reg_key, 'InstallPath')[0]
        libraries = [os.path.join(steam_path, 'steamapps')]
        with open(os.path.join(steam_path, 'steamapps', 'libraryfolders.vdf'), 'r', encoding='utf-8') as library_file:
            for line in library_file:
                folder_object = re.search(r'"path"\s*"(.+)"', line)
                if folder_object is not None:
                    libraries.append(os.path.join(Path(folder_object.group(1)), 'steamapps'))

        for library in libraries:
            if os.path.exists(os.path.join(library, 'appmanifest_730.acf')):
                csgo_path = os.path.join(library, 'common', 'Counter-Strike Global Offensive', 'csgo')
                break
        else:
            write(red('DID NOT FIND CSGO PATH'), add_time=False)
            csgo_path = ''
        global path_vars
        self.csgo = csgo_path
        self.steam = steam_path


class SoundPlayer(threading.Thread):
    def __init__(self):
        super(SoundPlayer, self).__init__()
        self.queue = queue.Queue()
        self.daemon = True
        self.name = 'SoundPlayer'

    def play(self, path: str, block: bool = True):
        self.queue.put(path, block=True, timeout=None)
        return

    def run(self) -> None:
        while True:
            path = self.queue.get(block=True, timeout=None)
            playsound.playsound(sound=path, block=True)


@dataclass()
class Sounds:
    button_found: str = 'sounds/accept_found.wav'
    activated: str = 'sounds/activated.wav'
    not_all_accepted: str = 'sounds/back_to_testing.wav'
    deactivated: str = 'sounds/deactivated.wav'
    ding: str = 'sounds/ding.wav'
    all_accepted: str = 'sounds/done_testing.wav'
    fail: str = 'sounds/fail.wav'
    accept_failed: str = 'sounds/failed_to_accept.wav'
    minute_warning: str = 'sounds/minute_warning.wav'
    ready: str = 'sounds/ready_up.wav'
    server_found: str = 'sounds/server_found.wav'


class SoundMatch(Enum):
    button_found = 0
    activated = 1
    not_all_accepted = 2
    ding = 3
    all_accepted = 4
    fail = 5
    accept_failed = 6
    ready = 7
    server_found = 8


def get_sounds(get_web_sounds: bool = True):
    if not cfg.web_sounds or not get_web_sounds:
        return Sounds()
    if cfg.web_sounds and get_web_sounds:
        base = 'sounds/web_sounds'
        os.makedirs(base, exist_ok=True)
        files = [os.path.basename(path) for path in glob.glob(os.path.join(base, '*_*.wav'))]
        file_hash = hashlib.sha256('#'.join(files).encode()).hexdigest()

        url = f'http://{cfg.server_ip}:{cfg.server_port}/sound_hash'
        base_url = f'http://{cfg.server_ip}:{cfg.server_port}/sounds/'
        try:
            r = requests.get(url, timeout=0.5)
            if r.status_code != 200:
                return get_sounds(False)
        except (requests.ConnectionError, requests.ConnectTimeout):
            write(yellow('Loading default sounds since server is not responding'))
            return get_sounds(False)
        info = r.json()
        if file_hash != info['hash']:
            write(f'Miss-matched hash between server sound files and local files!')
            to_delete = []
            for i, file in enumerate(files):
                for s_file in info['items']:
                    if file == s_file:
                        break
                else:
                    to_delete.append((i, file))

            to_delete.sort(key=lambda x: x[0], reverse=True)
            for idx, filename in to_delete:
                os.remove(os.path.join(base, filename))
                write(f'removed {filename} from local since its no longer on the server')
                files.pop(idx)
            with requests.Session() as session:
                for s_file in info['items']:
                    for file in files:
                        if s_file == file:
                            break
                    else:
                        r = session.get(base_url + s_file)
                        if r.status_code != 200:
                            write(red(f'failed to download "{s_file}" from server'))
                        write(f'added "{s_file}" to local sound bib')
                        with open(os.path.join(base, s_file), 'wb') as fp:
                            fp.write(r.content)
        files = [os.path.basename(path) for path in glob.glob(os.path.join(base, '*_*.wav'))]
        sorted_files = {}
        for file in files:
            obj = re.search(r'(\d)_\d+\.wav', file)
            if obj is None:
                write(f'failed to defer use case from "{file}"')
                continue
            use_case = int(obj.group(1))
            if use_case not in sorted_files:
                sorted_files[use_case] = [file]
            else:
                sorted_files[use_case].append(file)
        out = Sounds()
        random.seed(os.urandom(128))
        for key, value in sorted_files.items():
            use_case = SoundMatch(key)
            if getattr(cfg.sound_usage, use_case.name):
                random_sound = random.choice(value)
                setattr(out, use_case.name, os.path.join(base, random_sound))
        return out


@dataclass()
class UseSounds:
    button_found: bool
    activated: bool
    not_all_accepted: bool
    ding: bool
    all_accepted: bool
    fail: bool
    accept_failed: bool
    ready: bool
    server_found: bool


@dataclass
class ConfigItems:
    webhook_ip: str
    webhook_port: int

    sleep_interval: float
    forbidden_programs: str
    match_list_length: int
    telnet_ip: str
    telnet_port: int
    anti_afk_delay: float
    afk_reset_delay: float

    steam_api_key: str
    auto_retry_interval: int
    status_requester: str
    secret: bytes
    server_ip: str
    server_port: int

    discord_user_id: int

    web_sounds: bool
    sound_usage: UseSounds

    parser: configparser.ConfigParser


subprocess.run('cls', shell=True)
path_vars = PathVars()
os.makedirs(path_vars.appdata, exist_ok=True)

config = configparser.ConfigParser()


def get_cfg(recursion: bool = False):

    config.read('config.ini')
    data = {}
    try:
        data['webhook_ip'] = config.get('HotKeys', 'WebHook IP')
        data['webhook_port'] = config.getint('HotKeys', 'WebHook Port')

        data['sleep_interval'] = config.getfloat('Script Settings', 'Interval')
        data['forbidden_programs'] = config.get('Script Settings', 'Forbidden Programs')
        data['match_list_length'] = config.getint('Script Settings', 'Match History Length')
        data['telnet_ip'] = config.get('Script Settings', 'TelNet IP')
        data['telnet_port'] = config.getint('Script Settings', 'TelNet Port')
        data['anti_afk_delay'] = config.getfloat('Script Settings', 'Anti-AFK Delay')
        data['afk_reset_delay'] = config.getfloat('Script Settings', 'AFK Reset Delay')

        data['steam_api_key'] = config.get('csgostats.gg', 'API Key')
        data['auto_retry_interval'] = config.getint('csgostats.gg', 'Auto-Retrying-Interval')
        data['status_requester'] = config.getboolean('csgostats.gg', 'Status Requester')
        data['secret'] = config.get('csgostats.gg', 'Secret')
        data['server_ip'] = config.get('csgostats.gg', 'WebServer IP')
        data['server_port'] = config.getint('csgostats.gg', 'WebServer Port')

        data['discord_user_id'] = config.getint('Notifier', 'Discord User ID')

        data['web_sounds'] = config.getboolean('Sounds', 'Use Web Sounds')

        sound_data = [
            config.getboolean('Sounds', 'Use button_found'),
            config.getboolean('Sounds', 'Use activated'),
            config.getboolean('Sounds', 'Use not_all_accepted'),
            config.getboolean('Sounds', 'Use ding'),
            config.getboolean('Sounds', 'Use all_accepted'),
            config.getboolean('Sounds', 'Use fail'),
            config.getboolean('Sounds', 'Use accept_failed'),
            config.getboolean('Sounds', 'Use ready'),
            config.getboolean('Sounds', 'Use server_found'),
        ]
        data['sound_usage'] = UseSounds(*sound_data)
        data['parser'] = config

        config_items: ConfigItems = ConfigItems(**data)
        return config_items
    except (configparser.NoOptionError, configparser.NoSectionError, ValueError) as e:
        if recursion is True:
            write(f'failed to fix config with default values!')
            exit()
        write(f'ERROR IN CONFIG - {str(e)}')
        write(f'trying to fix it!', add_time=False)
        write('', add_time=False)
        fix_config()
        return get_cfg(recursion=True)


cfg = get_cfg()

accounts = get_accounts_from_cfg(cfg.parser)
steam_id = get_current_steam_user()

sounds = get_sounds()
sound_player = SoundPlayer()
sound_player.start()

if not steam_id:
    account = accounts[0]
    steam_id = account.steam_id
    current_steam_account = 0
else:
    for account_number, cfg_account in enumerate(accounts):
        if steam_id == cfg_account.steam_id:
            account = cfg_account
            current_steam_account = account_number
            break
    else:
        write(red(f'Could not find {steam_id} in config file, defaulting to account 0'), add_time=False)
        account = accounts[0]
        steam_id = account.steam_id
        current_steam_account = 0

with open(os.path.join(path_vars.appdata, 'console.log'), 'w', encoding='utf-8') as fp:
    fp.write('')

if path_vars.csgo:
    if not os.path.exists(os.path.join(path_vars.csgo, 'cfg', 'gamestate_integration_GSI.cfg')):
        copyfile(os.path.join(os.getcwd(), 'GSI', 'gamestate_integration_GSI.cfg'),
                 os.path.join(path_vars.csgo, 'cfg', 'gamestate_integration_GSI.cfg'))
        write(red('Added GSI CONFIG to cfg folder. Counter-Strike needs to be restarted if running!'))

afk_message = False

sleep_interval = cfg.sleep_interval
sleep_interval_looking_for_accept = 0.05
log_reader = LogReader(os.path.join(path_vars.appdata, 'console.log'))

lobby_info = re.compile(r"(?<!Machines' = '\d''members:num)(C?TSlotsFree|Players)' = '(\d+'?)")

if __name__ == '__main__':
    def main():
        print('')
        r = round_wins_since_reset(76561199014843546)
        # r = match_win_list(4000, 76561199014843546)
        print(r)


    main()
