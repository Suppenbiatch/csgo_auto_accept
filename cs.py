import configparser
import csv
import json
import operator
import os
import random
import re
import sqlite3
import subprocess
import sys
import threading
import time
import winreg
from dataclasses import dataclass
from datetime import datetime
from datetime import timedelta as td
from pathlib import Path
from shutil import copyfile
from typing import List, Union

import keyboard
import requests
import win32api
import win32con
import win32gui
import win32process
from PIL import ImageGrab, Image
from pytz import utc

from GSI import server
from csgostats.Log import LogReader
from utils import *
from write import *


def mute_csgo(lvl: int):
    global path_vars

    os.system(f'{path_vars["mute_csgo_path"]} {lvl}')
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
    win32gui.PostMessage(window_id, win32con.WM_SYSKEYUP, 0x1B, 0)
    win32gui.PostMessage(window_id, win32con.WM_SYSKEYDOWN, 0x1B, 0)


# noinspection PyShadowingNames
def anti_afk(window_id: int):
    current_cursor_position = win32api.GetCursorPos()
    screen_mid = (int(win32api.GetSystemMetrics(0) / 2), int(win32api.GetSystemMetrics(1) / 2))
    moves = int(win32api.GetSystemMetrics(1) / 3) + 1
    set_mouse_position(screen_mid)
    win32gui.ShowWindow(window_id, win32con.SW_MAXIMIZE)
    for _ in range(moves):
        win32api.mouse_event(win32con.MOUSEEVENTF_MOVE, 0, -15)
    click(screen_mid)
    for _ in range(moves):
        win32api.mouse_event(win32con.MOUSEEVENTF_MOVE, 0, 15)
    for _ in range(int(moves / 1.07)):
        win32api.mouse_event(win32con.MOUSEEVENTF_MOVE, 0, -8)
    time.sleep(0.075)
    set_mouse_position(current_cursor_position)
    minimize_csgo(window_id)


def task_bar(factor: float = 2.0):
    monitor = win32api.GetMonitorInfo(win32api.MonitorFromPoint((0, 0)))
    taskbar_size = tuple(map(operator.sub, monitor['Monitor'], monitor['Work']))
    position_int = [(i, abs(x)) for i, x in enumerate(taskbar_size) if x]
    if len(position_int) != 1:
        write(yellow('Taskbar location failed'), add_time=False)
        return 0, 0
    position_int = position_int[0]
    pos = position_int[0]
    if pos == 0:  # left
        return int(position_int[1] / 2), int(monitor['Monitor'][3] * factor)
    elif pos == 1:  # top
        return int(monitor['Monitor'][2] * factor), int(position_int[1] / 2)
    elif pos == 2:  # right
        return monitor['Monitor'][2] - int(position_int[1] / 2), int(monitor['Monitor'][3] * factor)
    elif pos == 3:  # bottom
        return int(monitor['Monitor'][2] * factor), monitor['Monitor'][3] - int(position_int[1] / 2)
    return 0, 0


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
def get_accounts_from_cfg():
    steam_ids = ''
    global accounts
    for i in config.sections():
        if i.startswith('Account'):
            steam_id = config.get(i, 'Steam ID')
            steam_id_3 = str(int(steam_id) - 76561197960265728)
            auth_code = config.get(i, 'Authentication Code')
            match_token = config.get(i, 'Match Token')
            steam_ids += steam_id + ','
            accounts.append({'steam_id': steam_id, 'steam_id_3': steam_id_3, 'auth_code': auth_code, 'match_token': match_token})

    steam_ids = steam_ids.rstrip(',')
    steam_api_error = False
    try:
        profiles = requests.get(f'http://api.steampowered.com/ISteamUser/GetPlayerSummaries/v0002/?key={cfg.steam_api_key}&steamids={steam_ids}')
        if profiles.status_code == requests.status_codes.codes.ok:
            profiles = profiles.json()['response']['players']
            name_list = [(online_data['personaname'], online_data['avatarhash'], online_data['avatarfull']) for local_acc in accounts for online_data in profiles if online_data['steamid'] == local_acc['steam_id']]

            for num, val in enumerate(accounts):
                val['name'] = name_list[num][0]
                val['avatar_hash'] = name_list[num][1]
                val['avatar_url'] = name_list[num][2]
        else:
            steam_api_error = True
    except (TimeoutError, requests.ConnectionError):
        steam_api_error = True

    if steam_api_error:
        write(red('INVAILD STEAM API KEY or INTERNET CONNECTION ERROR, could not fetch usernames'))
        for num, val in enumerate(accounts):
            val['name'] = f'Unknown Name {num}'
            val['avatar_hash'] = f'Unknown Avatar {num}'
            val['avatar_url'] = 'https://i.imgur.com/MhAf20U.png'

    colors_1 = ['00{:02x}ff', '00ff{:02x}', '{:02x}00ff', '{:02x}00ff', 'ff00{:02x}', 'ff{:02x}00']
    colors_2 = ['{:02x}ffff', 'ff{:02x}ff', 'ffff{:02x}']
    two_part_numbers = list(set(int(pattern.format(i), 16) for pattern in colors_1 for i in range(256)))
    single_part_numbers = list(set(int(pattern.format(i), 16) for pattern in colors_2 for i in range(177)))
    numbers = list(set(two_part_numbers + single_part_numbers))

    for account in accounts:
        random.seed(f'{account["name"]}_{account["steam_id"]}_{account["avatar_hash"]}', version=2)
        account['color'] = numbers[random.randint(0, len(numbers))]


# noinspection PyShadowingNames
def get_csgo_path():
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
    path_vars['csgo_path'] = csgo_path
    path_vars['steam_path'] = steam_path


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
    userdata_path = os.path.join(path_vars['steam_path'], 'userdata', steam_id_3, '730', 'local', 'cfg')
    str_in_autoexec = ['developer 1', 'con_logfile "console_log.log"', 'con_filter_enable "2"',
                       'con_filter_text_out "Player:"', 'con_filter_text "Damage"', f'log_color General {cfg.log_color}',
                       f'bind "{cfg.status_key}" "status"' if cfg.status_key else '']
    os.makedirs(userdata_path, exist_ok=True)
    with open(os.path.join(userdata_path, 'autoexec.cfg'), 'a+') as autoexec:
        autoexec.seek(0)
        lines = autoexec.readlines()
        for autoexec_str in str_in_autoexec:
            if not any(autoexec_str.lower() in line.rstrip('\n').lower() for line in lines):
                write(yellow(f'Added {autoexec_str} to "autoexec.cfg"'), add_time=False)
                write(red('RESTART Counter-Strike for the script to work'), add_time=False)
                autoexec.write(f'\n{autoexec_str}\n')

    if os.path.exists(os.path.join(path_vars['csgo_path'], 'cfg', 'autoexec.cfg')):
        write(red(f'YOU HAVE TO DELETE THE "autoexec.cfg" in {os.path.join(path_vars["csgo_path"], "cfg")} WITH AND MERGE IT WITH THE ONE IN {userdata_path}'), add_time=False)
        write(red(f'THE SCRIPT WONT WORK UNTIL THERE IS NO "autoexec.cfg" in {os.path.join(path_vars["csgo_path"], "cfg")}'), add_time=False)


# noinspection PyShadowingNames
def get_avg_match_time(steam_id: int):
    with sqlite3.connect(path_vars['db_path']) as db:
        cur = db.execute("""SELECT AVG(match_time), SUM(match_time), AVG(wait_time), SUM(wait_time) FROM matches WHERE steam_id = ?""", (steam_id,))
        match_avg, match_sum, search_avg, search_sum = cur.fetchone()
        cur = db.execute("""SELECT SUM(afk_time), COUNT(afk_time), SUM(team_score + enemy_score) FROM matches WHERE steam_id = ? AND afk_time NOT NULL""", (steam_id,))
        afk_sum, afk_count, rounds_sum = cur.fetchone()

    afk_avg = afk_sum / afk_count
    afk_per_round = afk_sum / rounds_sum
    return {
        'match_time': (round(match_avg, 0), match_sum),
        'search_time': (round(search_avg, 0), search_sum),
        'afk_time': (round(afk_avg), afk_sum, round(afk_per_round, 0))
    }


def add_first_match(path):
    if not account['match_token']:
        raise ValueError('Missing Match Token in Config')
    now = datetime.now(tz=utc).timestamp()
    create_table(path, account['match_token'], account['steam_id'], now)
    return [account['match_token']]


# noinspection PyShadowingNames
def get_old_sharecodes(last_x: int):
    if last_x >= 0:
        return []
    path = path_vars['db_path']
    if os.path.isfile(path):
        with sqlite3.connect(path) as db:
            cur = db.execute("""SELECT sharecode FROM matches WHERE steam_id = ? ORDER BY timestamp DESC LIMIT ?""", (steam_id, abs(last_x)))
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
        steam_url = f'https://api.steampowered.com/ICSGOPlayers_730/GetNextMatchSharingCode/v1?key={cfg.steam_api_key}&steamid={steam_id}&steamidkey={account["auth_code"]}&knowncode={game_id}'
        try:
            r = requests.get(steam_url, timeout=2)
            next_code = r.json()['result']['nextcode']
        except (KeyError, requests.exceptions.ConnectionError, requests.exceptions.Timeout, json.decoder.JSONDecodeError) as e:
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

    path = path_vars['db_path']
    with sqlite3.connect(path) as db:
        if len(sharecodes) > 1:
            # > 1 is true if there is a new sharecode, first sharecode is the last supplied one

            # add all matches expect the newest one without any extra data
            db_data = [(sharecode, int(steam_id)) for sharecode in sharecodes[:-1]]
            db.executemany("""INSERT OR IGNORE INTO matches (sharecode, steam_id) VALUES (?, ?)""", db_data)

            if stats is None:
                stats = {'map': None, 'match_time': None, 'wait_time': None, 'afk_time': None, 'mvps': None, 'score': None}
            if 'mvps' not in stats:
                stats = {'map': None, 'match_time': None, 'wait_time': None, 'afk_time': None, 'mvps': None, 'score': None}

            now = datetime.now(tz=utc).timestamp()
            match_data = (sharecodes[-1], int(steam_id), stats['match_time'], stats['wait_time'], stats['afk_time'], stats['mvps'], stats['score'], now)
            db.execute("""INSERT OR IGNORE INTO matches (sharecode, steam_id, match_time, wait_time, afk_time, mvps, points, timestamp) VALUES (?, ?, ?, ?, ?, ?, ?, ?)""", match_data)
            db.commit()

        # Test if any tracked match has missing info
        cur = db.execute("""SELECT sharecode FROM matches WHERE map IS NULL AND error = 0 and steam_id = ? ORDER BY timestamp ASC""", (int(steam_id),))
        sharecodes = cur.fetchall()

    return [{'sharecode': code, 'queue_pos': None} for code, in sharecodes]


# noinspection PyShadowingNames
def str_in_list(compare_strings: List[str], list_of_strings: List[str], replace: bool = False):
    replacement_str = '' if not replace else compare_strings[0]
    matching = [string.replace(replacement_str, '') for string in list_of_strings for compare_str in compare_strings if compare_str in string]
    return any(matching) if not replace else matching


def check_for_forbidden_programs(process_list):
    titles = [i[1].lower() for i in process_list]
    forbidden_programs = [i.lstrip(' ').lower() for i in cfg.forbidden_programs.split(',')]
    if forbidden_programs[0]:
        return any(name for name in titles for forbidden_name in forbidden_programs if forbidden_name == name)
    else:
        return False


def read_console():
    log_path = os.path.join(path_vars['csgo_path'], 'console_log.log')
    with open(log_path, 'r+', encoding='utf-8') as log:
        data = log.readlines()
        console_lines = [i.strip('\n') for i in data]
        if len(console_lines) >= 1:
            log.seek(0, os.SEEK_SET)
            log.truncate(0)
            with open(os.path.join(path_vars['appdata_path'], 'console.log'), 'a', encoding='utf-8') as debug_log:
                [debug_log.write(i + '\n') for i in console_lines]
        else:
            console_lines = []
    return {'msg': str_in_list(['Matchmaking message: '], console_lines, replace=True), 'update': str_in_list(['Matchmaking update: '], console_lines, replace=True),
            'players_accepted': str_in_list(['Server reservation2 is awaiting '], console_lines, replace=True), 'lobby_data': str_in_list(["LobbySetData: "], console_lines, replace=True),
            'server_found': str_in_list(['Matchmaking reservation confirmed: '], console_lines), 'server_ready': str_in_list(['ready-up!'], console_lines),
            'server_abandon': str_in_list(['Closing Steam Net Connection to =', 'Kicked by Console'], console_lines, replace=True), 'map': str_in_list(['Map: '], console_lines, replace=True),
            'server_settings': str_in_list(['SetConVar: mp_'], console_lines, replace=True)}


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


def round_start_msg(msg: str, round_phase: str, freezetime_start: float, old_window_status: bool, current_window_status: bool, scoreboard: dict, overwrite_key: str = '7'):
    if old_window_status:
        if current_window_status:
            timer_stopped = ''
        else:
            old_window_status = False
            timer_stopped = ' - ' + green('stopped')

        freeze_time = scoreboard['freeze_time']
        buy_time = scoreboard['buy_time']

        if round_phase == 'freezetime':
            time_str = green(timedelta(seconds=time.time() - (freezetime_start + freeze_time)))
        elif time.time() - freezetime_start > 35:
            time_str = red(timedelta(then=freezetime_start))
        else:
            time_str = yellow(timedelta(seconds=time.time() - (freezetime_start + freeze_time + buy_time)))

        msg += f' - {time_str}{timer_stopped}'
        write(msg, overwrite=overwrite_key)
    return old_window_status


def time_output(current: Union[float, int], average: Union[float, int]):
    difference = abs(current - average)
    if current <= average:
        return f'{timedelta(seconds=current)}, {timedelta(seconds=difference)} {green("shorter")} than average of {timedelta(seconds=average)}'
    else:
        return f'{timedelta(seconds=current)}, {timedelta(seconds=difference)} {red("longer")}  than average of {timedelta(seconds=average)}'


# noinspection PyShadowingNames
def enum_cb(hwnd: int, results: list):
    _, cpid = win32process.GetWindowThreadProcessId(hwnd)
    name = win32gui.GetWindowText(hwnd)
    results.append((hwnd, name, cpid))


def get_hwnd(exe_name: str = 'csgo.exe', window_name: str = 'counter-strike'):
    r = subprocess.check_output(f'tasklist /FI "IMAGENAME EQ {exe_name}" /FO "CSV"', shell=False)
    procs = [line.decode('utf-8', errors='ignore') for line in r.splitlines()]
    data = list(csv.DictReader(procs))
    if len(data) < 1:
        raise ProcessNotFoundError(exe_name)
    pid = int(data[0]["PID"])
    for window_id, title, cpid in window_ids:
        if cpid == pid:
            if window_name in title.lower():
                return window_id
    raise WindowNotFoundError(window_name)


class ProcessNotFoundError(BaseException):
    def __init__(self, name):
        super().__init__(f'no process found by {name}')


class WindowNotFoundError(BaseException):
    def __init__(self, name):
        super().__init__(f'no window found for {name}')


def restart_gsi_server(gsi_server: server.GSIServer = None):
    if gsi_server is None:
        gsi_server = server.GSIServer(('127.0.0.1', 3000), "IDONTUSEATOKEN")
    elif gsi_server.running:
        gsi_server.shutdown()
        if get_hwnd() is not None:
            gsi_server = server.GSIServer(('127.0.0.1', 3000), "IDONTUSEATOKEN")
            gsi_server.start_server()
        else:
            gsi_server = server.GSIServer(('127.0.0.1', 3000), "IDONTUSEATOKEN")
    else:
        gsi_server.start_server()
    return gsi_server


def request_status_command(hwnd, key: str = 'F12'):
    current_csgo_status = win32gui.GetWindowPlacement(hwnd)[1]
    win32gui.ShowWindow(hwnd, win32con.SW_MAXIMIZE)
    time.sleep(0.15)
    keyboard.send(key)
    time.sleep(0.1)
    if current_csgo_status == 2:
        minimize_csgo(hwnd)
    return


class MatchRequest(threading.Thread):
    """Using a thread so we are not blocking the script while performing the request"""

    def __init__(self):
        super().__init__()
        self.name = 'MatchRequester'
        self.daemon = True

    def run(self) -> None:
        time.sleep(1.0)
        match_log = log_reader.get_log_info()
        if match_log is None:
            write(f'no new match log found')
            return
        data = match_log.to_web_request(cfg.secret, steam_id)
        url = f"http://{cfg.server_ip}:{cfg.server_port}/check"
        r = requests.post(url, json=data)
        if r.status_code != 200:
            write(f'failed to send check match message to {repr(cfg.server_ip)} with status {r.status_code} - {r.text}')


def match_win_list(number_of_matches: int, _steam_id, time_difference: int = 7_200, replace_chars: bool = False):
    with sqlite3.connect(path_vars['db_path']) as db:
        cur = db.execute("""SELECT outcome, timestamp FROM matches WHERE steam_id = ? ORDER BY timestamp DESC LIMIT ?""", (_steam_id, abs(number_of_matches)))
        items = cur.fetchall()
    outcome_lst = []
    for outcome, timestamp in items:
        if not outcome:
            outcome = 'U'
        if not timestamp:
            timestamp = datetime.now(tz=utc).timestamp() - (60 * 60)

        if outcome == 'W':
            char = '\u2588' if not replace_chars else 'W'
            outcome_lst.append((timestamp, green(char)))
        elif outcome == 'L':
            char = '\u2588' if not replace_chars else 'L'
            outcome_lst.append((timestamp, red(char)))
        elif outcome == 'D':
            char = '\u2588' if not replace_chars else 'W'
            outcome_lst.append((timestamp, blue(char)))
        else:
            char = '\u2588' if not replace_chars else 'U'
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
    def __init__(self, sleep_interval: float = 0.5):
        super().__init__(name='WindowEnumerator')
        self._kill = threading.Event()
        self._interval = sleep_interval
        self.daemon = True

    def run(self):
        global window_ids
        while True:
            current_ids = []
            win32gui.EnumWindows(enum_cb, current_ids)
            window_ids = current_ids
            is_killed = self._kill.wait(self._interval)
            if is_killed:
                break
            time.sleep(0.5)

    def kill(self):
        self._kill.set()


path_vars = {'appdata_path': os.path.join(os.getenv('APPDATA'), 'CSGO AUTO ACCEPT'),
             'mute_csgo_path': f'"{os.path.abspath(os.path.expanduser("sounds/nircmdc.exe"))}" muteappvolume csgo.exe',
             'db_path': os.path.join(os.path.join(os.getenv('APPDATA'), 'CSGO AUTO ACCEPT', 'matches.db'))}

try:
    os.mkdir(path_vars['appdata_path'])
except FileExistsError:
    pass

overwrite_dict = {'key': '0', 'msg': '', 'end': '\n'}
if not sys.stdout.isatty():
    console_window = {'prefix': '\r', 'suffix': '', 'isatty': False}
else:
    console_window = {'prefix': '', 'suffix': '\r', 'isatty': True}

lobby_info = re.compile(r"(?<!Machines' = '\d''members:num)(C?TSlotsFree|Players)' = '(\d+'?)")

# CONFIG HANDLING
config = configparser.ConfigParser()
config.read('config.ini')

try:
    @dataclass
    class ConfigItems:
        webhook_port = config.getint('HotKeys', 'WebHook Port')

        sleep_interval: float = config.getfloat('Script Settings', 'Interval')
        log_color: str = config.get('Script Settings', 'Log Color')
        forbidden_programs: str = config.get('Script Settings', 'Forbidden Programs')
        taskbar_position: tuple = config.getfloat('Script Settings', 'Taskbar Factor')
        match_list_lenght: int = config.getint('Script Settings', 'Match History Lenght')
        steam_api_key: str = config.get('csgostats.gg', 'API Key')
        auto_retry_interval: int = config.getint('csgostats.gg', 'Auto-Retrying-Interval')
        status_key: str = config.get('csgostats.gg', 'Status Key')
        secret: bytes = config.get('csgostats.gg', 'Secret')
        server_ip: str = config.get('csgostats.gg', 'WebServer IP')
        server_port: int = config.getint('csgostats.gg', 'WebServer Port')
        discord_user_id: int = config.getint('Notifier', 'Discord User ID')

        def __post_init__(self):
            self.log_color = self.log_color.lower()
            if isinstance(self.secret, str):
                self.secret = self.secret.encode()

            if isinstance(self.taskbar_position, float):
                if self.taskbar_position > 1.0:
                    self.taskbar_position = task_bar(1.0 / self.taskbar_position)
                else:
                    self.taskbar_position = task_bar(self.taskbar_position)


    cfg: ConfigItems = ConfigItems()
except (configparser.NoOptionError, configparser.NoSectionError, ValueError) as e:
    write(f'ERROR IN CONFIG - {str(e)}')
    cfg = None
    exit('REPAIR CONFIG')

accounts = []
get_accounts_from_cfg()
get_csgo_path()
steam_id = get_current_steam_user()

if not steam_id:
    account = accounts[0]
    steam_id = account['steam_id']
    current_steam_account = 0
else:
    for account_number, cfg_account in enumerate(accounts):
        if steam_id == cfg_account['steam_id']:
            account = cfg_account
            current_steam_account = account_number
            break
    else:
        write(red(f'Could not find {steam_id} in config file, defaulting to account 0'), add_time=False)
        account = accounts[0]
        steam_id = account['steam_id']
        current_steam_account = 0

with open(os.path.join(path_vars['csgo_path'], 'console_log.log'), 'w', encoding='utf-8') as log:
    log.write('')
with open(os.path.join(path_vars['appdata_path'], 'console.log'), 'w', encoding='utf-8') as debug_log:
    debug_log.write('')

if path_vars['csgo_path']:
    if not os.path.exists(os.path.join(path_vars['csgo_path'], 'cfg', 'gamestate_integration_GSI.cfg')):
        copyfile(os.path.join(os.getcwd(), 'GSI', 'gamestate_integration_GSI.cfg'), os.path.join(path_vars['csgo_path'], 'cfg', 'gamestate_integration_GSI.cfg'))
        write(red('Added GSI CONFIG to cfg folder. Counter-Strike needs to be restarted if running!'))

afk_message = False

window_ids = []

sleep_interval = cfg.sleep_interval
sleep_interval_looking_for_accept = 0.05
log_reader = LogReader(os.path.join(path_vars['appdata_path'], 'console.log'))

if __name__ == '__main__':
    while True:
        pass
    pass
