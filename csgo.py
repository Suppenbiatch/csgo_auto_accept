import configparser
import json
import operator
import os
import re
import sys
import time
import webbrowser
import winreg
import datetime
from shutil import copyfile
from typing import List

import pushbullet
import pyperclip
import requests
import win32api
import win32con
import win32gui
from PIL import ImageGrab, Image
from playsound import playsound

from GSI import server


# noinspection PyShadowingNames
def Avg(lst: list):
    if not lst:
        return None
    return sum(lst) / len(lst)


# noinspection PyShadowingNames,PyUnusedLocal
def enum_cb(hwnd, results):
    winlist.append((hwnd, win32gui.GetWindowText(hwnd)))


def mute_csgo(lvl: int):
    global path_vars
    os.system(path_vars['mute_csgo_path'] + str(lvl))


def timedelta(then=None, seconds=None):
    if seconds is not None:
        return str(datetime.timedelta(seconds=abs(int(seconds))))
    else:
        now = time.time()
        return str(datetime.timedelta(seconds=abs(int(now - then))))


# noinspection PyShadowingNames
def write(message, add_time: bool = True, push: int = 0, push_now: bool = False, output: bool = True, overwrite: str = '0'):  # last overwrite key used: 11
    if output:
        message = str(message)
        if add_time:
            message = datetime.datetime.now().strftime('%H:%M:%S') + ': ' + message
        else:
            message = ' ' * 10 + message
        global overwrite_dict
        if overwrite != '0':
            ending = console_window['suffix']
            if overwrite_dict['key'] == overwrite:
                if console_window['isatty']:
                    print(' ' * int(len(overwrite_dict['msg']) + 1), end=ending)
                message = console_window['prefix'] + message
            else:
                if overwrite_dict['end'] != '\n':
                    message = '\n' + message
        else:
            ending = '\n'
            if overwrite_dict['end'] != '\n':
                message = '\n' + message

        overwrite_dict = {'key': overwrite, 'msg': message, 'end': ending}
        print(message, end=ending)

    if push >= 3:
        global pushbullet_dict
        if message:
            pushbullet_dict['note'] = pushbullet_dict['note'] + str(message.strip('\n\r')) + '\n'
        if push_now:
            pushbullet_dict['device'].push_note('CSGO AUTO ACCEPT', pushbullet_dict['note'])
            pushbullet_dict['note'] = ''


# noinspection PyShadowingNames
def click(x: int or tuple, y: int = 0):
    if isinstance(x, tuple):
        y = x[1]
        x = x[0]

    win32api.mouse_event(win32con.MOUSEEVENTF_LEFTUP, x, y, 0, 0)
    win32api.SetCursorPos((x, y))
    win32api.mouse_event(win32con.MOUSEEVENTF_LEFTDOWN, x, y, 0, 0)
    win32api.mouse_event(win32con.MOUSEEVENTF_LEFTUP, x, y, 0, 0)


# noinspection PyShadowingNames
def anti_afk(window_id: int):
    current_cursor_position = win32api.GetCursorPos()
    moves = int(win32api.GetSystemMetrics(1) / 3) + 1
    win32gui.ShowWindow(window_id, win32con.SW_MAXIMIZE)
    for _ in range(moves):
        win32api.mouse_event(win32con.MOUSEEVENTF_MOVE, 0, -15)
    click(win32api.GetCursorPos())
    for _ in range(moves):
        win32api.mouse_event(win32con.MOUSEEVENTF_MOVE, 0, 15)
    for _ in range(int(moves / 1.07)):
        win32api.mouse_event(win32con.MOUSEEVENTF_MOVE, 0, -8)
    time.sleep(0.075)
    win32gui.ShowWindow(window_id, 2)
    click(0, 0)
    time.sleep(0.025)
    win32api.SetCursorPos(current_cursor_position)


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
def getScreenShot(window_id: int, area: tuple = (0, 0, 0, 0)):
    area = list(area)
    win32gui.ShowWindow(window_id, win32con.SW_MAXIMIZE)
    scaled_area = [screen_size[0] / 2560, screen_size[1] / 1440]
    scaled_area = 2 * scaled_area
    for i, _ in enumerate(area[-2:], start=len(area) - 2):
        area[i] += 1
    for i, val in enumerate(area, start=0):
        scaled_area[i] = scaled_area[i] * val
    scaled_area = list(map(int, scaled_area))
    image = ImageGrab.grab(scaled_area)
    return image


# noinspection PyShadowingNames
def getAccountsFromCfg():
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

    steam_ids = steam_ids.lstrip(',').rstrip(',')
    try:
        profiles = requests.get('http://api.steampowered.com/ISteamUser/GetPlayerSummaries/v0002/?key=' + cfg['steam_api_key'] + '&steamids=' + steam_ids)
        if profiles.status_code == 200:
            profiles = profiles.json()['response']['players']
            name_list = [online_data['personaname'] for local_acc in accounts for online_data in profiles if online_data['steamid'] == local_acc['steam_id']]
            for num, val in enumerate(accounts):
                val['name'] = name_list[num]
        else:
            truth_table['steam_error'] = True
    except TimeoutError:
        truth_table['steam_error'] = True

    if truth_table['steam_error']:
        write('INVAILD STEAM API KEY or INTERNET CONNECTION ERROR, couldnt fetch usernames')
        truth_table['steam_error'] = False
        for num, val in enumerate(accounts):
            val['name'] = 'Unknown Name ' + str(num)


# noinspection PyShadowingNames
def getCsgoPath():
    steam_reg_key = winreg.OpenKey(winreg.HKEY_LOCAL_MACHINE, 'SOFTWARE\WOW6432Node\Valve\Steam')
    steam_path = winreg.QueryValueEx(steam_reg_key, 'InstallPath')[0]
    libraries = [steam_path + '\\steamapps']
    with open(steam_path + '\\steamapps\\libraryfolders.vdf', 'r') as library_file:
        library_data = library_file.readlines()
        libraries.extend([re_pattern['steam_path'].sub('', i.rstrip('"\n')) for i in library_data if bool(re_pattern['steam_path'].match(i))])

    csgo_path = [i for i in libraries if os.path.exists(i + '\\appmanifest_730.acf')][0] + '\\common\\Counter-Strike Global Offensive\\csgo\\'
    if not csgo_path.replace('\\common\\Counter-Strike Global Offensive\\csgo\\', ''):
        write('DID NOT FIND CSGO PATH', add_time=False)
        global error_level
        error_level += 1
    global path_vars
    path_vars['csgo_path'] = csgo_path
    path_vars['steam_path'] = steam_path


# noinspection PyShadowingNames
def getCurrentSteamUser():
    steam_reg_key = winreg.OpenKey(winreg.HKEY_CURRENT_USER, 'Software\Valve\Steam\ActiveProcess')
    current_user = winreg.QueryValueEx(steam_reg_key, 'ActiveUser')[0]
    return str(current_user + 76561197960265728)


# noinspection PyShadowingNames
def CheckUserDataAutoExec(steam_id_3: str):
    global path_vars
    userdata_path = path_vars['steam_path'] + '\\userdata\\' + steam_id_3 + '\\730\\local\\cfg\\'
    str_in_autoexec = ['developer 1', 'con_logfile "console_log.log"', 'con_filter_enable "2"', 'con_filter_text_out "Player:"', 'con_filter_text "Damage"', 'log_color General ' + cfg['log_color']]
    with open(userdata_path + 'autoexec.cfg', 'a+') as autoexec:
        autoexec.seek(0)
        lines = autoexec.readlines()
        for autoexec_str in str_in_autoexec:
            if not any(autoexec_str.lower() in line.rstrip('\n').lower() for line in lines):
                write('Added {} to "autoexec.cfg" file in {}'.format(autoexec_str, userdata_path), add_time=False)
                write('RESTART Counter-Strike for the script to work', add_time=False)
                autoexec.write('\n' + autoexec_str + '\n')
    if os.path.exists(path_vars['csgo_path'] + '\\cfg\\autoexec.cfg'):
        write('YOU HAVE TO DELETE THE "autoexec.cfg" in {} WITH AND MERGE IT WITH THE ONE IN {}'.format(path_vars['csgo_path'] + '\\cfg', userdata_path), add_time=False)
        write('THE SCRIPT WONT WORK UNTIL THERE IS NO "autoexec.cfg" in {}'.format(path_vars['csgo_path'] + '\\cfg'), add_time=False)
        global error_level
        error_level += 1


# noinspection PyShadowingNames
def getAvgMatchTime(steam_id: str):
    try:
        with open(path_vars['appdata_path'] + 'game_time_' + steam_id + '.txt', 'r+') as game_time:
            all_game_times = game_time.readlines()
            game_time.seek(0)
            [game_time.write(i) for i in all_game_times[-10000:]]
            all_game_times = [i.rstrip('\n').split(',') for i in all_game_times[-10000:]]
            match_time = [int(i[0]) for i in all_game_times]
            search_time = [int(i[1]) for i in all_game_times if i[1] != '']
    except FileNotFoundError:
        return None, None, None, None
    return int(Avg(match_time)), int(Avg(search_time)), timedelta(seconds=sum(match_time)), timedelta(seconds=sum(search_time))


# noinspection PyShadowingNames
def getOldSharecodes(last_x: int = -1, from_x: str = ''):
    if last_x >= 0:
        return []
    global path_vars

    try:
        with open(path_vars['appdata_path'] + 'last_game_' + accounts[current_account]['steam_id'] + '.txt', 'r') as last_game:
            games = last_game.readlines()
    except FileNotFoundError:
        with open(path_vars['appdata_path'] + 'last_game_' + accounts[current_account]['steam_id'] + '.txt', 'w') as last_game:
            last_game.write(accounts[current_account]['match_token'] + '\n')
            games = [accounts[current_account]['match_token']]

    with open(path_vars['appdata_path'] + 'last_game_' + accounts[current_account]['steam_id'] + '.txt', 'w') as last_game:
        games = games[-1000:]
        for i, val in enumerate(games):
            games[i] = 'CSGO' + val.strip('\n').split('CSGO')[1]
            last_game.write(games[i] + '\n')

    if from_x:
        try:
            return games[(len(games) - games.index(from_x)) * -1:]
        except ValueError:
            return []
    return games[last_x:]


# noinspection PyShadowingNames
def getNewCSGOSharecodes(game_id: str):
    sharecodes = [game_id]
    next_code = game_id
    while next_code != 'n/a':
        steam_url = 'https://api.steampowered.com/ICSGOPlayers_730/GetNextMatchSharingCode/v1?key=' + cfg['steam_api_key'] + '&steamid=' + accounts[current_account]['steam_id'] + '&steamidkey=' + accounts[current_account][
            'auth_code'] + '&knowncode=' + game_id
        try:
            next_code = (requests.get(steam_url, timeout=2).json()['result']['nextcode'])
        except (KeyError, requests.exceptions.ConnectionError, requests.exceptions.Timeout, json.decoder.JSONDecodeError):
            write('WRONG Match Token, Authentication Code or Steam ID!')
            break

        if next_code:
            if next_code != 'n/a':
                sharecodes.append(next_code)
                game_id = next_code
                with open(path_vars['appdata_path'] + 'last_game_' + accounts[current_account]['steam_id'] + '.txt', 'a') as last_game:
                    last_game.write(next_code + '\n')
    sharecodes = sharecodes[1:] if len(sharecodes) > 1 else sharecodes
    return [{'sharecode': code, 'queue_pos': None} for code in sharecodes]


# noinspection PyShadowingNames
def UpdateCSGOstats(repeater=None, get_all_games=False):
    all_games, completed_games, not_completed_games, = [], [], []
    global queue_difference, time_table
    if repeater is None:
        repeater = []

    if repeater:
        if get_all_games:
            sharecodes = [getOldSharecodes(from_x=code['sharecode']) for code in repeater]
            sharecodes = max(sharecodes, key=len)
        else:
            sharecodes = [code['sharecode'] for code in repeater]

        responses = [requests.post('https://csgostats.gg/match/upload/ajax', data={'sharecode': sharecode, 'index': 0}) for sharecode in sharecodes]
        all_games = [r.json() for r in responses if r.status_code == requests.codes.ok]

    else:
        num = -1
        sharecode = getOldSharecodes(num)[0]
        while True:
            response = requests.post('https://csgostats.gg/match/upload/ajax', data={'sharecode': sharecode, 'index': '0'})
            try:
                all_games.append(response.json())
            except json.JSONDecodeError:
                return [{'sharecode': sharecode, 'queue_pos': None}]
            if response.json()['status'] != 'complete':
                num -= 1
                try:
                    sharecode = getOldSharecodes(num)[num]
                except IndexError:
                    break
            else:
                break
        temp_games = [{'sharecode': game['data']['sharecode']} for game in all_games if game['status'] != 'complete']
        if temp_games and len(all_games) > 1:
            all_games = all_games[:-1]

    for game in all_games:
        if game['status'] == 'complete':
            completed_games.append(game)
        else:
            not_completed_games.append(game)

    queued_games = [{'sharecode': game['data']['sharecode'], 'queue_pos': game['data']['queue_pos']} for game in not_completed_games if game['status'] != 'error']
    corrupt_games = [{'sharecode': game['data']['sharecode'], 'queue_pos': None} for game in not_completed_games if game['status'] == 'error']

    if queued_games:
        temp_string = ''
        for i, val in enumerate(queued_games):
            temp_string += '#' + str(i + 1) + ': in Queue #' + str(val['queue_pos']) + ' - '

        if repeater:
            current_queue_difference = Avg([last_game['queue_pos'] - game['queue_pos'] for game in queued_games for last_game in repeater if last_game['sharecode'] == game['sharecode'] and last_game['queue_pos'] is not None])
            if current_queue_difference:
                if current_queue_difference >= 0.0:
                    queue_difference.append(current_queue_difference / ((time.time() - time_table['csgostats_retry']) / 60))
                    queue_difference = queue_difference[-10:]
                    matches_per_min = round(Avg(queue_difference), 1)
                    if matches_per_min != 0.0:
                        time_till_done = timedelta(seconds=(queued_games[0]['queue_pos'] / matches_per_min) * 60)
                    else:
                        time_till_done = '∞:∞:∞'
                    temp_string += str(matches_per_min) + ' matches/min - #1 done in ' + time_till_done
        temp_string = temp_string.rstrip(' - ')
        write(temp_string, add_time=False, overwrite='4')

    time_table['csgostats_retry'] = time.time()
    repeater = [game for game in queued_games if game['queue_pos'] < cfg['max_queue_position']]
    repeater.extend([game for game in corrupt_games])

    if corrupt_games:
        write('An error occurred in {} game[s].'.format(len(corrupt_games)), overwrite='5')

    if completed_games:
        global pushbullet_dict
        for i in completed_games:
            sharecode = i['data']['sharecode']
            game_url = i['data']['url']
            info = ' '.join(i['data']['msg'].replace('-', '').replace('<br />', '. ').split('<')[0].rstrip(' ').split())
            write('Sharecode: {}'.format(sharecode), add_time=False, push=pushbullet_dict['urgency'])
            write('URL: {}'.format(game_url), add_time=False, push=pushbullet_dict['urgency'])
            write('Status: {}'.format(info), add_time=True, push=pushbullet_dict['urgency'])
            try:
                pyperclip.copy(game_url)
            except (pyperclip.PyperclipWindowsException, pyperclip.PyperclipTimeoutException):
                write('Failed to load URL in to clipboard', add_time=False)
        write(None, add_time=False, push=pushbullet_dict['urgency'], push_now=True, output=False)
    return repeater


# noinspection PyShadowingNames
def str_in_list(compare_strings: List[str], list_of_strings: List[str], replace: bool = False):
    replacement_str = '' if not replace else compare_strings[0]
    matching = [string.replace(replacement_str, '') for string in list_of_strings for compare_str in compare_strings if compare_str in string]
    if not replace:
        return any(matching)
    else:
        return matching


def check_for_forbidden_programs(process_list):
    titles = [i[1].lower() for i in process_list]
    forbidden_programs = [i.lstrip(' ').lower() for i in cfg['forbidden_programs'].split(',')]
    if forbidden_programs[0]:
        return any([name for name in titles for forbidden_name in forbidden_programs if forbidden_name == name])
    else:
        return False


error_level = 0
# OVERWRITE SETUP
path_vars = {'appdata_path': os.getenv('APPDATA') + '\\CSGO AUTO ACCEPT\\'}
try:
    os.mkdir(path_vars['appdata_path'])
except FileExistsError:
    pass

overwrite_dict = {'key': '0', 'msg': '', 'end': '\n'}
if not sys.stdout.isatty():
    console_window = {'prefix': '\r', 'suffix': '', 'isatty': False}
else:
    console_window = {'prefix': '', 'suffix': '\r', 'isatty': True}

# CONFIG HANDLING
config = configparser.ConfigParser()
config.read('config.ini')

try:
    cfg = {'activate_script': int(config.get('HotKeys', 'Activate Script'), 16), 'activate_push_notification': int(config.get('HotKeys', 'Activate Push Notification'), 16),
           'info_newest_match': int(config.get('HotKeys', 'Get Info on newest Match'), 16), 'mute_csgo_toggle': int(config.get('HotKeys', 'Mute CSGO'), 16),
           'open_live_tab': int(config.get('HotKeys', 'Live Tab Key'), 16), 'switch_accounts': int(config.get('HotKeys', 'Switch accounts for csgostats.gg'), 16),
           'end_script': int(config.get('HotKeys', 'End Script'), 16),
           'screenshot_interval': float(config.get('Screenshot', 'Interval')), 'debug_path': config.get('Screenshot', 'Debug Path'), 'steam_api_key': config.get('csgostats.gg', 'API Key'),
           'max_queue_position': config.getint('csgostats.gg', 'Auto-Retrying for queue position below'), 'log_color': config.get('Screenshot', 'Log Color').lower(),
           'auto_retry_interval': config.getint('csgostats.gg', 'Auto-Retrying-Interval'), 'pushbullet_device_name': config.get('Pushbullet', 'Device Name'), 'pushbullet_api_key': config.get('Pushbullet', 'API Key'),
           'forbidden_programs': config.get('Screenshot', 'Forbidden Programs')}
except (configparser.NoOptionError, configparser.NoSectionError, ValueError):
    write('ERROR IN CONFIG')
    cfg = {'ERROR': None}
    exit('CHECK FOR NEW CONFIG')


# BOOLEAN, TIME INITIALIZATION
truth_table = {'test_for_accept_button': False, 'test_for_warmup': False, 'test_for_success': False, 'first_ocr': True, 'testing': False, 'first_push': True, 'still_in_warmup': False, 'test_for_server': False, 'first_freezetime': True,
               'gsi_server_running': False, 'game_over': False, 'monitoring_since_start': False, 'players_still_connecting': False, 'first_game_over': True, 'disconnected_form_last': False, 'c4_round_first': True, 'steam_error': False}
time_table = {'csgostats_retry': time.time(), 'warmup_test_timer': time.time(), 'search_started': time.time(), 'console_read': time.time(), 'timed_execution_time': time.time(), 'match_accepted': time.time(),
              'match_started': time.time(), 'freezetime_started': time.time(), 'join_warmup_time': 0.0}
matchmaking = {'msg': [], 'update': [], 'players_accepted': [], 'lobby_data': [], 'server_found': False, 'server_ready': False}
afk_dict = {'time': time.time(), 'still_afk': [], 'start_time': time.time(), 'seconds_afk': 0, 'player_info': {'steamid': 0, 'state': {}}}
join_dict = {'t_full': False, 'ct_full': False}
scoreboard = {'CT': 0, 'T': 0, 'last_round_info': '', 'last_round_key': '0', 'extra_round_info': '', 'player': {}}
damage = []

re_pattern = {'damage': [re.compile('(Player: (.+?) - Damage Given\n-------------------------)'),
                         re.compile('(Damage Given to "(.+?)" - \d+ in \d (hit|hits))'),
                         re.compile('(Player: (.+?) - Damage Taken\n-------------------------)'),
                         re.compile('(Damage Taken from "(.+?)" - \d+ in \d (hit|hits))]}')],
              'lobby_info': re.compile("(?<!Machines' = '\d''members:num)(C?TSlotsFree|Players)(?:' = ')(\d+'?)"),
              'steam_path': re.compile('\\t"\d*"\\t\\t"')}



# ACCOUNT HANDLING, GETTING ACCOUNT NAME, GETTING CSGO PATH, CHECKING AUTOEXEC
accounts, current_account = [], 0
path_vars = {'steam_path': '', 'csgo_path': '', 'mute_csgo_path': '"' + os.getcwd() + '\\sounds\\nircmdc.exe" muteappvolume csgo.exe '}
getAccountsFromCfg()
getCsgoPath()
CheckUserDataAutoExec(accounts[current_account]['steam_id_3'])

if error_level:
    exit('an error occurred')

with open(path_vars['csgo_path'] + 'console_log.log', 'w', encoding='utf-8') as log:
    log.write('')
with open(cfg['debug_path'] + '\\console.log', 'w', encoding='utf-8') as debug_log:
    debug_log.write('')

if not os.path.exists(path_vars['csgo_path'] + 'cfg\\gamestate_integration_GSI.cfg'):
    copyfile(os.path.join(os.getcwd(), 'GSI') + '\\gamestate_integration_GSI.cfg', path_vars['csgo_path'] + 'cfg\\gamestate_integration_GSI.cfg')
    write('Added GSI CONFIG to cfg folder. Counter-Strike needs to be restarted if running!')
gsi_server = server.GSIServer(('127.0.0.1', 3000), "IDONTUSEATOKEN")

# INITIALIZATION FOR getScreenShot
screen_size = (win32api.GetSystemMetrics(0), win32api.GetSystemMetrics(1))
hwnd, hwnd_old = 0, 0
csgo_window_status = {'server_found': 2, 'new_tab': 2, 'in_game': 0}
toplist, csgo = [], []


# csgostats.gg VAR
retryer = []
queue_difference = []

'''
# WARMUP DETECTION SETUP
pytesseract.pytesseract.tesseract_cmd = cfg['tesseract_path']
cfg['stop_warmup_ocr'] = [int(i, 16) for i in cfg['stop_warmup_ocr'].split('-')]
cfg['stop_warmup_ocr'][1] += 1
no_text_found = 0
'''
# PUSHBULLET VAR
pushbullet_dict = {'note': '', 'urgency': 0, 'device': 0,
                   'push_info': ('not active', 'only if accepted', 'all game status related information', 'all information (game status/csgostats.gg information)')}

mute_csgo(0)
path_vars['appdata_path'] = os.getenv('APPDATA') + '\\CSGO AUTO ACCEPT\\'

write('READY')
while True:
    if win32api.GetAsyncKeyState(cfg['activate_script']) & 1:  # F9 (ACTIVATE / DEACTIVATE SCRIPT)
        truth_table['test_for_server'] = not truth_table['test_for_server']
        write('Looking for game: {}'.format(truth_table['test_for_server']), overwrite='1')
        if truth_table['test_for_server']:
            playsound('sounds/activated.wav', block=False)
            time_table['search_started'] = time.time()
            mute_csgo(1)
        else:
            playsound('sounds/deactivated.wav', block=False)
            mute_csgo(0)

    if win32api.GetAsyncKeyState(cfg['activate_push_notification']) & 1:  # F8 (ACTIVATE / DEACTIVATE PUSH NOTIFICATION)
        if not pushbullet_dict['device']:
            try:
                pushbullet_dict['device'] = pushbullet.PushBullet(cfg['pushbullet_api_key']).get_device(cfg['pushbullet_device_name'])
            except (pushbullet.errors.PushbulletError, pushbullet.errors.InvalidKeyError):
                write('Pushbullet is wrongly configured.\nWrong API Key or DeviceName in config.ini\n Restart Script if changes to config.ini were made.')
        if pushbullet_dict['device']:
            pushbullet_dict['urgency'] += 1
            if pushbullet_dict['urgency'] > len(pushbullet_dict['push_info']) - 1:
                pushbullet_dict['urgency'] = 0
            write('Pushing: {}'.format(pushbullet_dict['push_info'][pushbullet_dict['urgency']]), overwrite='2')

    if win32api.GetAsyncKeyState(cfg['info_newest_match']) & 1:  # F7 Key (UPLOAD NEWEST MATCH)
        write('Uploading / Getting status on newest match')
        queue_difference = []
        new_sharecodes = getNewCSGOSharecodes(getOldSharecodes(-1)[0])
        write(new_sharecodes)
        for new_code in new_sharecodes:
            retryer.append(new_code) if new_code['sharecode'] not in [old_code['sharecode'] for old_code in retryer] else retryer
        retryer = UpdateCSGOstats(retryer, get_all_games=True)

    if win32api.GetAsyncKeyState(cfg['open_live_tab']) & 1:  # F13 Key (OPEN WEB BROWSER ON LIVE GAME TAB)
        if hwnd:
            csgo_window_status['new_tab'] = win32gui.GetWindowPlacement(hwnd)[1]
        if csgo_window_status['new_tab'] != 2:
            win32gui.ShowWindow(hwnd, win32con.SW_MAXIMIZE)
        webbrowser.open_new_tab('https://csgostats.gg/player/' + accounts[current_account]['steam_id'] + '#/live')
        # write('new tab opened', add_time=False)
        if csgo_window_status['new_tab'] != 2:
            time.sleep(0.5)
            win32gui.ShowWindow(hwnd, win32con.SW_MAXIMIZE)

    if win32api.GetAsyncKeyState(cfg['switch_accounts']) & 1:  # F15 (SWITCH ACCOUNTS)
        current_account += 1
        if current_account > len(accounts) - 1:
            current_account = 0
        CheckUserDataAutoExec(accounts[current_account]['steam_id_3'])
        write('current account is: {}'.format(accounts[current_account]['name']), add_time=False, overwrite='3')

    if win32api.GetAsyncKeyState(cfg['mute_csgo_toggle']) & 1:  # F6 (TOGGLE MUTE CSGO)
        write('Mute toggled!', add_time=False)
        mute_csgo(2)

    if win32api.GetAsyncKeyState(cfg['end_script']) & 1:  # POS1 (END SCRIPT)
        write('Exiting Script!')
        break

    if retryer:
        if time.time() - time_table['csgostats_retry'] > cfg['auto_retry_interval']:
            retryer = UpdateCSGOstats(retryer)
    winlist = []
    win32gui.EnumWindows(enum_cb, toplist)
    csgo = [(hwnd, title) for hwnd, title in winlist if 'counter-strike: global offensive' == title.lower()]

    if not csgo:
        continue
    hwnd = csgo[0][0]

    if hwnd_old != hwnd:
        truth_table['test_for_server'] = False
        hwnd_old = hwnd
        current_steamid = getCurrentSteamUser()
        try:
            current_account = [i for i, val in enumerate(accounts) if current_steamid == val['steam_id']][0]
            CheckUserDataAutoExec(accounts[current_account]['steam_id_3'])
        except IndexError:
            write('Account is not in the config.ini!\nScript will not work properly!', add_time=False, overwrite='9')
            playsound('sounds/fail.wav', block=False)
            exit('Update config.ini!')
        write('Current account is: {}'.format(accounts[current_account]['name']), add_time=False, overwrite='9')

        if check_for_forbidden_programs(winlist):
            write('A forbidden program is still running...', add_time=False)
            playsound('sounds/fail.wav', block=False)

    if not truth_table['gsi_server_running']:
        write('CS:GO GSI Server starting..', overwrite='8')
        gsi_server.start_server()
        truth_table['gsi_server_running'] = True
        write('CS:GO GSI Server running..', overwrite='8')

    # TESTING HERE
    if win32api.GetAsyncKeyState(0x0) & 1:  # UNBOUND, 6f == '\' TEST CODE
        truth_table['testing'] = not truth_table['testing']
        write('TestCode active: %s.' % str(truth_table['testing']), add_time=False, overwrite='testcode')

    if time.time() - time_table['console_read'] > 0.2:
        time_table['console_read'] = time.time()
        with open(path_vars['csgo_path'] + 'console_log.log', 'r+', encoding='utf-8') as log:
            console_lines = [i.strip('\n') for i in log.readlines()]
            '''for i in console_lines:
                write(i)'''
            log.seek(0)
            log.truncate()
        with open(cfg['debug_path'] + '\\console.log', 'a', encoding='utf-8') as debug_log:
            [debug_log.write(i + '\n') for i in console_lines]
        matchmaking['msg'] = str_in_list(['Matchmaking message: '], console_lines, replace=True)
        matchmaking['update'] = str_in_list(['Matchmaking update: '], console_lines, replace=True)
        matchmaking['players_accepted'] = str_in_list(['Server reservation2 is awaiting '], console_lines, replace=True)
        matchmaking['lobby_data'] = str_in_list(["LobbySetData: "], console_lines, replace=True)
        matchmaking['server_found'] = str_in_list(['Matchmaking reservation confirmed: '], console_lines)
        matchmaking['server_ready'] = str_in_list(['ready-up!'], console_lines)
        matchmaking['server_abandon'] = str_in_list(['Closing Steam Net Connection to ='], console_lines, replace=True)
    else:
        matchmaking = {'msg': [], 'update': [], 'players_accepted': [], 'lobby_data': [], 'server_found': False, 'server_ready': False, 'server_abandon': []}

    if matchmaking['update']:
        if matchmaking['update'][-1] == '1':
            if not truth_table['test_for_server']:
                truth_table['test_for_server'] = True
                write('Looking for match: {}'.format(truth_table['test_for_server']), overwrite='1')
                time_table['search_started'] = time.time()
                playsound('sounds/activated.wav', block=False)
            mute_csgo(1)
        elif matchmaking['update'][-1] == '0' and truth_table['test_for_server']:
            mute_csgo(0)

    if truth_table['test_for_server']:
        if matchmaking['server_found']:
            playsound('sounds/server_found.wav', block=False)
            truth_table['test_for_success'] = True
        if matchmaking['server_ready']:
            write('Server found, starting to look for accept button.')
            truth_table['test_for_accept_button'] = True
            csgo_window_status['server_found'] = win32gui.GetWindowPlacement(hwnd)[1]
            win32gui.ShowWindow(hwnd, win32con.SW_MAXIMIZE)

    if truth_table['test_for_accept_button']:
        img = getScreenShot(hwnd, (1265, 760, 1295, 785))
        accept_avg = color_average(img, [(76, 175, 80), (90, 203, 94)])
        if relate_list(accept_avg, (2, 2, 2)):
            write('Trying to Accept.', push=pushbullet_dict['urgency'] + 1)
            truth_table['test_for_accept_button'] = False

            current_cursor_position = win32api.GetCursorPos()
            for _ in range(5):
                win32gui.ShowWindow(hwnd, win32con.SW_MAXIMIZE)
                click(int(screen_size[0] / 2), int(screen_size[1] / 1.78))
            if csgo_window_status['server_found'] == 2:  # was minimized when a server was found
                time.sleep(0.075)
                win32gui.ShowWindow(hwnd, 2)
                time.sleep(0.025)
                click(0, 0)
                win32api.SetCursorPos(current_cursor_position)
            else:
                win32api.SetCursorPos(current_cursor_position)

            write('Trying to catch a loading map.')
            playsound('sounds/accept_found.wav', block=False)

    if truth_table['test_for_accept_button'] or truth_table['test_for_success']:
        if str_in_list(['Match confirmed'], matchmaking['msg']):
            write('All Players accepted.', add_time=False, overwrite='11')
            write('Took {} since trying to find a match.'.format(timedelta(time_table['search_started'])), add_time=False, push=pushbullet_dict['urgency'] + 1)
            write('Match has started.', push=pushbullet_dict['urgency'] + 2, push_now=True)
            truth_table['test_for_warmup'] = True
            truth_table['first_game_over'], truth_table['game_over'] = True, False
            truth_table['disconnected_form_last'] = False
            truth_table['warmup_started'] = False
            truth_table['first_freezetime'] = False
            truth_table['test_for_server'] = False
            truth_table['test_for_accept_button'] = False
            truth_table['test_for_success'] = False
            truth_table['monitoring_since_start'] = True
            mute_csgo(0)
            playsound('sounds/done_testing.wav', block=False)
            time_table['match_accepted'] = time.time()
            afk_dict['time'] = time.time()
            afk_dict['start_time'] = time.time()

        if str_in_list(['Other players failed to connect', 'Failed to ready up'], matchmaking['msg']):
            write('Match has not started! Continuing to search for a Server!', push=pushbullet_dict['urgency'] + 1, push_now=True)
            playsound('sounds/back_to_testing.wav', block=False)
            mute_csgo(1)
            truth_table['test_for_server'] = True
            truth_table['test_for_accept_button'] = False
            truth_table['test_for_success'] = False

        for i in matchmaking['players_accepted']:
            i = i.split('/')
            players_accepted = str(int(i[1]) - int(i[0]))
            write('{} Players of {} already accepted.'.format(players_accepted, i[1]), add_time=False, overwrite='11')

    if truth_table['players_still_connecting']:
        lobby_data = ''.join(matchmaking['lobby_data'])
        lobby_info = re_pattern['lobby_info'].findall(lobby_data)
        lobby_data = [(info, int(num.strip("'\n"))) for info, num in lobby_info]
        for i in lobby_data:
            if i[0] == 'Players':
                write('{} players joined.'.format(i[1]), add_time=False, overwrite='11')
            if i[0] == 'TSlotsFree' and i[1] == 0:
                join_dict['t_full'] = True
            if i[0] == 'CTSlotsFree' and i[1] == 0:
                join_dict['ct_full'] = True
            if join_dict['t_full'] and join_dict['ct_full']:
                write('Server full, All Players connected. Took {} since match start.'.format(timedelta(time_table['warmup_started'])), overwrite='11')
                playsound('sounds/minute_warning.wav', block=True)
                truth_table['players_still_connecting'] = False
                join_dict['t_full'], join_dict['ct_full'] = False, False
                break

    try:
        if 'Disconnect' in matchmaking['server_abandon'][-1]:
            # time_table['match_started'], time_table['match_accepted'] = time.time(), time.time()
            write('Server disconnected')
            truth_table['disconnected_form_last'] = True
            afk_dict['time'] = time.time()
    except IndexError:
        pass

    if time.time() - time_table['timed_execution_time'] > 2:
        time_table['timed_execution_time'] = time.time()
        game_state = {'map_phase': gsi_server.get_info('map', 'phase'), 'round_phase': gsi_server.get_info('round', 'phase')}

        if truth_table['first_freezetime']:
            if game_state['map_phase'] == 'live' and game_state['round_phase'] == 'freezetime':
                truth_table['first_game_over'], truth_table['game_over'] = True, False
                truth_table['first_freezetime'] = False
                time_table['freezetime_started'] = time.time()
                scoreboard['CT'] = gsi_server.get_info('map', 'team_ct')['score']
                scoreboard['T'] = gsi_server.get_info('map', 'team_t')['score']
                scoreboard['last_round_info'] = gsi_server.get_info('map', 'round_wins')
                scoreboard['player'] = gsi_server.get_info('player')
                scoreboard['weapons'] = [inner for outer in scoreboard['player']['weapons'].values() for inner in outer.items()]
                scoreboard['c4'] = ' - Bomb Carrier!' if 'weapon_c4' in [i for _, i in scoreboard['weapons']] else ''
                scoreboard['total_score'] = scoreboard['CT'] + scoreboard['T']
                try:
                    scoreboard['opposing_team'] = 'T' if scoreboard['team'] == 'CT' else 'CT'
                except KeyError:
                    scoreboard['team'] = scoreboard['player']['team']
                    scoreboard['opposing_team'] = 'T' if scoreboard['team'] == 'CT' else 'CT'
                try:
                    scoreboard['last_round_key'] = list(scoreboard['last_round_info'].keys())[-1]
                    scoreboard['last_round_info'] = scoreboard['last_round_info'][scoreboard['last_round_key']].split('_')[0].upper()
                    scoreboard['last_round_info'] = ' - You ({}) won the last round'.format(scoreboard['team']) if scoreboard['team'] == scoreboard['last_round_info'] else ' - The Enemy ({}) won the last round'.format(
                        scoreboard['opposing_team'])
                except AttributeError:
                    scoreboard['last_round_info'] = ' - You ({}), no info on the last round'.format(scoreboard['team'])

                scoreboard['team'] = scoreboard['player']['team']
                scoreboard['opposing_team'] = 'T' if scoreboard['team'] == 'CT' else 'CT'

                if scoreboard['total_score'] == 14:
                    scoreboard['extra_round_info'] = ' - Last round of first half!'
                elif scoreboard['CT'] == 15 or scoreboard['T'] == 15:
                    scoreboard['extra_round_info'] = ' - Match Point'
                else:
                    scoreboard['extra_round_info'] = ''

                write('Freeze Time' + scoreboard['last_round_info'] + ' - {:02d}:{:02d}'.format(scoreboard[scoreboard['team']], scoreboard[scoreboard['opposing_team']]) + scoreboard['extra_round_info'] + scoreboard[
                    'c4'], overwrite='7')
                if win32gui.GetWindowPlacement(hwnd)[1] == 2:
                    playsound('sounds/ready_up.wav', block=True)
                if 'Last round' in scoreboard['extra_round_info']:
                    playsound('sounds/ding.wav', block=True)

        elif game_state['map_phase'] == 'live' and game_state['round_phase'] != 'freezetime':
            truth_table['first_freezetime'] = True
            truth_table['c4_round_first'] = True
            if time.time() - time_table['freezetime_started'] >= 20 and win32gui.GetWindowPlacement(hwnd)[1] == 2:
                playsound('sounds/ready_up.wav', block=False)

        if game_state['round_phase'] == 'freezetime' and truth_table['c4_round_first']:
            scoreboard['c_weapons'] = [inner for outer in gsi_server.get_info('player', 'weapons').values() for inner in outer.items()]
            scoreboard['has_c4'] = True if 'weapon_c4' in [i for _, i in scoreboard['c_weapons']] else False
            if scoreboard['has_c4']:
                playsound('sounds/ding.wav', block=False)
                truth_table['c4_round_first'] = False

        if truth_table['still_in_warmup']:
            if game_state['map_phase'] != 'warmup':
                truth_table['still_in_warmup'] = False
                write('Warmup is over! Team: {}, Map: {}'.format(gsi_server.get_info('player', 'team'), gsi_server.get_info('map', 'name')), push=pushbullet_dict['urgency'] + 2, push_now=True, overwrite='7')
                write('Took {} since the match started.'.format(timedelta(time_table['warmup_started'])), add_time=False)
                time_table['match_started'] = time.time()
                time_table['freezetime_started'] = time.time()
                if win32gui.GetWindowPlacement(hwnd)[1] == 2:
                    playsound('sounds/ready_up_warmup.wav', block=False)

        if game_state['map_phase'] in ['live', 'warmup'] and not truth_table['game_over'] and not truth_table['disconnected_form_last']:
            csgo_window_status['in_game'] = win32gui.GetWindowPlacement(hwnd)[1]
            afk_dict['still_afk'].append(csgo_window_status['in_game'] == 2)
            afk_dict['still_afk'] = [all(afk_dict['still_afk'])]
            if not afk_dict['still_afk'][0]:
                afk_dict['still_afk'] = []
                afk_dict['time'] = time.time()
            if time.time() - afk_dict['time'] >= 180:
                while True:
                    afk_dict['player_info'] = gsi_server.get_info('player')
                    afk_dict['round_phase'] = gsi_server.get_info('round', 'phase')
                    if afk_dict['round_phase'] is None:
                        afk_dict['round_phase'] = 'warmup'
                    if afk_dict['player_info']['steamid'] == accounts[current_account]['steam_id'] and afk_dict['player_info']['state']['health'] > 0 and afk_dict['round_phase'] != 'freezetime':
                        write('Ran Anti-Afk Script.', overwrite='10')
                        anti_afk(hwnd)
                        break
                    if win32gui.GetWindowPlacement(hwnd)[1] != 2:
                        break
                afk_dict['still_afk'] = []
                afk_dict['time'] = time.time()

            if csgo_window_status['in_game'] != 2:
                afk_dict['start_time'] = time.time()
            elif game_state['map_phase'] == 'live':
                afk_dict['seconds_afk'] += int(time.time() - afk_dict['start_time'])
                afk_dict['start_time'] = time.time()

        if game_state['map_phase'] == 'gameover':
            truth_table['game_over'] = True

        if truth_table['game_over'] and truth_table['first_game_over']:
            if gsi_server.get_info('map', 'mode') == 'competitive' and game_state['map_phase'] == 'gameover' and not truth_table['test_for_warmup'] and not truth_table['still_in_warmup']:
                write('The match is over!')
                write('Match duration: {}'.format(timedelta(time_table['match_started'])), add_time=False)
                write('Search-time:    {}'.format(timedelta(seconds=time_table['match_accepted'] - time_table['search_started'])), add_time=False)
                write('Time AFK:       {}, {:.1%} of match duration.'.format(timedelta(seconds=afk_dict['seconds_afk']), afk_dict['seconds_afk'] / (time.time() - time_table['match_started'])), add_time=False)
                if truth_table['monitoring_since_start']:
                    with open(path_vars['appdata_path'] + 'game_time_' + accounts[current_account]['steam_id'] + '.txt', 'a') as game_time:
                        game_time.write(str(int(time.time() - time_table['match_started'])) + ', ' + str(int(time_table['match_started'] - time_table['search_started'])) + '\n')

                average_match_time = getAvgMatchTime(accounts[current_account]['steam_id'])
                this_game_time = (time.time() - time_table['match_started'], time_table['match_accepted'] - time_table['search_started'])
                game_time_output_strs = (('The match was {} longer than the average match with {}', 'The match was {} shorter than the average match with {}'),
                                         ('The search-time was {} longer than the average search-time with {}', 'The search-time was {} shorter than the average search-time with {}'),
                                         'Time in competitive matchmaking: {}', 'Time in the searching queue: {}')
                for i, val in enumerate(average_match_time):
                    if isinstance(val, int):
                        avg_time_difference = this_game_time[i] - val
                        if avg_time_difference >= 0:
                            write(game_time_output_strs[i][0].format(timedelta(seconds=avg_time_difference), timedelta(seconds=val)), add_time=False)
                        else:
                            write(game_time_output_strs[i][1].format(timedelta(seconds=avg_time_difference), timedelta(seconds=val)), add_time=False)
                    elif isinstance(val, str):
                        write(game_time_output_strs[i].format(val), add_time=False)

                if game_state['map_phase'] == 'gameover':
                    time.sleep(5)
                    new_sharecodes = getNewCSGOSharecodes(getOldSharecodes(-1)[0])
                    write(new_sharecodes)
                    try:
                        for new_code in new_sharecodes:
                            retryer.append(new_code) if new_code['sharecode'] not in [old_code['sharecode'] for old_code in retryer] else retryer
                        retryer = UpdateCSGOstats(retryer, get_all_games=True)
                    except TypeError:
                        write('ERROR IN GETTING NEW MATCH CODE! TRY PRESSING "F6" to add it manually')

            truth_table['game_over'] = False
            truth_table['first_game_over'] = False
            truth_table['monitoring_since_start'] = False
            time_table['match_started'], time_table['match_accepted'] = time.time(), time.time()
            afk_dict['seconds_afk'], afk_dict['time'] = 0, time.time()

    if truth_table['testing']:
        # test_time = time.time()
        pass
        # write(gsi_server.get_info('player', 'state'), overwrite='state')
        # print('Took: {}'.format(str(datetime.timedelta(milliseconds=int(time.time()*1000 - test_time*1000))))

    if truth_table['test_for_warmup']:

        time_table['warmup_started'] = time.time()
        while True:
            if time.time() - time_table['warmup_started'] > 1:
                time_table['warmup_started'] = time.time()
                if gsi_server.get_info('map', 'phase') == 'warmup':
                    write('Warmup detected', overwrite='12')
                    if gsi_server.get_info('player', 'team') is not None:
                        time.sleep(2)
                        write('You will play as {} in the first half on {}.'.format(gsi_server.get_info('player', 'team'), gsi_server.get_info('map', 'name')), add_time=True, overwrite='12')
                        truth_table['still_in_warmup'] = True
                        truth_table['players_still_connecting'] = True
                        time_table['warmup_started'] = time.time()
                        truth_table['test_for_warmup'] = False
                        break

if console_window['isatty']:
    if overwrite_dict['end'] != '\n':
        print('')
exit('ENDED BY USER')
