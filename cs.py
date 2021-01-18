import configparser
import csv
import datetime
import itertools
import json
import operator
import os
import random
import re
import sys
import threading
import time
import winreg
from shutil import copyfile
from typing import List, Dict, Union, Tuple

import cloudscraper
import keyboard
import pushbullet
import pyperclip
import requests
import win32api
import win32com.client
import win32con
import win32gui
from PIL import ImageGrab, Image
from color import colorize, FgColor
from color import green, red, yellow

from GSI import server


# noinspection PyShadowingNames
def Avg(lst: list, non_return=None):
    if not lst:
        return non_return
    return sum(lst) / len(lst)


def mute_csgo(lvl: int):
    global path_vars
    os.system(path_vars['mute_csgo_path'] + str(lvl))
    if lvl == 2:
        write('Mute toggled!', add_time=False)


def timedelta(then=None, seconds=None):
    if seconds is not None:
        return str(datetime.timedelta(seconds=abs(int(seconds))))
    else:
        now = time.time()
        return str(datetime.timedelta(seconds=abs(int(now - then))))


# noinspection PyShadowingNames
def write(message, add_time: bool = True, push: int = 0, push_now: bool = False, output: bool = True, overwrite: str = '0', color: FgColor = FgColor.Null):  # last overwrite key used: 11
    message = str(message)
    global re_pattern
    push_message = re_pattern['decolor'].sub('', message)
    if output:
        if add_time:
            message = datetime.datetime.now().strftime('%H:%M:%S') + ': ' + message
        else:
            message = ' ' * 10 + message
        global overwrite_dict
        if overwrite != '0':
            ending = console_window['suffix']
            if overwrite_dict['key'] == overwrite:
                if console_window['isatty']:
                    print(' ' * len(overwrite_dict['msg']), end=ending)
                message = console_window['prefix'] + message
            else:
                if overwrite_dict['end'] != '\n':
                    message = '\n' + message
        else:
            ending = '\n'
            if overwrite_dict['end'] != '\n':
                message = '\n' + message

        overwrite_dict = {'key': overwrite, 'msg': re_pattern['decolor'].sub('', message), 'end': ending}

        message = colorize(10, 10, color, message)
        print(message, end=ending)

    if push >= 3:
        if message:
            pushbullet_dict['note'] = pushbullet_dict['note'] + str(push_message.strip('\r').strip('\n')) + '\n'
        if push_now:
            pushbullet_dict['device'].push_note('CSGO AUTO ACCEPT', pushbullet_dict['note'])
            pushbullet_dict['note'] = ''


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
    time.sleep(0.05)
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
        profiles = requests.get('http://api.steampowered.com/ISteamUser/GetPlayerSummaries/v0002/?key=' + cfg['steam_api_key'] + '&steamids=' + steam_ids)
        if profiles.status_code == requests.status_codes.codes.ok:
            profiles = profiles.json()['response']['players']
            name_list = [(online_data['personaname'], online_data['avatarhash'], online_data['avatarfull']) for local_acc in accounts for online_data in profiles if online_data['steamid'] == local_acc['steam_id']]

            for num, val in enumerate(accounts):
                val['name'] = name_list[num][0]
                val['avatar_hash'] = name_list[num][1]
                val['avatar_url'] = name_list[num][2]
        else:
            steam_api_error = True
    except TimeoutError:
        steam_api_error = True

    if steam_api_error:
        write('INVAILD STEAM API KEY or INTERNET CONNECTION ERROR, could not fetch usernames', color=FgColor.Red)
        for num, val in enumerate(accounts):
            val['name'] = f'Unknown Name {num}'
            val['avatar_hash'] = f'Unknown Avatar {num}'
            val['avatar_url'] = 'https://i.imgur.com/MhAf20U.png'

    colors_1 = ['00{:02x}ff', '00ff{:02x}', '{:02x}00ff', '{:02x}00ff', 'ff00{:02x}', 'ff{:02x}00']
    colors_2 = ['{:02x}ffff', 'ff{:02x}ff', 'ffff{:02x}']
    two_part_numbers = list(dict.fromkeys(int(pattern.format(i), 16) for pattern in colors_1 for i in range(256)))
    single_part_numbers = list(dict.fromkeys(int(pattern.format(i), 16) for pattern in colors_2 for i in range(177)))
    numbers = list(dict.fromkeys(two_part_numbers + single_part_numbers))

    for account in accounts:
        random.seed(f'{account["name"]}_{account["steam_id"]}_{account["avatar_hash"]}', version=2)
        # random.seed(f'{account["name"]}_{account["steam_id"]}', version=2) #  Should the avatar influence discord color?
        account['color'] = numbers[random.randint(0, len(numbers))]


# noinspection PyShadowingNames
def get_csgo_path():
    steam_reg_key = winreg.OpenKey(winreg.HKEY_LOCAL_MACHINE, 'SOFTWARE\WOW6432Node\Valve\Steam')
    steam_path = winreg.QueryValueEx(steam_reg_key, 'InstallPath')[0]
    libraries = [steam_path + '\\steamapps']
    with open(steam_path + '\\steamapps\\libraryfolders.vdf', 'r') as library_file:
        library_data = library_file.readlines()
        libraries.extend([re_pattern['steam_path'].sub('', i.rstrip('"\n')) for i in library_data if bool(re_pattern['steam_path'].match(i))])
    try:
        csgo_path = [i for i in libraries if os.path.exists(i + '\\appmanifest_730.acf')][0] + '\\common\\Counter-Strike Global Offensive\\csgo\\'
    except IndexError:
        write('DID NOT FIND CSGO PATH', add_time=False, color=FgColor.Red)
        csgo_path = ''
    global path_vars
    path_vars['csgo_path'] = csgo_path
    path_vars['steam_path'] = steam_path


# noinspection PyShadowingNames
def get_current_steam_user():
    try:
        steam_reg_key = winreg.OpenKey(winreg.HKEY_CURRENT_USER, 'Software\Valve\Steam\ActiveProcess')
        current_user = winreg.QueryValueEx(steam_reg_key, 'ActiveUser')[0]
        if not current_user:
            return ''
        return str(current_user + 76561197960265728)
    except OSError:
        return ''


# noinspection PyShadowingNames
def check_userdata_autoexec(steam_id_3: str):
    global path_vars
    userdata_path = os.path.join(path_vars['steam_path'], 'userdata', steam_id_3, '730', 'local', 'cfg')
    str_in_autoexec = ['developer 1', 'con_logfile "console_log.log"', 'con_filter_enable "2"', 'con_filter_text_out "Player:"', 'con_filter_text "Damage"', 'log_color General ' + cfg['log_color']]
    os.makedirs(userdata_path, exist_ok=True)
    with open(os.path.join(userdata_path, 'autoexec.cfg'), 'a+') as autoexec:
        autoexec.seek(0)
        lines = autoexec.readlines()
        for autoexec_str in str_in_autoexec:
            if not any(autoexec_str.lower() in line.rstrip('\n').lower() for line in lines):
                write(f'Added {autoexec_str} to "autoexec.cfg" file in {userdata_path}', add_time=False, color=FgColor.Yellow)
                write('RESTART Counter-Strike for the script to work', add_time=False, color=FgColor.Red)
                autoexec.write('\n' + autoexec_str + '\n')
    if os.path.exists(path_vars['csgo_path'] + '\\cfg\\autoexec.cfg'):
        write('YOU HAVE TO DELETE THE "autoexec.cfg" in {} WITH AND MERGE IT WITH THE ONE IN {}'.format(path_vars["csgo_path"] + "\\cfg", userdata_path), add_time=False)
        write('THE SCRIPT WONT WORK UNTIL THERE IS NO "autoexec.cfg" in {}'.format(path_vars["csgo_path"] + "\\cfg"), add_time=False)


# noinspection PyShadowingNames
def get_avg_match_time(steam_id: str):
    global path_vars
    try:
        data = get_csv_list(os.path.join(path_vars['appdata_path'], f'last_game_{steam_id}.csv'))
    except FileNotFoundError:
        return []
    match_time = [int(i['match_time']) for i in data if i['match_time']]
    search_time = [int(i['wait_time']) for i in data if i['wait_time']]
    afk_time = [int(i['afk_time']) for i in data if i['afk_time']]
    afk_time_per_round = [int(i['afk_time']) / (int(i['team_score']) + int(i['enemy_score'])) for i in data if i['afk_time'] and i['team_score'] and i['enemy_score']]
    return {
        'match_time': (round(Avg(match_time, 0)), sum(match_time)),
        'search_time': (round(Avg(search_time, 0)), sum(search_time)),
        'afk_time': (round(Avg(afk_time, 0)), sum(afk_time), round(Avg(afk_time_per_round, 0)))
    }
    # return int(Avg(match_time, 0)), int(Avg(search_time, 0)), int(Avg(afk_time, 0)), int(Avg(afk_time_per_round, 0)), timedelta(seconds=sum(match_time)), timedelta(seconds=sum(search_time)), timedelta(seconds=sum(afk_time))


# noinspection PyShadowingNames
def get_old_sharecodes(last_x: int = -1, from_x: str = ''):
    if last_x >= 0:
        return []
    global path_vars, csv_header
    try:
        game_dict = get_csv_list(os.path.join(path_vars['appdata_path'], f'last_game_{steam_id}.csv'))
    except FileNotFoundError:
        with open(os.path.join(path_vars['appdata_path'], f'last_game_{steam_id}.csv'), 'w') as last_game:
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
    next_code = game_id
    while next_code != 'n/a':
        steam_url = f'https://api.steampowered.com/ICSGOPlayers_730/GetNextMatchSharingCode/v1?key={cfg["steam_api_key"]}&steamid={steam_id}&steamidkey={account["auth_code"]}&knowncode={game_id}'
        try:
            next_code = (requests.get(steam_url, timeout=2).json()['result']['nextcode'])
        except (KeyError, requests.exceptions.ConnectionError, requests.exceptions.Timeout, json.decoder.JSONDecodeError) as e:
            write(f'STEAM API ERROR! "{e}"', color=FgColor.Red)
            break

        if next_code != 'n/a':
            sharecodes.append(next_code)
            game_id = next_code

    global csv_header, csgo_stats_test_for
    if len(sharecodes) > 1:
        with open(os.path.join(path_vars['appdata_path'], f'last_game_{steam_id}.csv'), 'a', newline='', encoding='utf-8') as last_game:
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

        # Test if the last tracked match has missing info
        data = get_csv_list(os.path.join(path_vars['appdata_path'], f'last_game_{steam_id}.csv'))
        match_index = find_dict(data, 'sharecode', sharecodes[0])
        if match_index is not None:
            for item in data[match_index].items():
                if item[0] in csgo_stats_test_for and not item[1]:
                    break
            else:
                del sharecodes[0]  # Strip the old sharecode
    return [{'sharecode': code, 'queue_pos': None} for code in sharecodes]


# noinspection PyShadowingNames
def update_csgo_stats(new_codes: List[dict], discord_output: bool = False):
    global queue_difference, csgostats_retry, scraper, cfg, csgo_stats_test_for

    sharecodes = [code['sharecode'] for code in new_codes]
    responses, cloudflare_blocked = [], []
    for sharecode in sharecodes:
        try:
            response = scraper.post('https://csgostats.gg/match/upload/ajax', data={'sharecode': sharecode, 'index': 0})
            responses.append(response)
        except (cloudscraper.exceptions.CloudflareCode1020, requests.exceptions.ConnectionError, cloudscraper.exceptions.CaptchaException, cloudscraper.exceptions.CloudflareChallengeError) as e:
            write(f'"{str(e).split(",")[0]}", match added to queue', color=FgColor.Yellow, overwrite='4')
            cloudflare_blocked.append({'sharecode': sharecode, 'queue_pos': None})
    all_games = [r.json() for r in responses if r.status_code == requests.codes.ok]
    completed_games, not_completed_games, = [], []

    for game in all_games:
        if game['status'] == 'complete':
            completed_games.append(game)
        else:
            not_completed_games.append(game)

    queued_games = [{'sharecode': game['data']['sharecode'], 'queue_pos': game['data']['queue_pos']} for game in not_completed_games if game['status'] != 'error']
    corrupt_games = [{'sharecode': game['data']['sharecode'], 'queue_pos': None} for game in not_completed_games if game['status'] == 'error']

    if queued_games:
        temp_string = ''
        for i, val in enumerate(queued_games, start=1):
            temp_string += '#' + str(i) + ': in Queue #' + str(val['queue_pos']) + ' - '

        current_queue_difference = Avg([last_game['queue_pos'] - game['queue_pos'] for game in queued_games for last_game in new_codes if last_game['sharecode'] == game['sharecode'] and last_game['queue_pos'] is not None])
        if current_queue_difference is not None:
            if current_queue_difference >= 0.0:
                queue_difference.append(current_queue_difference / ((time.time() - csgostats_retry) / 60))
                queue_difference = queue_difference[-10:]
                matches_per_min = round(Avg(queue_difference), 1)
                if matches_per_min != 0.0:
                    time_till_done = timedelta(seconds=(queued_games[0]['queue_pos'] / matches_per_min) * 60)
                else:
                    time_till_done = '∞:∞:∞'
                temp_string += str(matches_per_min) + ' matches/min - #1 done in ' + time_till_done
        temp_string = temp_string.rstrip(' - ')
        write(temp_string, add_time=False, overwrite='4')

    csgostats_retry = time.time()
    new_codes = [game for game in queued_games if game['queue_pos'] < cfg['max_queue_position']]
    new_codes.extend([game for game in corrupt_games])
    new_codes.extend(cloudflare_blocked)

    if corrupt_games:
        corrupt_games_string = 'An error occurred in one game' if len(corrupt_games) == 1 else f'An error occurred in {len(corrupt_games)} games'
        write(corrupt_games_string, overwrite='5')

    if completed_games:
        time.sleep(2.5)  # idk if this helps to give csgostats some time
        global account
        for i, responses in enumerate(completed_games):
            game_url = responses['data']['url']
            sharecode = responses['data']['sharecode']
            match_id = game_url.rpartition('/')[2]

            discord_obj = None

            write(f'URL: {game_url}', add_time=True, push=pushbullet_dict['urgency'], color=FgColor.Green)
            data = get_csv_list(os.path.join(path_vars['appdata_path'], f'last_game_{steam_id}.csv'))
            match_index = find_dict(data, 'sharecode', sharecode)

            match_infos = None
            if match_index is not None:
                for item in data[match_index].items():
                    if item[0] in csgo_stats_test_for and not item[1]:  # Match has missing info in csv
                        match_infos = get_match_infos(match_id, steam_id)
                        if match_infos is not None:  # None is return if error in csgostats request
                            discord_obj = add_match_id(sharecode, match_infos)
                        break
                else:
                    discord_obj = generate_table(data[match_index], account['avatar_url'])  # Match has no missing info (was already done)
            else:
                match_infos = get_match_infos(match_id, steam_id)  # Match is completely new, no info in csv
                if match_infos is not None:  # None is return if error in csgostats request
                    discord_obj = add_match_id(sharecode, match_infos)

            if match_infos is not None:
                add_players_to_list(match_infos, steam_id)

            if discord_output and discord_obj is not None:
                send_discord_msg(discord_obj, cfg['discord_url'], f'{account["name"]} - Match Stats')
            try:
                pyperclip.copy(game_url)
            except (pyperclip.PyperclipWindowsException, pyperclip.PyperclipTimeoutException):
                write('Failed to load URL in to clipboard', add_time=False)
        write(None, add_time=False, push=pushbullet_dict['urgency'], push_now=True, output=False)
    return new_codes


def get_csv_list(path, header=None):
    if header is None:
        global csv_header
        header = csv_header

    if not os.path.isfile(path):
        with open(path, 'w', newline='', encoding='utf-8') as f:
            writer = csv.DictWriter(f, fieldnames=header, delimiter=';', lineterminator='\n')
            writer.writeheader()

    with open(path, 'r', newline='', encoding='utf-8') as f:
        data = list(csv.DictReader(f, fieldnames=header, delimiter=';', restval=''))
    first_element = tuple(data[0].values())
    if all(head == first_element[i] for i, head in enumerate(header)):  # File has a valid header
        del data[0]  # Remove the header from the data
        return data

    # rewrite file with the new header and reuse all the old values
    with open(path, 'r', newline='', encoding='utf-8') as f:
        data = list(csv.DictReader(f, delimiter=';', restval=''))
    rows = []
    for i in data:
        row_dict = {}
        for key in header:
            try:
                row_dict[key] = i[key]
            except KeyError:
                row_dict[key] = ''
        rows.append(row_dict)
    with open(path, 'w', newline='', encoding='utf-8') as f:
        writer = csv.DictWriter(f, fieldnames=header, delimiter=';', lineterminator='\n')
        writer.writeheader()
        writer.writerows(rows)
    return rows


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
    with open(path_vars['csgo_path'] + 'console_log.log', 'r+', encoding='utf-8', errors='ignore') as log:
        console_lines = [i.strip('\n') for i in log.readlines()]
        log.seek(0)
        log.truncate()
    with open(path_vars['appdata_path'] + '\\console.log', 'a', encoding='utf-8') as debug_log:
        [debug_log.write(i + '\n') for i in console_lines]
    return {'msg': str_in_list(['Matchmaking message: '], console_lines, replace=True), 'update': str_in_list(['Matchmaking update: '], console_lines, replace=True),
            'players_accepted': str_in_list(['Server reservation2 is awaiting '], console_lines, replace=True), 'lobby_data': str_in_list(["LobbySetData: "], console_lines, replace=True),
            'server_found': str_in_list(['Matchmaking reservation confirmed: '], console_lines), 'server_ready': str_in_list(['ready-up!'], console_lines),
            'server_abandon': str_in_list(['Closing Steam Net Connection to =', 'Kicked by Console'], console_lines, replace=True), 'map': str_in_list(['Map: '], console_lines, replace=True)}


def remove_indices(lst: list, index: list):
    for i in sorted(index, reverse=True):
        del lst[i]
    return lst


def create_field(field: tuple):
    return {
        'name': field[0],
        'value': str(field[1]),
        'inline': field[2]
    }


def find_dict(lst: list, key: str, value):
    for i, dic in enumerate(lst):
        if dic[key] == value:
            return i
    return None


def remove_dict(lst: list, key: str, value):
    for i, _dict in enumerate(lst):
        if (key, value) in _dict.items():
            break
    else:
        return lst
    del lst[i]
    return lst


# noinspection PyShadowingNames
def generate_table(match, avatar_url: str = ''):
    match_time = timedelta(seconds=match['match_time'] if match['match_time'] else 0)
    search_time = timedelta(seconds=match['wait_time'] if match['wait_time'] else 0)
    afk_time = timedelta(seconds=match['afk_time'] if match['afk_time'] else 0)
    afk_per_round = timedelta(seconds=int(int(match['afk_time']) / (int(match['team_score']) + int(match['enemy_score']))) if match['afk_time'] else 0)
    mvps = match['mvps'] if match['mvps'] else '0'
    points = match['points'] if match['points'] else '0'

    rank_names = ['None',
                  'S1', 'S2', 'S3', 'S4', 'SE', 'SEM',
                  'GN1', 'GN2', 'GN3', 'GNM',
                  'MG1', 'MG2', 'MGE', 'DMG',
                  'LE', 'LEM', 'SMFC', 'GE']

    rank_integer = int(re.sub('\D', '', match['rank']))
    rank_changed = re.sub('[\d ]', '', match['rank'])
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
                        'footer': {'text': 'CS:GO', 'icon_url': 'https://i.imgur.com/qlBV96I.png'}, 'timestamp': epoch_to_iso(match['timestamp']),
                        'fields': [create_field(i) for i in field_values]}], 'avatar_url': avatar_url}


# noinspection PyShadowingNames
def get_match_infos(match_id, steam_id):
    url = f'https://csgostats.gg/match/{match_id}'
    try:
        r = scraper.get(url)
    except (cloudscraper.exceptions.CaptchaException, cloudscraper.exceptions.CloudflareChallengeError):
        write('Failed to get match data because of cloudflare captcha', color=FgColor.Red, add_time=False)
        return None
    if r.status_code != requests.status_codes.codes.ok:
        write(f'Failed to retrieve match data with code {r.status_code}', color=FgColor.Red, add_time=False)
        return None
    formatted_html = r.text.replace('\n', '').replace('\t', '')
    all_info = formatted_html.replace('<tr class="">', '\r\n').replace('<tr class="has-banned">', '\r\n').replace('<div id="match-rounds" class="content-tab">', '\r\n').split('\r\n')
    players = get_player_info(all_info[1:-1])
    # round_wins = get_round_info(all_info[1:-1])  # normally stored in the fifth player
    played_map: str = re.search('<div style="font-weight:\d+;">[a-z]+_([a-zA-Z0-9_]+)</div>', all_info[0]).group(1).replace('_', ' ').title()
    score: Union[list, tuple] = re.findall('<span style="letter-spacing:[0-9\-.]+?em;">(\d+)</span>', all_info[0])
    started_as = ''
    played_server = re.search('<div style="font-weight:\d+;">([A-Za-z ]+Server)</div>', all_info[0])
    timestamp = re.search('<div style="font-weight:\d+;">(\d+?(?:st|nd|rd|th) [A-Za-z]+ \d+? \d+?:\d+?:\d+?)</div>', all_info[0])

    if timestamp is not None:
        timestamp = parse_time(timestamp.group(1))
    else:
        write(f'Could not parse time... report: {match_id}', color=FgColor.Yellow)
        timestamp = 0

    if played_server is not None:
        played_server = played_server.group(1)
    else:
        played_server = 'undetected'
    searched_player: Dict[str, Union[str, Dict[str]]] = {}
    for i, team in enumerate(players):
        for player in team:
            if player['steam_id'] == str(steam_id):
                searched_player = player
                score = (score[0], score[1]) if i == 0 else (score[1], score[0])
                score = tuple(map(str, score))
                started_as = 'T' if i == 0 else 'CT'
                break
    return {'match_id': str(match_id), 'map': played_map, 'score': score, 'server': played_server,
            'player': searched_player, 'players': players, 'started_as': started_as, 'timestamp': timestamp}


def get_player_info(raw_players: list):
    players: List[List[Dict[str, Union[str, Dict[str, str]]]]] = [[], []]
    stat_keys = ['K', 'D', 'A', '+/-', 'K/D', 'ADR', 'HS', 'FK', 'FD', 'Trade_K', 'Trade_D', 'Trade_FK', 'Trade_FD', '1v5', '1v4', '1v3', '1v2', '1v1', '5k', '4k', '3k', '2k', '1k', 'KAST', 'HLTV']
    pattern = {
        'info': re.compile('img src="(.+?)".+?<a href="/player/(\d+)".+?;">(.*?)</span>'),
        'rank': re.compile('(?:ranks/)(\d+)(?:\.png)'),
        'rank_change': re.compile('(?:glyphicon glyphicon-chevron-)(up|down)'),
        'stats': re.compile('(?:"> *)([\d.\-%]*)(?: *</td>)'),
        'team': re.compile('</tr> +</tbody> +<tbody>'),
        'email_name': re.compile('data-cfemail="(.+?)"')
    }
    team = 0
    for player in raw_players:
        info = pattern['info'].search(player)

        encoded_name = pattern['email_name'].search(info.group(3))
        if encoded_name is not None:
            name = email_decode(encoded_name.group(1))
        else:
            name = info.group(3)

        try:
            rank = pattern['rank'].search(player).group(1)
        except AttributeError:
            rank = '0'
        try:
            rank_change = pattern['rank_change'].search(player).group(1)
            if rank_change == 'up':
                rank += '+'
            else:
                rank += '-'
        except AttributeError:
            pass
        # stat_values = remove_indices(re.findall('(?:"> *)([\d.\-%]*)(?: *</td>)', player), [9, 10, 11, 12, 17, 18, 19, 20])
        stat_values: List[str] = remove_indices(pattern['stats'].findall(player), [9, 10, 11, 12, 17, 18, 19, 20])
        stats = dict(zip(stat_keys, stat_values))
        players[team].append({'steam_id': info.group(2), 'username': name, 'rank': rank, 'avatar_url': info.group(1), 'stats': stats})
        if not team:
            team = 1 if pattern['team'].search(player) is not None else 0
    return players


def get_round_info(raw_players):
    pattern = {'rounds': '<ul style="padding:0; margin:0; list-style-type:none;">',
               'winner': re.compile('li style=".+? <div style=".+?solid #([0-9A-Fa-f]+);'),
               'ct': 3844602,
               't': 16232254}
    round_info = None
    for player in raw_players:
        if pattern['rounds'] in player:
            round_info = player
            break
    if not round_info:
        return None
    round_wins = []
    for i in pattern['winner'].findall(round_info):
        if int(i, 16) == pattern['t']:
            round_wins.append(0)
        elif int(i, 16) == pattern['ct']:
            round_wins.append(1)
        else:
            write(f'unknown team #{i}')
    return round_wins


# noinspection PyShadowingNames
def add_players_to_list(match_data: dict, steam_id):
    global player_list_header
    player_list_path = os.path.join(path_vars['appdata_path'], f'player_list_{steam_id}.csv')
    data = get_csv_list(player_list_path, player_list_header)
    for i, _dict in enumerate(data):
        data[i]['seen_in'] = convert_string_to_list(_dict['seen_in'])
    all_player = list(itertools.chain.from_iterable(match_data['players']))
    players = remove_dict(all_player, 'steam_id', str(steam_id))

    for player in players:
        i = find_dict(data, 'steam_id', player['steam_id'])

        if i is not None:
            data[i]['name'] = player['username']
            data[i]['seen_in'].append(int(match_data['match_id']))
            data[i]['seen_in'] = list(dict.fromkeys(data[i]['seen_in']))
            data[i]['timestamp'] = match_data['timestamp'] if int(data[i]['timestamp']) < int(match_data['timestamp']) else data[i]['timestamp']
        else:
            data.append({'steam_id': player['steam_id'], 'name': player['username'], 'seen_in': [int(match_data['match_id'])], 'timestamp': match_data['timestamp']})

    data.sort(key=lambda x: (len(x['seen_in']), int(x['timestamp'])), reverse=True)

    with open(player_list_path, 'w', encoding='utf-8', newline='') as f:
        writer = csv.DictWriter(f, fieldnames=player_list_header, restval='', delimiter=';')
        writer.writeheader()
        writer.writerows(data)


def parse_time(datetime_str: str):
    clean_date = re.sub(r'(\d)(st|nd|rd|th)', r'\1', datetime_str)
    dt_obj = datetime.datetime.strptime(f'{clean_date} +0000', '%d %b %Y %H:%M:%S %z')
    return int(datetime.datetime.timestamp(dt_obj))


def epoch_to_iso(epoch_time):
    return datetime.datetime.fromtimestamp(float(epoch_time), datetime.datetime.now().astimezone().tzinfo).isoformat()


def add_match_id(sharecode: str, match: dict):
    global path_vars
    csv_path = os.path.join(path_vars['appdata_path'], f'last_game_{steam_id}.csv')
    data = get_csv_list(csv_path)
    m_index = find_dict(data, 'sharecode', sharecode)
    if isinstance(match, str):  # request wasn't successful
        data[m_index]['match_id'] = match
        avatar_url = ''
    else:
        data[m_index]['match_id'] = match['match_id']
        data[m_index]['map'] = match['map']
        data[m_index]['server'] = match['server']
        data[m_index]['timestamp'] = match['timestamp']
        data[m_index]['team_score'] = match['score'][0]
        data[m_index]['enemy_score'] = match['score'][1]
        data[m_index]['start_team'] = match['started_as']
        data[m_index]['kills'] = match['player']['stats']['K']
        data[m_index]['assists'] = match['player']['stats']['A']
        data[m_index]['deaths'] = match['player']['stats']['D']
        data[m_index]['5k'] = match['player']['stats']['5k']
        data[m_index]['4k'] = match['player']['stats']['4k']
        data[m_index]['3k'] = match['player']['stats']['3k']
        data[m_index]['2k'] = match['player']['stats']['2k']
        data[m_index]['1k'] = match['player']['stats']['1k']
        data[m_index]['ADR'] = match['player']['stats']['ADR']
        data[m_index]['HS%'] = re.sub('\D', '', match['player']['stats']['HS'])
        data[m_index]['HLTV'] = round(float(match['player']['stats']['HLTV']) * 100)
        data[m_index]['rank'] = match['player']['rank']
        data[m_index]['username'] = match['player']['username']
        avatar_url = match['player']['avatar_url']

        try:
            data[m_index]['K/D'] = round((float(match['player']['stats']['K']) / float(match['player']['stats']['D'])) * 100)
        except (ZeroDivisionError, ValueError):
            data[m_index]['K/D'] = '∞'

    global csv_header
    with open(csv_path, 'w', newline='', encoding='utf-8') as last_game:
        writer = csv.DictWriter(last_game, fieldnames=csv_header, delimiter=';', lineterminator='\n')
        writer.writeheader()
        writer.writerows(data)
    return generate_table(data[m_index], avatar_url)


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
        print('sleeping', ratelimit_wait)
        time.sleep(ratelimit_wait)


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


def time_output(current: int, average: int):
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
    global shell
    current_position = win32api.GetCursorPos()
    current_csgo_status = win32gui.GetWindowPlacement(hwnd)[1]
    win32gui.ShowWindow(hwnd, win32con.SW_MAXIMIZE)
    # shell.AppActivate('Counter-Strike: Global Offensive')
    shell.SendKeys('toggleconsole', True)
    shell.SendKeys('{enter}', True)
    keyboard.send(key)
    time.sleep(0.05)
    shell.sendKeys('status', True)
    shell.SendKeys('{enter}', True)
    shell.SendKeys('toggleconsole', True)
    time.sleep(0.05)
    shell.SendKeys('{enter}', True)
    if current_csgo_status == 2:
        minimize_csgo(hwnd, reset_position, current_position)
    return


# noinspection PyShadowingNames
class WindowEnumerator(threading.Thread):
    def __init__(self, sleep_interval: float = 0.5):
        super().__init__(name='WindowEnumerator')
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


def convert_string_to_list(_str: str) -> list:
    return list(map(int, _str.lstrip('[').rstrip(']').split(', ')))


path_vars = {'appdata_path': os.path.join(os.getenv('APPDATA'), 'CSGO AUTO ACCEPT\\'), 'mute_csgo_path': f'"{os.path.join(os.getcwd(), "sounds", "nircmdc.exe")}" muteappvolume csgo.exe '}

try:
    os.mkdir(path_vars['appdata_path'])
except FileExistsError:
    pass

overwrite_dict = {'key': '0', 'msg': '', 'end': '\n'}
if not sys.stdout.isatty():
    console_window = {'prefix': '\r', 'suffix': '', 'isatty': False}
else:
    console_window = {'prefix': '', 'suffix': '\r', 'isatty': True}

pushbullet_dict: Dict[str, Union[str, int, pushbullet.pushbullet.Device, Tuple[str, str, str, str]]] = \
    {'note': '', 'urgency': 0, 'device': None, 'push_info': ('not active', 'on if accepted', 'all game status related information', 'all information (game status/csgostats.gg information)')}

re_pattern = {'lobby_info': re.compile("(?<!Machines' = '\d''members:num)(C?TSlotsFree|Players)(?:' = ')(\d+'?)"),
              'steam_path': re.compile('\\t"\d*"\\t\\t"'),
              'decolor': re.compile('\033\[[0-9;]+m')}

# CONFIG HANDLING
config = configparser.ConfigParser()
config.read('config.ini')

try:
    cfg = {'activate_script': config.get('HotKeys', 'Activate Script'), 'activate_push_notification': config.get('HotKeys', 'Activate Push Notification'),
           'info_newest_match': config.get('HotKeys', 'Get Info on newest Match'), 'mute_csgo_toggle': config.get('HotKeys', 'Mute CSGO'),
           'open_live_tab': config.get('HotKeys', 'Live Tab Key'), 'switch_accounts': config.get('HotKeys', 'Switch accounts for csgostats.gg'),
           'end_script': config.get('HotKeys', 'End Script'), 'discord_key': config.get('HotKeys', 'Discord Toggle'), 'minimize_key': config.get('HotKeys', 'Minimize CSGO'),
           'sleep_interval': config.getfloat('Screenshot', 'Interval'), 'steam_api_key': config.get('csgostats.gg', 'API Key'),
           'max_queue_position': config.getint('csgostats.gg', 'Auto-Retrying for queue position below'), 'log_color': config.get('Screenshot', 'Log Color').lower(),
           'auto_retry_interval': config.getint('csgostats.gg', 'Auto-Retrying-Interval'), 'pushbullet_device_name': config.get('Pushbullet', 'Device Name'), 'pushbullet_api_key': config.get('Pushbullet', 'API Key'),
           'forbidden_programs': config.get('Screenshot', 'Forbidden Programs'), 'discord_url': config.get('csgostats.gg', 'Discord Webhook URL'), 'taskbar_position': config.getfloat('Screenshot', 'Taskbar Factor'),
           'player_webhook': config.get('csgostats.gg', 'Player Info Webhook')}
except (configparser.NoOptionError, configparser.NoSectionError, ValueError):
    write('ERROR IN CONFIG')
    cfg = {'ERROR': None}
    exit('CHECK FOR NEW CONFIG')

csv_header = ['sharecode', 'match_id', 'map', 'team_score', 'enemy_score', 'start_team',
              'match_time', 'wait_time', 'afk_time', 'mvps', 'points', 'kills', 'assists', 'deaths', '5k', '4k', '3k', '2k', '1k', 'K/D', 'ADR', 'HS%', 'HLTV', 'rank', 'username', 'server', 'timestamp']
player_list_header = ['steam_id', 'name', 'seen_in', 'timestamp']
csgo_stats_test_for = ['map', 'team_score', 'enemy_score', 'start_team', 'kills', 'assists', 'deaths', '5k', '4k', '3k', '2k', '1k', 'K/D', 'ADR', 'HS%', 'HLTV', 'rank', 'username', 'server', 'timestamp']

accounts = []
get_accounts_from_cfg()
get_csgo_path()
steam_id = get_current_steam_user()

if not steam_id:
    account = accounts[0]
    steam_id = account['steam_id']
else:
    account = [i for i in accounts if steam_id == i['steam_id']][0]

with open(path_vars['csgo_path'] + 'console_log.log', 'w', encoding='utf-8') as log:
    log.write('')
with open(path_vars['appdata_path'] + '\\console.log', 'w', encoding='utf-8') as debug_log:
    debug_log.write('')

if not os.path.exists(path_vars['csgo_path'] + 'cfg\\gamestate_integration_GSI.cfg'):
    copyfile(os.path.join(os.getcwd(), 'GSI') + '\\gamestate_integration_GSI.cfg', path_vars['csgo_path'] + 'cfg\\gamestate_integration_GSI.cfg')
    write('Added GSI CONFIG to cfg folder. Counter-Strike needs to be restarted if running!', color=FgColor.Red)

if cfg['taskbar_position'] > 1.0:
    cfg['taskbar_position'] = 1.0 / cfg['taskbar_position']
    write(f'Taskbar Factor to big, using inverse {cfg["taskbar_position"]}')
cfg['taskbar_position'] = task_bar(cfg['taskbar_position'])

scraper = cloudscraper.create_scraper()
queue_difference = []
csgostats_retry = time.time()

window_ids = []

sleep_interval = cfg['sleep_interval']
sleep_interval_looking_for_accept = 0.05
shell = win32com.client.Dispatch('WScript.Shell')

if __name__ == '__main__':
    pass
