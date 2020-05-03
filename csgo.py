import configparser
import operator
import os
import re
import sys
import time
import webbrowser
import winreg
from datetime import datetime, timedelta

import pushbullet
import pyperclip
import pytesseract
import requests
import win32api
import win32con
import win32gui
from PIL import ImageGrab, Image
from playsound import playsound


def Avg(lst: list):
    if not lst:
        return 0
    return sum(lst) / len(lst)


# noinspection PyShadowingNames,PyUnusedLocal
def enum_cb(hwnd, results):
    winlist.append((hwnd, win32gui.GetWindowText(hwnd)))


def mute_csgo(lvl: int):
    os.system(mute_csgo_path + str(lvl))



# noinspection PyShadowingNames
def write(message, add_time: bool = True, push: int = 0, push_now: bool = False, output: bool = True, overwrite: str = '0'):
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
                    print(' ' * len(last_string.decode()), end=ending)
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
        global note
        if message:
            note = note + str(message.strip('\n\r')) + '\n'
        if push_now:
            device.push_note('CSGO AUTO ACCEPT', note)
            note = ''


# noinspection PyShadowingNames
def click(x: int, y: int):
    win32api.SetCursorPos((x, y))
    win32api.mouse_event(win32con.MOUSEEVENTF_LEFTDOWN, x, y, 0, 0)
    win32api.mouse_event(win32con.MOUSEEVENTF_LEFTUP, x, y, 0, 0)


# noinspection PyShadowingNames
def relate_list(l_org, compare_list, relate: operator = operator.le):
    if not l_org:
        return False
    truth_list = []
    for list_part in compare_list:
        partial_truth = []
        for i, val in enumerate(list_part):
            partial_truth.append(relate(l_org[i], val))
        truth_list.append(all(partial_truth))
        l_org = l_org[len(list_part):]
    return any(truth_list)


# noinspection PyShadowingNames
def color_average(image: Image, compare_list: list):
    average = []
    r, g, b = [], [], []
    data = image.getdata()
    for i in data:
        r.append(i[0])
        g.append(i[1])
        b.append(i[2])

    rgb = [Avg(r), Avg(g), Avg(b)] * len(compare_list)
    for part in compare_list:
        for i, val in enumerate(part):
            average.append(val - rgb[i])
    average = list(map(abs, average))
    return average


# noinspection PyShadowingNames
def getScreenShot(window_id: int, area: tuple = (0, 0, 0, 0)):
    area = list(area)
    win32gui.ShowWindow(window_id, win32con.SW_MAXIMIZE)
    scaled_area = [screen_width / 2560, screen_height / 1440]
    scaled_area = 2 * scaled_area
    for i, _ in enumerate(area[-2:], start=len(area) - 2):
        area[i] += 1
    for i, val in enumerate(area, start=0):
        scaled_area[i] = scaled_area[i] * val
    scaled_area = list(map(int, scaled_area))
    # time.sleep(0.001)
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
def getCsgoPath(steam_id_3: str):
    steam_reg_key = winreg.OpenKey(winreg.HKEY_LOCAL_MACHINE, 'SOFTWARE\WOW6432Node\Valve\Steam')
    steam_path = winreg.QueryValueEx(steam_reg_key, 'InstallPath')[0]
    libraries = [steam_path + '\\steamapps']
    with open(steam_path + '\\steamapps\\libraryfolders.vdf', 'r') as library_file:
        library_data = library_file.readlines()
        compare_str = re.compile('\\t"\d*"\\t\\t"')
        libraries.extend([re.sub(compare_str, "", i.rstrip('"\n')) for i in library_data if bool(re.match(compare_str, i))])

    csgo_path = [i for i in libraries if os.path.exists(i + '\\appmanifest_730.acf')][0] + '\\common\\Counter-Strike Global Offensive\\csgo\\'
    if not csgo_path:
        write('DID NOT FIND CSGO PATH', add_time=False)
        exit('LORD PLZ HELP')

    userdata_path = steam_path + '\\userdata\\' + steam_id_3 + '\\730\\local\\cfg\\'
    autoexec_strs = ['developer 1', 'con_logfile "console_log.log"', 'con_filter_enable "2"', 'con_filter_text_out "Player:"', 'con_filter_text "Damage"', 'log_color General ' + cfg['log_color']]
    with open(userdata_path + 'autoexec.cfg', 'a+') as autoexec:
        autoexec.seek(0)
        lines = autoexec.readlines()
        for autoexec_str in autoexec_strs:
            if not any(autoexec_str.lower() in line.rstrip('\n').lower() for line in lines):
                write('Added %s to "autoexec.cfg" file in %s' % (autoexec_str, userdata_path), add_time=False)
                write('RESTART Counter-Strike for the script to work', add_time=False)
                autoexec.write('\n' + autoexec_str + '\n')
    if os.path.exists(csgo_path + '\\cfg\\autoexec.cfg'):
        write('YOU HAVE TO DELETE THE "autoexec.cfg" in %s WITH AND MERGE IT WITH THE ONE IN %s' % (csgo_path + '\\cfg', userdata_path), add_time=False)
        write('THE SCRIPT WONT WORK UNTIL THERE IS NO "autoexec.cfg" in %s' % csgo_path + '\\cfg', add_time=False)
        exit()
    return csgo_path


# noinspection PyShadowingNames
def getOldSharecodes(last_x: int = -1, from_x: str = ''):
    if last_x >= 0:
        return []
    try:
        last_game = open(appdata_path+'last_game_' + accounts[current_account]['steam_id'] + '.txt', 'r')
        games = last_game.readlines()
        last_game.close()
    except FileNotFoundError:
        last_game = open(appdata_path+'last_game_' + accounts[current_account]['steam_id'] + '.txt', 'w')
        last_game.write(accounts[current_account]['match_token'] + '\n')
        games = [accounts[current_account]['match_token']]
        last_game.close()
    last_game = open(appdata_path+'last_game_' + accounts[current_account]['steam_id'] + '.txt', 'w')
    games = games[-200:]
    for i, val in enumerate(games):
        games[i] = 'CSGO' + val.strip('\n').split('CSGO')[1]
        last_game.write(games[i] + '\n')
    last_game.close()
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
    last_game = open(appdata_path+'last_game_' + accounts[current_account]['steam_id'] + '.txt', 'a')
    while next_code != 'n/a':
        steam_url = 'https://api.steampowered.com/ICSGOPlayers_730/GetNextMatchSharingCode/v1?key=' + cfg['steam_api_key'] + '&steamid=' + accounts[current_account]['steam_id'] + '&steamidkey=' + accounts[current_account][
            'auth_code'] + '&knowncode=' + game_id
        try:
            next_code = (requests.get(steam_url).json()['result']['nextcode'])
        except KeyError:
            write('WRONG Match Token, Authentication Code or Steam ID ')
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
        all_games = [requests.post('https://csgostats.gg/match/upload/ajax', data={'sharecode': sharecode, 'index': '1'}).json() for sharecode in sharecodes]
    else:
        num = -1
        sharecode = getOldSharecodes(num)[0]
        while True:
            response = requests.post('https://csgostats.gg/match/upload/ajax', data={'sharecode': sharecode, 'index': '1'})
            all_games.append(response.json())
            if response.json()['status'] != 'complete':
                num -= 1
                try:
                    sharecode = getOldSharecodes(num)[0]
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
        for i in completed_games:
            sharecode = i['data']['sharecode']
            game_url = i['data']['url']
            info = ' '.join(i['data']['msg'].replace('-', '').replace('<br />', '. ').split('<')[0].rstrip(' ').split())
            write('Sharecode: %s' % sharecode, add_time=False, push=push_urgency)
            write('URL: %s' % game_url, add_time=False, push=push_urgency)
            write('Status: %s.' % info, add_time=True, push=push_urgency)
            pyperclip.copy(game_url)
        write(None, add_time=False, push=push_urgency, push_now=True, output=False)
    return repeater


# noinspection PyShadowingNames,PyUnusedLocal
def Image_to_Text(image: Image, size: tuple, white_threshold: tuple, arg: str = ''):
    image_data = image.getdata()
    pixel_map, image_text = [], ''
    for y in range(size[1]):
        for x in range(size[0]):
            if relate_list(image_data[y * size[0] + x], [white_threshold], relate=operator.ge):
                pixel_map.append((0, 0, 0))
            else:
                pixel_map.append((255, 255, 255))
    temp_image = Image.new('RGB', (size[0], size[1]))
    temp_image.putdata(pixel_map)
    try:
        image_text = pytesseract.image_to_string(temp_image, timeout=0.3, config=arg)
    except RuntimeError:
        # as timeout_error:
        pass
    if image_text:
        image_text = ' '.join(image_text.replace(': ', ':').split())
        global truth_table
        if truth_table['debugging']:
            image.save(str(cfg['debug_path']) + '\\' + datetime.now().strftime('%H-%M-%S') + '_' + image_text.replace(':', '-') + '.png', format='PNG')
            temp_image.save(str(cfg['debug_path']) + '\\' + datetime.now().strftime('%H-%M-%S') + '_' + image_text.replace(':', '-') + '_temp.png', format='PNG')
        return image_text
    else:
        return ''


def getCfgData():
    try:
        get_cfg = {'activate_script': int(config.get('HotKeys', 'Activate Script'), 16), 'activate_push_notification': int(config.get('HotKeys', 'Activate Push Notification'), 16),
                   'info_newest_match': int(config.get('HotKeys', 'Get Info on newest Match'), 16), 'mute_csgo_toggle': int(config.get('HotKeys', 'Mute CSGO'), 16),
                   'open_live_tab': int(config.get('HotKeys', 'Live Tab Key'), 16), 'switch_accounts': int(config.get('HotKeys', 'Switch accounts for csgostats.gg'), 16),
                   'end_script': int(config.get('HotKeys', 'End Script'), 16), 'stop_warmup_ocr': config.get('HotKeys', 'Stop Warmup OCR'),
                   'screenshot_interval': float(config.get('Screenshot', 'Interval')), 'timeout_time': config.getint('Screenshot', 'Timeout Time'), 'debug_path': config.get('Screenshot', 'Debug Path'), 'steam_api_key': config.get('csgostats.gg', 'API Key'),
                   'max_queue_position': config.getint('csgostats.gg', 'Auto-Retrying for queue position below'), 'log_color': config.get('Screenshot', 'Log Color').lower(),
                   'auto_retry_interval': config.getint('csgostats.gg', 'Auto-Retrying-Interval'), 'pushbullet_device_name': config.get('Pushbullet', 'Device Name'), 'pushbullet_api_key': config.get('Pushbullet', 'API Key'),
                   'tesseract_path': config.get('Warmup', 'Tesseract Path'), 'warmup_test_interval': config.getint('Warmup', 'Test Interval'), 'warmup_push_interval': config.get('Warmup', 'Push Interval'),
                   'warmup_no_text_limit': config.getint('Warmup', 'No Text Limit')}
        return get_cfg
        # 'imgur_id': config.get('Imgur', 'Client ID'), 'imgur_secret': config.get('Imgur', 'Client Secret'), 'stop_warmup_ocr': int(config.get('HotKeys', 'Stop Warmup OCR'), 16), 'info_multiple_matches': int(config.get('HotKeys', 'Get Info on multiple Matches'), 16),
    except (configparser.NoOptionError, configparser.NoSectionError, ValueError):
        write('ERROR IN CONFIG')
        exit('CHECK FOR NEW CONFIG')


# OVERWRITE SETUP
appdata_path = os.getenv('APPDATA') + '\\CSGO AUTO ACCEPT\\'
try:
    os.mkdir(appdata_path)
except FileExistsError:
    pass
last_printed_line = b'0**\n'
console_window = {}
if not sys.stdout.isatty():
    console_window = {'prefix': '\r', 'suffix': '', 'isatty': False}
else:
    console_window = {'prefix': '', 'suffix': '\r', 'isatty': True}

# CONFIG HANDLING
config = configparser.ConfigParser()
config.read('config.ini')
cfg = getCfgData()
cfg['timeout_time'] = int(cfg['timeout_time'] / cfg['screenshot_interval'])
cfg['stop_warmup_ocr'] = [int(i, 16) for i in cfg['stop_warmup_ocr'].split('-')]
cfg['stop_warmup_ocr'][1] += 1
device = 0

# ACCOUNT HANDLING, GETTING ACCOUNT NAME, GETTING CSGO PATH, CHECKING AUTOEXEC
accounts, current_account = [], 0
getAccountsFromCfg()
csgo_path = getCsgoPath(accounts[current_account]['steam_id_3'])
match_server_ready = re.compile('^Server reservation check .* ready-up!$')
match_reservation = 'Matchmaking reservation confirmed: '
match_warmup_time = re.compile('\d+?:\d+')
inverted_warmup_time = re.compile('[^\d:]')
with open(csgo_path + 'console_log.log', 'w') as log:
    log.write('')
with open(cfg['debug_path'] + '\\console.log', 'w') as debug_log:
    debug_log.write('')

# INITIALIZATION FOR getScreenShot
screen_width, screen_height = win32api.GetSystemMetrics(0), win32api.GetSystemMetrics(1)
hwnd = 0
toplist, csgo = [], []

# BOOLEAN, TIME INITIALIZATION
truth_table = {'test_for_accept_button': False, 'test_for_success': False, 'test_for_warmup': False, 'first_ocr': True, 'testing': False, 'debugging': False, 'first_push': True, 'test_for_server': False}
time_table = {'screenshot_time': time.time(), 'time_since_retry': time.time(), 'warmup_test_timer': time.time(), 'time_searching': time.time(), 'not_searching_cc': time.time(), 'searching_cc': time.time()}
test_for_accept_counter = 0

# csgostats.gg VAR
retryer = []

# WARMUP DETECTION SETUP
pytesseract.pytesseract.tesseract_cmd = cfg['tesseract_path']
no_text_found, push_counter = 0, 0
push_times = [int(i) for i in cfg['warmup_push_interval'].split(',')]
push_times.sort(reverse=True)
join_warmup_time = push_times[0] + 1

# PUSHBULLET VAR
note = ''
push_urgency = 0

# MUTE CSGO PATH
mute_csgo_path = '"' + os.getcwd() + '\\sounds\\nircmdc.exe" muteappvolume csgo.exe '
mute_csgo(0)

write('READY')
write('Current account is: %s\n' % accounts[current_account]['name'], add_time=False)


while True:
    if win32api.GetAsyncKeyState(cfg['activate_script']) & 1:  # F9 (ACTIVATE / DEACTIVATE SCRIPT)
        truth_table['test_for_server'] = not truth_table['test_for_server']
        write('TESTING: %s' % truth_table['test_for_server'], overwrite='1')
        if truth_table['test_for_server']:
            playsound('sounds/activated_2.mp3')
            time_table['time_searching'] = time.time()
            mute_csgo(1)
        else:
            playsound('sounds/deactivated.mp3')
            mute_csgo(0)

    if win32api.GetAsyncKeyState(cfg['activate_push_notification']) & 1:  # F8 (ACTIVATE / DEACTIVATE PUSH NOTIFICATION)
        if not device:
            try:
                device = pushbullet.PushBullet(cfg['pushbullet_api_key']).get_device(cfg['pushbullet_device_name'])
            except (pushbullet.errors.PushbulletError, pushbullet.errors.InvalidKeyError):
                write('Pushbullet is wrongly configured.\nWrong API Key or DeviceName in config.ini')
        if device:
            push_urgency += 1
            if push_urgency > 3:
                push_urgency = 0
            push_info = ['not active', 'only if accepted', 'all game status related information', 'all information (game status/csgostats.gg information)']
            write('Pushing: %s' % push_info[push_urgency], overwrite='2')

    if win32api.GetAsyncKeyState(cfg['info_newest_match']) & 1:  # F7 Key (UPLOAD NEWEST MATCH)
        write('Uploading / Getting status on newest match')
        queue_difference = []
        new_sharecodes = getNewCSGOSharecodes(getOldSharecodes(-1)[0])
        for new_code in new_sharecodes:
            retryer.append(new_code) if new_code['sharecode'] not in [old_code['sharecode'] for old_code in retryer] else retryer
        retryer = UpdateCSGOstats(retryer, get_all_games=True)

    if win32api.GetAsyncKeyState(cfg['open_live_tab']) & 1:  # F13 Key (OPEN WEB BROWSER ON LIVE GAME TAB)
        win32gui.ShowWindow(hwnd, win32con.SW_MAXIMIZE)
        webbrowser.open_new_tab('https://csgostats.gg/player/' + accounts[current_account]['steam_id'] + '#/live')
        write('new tab opened', add_time=False)
        time.sleep(0.5)
        win32gui.ShowWindow(hwnd, win32con.SW_MAXIMIZE)

    if win32api.GetAsyncKeyState(cfg['switch_accounts']) & 1:  # F15 (SWITCH ACCOUNTS)
        current_account += 1
        if current_account > len(accounts) - 1:
            current_account = 0
        getCsgoPath(accounts[current_account]['steam_id_3'])
        write('current account is: %s' % accounts[current_account]['name'], add_time=False, overwrite='3')

    if win32api.GetAsyncKeyState(cfg['mute_csgo_toggle']) & 1:  # POS1 (END SCRIPT)
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
    csgo = [(hwnd, title) for hwnd, title in winlist if 'counter-strike: global offensive' in title.lower()]
    if not csgo:
        continue
    hwnd = csgo[0][0]

    # TESTING HERE
    if win32api.GetAsyncKeyState(0x6F) & 1:  # UNBOUND, TEST CODE
        # truth_table['debugging'] = not truth_table['debugging']
        truth_table['test_for_warmup'] = not truth_table['test_for_warmup']
        write('DEBUGGING: %s\n' % truth_table['debugging'])

    if truth_table['testing']:
        # time_table['screenshot_time'] = time.time()
        pass
        # print('Took: %s ' % str(timedelta(milliseconds=int(time.time(*1000 - time_table['screenshot_time']*1000))))
    # TESTING ENDS HERE

    if truth_table['test_for_server']:
        if time.time() - time_table['searching_cc'] > 0.2:
            time_table['searching_cc'] = time.time()
        else:
            continue
        with open(csgo_path + 'console_log.log', 'rb+') as log:
            log_lines = log.readlines()
            console_line = [line.decode('utf-8', 'ignore').encode("utf-8").rstrip(b'\n\r').decode() for line in log_lines]
            log.seek(0)
            log.truncate()
        with open(cfg['debug_path'] + '\\console.log', 'ab') as debug_log:
            [debug_log.write(i) for i in log_lines]
        # server_ready = any([bool(re.match(match_server_ready, i)) for i in console_line])
        server_ready = any(match_reservation in i for i in console_line)
        if server_ready:
            test_for_accept_counter = 0
            write('Server found, starting to look for accept button')
            truth_table['test_for_accept_button'] = True
            # truth_table['test_for_server'] = False
            playsound('sounds/server_found.mp3')
            win32gui.ShowWindow(hwnd, win32con.SW_MAXIMIZE)
    else:
        if time.time() - time_table['not_searching_cc'] > 20:
            time_table['not_searching_cc'] = time.time()
            with open(csgo_path + 'console_log.log', 'w') as log:
                log.write('')

    if truth_table['test_for_accept_button']:
        if time.time() - time_table['screenshot_time'] < cfg['screenshot_interval']:
            continue
        time_table['screenshot_time'] = time.time()
        img = getScreenShot(hwnd, (1265, 760, 1295, 785))
        if not img:
            continue
        accept_avg = color_average(img, [(76, 176, 80), (89, 203, 94)])
        mute_csgo(0)
        if relate_list(accept_avg, [(2, 2, 2), (2, 2, 2)]):
            write('Trying to Accept', push=push_urgency + 1)

            truth_table['test_for_success'] = True
            truth_table['test_for_accept_button'] = False
            truth_table['test_for_server'] = False
            accept_avg = []

            for _ in range(5):
                click(int(screen_width / 2), int(screen_height / 1.78))
                pass

            write('Trying to catch a loading map')
            playsound('sounds/accept_found.mp3')
            time_table['screenshot_time'] = time.time()
        test_for_accept_counter += 1
        if test_for_accept_counter > cfg['timeout_time']:
            write('NO ACCEPT BUTTON FOUND AFTER %s seconds.' % str(int(cfg['timeout_time']*cfg['screenshot_interval'])))
            write('Continuing to look for ready server.')
            mute_csgo(1)
            playsound('sounds/back_to_testing.mp3')
            truth_table['test_for_accept_button'] = False

    if truth_table['test_for_success']:
        if time.time() - time_table['screenshot_time'] < 40:
            img = getScreenShot(hwnd, (2435, 65, 2555, 100))
            not_searching_avg = color_average(img, [(6, 10, 10)])
            searching_avg = color_average(img, [(6, 163, 97), (4, 63, 35)])

            not_searching = relate_list(not_searching_avg, [(2, 5, 5)])
            searching = relate_list(searching_avg, [(2.7, 55, 35), (1, 50, 35)])

            img = getScreenShot(hwnd, (467, 1409, 1300, 1417))
            success_avg = color_average(img, [(21, 123, 169)])
            success = relate_list(success_avg, [(1, 8, 7)])

            if success:
                write('\tTook %s since pressing accept.' % str(timedelta(seconds=int(time.time() - time_table['screenshot_time']))), add_time=False, push=push_urgency + 1)
                write('\tTook %s since trying to find a game.' % str(timedelta(seconds=int(time.time() - time_table['time_searching']))), add_time=False, push=push_urgency + 1)
                write('Game should have started', push=push_urgency + 2, push_now=True)
                truth_table['test_for_success'] = False
                truth_table['test_for_warmup'] = True
                playsound('sounds/done_testing.mp3')
                time_table['warmup_test_timer'] = time.time() + 5
                continue

            if any([searching, not_searching]):
                write('\tTook: %s ' % str(timedelta(seconds=int(time.time() - time_table['screenshot_time']))), add_time=False, push=push_urgency + 1)
                write('Game doesnt seem to have started. Continuing to search for a Server!', push=push_urgency + 1, push_now=True)
                playsound('sounds/back_to_testing.mp3')
                mute_csgo(1)
                truth_table['test_for_success'] = False
                truth_table['test_for_server'] = True
                continue

        else:
            write('40 Seconds after accept, did not find a loading map nor searching queue')
            truth_table['test_for_success'] = False
            # noinspection PyUnboundLocalVariable
            print(success_avg)
            # noinspection PyUnboundLocalVariable
            print(searching_avg)
            # noinspection PyUnboundLocalVariable
            print(not_searching_avg)
            playsound('sounds/fail.mp3')
            # noinspection PyUnboundLocalVariable
            img.save(cfg['debug_path'] + '\\Unknown Error.png')

    if truth_table['test_for_warmup']:

        for i in range(cfg['stop_warmup_ocr'][0], cfg['stop_warmup_ocr'][1]):
            win32api.GetAsyncKeyState(i) & 1
        while True:
            keys = [(win32api.GetAsyncKeyState(i) & 1) for i in range(cfg['stop_warmup_ocr'][0], cfg['stop_warmup_ocr'][1])]

            if any(keys):
                write('Break from warmup-loop')
                truth_table['test_for_warmup'] = False
                truth_table['first_ocr'] = True
                truth_table['first_push'] = True
                break

            if time.time() - time_table['warmup_test_timer'] >= cfg['warmup_test_interval']:
                img = getScreenShot(hwnd, (1036, 425, 1525, 456))  # 'WAITING FOR PLAYERS X:XX'
                img_text = Image_to_Text(img, img.size, (225, 225, 225), arg='--psm 6')
                time_table['warmup_test_timer'] = time.time()
                time_left = re.sub(inverted_warmup_time, "", img_text)
                if time_left:
                    time_left = time_left.split()[-1].split(':')
                    # write(img_text, add_time=False)
                    try:
                        time_left = int(time_left[0]) * 60 + int(time_left[1])
                        if truth_table['first_ocr']:
                            join_warmup_time = time_left
                            time_table['screenshot_time'] = time.time()
                            truth_table['first_ocr'] = False

                    except (ValueError, IndexError):
                        continue

                    time_left_data = timedelta(seconds=int(time.time() - time_table['screenshot_time'])), time.strftime('%H:%M:%S', time.gmtime(abs((join_warmup_time - time_left) - (time.time() - time_table['screenshot_time'])))), img_text
                    write('Time since start: %s - Time Difference: %s - Time left: %s' % (time_left_data[0], time_left_data[1], time_left_data[2]), add_time=False, overwrite='1')
                    if no_text_found > 0:
                        no_text_found = 0

                    if time_left <= push_times[push_counter]:
                        push_counter += 1
                        write('Time since start: %s\nTime Difference: %s\nTime left: %s' % (time_left_data[0], time_left_data[1], time_left_data[2]), push=push_urgency + 1, push_now=True, output=False)

                    if truth_table['first_push']:
                        if abs((join_warmup_time - time_left) - (time.time() - time_table['screenshot_time'])) >= 5:
                            truth_table['first_push'] = False
                            write('Match should start in ' + str(time_left) + ' seconds, All players have connected', push=push_urgency + 2, push_now=True)

                else:
                    no_text_found += 1

            if push_counter >= len(push_times):
                push_counter = 0
                no_text_found = 0
                truth_table['test_for_warmup'] = False
                truth_table['first_ocr'] = True
                truth_table['first_push'] = True
                write('Warmup should be over in less then %s seconds!' % push_times[-1], push=push_urgency + 2, push_now=True)
                break

            if no_text_found >= cfg['warmup_no_text_limit']:
                push_counter = 0
                no_text_found = 0
                truth_table['test_for_warmup'] = False
                truth_table['first_ocr'] = True
                truth_table['first_push'] = True
                write('Did not find any warmup text.', push=push_urgency + 2, push_now=True)
                break
if console_window['isatty']:
    if last_printed_line.split(b'**')[-1] != b'\n':
        print('')
exit('ENDED BY USER')
