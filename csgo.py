import configparser
import operator
import os
import re
from shutil import copyfile
import sys
import time
import webbrowser
import winreg
from datetime import datetime, timedelta
from typing import List

import pushbullet
import pyperclip
import pytesseract
import requests
import win32api
import win32con
import win32gui
from GSI import server
from PIL import ImageGrab, Image
from playsound import playsound


def Avg(lst: list):
    if not lst:
        return None
    return sum(lst) / len(lst)


# noinspection PyShadowingNames,PyUnusedLocal
def enum_cb(hwnd, results):
    winlist.append((hwnd, win32gui.GetWindowText(hwnd)))


def mute_csgo(lvl: int):
    os.system(path_vars['mute_csgo_path'] + str(lvl))


# noinspection PyShadowingNames
def write(message, add_time: bool = True, push: int = 0, push_now: bool = False, output: bool = True, overwrite: str = '0'):  # last overwrite key used: 11
    if output:
        message = str(message)
        if add_time:
            message = datetime.now().strftime('%H:%M:%S') + ': ' + message
        global last_printed_line
        splits = last_printed_line.split(b'**')
        last_key = splits[0]
        last_string = splits[1].strip(b'\n\r')
        last_end = splits[-1]
        if overwrite != '0':
            ending = console_window['suffix']
            if last_key == overwrite.encode():
                if console_window['isatty']:
                    print('\t' * int(len(last_string.decode()) / 4 + 1), end=ending)
                message = console_window['prefix'] + message
            else:
                if last_end != b'\n':
                    message = '\n' + message
        else:
            ending = '\n'
            if last_end != b'\n':
                message = '\n' + message

        last_printed_line = (overwrite + '**' + message + '**' + ending).encode()
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
    time.sleep(0.01)
    win32gui.ShowWindow(window_id, 2)
    click(current_cursor_position)
    time.sleep(0.01)
    win32api.SetCursorPos(current_cursor_position)
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
    profiles = requests.get('http://api.steampowered.com/ISteamUser/GetPlayerSummaries/v0002/?key=' + cfg['steam_api_key'] + '&steamids=' + steam_ids).json()['response']['players']
    name_list = [online_data['personaname'] for local_acc in accounts for online_data in profiles if online_data['steamid'] == local_acc['steam_id']]
    for num, val in enumerate(accounts):
        val['name'] = name_list[num]


# noinspection PyShadowingNames
def getCsgoPath():
    steam_reg_key = winreg.OpenKey(winreg.HKEY_LOCAL_MACHINE, 'SOFTWARE\WOW6432Node\Valve\Steam')
    steam_path = winreg.QueryValueEx(steam_reg_key, 'InstallPath')[0]
    libraries = [steam_path + '\\steamapps']
    with open(steam_path + '\\steamapps\\libraryfolders.vdf', 'r') as library_file:
        library_data = library_file.readlines()
        compare_str = re.compile('\\t"\d*"\\t\\t"')
        libraries.extend([re.sub(compare_str, '', i.rstrip('"\n')) for i in library_data if bool(re.match(compare_str, i))])

    csgo_path = [i for i in libraries if os.path.exists(i + '\\appmanifest_730.acf')][0] + '\\common\\Counter-Strike Global Offensive\\csgo\\'
    if not csgo_path.replace('\\common\\Counter-Strike Global Offensive\\csgo\\', ''):
        write('DID NOT FIND CSGO PATH', add_time=False)
        global error_level
        error_level += 1
    global path_vars
    path_vars['csgo_path'] = csgo_path
    path_vars['steam_path'] = steam_path


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
                write('Added %s to "autoexec.cfg" file in %s' % (autoexec_str, userdata_path), add_time=False)
                write('RESTART Counter-Strike for the script to work', add_time=False)
                autoexec.write('\n' + autoexec_str + '\n')
    if os.path.exists(path_vars['csgo_path'] + '\\cfg\\autoexec.cfg'):
        write('YOU HAVE TO DELETE THE "autoexec.cfg" in %s WITH AND MERGE IT WITH THE ONE IN %s' % (path_vars['csgo_path'] + '\\cfg', userdata_path), add_time=False)
        write('THE SCRIPT WONT WORK UNTIL THERE IS NO "autoexec.cfg" in %s' % path_vars['csgo_path'] + '\\cfg', add_time=False)
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
    return int(Avg(match_time)), int(Avg(search_time)), str(timedelta(seconds=sum(match_time))), str(timedelta(seconds=sum(search_time)))


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
    sharecodes = []
    next_code = game_id
    last_game = open(path_vars['appdata_path'] + 'last_game_' + accounts[current_account]['steam_id'] + '.txt', 'a')
    while next_code != 'n/a':
        steam_url = 'https://api.steampowered.com/ICSGOPlayers_730/GetNextMatchSharingCode/v1?key=' + cfg['steam_api_key'] + '&steamid=' + accounts[current_account]['steam_id'] + '&steamidkey=' + accounts[current_account][
            'auth_code'] + '&knowncode=' + game_id
        try:
            next_code = (requests.get(steam_url, timeout=2).json()['result']['nextcode'])
        except (KeyError, requests.exceptions.ConnectionError, requests.exceptions.Timeout):
            write('WRONG Match Token, Authentication Code or Steam ID!')
            if sharecodes:
                return sharecodes
            else:
                return [{'sharecode': game_id, 'queue_pos': None}]

        if next_code:
            if next_code != 'n/a':
                sharecodes.append(next_code)
                game_id = next_code
                last_game.write(next_code + '\n')
    last_game.close()
    return [{'sharecode': code, 'queue_pos': None} for code in sharecodes]


# noinspection PyShadowingNames
def UpdateCSGOstats(repeater=None, get_all_games=False):
    all_games, completed_games, not_completed_games, = [], [], []
    if repeater is None:
        repeater = []

    if repeater:
        if get_all_games:
            sharecodes = [getOldSharecodes(from_x=code['sharecode']) for code in repeater]
            sharecodes = max(sharecodes, key=len)
        else:
            sharecodes = [code['sharecode'] for code in repeater]
        all_games = [requests.post('https://csgostats.gg/match/upload/ajax', data={'sharecode': sharecode, 'index': '0'}).json() for sharecode in sharecodes]
    else:
        num = -1
        sharecode = getOldSharecodes(num)[0]
        while True:
            response = requests.post('https://csgostats.gg/match/upload/ajax', data={'sharecode': sharecode, 'index': '0'})
            all_games.append(response.json())
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

    global queue_difference, time_table
    if queued_games:
        temp_string = ''
        for i, val in enumerate(queued_games):
            temp_string += '#' + str(i + 1) + ': in Queue #' + str(val['queue_pos']) + ' - '

        if repeater:
            current_queue_difference = Avg([last_game['queue_pos'] - game['queue_pos'] for game in queued_games for last_game in repeater if last_game['sharecode'] == game['sharecode'] and last_game['queue_pos'] is not None])
            if current_queue_difference:
                if current_queue_difference >= 0.0:
                    queue_difference.append(current_queue_difference / ((time.time() - time_table['time_since_retry']) / 60))
                    queue_difference = queue_difference[-10:]
                    matches_per_min = round(Avg(queue_difference), 1)
                    if matches_per_min != 0.0:
                        time_till_done = str(timedelta(seconds=int((queued_games[0]['queue_pos'] / matches_per_min) * 60)))
                    else:
                        time_till_done = '∞:∞:∞'
                    temp_string += str(matches_per_min) + ' matches/min - #1 done in ' + time_till_done
        temp_string = temp_string.rstrip(' - ')
        write(temp_string, add_time=False, overwrite='4')

    time_table['time_since_retry'] = time.time()
    repeater = [game for game in queued_games if game['queue_pos'] < cfg['max_queue_position']]
    repeater.extend([game for game in corrupt_games])

    if corrupt_games:
        write('An error occurred in %s game[s].' % len(corrupt_games), overwrite='5')

    if completed_games:
        global pushbullet_dict
        for i in completed_games:
            sharecode = i['data']['sharecode']
            game_url = i['data']['url']
            info = ' '.join(i['data']['msg'].replace('-', '').replace('<br />', '. ').split('<')[0].rstrip(' ').split())
            write('Sharecode: %s' % sharecode, add_time=False, push=pushbullet_dict['urgency'])
            write('URL: %s' % game_url, add_time=False, push=pushbullet_dict['urgency'])
            write('Status: %s.' % info, add_time=True, push=pushbullet_dict['urgency'])
            pyperclip.copy(game_url)
        write(None, add_time=False, push=pushbullet_dict['urgency'], push_now=True, output=False)
    return repeater


# noinspection PyShadowingNames,PyUnusedLocal
def Image_to_Text(image: Image, size: tuple, white_threshold: int, arg: str = ''):
    image_data = image.getdata()
    image_text = ''

    black_white_map = [all(color_value >= white_threshold for color_value in single_pixel) for single_pixel in image_data]
    pixel_map = list(map(lambda x: (0, 0, 0) if x else (255, 255, 255), black_white_map))

    temp_image = Image.new('RGB', (size[0], size[1]))
    temp_image.putdata(pixel_map)
    try:
        image_text = pytesseract.image_to_string(temp_image, timeout=0.3, config=arg)
    except RuntimeError:
        pass
    if image_text:
        image_text = ' '.join(image_text.replace(': ', ':').split())
        return image_text
    else:
        return ''


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
last_printed_line = b'0**\n'
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
           'end_script': int(config.get('HotKeys', 'End Script'), 16), 'stop_warmup_ocr': config.get('HotKeys', 'Stop Warmup OCR'),
           'screenshot_interval': float(config.get('Screenshot', 'Interval')), 'debug_path': config.get('Screenshot', 'Debug Path'), 'steam_api_key': config.get('csgostats.gg', 'API Key'),
           'max_queue_position': config.getint('csgostats.gg', 'Auto-Retrying for queue position below'), 'log_color': config.get('Screenshot', 'Log Color').lower(),
           'auto_retry_interval': config.getint('csgostats.gg', 'Auto-Retrying-Interval'), 'pushbullet_device_name': config.get('Pushbullet', 'Device Name'), 'pushbullet_api_key': config.get('Pushbullet', 'API Key'),
           'tesseract_path': config.get('Warmup', 'Tesseract Path'), 'warmup_test_interval': config.getint('Warmup', 'Test Interval'), 'warmup_push_interval': config.get('Warmup', 'Push Interval'),
           'warmup_no_text_limit': config.getint('Warmup', 'No Text Limit'), 'forbidden_programs': config.get('Screenshot', 'Forbidden Programs')}
except (configparser.NoOptionError, configparser.NoSectionError, ValueError):
    write('ERROR IN CONFIG')
    cfg = {'ERROR': None}
    exit('CHECK FOR NEW CONFIG')

# ACCOUNT HANDLING, GETTING ACCOUNT NAME, GETTING CSGO PATH, CHECKING AUTOEXEC
accounts, current_account = [], 0
path_vars = {'steam_path': '', 'csgo_path': '', 'mute_csgo_path': '"' + os.getcwd() + '\\sounds\\nircmdc.exe" muteappvolume csgo.exe '}
getAccountsFromCfg()
getCsgoPath()
CheckUserDataAutoExec(accounts[current_account]['steam_id_3'])

if error_level:
    exit('an error occurred')

with open(path_vars['csgo_path'] + 'console_log.log', 'w') as log:
    log.write('')
with open(cfg['debug_path'] + '\\console.log', 'w') as debug_log:
    debug_log.write('')

if not os.path.exists(path_vars['csgo_path'] + 'cfg\\gamestate_integration_GSI.cfg'):
    copyfile(os.path.join(os.getcwd(), 'GSI') + '\\gamestate_integration_GSI.cfg', path_vars['csgo_path'] + 'cfg\\gamestate_integration_GSI.cfg')
    write('Added GSI CONFIG to cfg folder. Counter-Strike needs to be restarted if running!')
gsi_server = server.GSIServer(('127.0.0.1', 3000), "IDONTUSEATOKEN")

# INITIALIZATION FOR getScreenShot
screen_size = (win32api.GetSystemMetrics(0), win32api.GetSystemMetrics(1))
hwnd, hwnd_old = 0, 0
csgo_window_status = {'server_found': 2, 'new_tab': 2}
toplist, csgo = [], []

# BOOLEAN, TIME INITIALIZATION
truth_table = {'test_for_accept_button': False, 'test_for_warmup': False, 'test_for_success': False, 'first_ocr': True, 'testing': False, 'first_push': True, 'still_in_warmup': False, 'test_for_server': False, 'first_freezetime': True,
               'gsi_server_running': False, 'game_over': False, 'csgo_re-started': False, 'monitoring_since_start': False, 'players_still_connecting': False}
time_table = {'screenshot_time': time.time(), 'time_since_retry': time.time(), 'warmup_test_timer': time.time(), 'time_searching': time.time(), 'searching_cc': time.time(), 'timed_execution_time': time.time(), 'join_warmup_time': 0.0,
              'time_in_warmup': 0, 'search_time_seconds': 0}
matchmaking_blank = {'msg': [], 'update': [], 'players_accepted': [], 'lobby_data': [], 'server_found': False, 'server_ready': False}
matchmaking = matchmaking_blank
anti_afk_dict = {'time': time.time(), 'still_afk': []}
join_dict = {'lobby_data': [], 'unwanted_indices': [], 't_full': False, 'ct_full': False}

# csgostats.gg VAR
retryer = []
queue_difference = []

# WARMUP DETECTION SETUP
pytesseract.pytesseract.tesseract_cmd = cfg['tesseract_path']
cfg['stop_warmup_ocr'] = [int(i, 16) for i in cfg['stop_warmup_ocr'].split('-')]
cfg['stop_warmup_ocr'][1] += 1
no_text_found = 0

# PUSHBULLET VAR
pushbullet_dict = {'note': '', 'urgency': 0, 'device': 0, 'times': [int(i) for i in cfg['warmup_push_interval'].split(',')].sort(reverse=True), 'counter': 0,
                   'push_info': ('not active', 'only if accepted', 'all game status related information', 'all information (game status/csgostats.gg information)')}

mute_csgo(0)
path_vars['appdata_path'] = os.getenv('APPDATA') + '\\CSGO AUTO ACCEPT\\'

write('READY')


while True:
    if win32api.GetAsyncKeyState(cfg['activate_script']) & 1:  # F9 (ACTIVATE / DEACTIVATE SCRIPT)
        truth_table['test_for_server'] = not truth_table['test_for_server']
        write('Looking for game: %s' % truth_table['test_for_server'], overwrite='1')
        if truth_table['test_for_server']:
            playsound('sounds/activated.wav', block=False)
            time_table['time_searching'] = time.time()
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
            write('Pushing: %s' % pushbullet_dict['push_info'][pushbullet_dict['urgency']], overwrite='2')

    if win32api.GetAsyncKeyState(cfg['info_newest_match']) & 1:  # F7 Key (UPLOAD NEWEST MATCH)
        write('Uploading / Getting status on newest match')
        queue_difference = []
        new_sharecodes = getNewCSGOSharecodes(getOldSharecodes(-1)[0])
        for new_code in new_sharecodes:
            retryer.append(new_code) if new_code['sharecode'] not in [old_code['sharecode'] for old_code in retryer] else retryer
        retryer = UpdateCSGOstats(retryer, get_all_games=True)

    if win32api.GetAsyncKeyState(cfg['open_live_tab']) & 1:  # F13 Key (OPEN WEB BROWSER ON LIVE GAME TAB)
        csgo_window_status['new_tab'] = win32gui.GetWindowPlacement(hwnd)[1]
        if csgo_window_status['new_tab'] != 2:
            win32gui.ShowWindow(hwnd, win32con.SW_MAXIMIZE)
        webbrowser.open_new_tab('https://csgostats.gg/player/' + accounts[current_account]['steam_id'] + '#/live')
        write('new tab opened', add_time=False)
        if csgo_window_status['new_tab'] != 2:
            time.sleep(0.5)
            win32gui.ShowWindow(hwnd, win32con.SW_MAXIMIZE)

    if win32api.GetAsyncKeyState(cfg['switch_accounts']) & 1:  # F15 (SWITCH ACCOUNTS)
        current_account += 1
        if current_account > len(accounts) - 1:
            current_account = 0
        CheckUserDataAutoExec(accounts[current_account]['steam_id_3'])
        write('current account is: %s' % accounts[current_account]['name'], add_time=False, overwrite='3')

    if win32api.GetAsyncKeyState(cfg['mute_csgo_toggle']) & 1:  # F6 (TOGGLE MUTE CSGO)
        write("MUTE TOGGLED", add_time=False)
        mute_csgo(2)

    if win32api.GetAsyncKeyState(cfg['end_script']) & 1:  # POS1 (END SCRIPT)
        write('Exiting Script')
        break

    if retryer:
        if time.time() - time_table['time_since_retry'] > cfg['auto_retry_interval']:
            retryer = UpdateCSGOstats(retryer)
    winlist = []
    win32gui.EnumWindows(enum_cb, toplist)
    csgo = [(hwnd, title) for hwnd, title in winlist if 'counter-strike: global offensive' == title.lower()]

    if not csgo:
        continue
    hwnd = csgo[0][0]

    if hwnd_old != hwnd:
        if hwnd_old:
            truth_table['test_for_server'] = False
        truth_table['csgo_re-started'] = True
        hwnd_old = hwnd
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
        write('TestCode active: %s' % str(truth_table['testing']), add_time=False, overwrite='testcode')

    if time.time() - time_table['searching_cc'] > 0.2:
        time_table['searching_cc'] = time.time()
        with open(path_vars['csgo_path'] + 'console_log.log', 'rb+') as log:
            log_lines = log.readlines()
            console_lines = [line.decode('utf-8', 'ignore').encode('utf-8').rstrip(b'\n\r').decode() for line in log_lines]
            log.seek(0)
            log.truncate()
        with open(cfg['debug_path'] + '\\console.log', 'ab') as debug_log:
            [debug_log.write(i) for i in log_lines]
        matchmaking['msg'] = str_in_list(['Matchmaking message: '], console_lines, replace=True)
        matchmaking['update'] = str_in_list(['Matchmaking update: '], console_lines, replace=True)
        matchmaking['players_accepted'] = str_in_list(['Server reservation2 is awaiting '], console_lines, replace=True)
        matchmaking['lobby_data'] = str_in_list(["LobbySetData: 'members:num"], console_lines, replace=True)
        matchmaking['server_found'] = str_in_list(['Matchmaking reservation confirmed: '], console_lines)
        matchmaking['server_ready'] = str_in_list(['ready-up!'], console_lines)
    else:
        matchmaking = matchmaking_blank

    if matchmaking['update']:
        if matchmaking['update'][-1] == '1':
            if not truth_table['test_for_server']:
                truth_table['test_for_server'] = True
                write('Looking for game: %s' % truth_table['test_for_server'], overwrite='1')
                time_table['time_searching'] = time.time()
                playsound('sounds/activated.wav', block=False)
            mute_csgo(1)
        elif matchmaking['update'][-1] == '0' and truth_table['test_for_server']:
            mute_csgo(0)

    if truth_table['test_for_server']:
        if matchmaking['server_found']:
            playsound('sounds/server_found.wav', block=False)
            truth_table['test_for_success'] = True
        if matchmaking['server_ready']:
            write('Server found, starting to look for accept button')
            truth_table['test_for_accept_button'] = True
            csgo_window_status['server_found'] = win32gui.GetWindowPlacement(hwnd)[1]
            win32gui.ShowWindow(hwnd, win32con.SW_MAXIMIZE)
        if truth_table['csgo_re-started']:
            truth_table['csgo_re-started'] = False
            if gsi_server.get_info('map', 'name') is None and gsi_server.get_info('player', 'activity') == 'menu':
                current_steamid = gsi_server.get_info('player', 'steamid')
                try:
                    current_account = [i for i, val in enumerate(accounts) if current_steamid == val['steam_id']][0]
                    CheckUserDataAutoExec(accounts[current_account]['steam_id_3'])
                except IndexError:
                    write('\tAccount is not in the config.ini!\nScript will not work properly!', overwrite='9')
                    playsound('sounds/fail.wav', block=False)
                    exit('Update config.ini')
            write('\tCurrent account is: %s' % accounts[current_account]['name'], add_time=False, overwrite='9')

    if truth_table['test_for_accept_button']:
        img = getScreenShot(hwnd, (1265, 760, 1295, 785))
        accept_avg = color_average(img, [(76, 175, 80), (90, 203, 94)])
        if relate_list(accept_avg, (2, 2, 2)):
            write('Trying to Accept', push=pushbullet_dict['urgency'] + 1)
            truth_table['test_for_accept_button'] = False

            with open(cfg['debug_path'] + '\\console.log', 'ab') as debug_log:
                debug_log.write(b'\naccepted\n\n ')
            current_cursor_position = win32api.GetCursorPos()
            for _ in range(5):
                click(int(screen_size[0] / 2), int(screen_size[1] / 1.78))
                pass
            if csgo_window_status['server_found'] == 2:  # was minimized when a server was found
                time.sleep(0.075)
                win32gui.ShowWindow(hwnd, 2)
                time.sleep(0.025)
                click(current_cursor_position)
            else:
                win32api.SetCursorPos(current_cursor_position)

            write('Trying to catch a loading map')
            playsound('sounds/accept_found.wav', block=False)
            time_table['screenshot_time'] = time.time()

    if truth_table['test_for_accept_button'] or truth_table['test_for_success']:
        if str_in_list(['Match confirmed'], matchmaking['msg']):
            # write('\tTook %s since pressing accept.' % str(timedelta(seconds=int(time.time() - time_table['screenshot_time']))), add_time=False, push=pushbullet_dict['urgency'] + 1)
            time_table['search_time_seconds'] = int(time.time() - time_table['time_searching'])
            write('\tAll Players accepted', add_time=False, overwrite='11')
            write('\tTook %s since trying to find a game.' % str(timedelta(seconds=time_table['search_time_seconds'])), add_time=False, push=pushbullet_dict['urgency'] + 1)
            write('Game should have started', push=pushbullet_dict['urgency'] + 2, push_now=True)
            truth_table['test_for_warmup'] = True
            truth_table['warmup_started'] = False
            truth_table['first_freezetime'] = False
            truth_table['test_for_server'] = False
            truth_table['test_for_accept_button'] = False
            truth_table['test_for_success'] = False
            truth_table['monitoring_since_start'] = True
            mute_csgo(0)
            playsound('sounds/done_testing.wav', block=False)
            time_table['time_searching'] = time.time()
            anti_afk_dict['time'] = time.time()
            time_table['time_in_warmup'] = 0

        if str_in_list(['Other players failed to connect', 'Failed to ready up'], matchmaking['msg']):
            write('Game doesnt seem to have started. Continuing to search for a Server!', push=pushbullet_dict['urgency'] + 1, push_now=True)
            playsound('sounds/back_to_testing.wav', block=False)
            mute_csgo(1)
            truth_table['test_for_server'] = True
            truth_table['test_for_accept_button'] = False
            truth_table['test_for_success'] = False

        if matchmaking['players_accepted']:
            for i in matchmaking['players_accepted']:
                i = i.split('/')
                players_accepted = str(int(i[1]) - int(i[0]))
                write('\t%s Players of %s already accepted.' % (players_accepted, i[1]), add_time=False, overwrite='11')

    if truth_table['players_still_connecting']:
        if matchmaking['lobby_data']:
            join_dict['lobby_data'] = [i.rstrip("'\n").split("' = '") for i in matchmaking['lobby_data']]
            join_dict['unwanted_indices'] = [list(range(i, i + 3)) for i, val in enumerate(join_dict['lobby_data']) if val[0] == 'Machines']
            join_dict['unwanted_indices'] = [inner for outer in join_dict['unwanted_indices'] for inner in outer]
            for i in sorted(join_dict['unwanted_indices'], reverse=True):
                del join_dict['lobby_data'][i]
            join_dict['t_full'], join_dict['ct_full'] = False, False
            for i in join_dict['lobby_data']:
                if i[0] == 'Players':
                    write('\t%s players joined' % i[1], add_time=False, overwrite='11')
                if i[0] == 'TSlotsFree' and i[1] == '0':
                    join_dict['t_full'] = True
                if i[0] == 'CTSlotsFree' and i[1] == '0':
                    join_dict['ct_full'] = True
                if join_dict['t_full'] and join_dict['ct_full']:
                    write('Server Full, All Players connected', overwrite='11')
                    playsound('sounds/minute_warning.wav', block=True)
                    join_dict['t_full'], join_dict['ct_full'] = False, False
                    truth_table['players_still_connecting'] = False

    if time.time() - time_table['timed_execution_time'] > 2:
        time_table['timed_execution_time'] = time.time()
        game_state = {'map_phase': gsi_server.get_info('map', 'phase'), 'round_phase': gsi_server.get_info('round', 'phase')}

        if truth_table['first_freezetime']:
            if game_state['map_phase'] == 'live' and game_state['round_phase'] == 'freezetime':
                truth_table['first_freezetime'] = False
                truth_table['game_over'] = False
                write('Freeze Time starting.', overwrite='7')
                if win32gui.GetWindowPlacement(hwnd)[1] == 2:
                    playsound('sounds/ready_up.wav', block=False)
        elif game_state['map_phase'] == 'live' and game_state['round_phase'] != 'freezetime':
            truth_table['first_freezetime'] = True

        if truth_table['still_in_warmup']:
            if game_state['map_phase'] != 'warmup':
                truth_table['still_in_warmup'] = False
                write('WARMUP is over!', push=pushbullet_dict['urgency'] + 2, push_now=True, overwrite='7')
                write('\tTook %s since the Game started.' % str(timedelta(seconds=int(time.time() - time_table['time_searching']))), add_time=False)
                time_table['time_searching'] = time.time()

                if win32gui.GetWindowPlacement(hwnd)[1] == 2:
                    playsound('sounds/ready_up_warmup.wav', block=False)

        if game_state['map_phase'] in ['live', 'warmup']:
            anti_afk_dict['still_afk'].append(win32gui.GetWindowPlacement(hwnd)[1] == 2)
            anti_afk_dict['still_afk'] = [all(anti_afk_dict['still_afk'])]
            if not anti_afk_dict['still_afk'][0]:
                anti_afk_dict['still_afk'] = []
                anti_afk_dict['time'] = time.time()
            if time.time() - anti_afk_dict['time'] >= 180:
                write('Ran Anti-Afk Script.', overwrite='10')
                anti_afk_dict['still_afk'] = []
                anti_afk_dict['time'] = time.time()
                anti_afk(hwnd)

        if not truth_table['game_over'] and game_state['map_phase'] == 'gameover':
            game_took_seconds = int(time.time() - time_table['time_searching'])
            write('The Game is over!')
            write('\tMatch duration: %s.' % str(timedelta(seconds=game_took_seconds)), add_time=False)
            write('\tSearch-time:    %s.' % str(timedelta(seconds=time_table['search_time_seconds'])), add_time=False)
            if gsi_server.get_info('map', 'mode') == 'competitive':
                if truth_table['monitoring_since_start']:
                    with open(path_vars['appdata_path'] + 'game_time_' + accounts[current_account]['steam_id'] + '.txt', 'a') as game_time:
                        game_time.write(str(game_took_seconds) + ', ' + str(time_table['search_time_seconds']) + '\n')
                average_match_time = getAvgMatchTime(accounts[current_account]['steam_id'])
                this_game_time = (game_took_seconds, time_table['search_time_seconds'])
                game_time_output_strs = (('\tThe games was %s longer than the average game with %s.', '\tThe games was %s shorter than the average game with %s.'),
                                         ('\tThe search-time was %s longer than the average search-time with %s.', '\tThe search-time was %s shorter than the average search-time with %s.'),
                                         '\tTime wasted in competitive matchmaking: %s.', '\tTime wasted in the searching queue: %s.')
                for i, val in enumerate(average_match_time):
                    if isinstance(val, int):
                        avg_time_difference = this_game_time[i] - val
                        if avg_time_difference >= 0:
                            write(game_time_output_strs[i][0] % (str(timedelta(seconds=abs(avg_time_difference))), str(timedelta(seconds=val))), add_time=False)
                        else:
                            write(game_time_output_strs[i][1] % (str(timedelta(seconds=abs(avg_time_difference))), str(timedelta(seconds=val))), add_time=False)
                    elif isinstance(val, str):
                        write(game_time_output_strs[i] % val, add_time=False)

                time.sleep(5)
                new_sharecodes = getNewCSGOSharecodes(getOldSharecodes(-1)[0])
                for new_code in new_sharecodes:
                    retryer.append(new_code) if new_code['sharecode'] not in [old_code['sharecode'] for old_code in retryer] else retryer
                retryer = UpdateCSGOstats(retryer, get_all_games=True)
            truth_table['game_over'] = True

    if truth_table['testing']:
        # test_time = time.time()
        pass
        # print('Took: %s ' % str(timedelta(milliseconds=int(time.time()*1000 - test_time*1000))))

    if truth_table['test_for_warmup']:
        for i in range(cfg['stop_warmup_ocr'][0], cfg['stop_warmup_ocr'][1]):
            win32api.GetAsyncKeyState(i) & 1

        time_table['until_warmup_start'] = time.time()
        if not truth_table['still_in_warmup']:
            while True:
                if time.time() - time_table['until_warmup_start'] > 1:
                    time_table['until_warmup_start'] = time.time()
                    if gsi_server.get_info('map', 'phase') == 'warmup':
                        write("Warmup detected")
                        truth_table['still_in_warmup'] = True
                        truth_table['players_still_connecting'] = True
                        break

        while True:
            keys = [(win32api.GetAsyncKeyState(i) & 1) for i in range(cfg['stop_warmup_ocr'][0], cfg['stop_warmup_ocr'][1])]
            if any(keys):
                write('Break from warmup-loop')
                no_text_found = 0
                truth_table['test_for_warmup'] = False
                truth_table['first_ocr'] = True
                truth_table['first_push'] = True
                time_table['timed_execution_time'] = time.time()
                break

            if pushbullet_dict['urgency'] <= 2:
                truth_table['test_for_warmup'] = False
                break

            if time.time() - time_table['warmup_test_timer'] >= cfg['warmup_test_interval']:
                time_table['warmup_test_timer'] = time.time()
                img = getScreenShot(hwnd, (1036, 425, 1525, 456))  # 'WAITING FOR PLAYERS X:XX'
                img_text = Image_to_Text(img, img.size, 225, arg='--psm 6')
                try:
                    time_left = list(map(int, re.findall(re.compile('\d+?:\d+'), img_text)[0].split(':')))
                    time_left = time_left[0] * 60 + time_left[1]
                    if truth_table['first_ocr']:
                        time_table['join_warmup_time'] = time_left
                        time_table['screenshot_time'] = time.time()
                        truth_table['first_ocr'] = False
                    time_left_data = timedelta(seconds=int(time.time() - time_table['screenshot_time'])), time.strftime('%H:%M:%S', time.gmtime(
                        abs((time_table['join_warmup_time'] - time_left) - (time.time() - time_table['screenshot_time'])))), img_text
                    write('Time since start: %s - Time Difference: %s - Time left: %s' % (time_left_data[0], time_left_data[1], time_left_data[2]), add_time=False, overwrite='1')
                    if no_text_found > 0:
                        no_text_found = 0

                    if time_left <= pushbullet_dict['times'][pushbullet_dict['counter']] and pushbullet_dict['counter'] >= len(pushbullet_dict['times']):
                        pushbullet_dict['counter'] += 1
                        write('Time since start: %s\nTime Difference: %s\nTime left: %s' % (time_left_data[0], time_left_data[1], time_left_data[2]), push=pushbullet_dict['urgency'] + 1, push_now=True, output=False)

                    if truth_table['first_push']:
                        if abs((time_table['join_warmup_time'] - time_left) - (time.time() - time_table['screenshot_time'])) >= 5:
                            truth_table['first_push'] = False
                            write('Match should start in ' + str(time_left) + ' seconds, All players have connected.', push=pushbullet_dict['urgency'] + 2, push_now=True)

                except IndexError:
                    no_text_found += 1

                if time.time() - time_table['time_searching'] - time_table['time_in_warmup'] >= 210:
                    time_table['time_in_warmup'] += 210
                    write('Ran Anit-Afk Script.')
                    anti_afk_dict['time'] = time.time()
                    anti_afk(hwnd)

                if gsi_server.get_info('map', 'phase') != 'warmup':
                    no_text_found = 0
                    truth_table['test_for_warmup'] = False
                    truth_table['first_ocr'] = True
                    truth_table['first_push'] = True
                    pushbullet_dict['counter'] = 0
                    truth_table['still_in_warmup'] = False
                    write('WARMUP is over!', push=pushbullet_dict['urgency'] + 2, push_now=True)
                    write('\tTook %s since the Game started.' % str(timedelta(seconds=int(time.time() - time_table['time_searching']))), add_time=False)
                    break

            if no_text_found >= cfg['warmup_no_text_limit']:
                no_text_found = 0
                truth_table['test_for_warmup'] = False
                truth_table['first_ocr'] = True
                truth_table['first_push'] = True
                pushbullet_dict['counter'] = 0
                write('Did not find any warmup text.', push=pushbullet_dict['urgency'] + 2, push_now=True)
                time_table['timed_execution_time'] = time.time()
                break

if console_window['isatty']:
    if last_printed_line.split(b'**')[-1] != b'\n':
        print('')
exit('ENDED BY USER')
