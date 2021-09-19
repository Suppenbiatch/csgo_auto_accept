import configparser
import json
import operator
import os
import random
import re
import sys
import threading
import time
import winreg
from datetime import timedelta as td
from shutil import copyfile
from typing import List, Union
from pathlib import Path

import keyboard
import pushbullet
import requests
import win32api
import win32con
import win32gui
from PIL import ImageGrab, Image
from color import FgColor
from color import green, red, yellow, blue, magenta

from GSI import server
from utils import *
from write import write, pushbullet_dict


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


def minimize_csgo(window_id: int, reset_position: tuple, current_position=None):
    if current_position is None:
        current_position = win32api.GetCursorPos()
        if current_position == (0, 0):
            current_position = (int(win32api.GetSystemMetrics(0) / 2), int(win32api.GetSystemMetrics(1) / 2))
    win32gui.ShowWindow(window_id, win32con.SW_MINIMIZE)
    click((0, 0), lmb=False)
    time.sleep(0.15)
    click(reset_position)
    time.sleep(0.05)
    set_mouse_position(current_position)


# noinspection PyShadowingNames
def anti_afk(window_id: int, reset_position=None):
    if reset_position is None:
        reset_position = (0, 0)
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
    minimize_csgo(window_id, reset_position)


def task_bar(factor: float = 2.0):
    monitor = win32api.GetMonitorInfo(win32api.MonitorFromPoint((0, 0)))
    taskbar_size = tuple(map(operator.sub, monitor['Monitor'], monitor['Work']))
    position_int = [(i, abs(x)) for i, x in enumerate(taskbar_size) if x]
    if len(position_int) != 1:
        write('Taskbar location failed', color=FgColor.Yellow, add_time=False)
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
        profiles = requests.get(f'http://api.steampowered.com/ISteamUser/GetPlayerSummaries/v0002/?key={cfg["steam_api_key"]}&steamids={steam_ids}')
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
        write('INVAILD STEAM API KEY or INTERNET CONNECTION ERROR, could not fetch usernames', color=FgColor.Red)
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
        write('DID NOT FIND CSGO PATH', add_time=False, color=FgColor.Red)
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
                       'con_filter_text_out "Player:"', 'con_filter_text "Damage"', f'log_color General {cfg["log_color"]}',
                       f'bind "{cfg["status_key"]}" "status"' if cfg['status_key'] else '']
    os.makedirs(userdata_path, exist_ok=True)
    with open(os.path.join(userdata_path, 'autoexec.cfg'), 'a+') as autoexec:
        autoexec.seek(0)
        lines = autoexec.readlines()
        for autoexec_str in str_in_autoexec:
            if not any(autoexec_str.lower() in line.rstrip('\n').lower() for line in lines):
                write(f'Added {autoexec_str} to "autoexec.cfg"', add_time=False, color=FgColor.Yellow)
                write('RESTART Counter-Strike for the script to work', add_time=False, color=FgColor.Red)
                autoexec.write(f'\n{autoexec_str}\n')

    if os.path.exists(os.path.join(path_vars['csgo_path'], 'cfg', 'autoexec.cfg')):
        write(f'YOU HAVE TO DELETE THE "autoexec.cfg" in {os.path.join(path_vars["csgo_path"], "cfg")} WITH AND MERGE IT WITH THE ONE IN {userdata_path}', add_time=False, color=FgColor.Red)
        write(f'THE SCRIPT WONT WORK UNTIL THERE IS NO "autoexec.cfg" in {os.path.join(path_vars["csgo_path"], "cfg")}', add_time=False, color=FgColor.Red)


# noinspection PyShadowingNames
def get_avg_match_time(steam_id: str):
    csv_path = csv_path_for_steamid(steam_id)
    if os.path.isfile(csv_path):
        data = get_csv_list(csv_path)
    else:
        data = []
    match_time = [int(i['match_time']) for i in data if i['match_time']]
    search_time = [int(i['wait_time']) for i in data if i['wait_time']]
    afk_time = [int(i['afk_time']) for i in data if i['afk_time']]
    afk_time_per_round = [int(i['afk_time']) / (int(i['team_score']) + int(i['enemy_score'])) for i in data if i['afk_time'] and i['team_score'] and i['enemy_score']]
    return {
        'match_time': (round(avg(match_time, 0)), sum(match_time)),
        'search_time': (round(avg(search_time, 0)), sum(search_time)),
        'afk_time': (round(avg(afk_time, 0)), sum(afk_time), round(avg(afk_time_per_round, 0)))
    }


# noinspection PyShadowingNames
def get_old_sharecodes(last_x: int = -1, from_x: str = ''):
    if last_x >= 0:
        return []
    global csv_header
    csv_path = csv_path_for_steamid(steam_id)
    game_dict = []
    if os.path.isfile(csv_path):
        game_dict = get_csv_list(csv_path)
    if not os.path.isfile(csv_path) or not game_dict:
        with open(csv_path, 'w') as last_game:
            writer = csv.DictWriter(last_game, fieldnames=csv_header, delimiter=';', lineterminator='\n')
            writer.writeheader()
            writer.writerow({'sharecode': account['match_token']})
            game_dict = [{'sharecode': account['match_token']}]

    games = [i['sharecode'] for i in game_dict if i['sharecode']]
    if from_x:
        try:
            return games[(len(games) - games.index(from_x)) * -1:]
        except ValueError:
            return []
    return games[last_x:]


# noinspection PyShadowingNames
def get_new_sharecodes(game_id: str, stats=None):
    sharecodes = [game_id]
    stats_error = True
    while True:
        steam_url = f'https://api.steampowered.com/ICSGOPlayers_730/GetNextMatchSharingCode/v1?key={cfg["steam_api_key"]}&steamid={steam_id}&steamidkey={account["auth_code"]}&knowncode={game_id}'
        try:
            r = requests.get(steam_url, timeout=2)
            next_code = r.json()['result']['nextcode']
        except (KeyError, requests.exceptions.ConnectionError, requests.exceptions.Timeout, json.decoder.JSONDecodeError) as e:
            write(f'STEAM API ERROR! Error: "{e}"', color=FgColor.Red)
            break
        if r.status_code == 200:  # new match has been found
            sharecodes.append(next_code)
            game_id = next_code
            time.sleep(0.5)
        elif r.status_code == 202:  # no new match has been found
            if stats is None or len(sharecodes) > 1:
                if stats_error is False:
                    write('got a match code for the given stats', color=FgColor.Green)
                break
            else:
                if stats_error is True:
                    write('new match stats were given, yet steam api gave no new sharecode', color=FgColor.Yellow)
                    stats_error = False
                time.sleep(2)

    global csv_header, csgo_stats_test_for
    if len(sharecodes) > 1:
        with open(csv_path_for_steamid(steam_id), 'a', newline='', encoding='utf-8') as last_game:
            writer = csv.DictWriter(last_game, fieldnames=csv_header, delimiter=';', lineterminator='\n')
            for i in sharecodes[1:-1]:  # Add all matches except the newest one without any additional information
                row_dict = {'sharecode': i, 'match_id': '', 'map': '', 'team_score': '', 'enemy_score': '', 'wait_time': '', 'afk_time': '', 'mvps': 0, 'points': 0, 'kills': 0, 'assists': 0, 'deaths': 0}
                writer.writerow(row_dict)

            # Add the newest match with the given information
            if stats is None:
                stats = {'kills': 0, 'assists': 0, 'deaths': 0, 'mvps': 0, 'score': 0, 'map': '', 'match_score': ('', ''), 'match_time': '', 'wait_time': '', 'afk_time': ''}

            if 'mvps' not in stats:  # gameover match stats are given, but player has never been seen (demo watching only)
                for key, value in [('kills', 0), ('assists', 0), ('deaths', 0), ('mvps', 0), ('score', 0)]:
                    stats[key] = value

            row_dict = {'sharecode': sharecodes[-1], 'map': stats['map'], 'team_score': stats['match_score'][0], 'enemy_score': stats['match_score'][1],
                        'match_time': stats['match_time'], 'wait_time': stats['wait_time'], 'afk_time': stats['afk_time'],
                        'mvps': stats['mvps'], 'points': stats['score'], 'kills': stats['kills'], 'assists': stats['assists'], 'deaths': stats['deaths']}
            writer.writerow(row_dict)

    # Test if any tracked match has missing info
    sharecodes = []
    data = list(reversed(get_csv_list(csv_path_for_steamid(steam_id))))
    for match in data:
        for item in match.items():
            if item[0] in csgo_stats_test_for and not item[1]:
                if match['sharecode']:
                    sharecodes.insert(0, match['sharecode'])
                break

    return [{'sharecode': code, 'queue_pos': None} for code in sharecodes]


# noinspection PyShadowingNames
def str_in_list(compare_strings: List[str], list_of_strings: List[str], replace: bool = False):
    replacement_str = '' if not replace else compare_strings[0]
    matching = [string.replace(replacement_str, '') for string in list_of_strings for compare_str in compare_strings if compare_str in string]
    return any(matching) if not replace else matching


def check_for_forbidden_programs(process_list):
    titles = [i[1].lower() for i in process_list]
    forbidden_programs = [i.lstrip(' ').lower() for i in cfg['forbidden_programs'].split(',')]
    if forbidden_programs[0]:
        return any(name for name in titles for forbidden_name in forbidden_programs if forbidden_name == name)
    else:
        return False


# noinspection PyShadowingNames
def read_console():
    with open(os.path.join(path_vars['csgo_path'], 'console_log.log'), 'r+', encoding='utf-8', errors='ignore') as log:
        console_lines = [i.strip('\n') for i in log.readlines()]
        log.seek(0)
        log.truncate()
    with open(os.path.join(path_vars['appdata_path'], 'console.log'), 'a', encoding='utf-8') as debug_log:
        [debug_log.write(i + '\n') for i in console_lines]
    return {'msg': str_in_list(['Matchmaking message: '], console_lines, replace=True), 'update': str_in_list(['Matchmaking update: '], console_lines, replace=True),
            'players_accepted': str_in_list(['Server reservation2 is awaiting '], console_lines, replace=True), 'lobby_data': str_in_list(["LobbySetData: "], console_lines, replace=True),
            'server_found': str_in_list(['Matchmaking reservation confirmed: '], console_lines), 'server_ready': str_in_list(['ready-up!'], console_lines),
            'server_abandon': str_in_list(['Closing Steam Net Connection to =', 'Kicked by Console'], console_lines, replace=True), 'map': str_in_list(['Map: '], console_lines, replace=True)}


def activate_pushbullet():
    if not pushbullet_dict['device']:
        try:
            pushbullet_dict['device'] = pushbullet.PushBullet(cfg['pushbullet_api_key']).get_device(cfg['pushbullet_device_name'])
        except (pushbullet.errors.PushbulletError, pushbullet.errors.InvalidKeyError):
            write('Pushbullet is wrongly configured.\nWrong API Key or DeviceName in config.ini\nRestart Script if changes to config.ini were made.')
    if pushbullet_dict['device']:
        pushbullet_dict['urgency'] += 1
        if pushbullet_dict['urgency'] > len(pushbullet_dict['push_info']) - 1:
            pushbullet_dict['urgency'] = 0
        write(f'Pushing: {pushbullet_dict["push_info"][pushbullet_dict["urgency"]]}', overwrite='2')


def round_start_msg(msg: str, round_phase: str, freezetime_start: float, old_window_status: bool, current_window_status: bool, overwrite_key: str = '7'):
    if old_window_status:
        if current_window_status:
            timer_stopped = ''
        else:
            old_window_status = False
            timer_stopped = ' - ' + green('stopped')

        freeze_time = 15
        buy_time = 20

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
    results.append((hwnd, win32gui.GetWindowText(hwnd)))


def email_decode(encoded_string):
    r = int(encoded_string[:2], 16)
    email = ''.join([chr(int(encoded_string[i:i + 2], 16) ^ r) for i in range(2, len(encoded_string), 2)])
    return email


def check_if_running(program_name: str = 'counter-strike: global offensive'):
    ids = []
    win32gui.EnumWindows(enum_cb, ids)
    program = [(hwnd, title) for hwnd, title in ids if program_name.lower() == title.lower()]
    return bool(program)


def restart_gsi_server(gsi_server: server.GSIServer = None):
    if gsi_server is None:
        gsi_server = server.GSIServer(('127.0.0.1', 3000), "IDONTUSEATOKEN")
    elif gsi_server.running:
        gsi_server.shutdown()
        if check_if_running():
            gsi_server = server.GSIServer(('127.0.0.1', 3000), "IDONTUSEATOKEN")
            gsi_server.start_server()
        else:
            gsi_server = server.GSIServer(('127.0.0.1', 3000), "IDONTUSEATOKEN")
    else:
        gsi_server.start_server()
    return gsi_server


def request_status_command(hwnd, reset_position, key: str = 'F12'):
    current_position = win32api.GetCursorPos()
    current_csgo_status = win32gui.GetWindowPlacement(hwnd)[1]
    win32gui.ShowWindow(hwnd, win32con.SW_MAXIMIZE)
    time.sleep(0.15)
    keyboard.send(key)
    time.sleep(0.1)
    if current_csgo_status == 2:
        minimize_csgo(hwnd, reset_position, current_position)
    return


def match_win_list(number_of_matches: int, _steam_id, time_difference: int = 7_200):
    data = get_csv_list(csv_path_for_steamid(_steam_id))
    number_of_matches = abs(number_of_matches + 1) * -1
    outcome_lst = []
    for match in data[:number_of_matches:-1]:
        outcome = match['outcome']
        if not outcome:
            if match['team_score'] and match['enemy_score']:
                team = int(match['team_score'])
                enemy = int(match['enemy_score'])
            else:
                team, enemy = 0, 0

            if team > enemy:
                outcome = 'W'
            elif team < enemy:
                outcome = 'L'
            elif team == enemy and team == 15:
                outcome = 'D'
            else:
                outcome = 'U'
        if not match['timestamp']:
            timestamp = int(time.time()) - (60 * 60)
        else:
            timestamp = int(match['timestamp'])

        if outcome == 'W':
            outcome_lst.append((timestamp, green('\u2588')))
        elif outcome == 'L':
            outcome_lst.append((timestamp, red('\u2588')))
        elif outcome == 'D':
            outcome_lst.append((timestamp, blue('\u2588')))
        else:
            outcome_lst.append((timestamp, magenta('\u2588')))

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
        super().__init__(name='WindowEnumerator', daemon=True)
        self._kill = threading.Event()
        self._interval = sleep_interval

    def run(self):
        global window_ids
        while True:
            current_ids = []
            win32gui.EnumWindows(enum_cb, current_ids)
            window_ids = current_ids
            is_killed = self._kill.wait(self._interval)
            if is_killed:
                break

    def kill(self):
        self._kill.set()


path_vars = {'appdata_path': os.path.join(os.getenv('APPDATA'), 'CSGO AUTO ACCEPT'), 'mute_csgo_path': f'"{os.path.abspath(os.path.expanduser("sounds/nircmdc.exe"))}" muteappvolume csgo.exe'}

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
    cfg = {'activate_script': config.get('HotKeys', 'Activate Script'), 'activate_push_notification': config.get('HotKeys', 'Activate Push Notification'),
           'info_newest_match': config.get('HotKeys', 'Get Info on newest Match'), 'mute_csgo_toggle': config.get('HotKeys', 'Mute CSGO'),
           'open_live_tab': config.get('HotKeys', 'Live Tab Key'), 'switch_accounts': config.get('HotKeys', 'Switch accounts for csgostats.gg'),
           'end_script': config.get('HotKeys', 'End Script'), 'discord_key': config.get('HotKeys', 'Discord Toggle'), 'minimize_key': config.get('HotKeys', 'Minimize CSGO'),
           'cancel_csgostats': config.get('HotKeys', 'Cancel Match Retrying'), 'sleep_interval': config.getfloat('Script Settings', 'Interval'),

           'log_color': config.get('Script Settings', 'Log Color').lower(), 'forbidden_programs': config.get('Script Settings', 'Forbidden Programs'),
           'taskbar_position': config.getfloat('Script Settings', 'Taskbar Factor'), 'match_list_lenght': config.getint('Script Settings', 'Match History Lenght'),

           'steam_api_key': config.get('csgostats.gg', 'API Key'), 'max_queue_position': config.getint('csgostats.gg', 'Auto-Retrying for queue position below'),
           'auto_retry_interval': config.getint('csgostats.gg', 'Auto-Retrying-Interval'), 'discord_url': config.get('csgostats.gg', 'Discord Webhook URL'),
           'player_webhook': config.get('csgostats.gg', 'Player Info Webhook'), 'status_key': config.get('csgostats.gg', 'Status Key'),

           'pushbullet_device_name': config.get('Pushbullet', 'Device Name'), 'pushbullet_api_key': config.get('Pushbullet', 'API Key')
           }
except (configparser.NoOptionError, configparser.NoSectionError, ValueError) as e:
    write(f'ERROR IN CONFIG - {str(e)}')
    cfg = {'ERROR': None}
    exit('REPAIR CONFIG')

csv_header = ['sharecode', 'match_id', 'map', 'team_score', 'enemy_score', 'outcome', 'start_team',
              'match_time', 'wait_time', 'afk_time', 'mvps', 'points', 'kills', 'assists', 'deaths',
              '5k', '4k', '3k', '2k', '1k', 'K/D', 'ADR', 'HS%', 'KAST', 'HLTV', 'rank', 'username', 'server', 'timestamp']

csgo_stats_test_for = ['map', 'team_score', 'enemy_score', 'outcome', 'start_team', 'kills', 'assists', 'deaths',
                       '5k', '4k', '3k', '2k', '1k', 'K/D', 'ADR', 'HS%', 'HLTV', 'rank', 'username', 'server', 'timestamp']

player_list_header = ['steam_id', 'name', 'seen_in', 'timestamp']

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
        write(f'Could not find {steam_id} in config file, defaulting to account 0', color=FgColor.Red, add_time=False)
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
        write('Added GSI CONFIG to cfg folder. Counter-Strike needs to be restarted if running!', color=FgColor.Red)

if cfg['taskbar_position'] > 1.0:
    cfg['taskbar_position'] = 1.0 / cfg['taskbar_position']
    write(f'Taskbar Factor to big, using inverse {cfg["taskbar_position"]}')
cfg['taskbar_position'] = task_bar(cfg['taskbar_position'])

window_ids = []

sleep_interval = cfg['sleep_interval']
sleep_interval_looking_for_accept = 0.05

if __name__ == '__main__':
    pass
