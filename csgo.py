import configparser
import operator
import os
import webbrowser
from datetime import datetime, timedelta
import time

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
    return sum(lst) / len(lst)


# noinspection PyShadowingNames
def enum_cb(hwnd, results):
    winlist.append((hwnd, win32gui.GetWindowText(hwnd)))


# noinspection PyShadowingNames
def write(message, add_time: bool = True, push: int = 0, push_now: bool = False, output: bool = True, ending: str = '\n'):
    if add_time:
        m = datetime.now().strftime('%H:%M:%S') + ': ' + str(message)
    else:
        m = message
    if output:
        print(m, end=ending)

    if push >= 3:
        global note
        if message:
            note = note + m + '\n'
        if push_now:
            device.push_note('CSGO AUTO ACCEPT', note)
            note = ''


# noinspection PyShadowingNames
def click(x: int, y: int):
    win32api.SetCursorPos((x, y))
    win32api.mouse_event(win32con.MOUSEEVENTF_LEFTDOWN, x, y, 0, 0)
    win32api.mouse_event(win32con.MOUSEEVENTF_LEFTUP, x, y, 0, 0)


# noinspection PyShadowingNames
def relate_list(l_org, l1, l2=None, relate: operator = operator.le):
    if not l_org:
        return False
    truth_list, l3 = [], []
    for i, val in enumerate(l1, start=0):
        l3.append(relate(l_org[i], val))
    truth_list.append(all(l3))
    l3 = []
    if l2:
        for i, val in enumerate(l2, start=len(l1)):
            l3.append(relate(l_org[i], val))
        truth_list.append(all(l3))
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

    rgb = [Avg(r), Avg(g), Avg(b)] * int(len(compare_list) / 3)
    for i, val in enumerate(compare_list, start=0):
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
    image = ImageGrab.grab(scaled_area)
    return image


# noinspection PyShadowingNames
def getAccountsFromCfg():
    steam_ids = ''
    for i in config.sections():
        if i.startswith('Account'):
            steam_id = config.get(i, 'Steam ID')
            auth_code = config.get(i, 'Authentication Code')
            match_token = config.get(i, 'Match Token')
            steam_ids += steam_id + ','
            accounts.append({'steam_id': steam_id, 'auth_code': auth_code, 'match_token': match_token})

    steam_ids = steam_ids.lstrip(',').rstrip(',')
    profiles = requests.get('http://api.steampowered.com/ISteamUser/GetPlayerSummaries/v0002/?key=' + cfg['steam_api_key'] + '&steamids=' + steam_ids).json()['response']['players']
    for i in profiles:
        for n in accounts:
            if n['steam_id'] == i['steamid']:
                n['name'] = i['personaname']
                break


# noinspection PyShadowingNames
def getOldSharecodes(num: int = -1):
    try:
        last_game = open('last_game_' + accounts[current_account]['steam_id'] + '.txt', 'r')
        games = last_game.readlines()
        last_game.close()
    except FileNotFoundError:
        last_game = open('last_game_' + accounts[current_account]['steam_id'] + '.txt', 'w')
        last_game.write(accounts[current_account]['match_token'] + '\n')
        games = [accounts[current_account]['match_token']]
        last_game.close()
    last_game = open('last_game_' + accounts[current_account]['steam_id'] + '.txt', 'w')
    games = games[-200:]
    for i, val in enumerate(games):
        games[i] = 'CSGO' + val.strip('\n').split('CSGO')[1]
        last_game.write(games[i] + '\n')
    last_game.close()
    return games[num:]


# noinspection PyShadowingNames
def getNewCSGOMatches(game_id: str):
    sharecodes = []
    next_code = game_id
    last_game = open('last_game_' + accounts[current_account]['steam_id'] + '.txt', 'a')
    while next_code != 'n/a':
        steam_url = 'https://api.steampowered.com/ICSGOPlayers_730/GetNextMatchSharingCode/v1?key=' + cfg['steam_api_key'] + '&steamid=' + accounts[current_account]['steam_id'] + '&steamidkey=' + accounts[current_account][
            'auth_code'] + '&knowncode=' + game_id
        try:
            next_code = (requests.get(steam_url).json()['result']['nextcode'])
        except KeyError:
            write('WRONG Match Token, Authentication Code or Steam ID ')
            return [game_id]

        if next_code:
            if next_code != 'n/a':
                sharecodes.append(next_code)
                game_id = next_code
                last_game.write(next_code + '\n')
    if sharecodes:
        return sharecodes
    else:
        return [game_id]


# noinspection PyShadowingNames
def UpdateCSGOstats(sharecodes: list, num_completed: int = 1):
    completed_games, not_completed_games, = [], []
    for val in sharecodes:
        response = requests.post('https://csgostats.gg/match/upload/ajax', data={'sharecode': val, 'index': '1'})
        if response.json()['status'] == 'complete':
            completed_games.append(response.json())
        else:
            not_completed_games.append(response.json())

    queued_games = [game['data']['queue_pos'] for game in not_completed_games if game['status'] != 'error']
    global retrying_games
    retrying_games = []

    if queued_games:
        if queued_games[0] < cfg['max_queue_position']:
            global time_table
            retrying_games = [game['data']['sharecode'] for game in not_completed_games]
            time_table['error_check_time'] = time.time()
        for i, val in enumerate(queued_games):
            write('#%s: in Queue #%s.' % (i + 1, val), add_time=False)

    if len(not_completed_games) - len(queued_games) > 0:
        write('An error occurred in %s game[s].' % (len(not_completed_games) - len(queued_games)), add_time=False)
        retrying_games.append([game['data']['sharecode'] for game in not_completed_games if game['status'] == 'error'])

    if completed_games:
        for i in completed_games[num_completed * - 1:]:
            sharecode = i['data']['sharecode']
            game_url = i['data']['url']
            info = ' '.join(i['data']['msg'].replace('-', '').replace('<br />', '. ').split('<')[0].rstrip(' ').split())
            write('Sharecode: %s' % sharecode, add_time=False, push=push_urgency)
            write('URL: %s' % game_url, add_time=False, push=push_urgency)
            write('Status: %s.' % info, add_time=False, push=push_urgency)
            pyperclip.copy(game_url)
        write(None, add_time=False, push=push_urgency, push_now=True, output=False)


# noinspection PyShadowingNames
def Image_to_Text(image: Image, size: tuple, white_threshold: list, arg: str = ''):
    image_data = image.getdata()
    pixel_map, image_text = [], ''
    for y in range(size[1]):
        for x in range(size[0]):
            if relate_list(image_data[y * size[0] + x], white_threshold, relate=operator.ge):
                pixel_map.append((0, 0, 0))
            else:
                pixel_map.append((255, 255, 255))
    temp_image = Image.new('RGB', (size[0], size[1]))
    temp_image.putdata(pixel_map)
    try:
        image_text = pytesseract.image_to_string(temp_image, timeout=0.3, config=arg)
    except RuntimeError as timeout_error:
        pass
    if image_text:
        image_text = ' '.join(image_text.replace(': ', ':').split())
        global truth_table
        if truth_table['debugging']:
            image.save(str(cfg['debug_path']) + '\\' + datetime.now().strftime('%H-%M-%S') + '_' + image_text.replace(':', '-') + '.png', format='PNG')
            temp_image.save(str(cfg['debug_path']) + '\\' + datetime.now().strftime('%H-%M-%S') + '_' + image_text.replace(':', '-') + '_temp_.png', format='PNG')
        return image_text
    else:
        return False


def getCfgData():
    try:
        get_cfg = {'activate_script': int(config.get('HotKeys', 'Activate Script'), 16), 'activate_push_notification': int(config.get('HotKeys', 'Activate Push Notification'), 16),
                   'info_newest_match': int(config.get('HotKeys', 'Get Info on newest Match'), 16), 'info_multiple_matches': int(config.get('HotKeys', 'Get Info on multiple Matches'), 16),
                   'open_live_tab': int(config.get('HotKeys', 'Live Tab Key'), 16), 'switch_accounts': int(config.get('HotKeys', 'Switch accounts for csgostats.gg'), 16), 'stop_warmup_ocr': int(config.get('HotKeys', 'Stop Warmup OCR'), 16),
                   'end_script': int(config.get('HotKeys', 'End Script'), 16),
                   'screenshot_interval': config.getint('Screenshot', 'Interval'), 'debug_path': config.get('Screenshot', 'Debug Path'), 'steam_api_key': config.get('csgostats.gg', 'API Key'), 'last_x_matches': config.getint('csgostats.gg', 'Number of Requests'),
                   'completed_matches': config.getint('csgostats.gg', 'Completed Matches'), 'max_queue_position': config.getint('csgostats.gg', 'Auto-Retrying for queue position below'),
                   'auto_retry_interval': config.getint('csgostats.gg', 'Auto-Retrying-Interval'), 'pushbullet_device_name': config.get('Pushbullet', 'Device Name'), 'pushbullet_api_key': config.get('Pushbullet', 'API Key'),
                   'tesseract_path': config.get('Warmup', 'Tesseract Path'), 'warmup_test_interval': config.getint('Warmup', 'Test Interval'), 'warmup_push_interval': config.get('Warmup', 'Push Interval'),
                   'warmup_no_text_limit': config.getint('Warmup', 'No Text Limit')}
        return get_cfg
        # 'imgur_id': config.get('Imgur', 'Client ID'), 'imgur_secret': config.get('Imgur', 'Client Secret'),
    except (configparser.NoOptionError, configparser.NoSectionError, ValueError):
        write('ERROR IN CONFIG')
        exit('CHECK FOR NEW CONFIG')


# CONFIG HANDLING
config = configparser.ConfigParser()
config.read('config.ini')
cfg = getCfgData()
device = 0

# ACCOUNT HANDLING, GETTING ACCOUNT NAME
accounts, current_account = [], 0
getAccountsFromCfg()

# INITIALIZATION FOR getScreenShot
screen_width, screen_height = win32api.GetSystemMetrics(0), win32api.GetSystemMetrics(1)
toplist, winlist = [], []
hwnd = 0

# BOOLEAN INITIALIZATION
truth_table = {'test_for_live_game': False, 'test_for_success': False, 'test_for_warmup': False, 'first_ocr': True, 'testing': False, 'debugging': False}

# csgostats.gg VAR
retrying_games = []

# WARMUP DETECTION SETUP
pytesseract.pytesseract.tesseract_cmd = cfg['tesseract_path']
push_times, no_text_found, push_counter = [], 0, 0
for i in cfg['warmup_push_interval'].split(','):
    push_times.append(int(i))
push_times.sort(reverse=True)
join_warmup_time = push_times[0] + 1

# PUSHBULLET VAR
note = ''
push_urgency = 0

# INITIALIZATION OF TIME VARS
time_table = {'screenshot_time': time.time(), 'error_check_time': time.time(), 'warmup_test_timer': time.time()}

write('READY')
write('Current account is: %s\n' % accounts[current_account]['name'], add_time=False)

while True:
    if win32api.GetAsyncKeyState(cfg['activate_script']) & 1:  # F9 (ACTIVATE / DEACTIVATE SCRIPT)
        truth_table['test_for_live_game'] = not truth_table['test_for_live_game']
        write('TESTING: %s' % truth_table['test_for_live_game'])
        if truth_table['test_for_live_game']:
            playsound('sounds/activated_2.mp3')
            time_searching = time.time()
        else:
            playsound('sounds/deactivated.mp3')

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
            write('Pushing: %s' % push_info[push_urgency])

    if win32api.GetAsyncKeyState(cfg['info_newest_match']) & 1:  # F7 Key (UPLOAD NEWEST MATCH)
        write('Uploading / Getting status on newest match')
        UpdateCSGOstats(getNewCSGOMatches(getOldSharecodes()[0]))

    if win32api.GetAsyncKeyState(cfg['info_multiple_matches']) & 1:  # F6 Key (GET INFO ON LAST X MATCHES)
        write('Getting Info from last %s matches' % cfg['last_x_matches'])
        getNewCSGOMatches(getOldSharecodes()[0])
        UpdateCSGOstats(getOldSharecodes(num=cfg['last_x_matches'] * -1), num_completed=cfg['completed_matches'])

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
        write('current account is: %s' % accounts[current_account]['name'], add_time=False)

    if win32api.GetAsyncKeyState(cfg['stop_warmup_ocr']) & 1:  # ESC (STOP WARMUP OCR)
        write('STOPPING WARMUP TIME FINDER!', add_time=False)
        truth_table['test_for_warmup'] = False
        no_text_found = 0
        time_table['warmup_test_timer'] = time.time()

    if win32api.GetAsyncKeyState(cfg['end_script']) & 1:  # POS1 (END SCRIPT)
        write('Exiting Script')
        break

    if retrying_games:
        if time.time() - time_table['error_check_time'] > cfg['auto_retry_interval']:
            time_table['error_check_time'] = time.time()
            UpdateCSGOstats(retrying_games, num_completed=len(retrying_games))

    winlist = []
    win32gui.EnumWindows(enum_cb, toplist)
    csgo = [(hwnd, title) for hwnd, title in winlist if 'counter-strike: global offensive' in title.lower()]

    # ONLY CONTINUING IF CSGO IS RUNNING
    if not csgo:
        continue
    hwnd = csgo[0][0]

    # TESTING HERE
    if win32api.GetAsyncKeyState(0x6F) & 1:  # UNBOUND, TEST CODE
        # write('Executing Debugging\n')
        # truth_table['testing'] = not truth_table['testing']
        truth_table['debugging'] = not truth_table['debugging']
        write('DEBUGGING: %s\n' % truth_table['debugging'])

    if truth_table['testing']:
        # time_table['screenshot_time'] = time.time()
        pass
        # print('Took: %s ' % str(timedelta(milliseconds=int(time.time(*1000 - time_table['screenshot_time']*1000))))
    # TESTING ENDS HERE

    if truth_table['test_for_live_game']:
        if time.time() - time_table['screenshot_time'] < cfg['screenshot_interval']:
            continue
        time_table['screenshot_time'] = time.time()
        img = getScreenShot(hwnd, (1265, 760, 1295, 785))
        if not img:
            continue
        accept_avg = color_average(img, [76, 176, 80, 90, 203, 95])

        if relate_list(accept_avg, [1, 2, 1], l2=[1, 1, 2]):
            write('Trying to Accept', push=push_urgency + 1)

            truth_table['test_for_success'] = True
            truth_table['test_for_live_game'] = False
            accept_avg = []

            for _ in range(5):
                click(int(screen_width / 2), int(screen_height / 1.78))

            write('Trying to catch a loading map')
            playsound('sounds/accept_found.mp3')
            time_table['screenshot_time'] = time.time()

    if truth_table['test_for_success']:
        if time.time() - time_table['screenshot_time'] < 40:
            img = getScreenShot(hwnd, (2435, 65, 2555, 100))
            not_searching_avg = color_average(img, [6, 10, 10])
            searching_avg = color_average(img, [6, 163, 97, 4, 63, 35])

            not_searching = relate_list(not_searching_avg, [2, 5, 5])
            searching = relate_list(searching_avg, [2.7, 55, 35], l2=[1, 50, 35])

            img = getScreenShot(hwnd, (467, 1409, 1300, 1417))
            success_avg = color_average(img, [21, 123, 169])
            success = relate_list(success_avg, [1, 8, 7])

            if success:
                write('Took %s since pressing accept.' % str(timedelta(seconds=int(time.time() - time_table['screenshot_time']))), add_time=False, push=push_urgency + 1)
                write('Took %s since trying to find a game.' % str(timedelta(seconds=int(time.time() - time_searching))), add_time=False, push=push_urgency + 1)
                write('Game should have started', push=push_urgency + 2, push_now=True)
                truth_table['test_for_success'] = False
                truth_table['test_for_warmup'] = True
                playsound('sounds/done_testing.mp3')
                time_table['warmup_test_timer'] = time.time()+5

            if any([searching, not_searching]):
                write('Took: %s ' % str(timedelta(seconds=int(time.time() - time_table['screenshot_time']))), add_time=False, push=push_urgency + 1)
                write('Game doesnt seem to have started. Continuing to search for accept Button!', push=push_urgency + 1, push_now=True)
                playsound('sounds/back_to_testing.mp3')
                truth_table['test_for_success'] = False
                truth_table['test_for_live_game'] = True

        else:
            write('40 Seconds after accept, did not find loading map nor searching queue')
            truth_table['test_for_success'] = False
            print(success_avg)
            print(searching_avg)
            print(not_searching_avg)
            playsound('sounds/fail.mp3')
            img.save(os.path.expanduser('~') + '\\Unknown Error.png')

    if truth_table['test_for_warmup']:
        for i in range(112, 136):
            win32api.GetAsyncKeyState(i) & 1
        while True:
            keys = []
            for i in range(112, 136):
                keys.append(win32api.GetAsyncKeyState(i) & 1)
            if any(keys):
                print('')
                write('Break from warmup-loop')
                truth_table['test_for_warmup'] = False
                truth_table['first_ocr'] = True
                break

            if time.time() - time_table['warmup_test_timer'] >= cfg['warmup_test_interval']:
                img = getScreenShot(hwnd, (1036, 425, 1525, 456))  # 'WAITING FOR PLAYERS X:XX'
                img_text = Image_to_Text(img, img.size, [225, 225, 225], arg='--psm 6')
                time_table['warmup_test_timer'] = time.time()
                if img_text:
                    time_left = img_text.split()[-1].split(':')
                    # write(img_text, add_time=False)
                    try:
                        time_left = int(time_left[0]) * 60 + int(time_left[1])
                        if truth_table['first_ocr']:
                            join_warmup_time = time_left
                            time_table['screenshot_time'] = time.time()
                            truth_table['first_ocr'] = False

                    except ValueError:
                        time_left = push_times[0] + 1

                    write('\rTime since start: %s - Time Difference: %s - Time left: %s' % (timedelta(seconds=int(time.time() - time_table['screenshot_time'])), time.strftime('%H:%M:%S', time.gmtime(join_warmup_time-time_left)), img_text), add_time=False, ending='')
                    # write('Time since start: %s, %s' % (timedelta(seconds=int(time.time( - time_table['screenshot_time'])), img_text), add_time=False)
                    if no_text_found > 0:
                        no_text_found -= 1

                    if time_left <= push_times[push_counter]:
                        push_counter += 1
                        write('Time since start: %s\nTime Difference: %s\nTime left: %s' % (timedelta(seconds=int(time.time() - time_table['screenshot_time'])), time.strftime('%H:%M:%S', time.gmtime(join_warmup_time-time_left)), img_text), add_time=True, push=push_urgency + 1, output=False, push_now=True)

                else:
                    no_text_found += 1

            if push_counter >= len(push_times):
                push_counter = 0
                no_text_found = 0
                truth_table['test_for_warmup'] = False
                truth_table['first_ocr'] = True
                write('\nWarmup should be over in less then %s seconds!' % push_times[-1], add_time=False, push=push_urgency + 2, push_now=True)
                break

            if no_text_found >= cfg['warmup_no_text_limit']:
                push_counter = 0
                no_text_found = 0
                truth_table['test_for_warmup'] = False
                truth_table['first_ocr'] = True
                write('\nDid not find any warmup text.', add_time=False, push=push_urgency + 2, push_now=True)
                break

exit('ENDED BY USER')
