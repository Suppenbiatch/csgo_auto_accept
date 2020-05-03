import configparser
import operator
import os
import webbrowser
from datetime import datetime, timedelta
from time import time

import pushbullet
import pyperclip
import requests
import win32api
import win32con
import win32gui
from PIL import ImageGrab
from playsound import playsound


def Avg(lst):
    return sum(lst) / len(lst)


def enum_cb(hwnd, results):
    winlist.append((hwnd, win32gui.GetWindowText(hwnd)))


def write(message, add_time=True, push=0, push_now=False):
    if message:
        if add_time:
            m = datetime.now().strftime("%H:%M:%S") + ": " + str(message)
        else:
            m = message
        print(m)

    if push >= 3:
        global note
        if message:
            note = note + m + "\n"
        if push_now:
            device.push_note("CSGO AUTO ACCEPT", note)
            note = ""


def click(x, y):
    win32api.SetCursorPos((x, y))
    win32api.mouse_event(win32con.MOUSEEVENTF_LEFTDOWN, x, y, 0, 0)
    win32api.mouse_event(win32con.MOUSEEVENTF_LEFTUP, x, y, 0, 0)


def relate_list(l_org, l1, l2=[], relate=operator.le):
    if not l_org:
        return False
    truth_list, l3 = [], []
    for i, val in enumerate(l1, start=0):
        l3.append(relate(l_org[i], val))
    truth_list.append(all(l3))
    l3 = []
    if l2:
        for i, val in enumerate(l2, start=3):
            l3.append(relate(l_org[i], val))
        truth_list.append(all(l3))
    return any(truth_list)


def color_average(image, compare_list):
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


def getScreenShot(window_id, area=(0, 0, 0, 0)):
    area = list(area)
    scaled_area = [screen_width / 2560, screen_height / 1440]
    scaled_area = 2 * scaled_area
    for i, _ in enumerate(area[-2:], start=len(area) - 2):
        area[i] += 1
    for i, val in enumerate(area, start=0):
        scaled_area[i] = scaled_area[i] * val
    scaled_area = list(map(int, scaled_area))
    win32gui.ShowWindow(window_id, win32con.SW_MAXIMIZE)
    image = ImageGrab.grab(scaled_area)
    return image


def getOldSharecodes(num=-1):
    try:
        last_game = open("last_game.txt", "r")
        games = last_game.readlines()
        last_game.close()
    except FileNotFoundError:
        last_game = open("last_game.txt", "w")
        last_game.write(config.get("csgostats.gg", "Match Token") + "\n")
        games = [config.get("csgostats.gg", "Match Token")]
        last_game.close()
    last_game = open("last_game.txt", "w")
    games = games[-200:]
    for i, val in enumerate(games):
        games[i] = "CSGO" + val.strip("\n").split("CSGO")[1]
        last_game.write(games[i] + "\n")
    last_game.close()
    return games[num:]


def getNewCSGOMatches(game_id):
    sharecodes = []
    next_code = game_id
    last_game = open("last_game.txt", "a")
    while next_code != "n/a":
        steam_url = "https://api.steampowered.com/ICSGOPlayers_730/GetNextMatchSharingCode/v1?key=" + steam_api_key + "&steamid=" + steam_id + "&steamidkey=" + game_code + "&knowncode=" + game_id
        try:
            next_code = (requests.get(steam_url).json()["result"]["nextcode"])
        except KeyError:
            write("WRONG GAME_CODE, GAME_ID or STEAM_ID ")
            return 0

        if next_code:
            if next_code != "n/a":
                sharecodes.append(next_code)
                game_id = next_code
                last_game.write(next_code + "\n")
    if sharecodes:
        return sharecodes
    else:
        return [game_id]


def UpdateCSGOstats(sharecodes, num_completed=1):
    completed_games, analyze_games = [], []
    for val in sharecodes:
        response = requests.post("https://csgostats.gg/match/upload/ajax", data={'sharecode': val, 'index': '1'})
        if response.json()["status"] == "complete":
            completed_games.append(response.json())
        else:
            analyze_games.append(response.json())
            
    output = [completed_games[num_completed * -1:], analyze_games]
    for i in output:
        for json_dict in i:
            sharecode = json_dict["data"]["sharecode"]
            game_url = json_dict["data"]["url"]
            info = json_dict["data"]["msg"].split("<")[0].replace('-', '').rstrip(" ")
            write('Sharecode: %s' % sharecode, add_time=False, push=push_urgency)
            write("URL: %s" % game_url, add_time=False, push=push_urgency)
            write("Status: %s." % info, add_time=False, push=push_urgency)
    write(None, add_time=False, push=push_urgency, push_now=True)
    pyperclip.copy(completed_games[-1]["data"]["url"])
    return game_url


def getHotKeys():
    get_keys = [int(config.get("HotKeys", "Activate Script"), 16), int(config.get("HotKeys", "Activate Push Notification"), 16), int(config.get("HotKeys", "Get Info on newest Match"), 16),
                int(config.get("HotKeys", "Get Info on multiple Matches"), 16), int(config.get("HotKeys", "Live Tab Key"), 16),
                int(config.get("HotKeys", "End Script"), 16)]
    return get_keys


config = configparser.ConfigParser()
config.read("config.ini")

steam_api_key = config.get("csgostats.gg", "API Key")
steam_id = config.get("csgostats.gg", "Steam ID")
game_code = config.get("csgostats.gg", "Game Code")

screenshot_interval = config.getint("Screenshot", "Interval")

keys = getHotKeys()

device = 0

screen_width, screen_height = win32api.GetSystemMetrics(0), win32api.GetSystemMetrics(1)
toplist, winlist = [], []
hwnd = 0

test_for_live_game, test_for_success, push_urgency, testing = False, False, False, False
# accept_avg = []

note = ""

start_time = time()
write("READY")
print("\n")

while True:
    if win32api.GetAsyncKeyState(keys[0]) & 1:  # F9 (ACTIVATE / DEACTIVATE SCRIPT)
        test_for_live_game = not test_for_live_game
        write("TESTING: %s" % test_for_live_game)
        if test_for_live_game:
            playsound('sounds/activated.mp3')
            time_searching = time()
        else:
            playsound('sounds/deactivated.mp3')

    if win32api.GetAsyncKeyState(keys[1]) & 1:  # F8 (ACTIVATE / DEACTIVATE PUSH NOTIFICATION)
        if not device:
            PushBulletDeviceName = config.get('Pushbullet', 'Device Name')
            PushBulletAPIKey = config.get('Pushbullet', 'API Key')
            try:
                device = pushbullet.PushBullet(PushBulletAPIKey).get_device(PushBulletDeviceName)
            except pushbullet.errors.PushbulletError or pushbullet.errors.InvalidKeyError:
                write("Pushbullet is wrongly configured.\nWrong API Key or DeviceName in config.ini")
        if device:
            push_urgency += 1
            if push_urgency > 3:
                push_urgency = 0
            push_info = ["not active", "only if accepted", "all game status related information", "all information (game status/csgostats.gg information)"]
            write("Pushing: %s" % push_info[push_urgency])

    if win32api.GetAsyncKeyState(keys[2]) & 1:  # F7 Key (UPLOAD NEWEST MATCH)
        write("Uploading / Getting status on newest match")
        pyperclip.copy(UpdateCSGOstats(getNewCSGOMatches(getOldSharecodes()[0])))

    if win32api.GetAsyncKeyState(keys[3]) & 1:  # F6 Key (GET INFO ON LAST X MATCHES)
        last_x_matches = config.getint("csgostats.gg", "Number of Requests")
        completed_matches = config.getint("csgostats.gg", "Completed Matches")
        write("Getting Info from last %s matches" % last_x_matches)
        # write("Outputting %s completed match[es]" % completed_matches, add_time=False)
        getNewCSGOMatches(getOldSharecodes()[0])
        UpdateCSGOstats(getOldSharecodes(num=last_x_matches * -1), num_completed=completed_matches)

    if win32api.GetAsyncKeyState(keys[4]) & 1:  # F13 Key (OPEN WEB BROWSER ON LIVE GAME TAB)
        webbrowser.open_new_tab("https://csgostats.gg/player/" + steam_id + "#/live")
        write("new tab opened", add_time=False)

    if win32api.GetAsyncKeyState(keys[5]) & 1:  # POS1/HOME Key
        write("Exiting Script")
        break

    winlist = []
    win32gui.EnumWindows(enum_cb, toplist)
    csgo = [(hwnd, title) for hwnd, title in winlist if 'counter-strike: global offensive' in title.lower()]
    if not csgo:
        continue
    hwnd = csgo[0][0]

    # TESTING HERE
    if win32api.GetAsyncKeyState(0x73) & 1:  # F5, TEST CODE
        print("\n")
        write("Executing TestCode")
        print("\n")
        testing = not testing

    if testing:
        # start_time = time()
        img = getScreenShot(hwnd, (2435, 65, 2555, 100))
        not_searching_avg = color_average(img, [6, 10, 10])
        searching_avg = color_average(img, [6, 163, 97, 4, 63, 35])
        not_searching = relate_list(not_searching_avg, [2, 5, 5])
        searching = relate_list(searching_avg, [2.7, 55, 35], l2=[1, 50, 35])
        img = getScreenShot(hwnd, (467, 1409, 1300, 1417))
        success_avg = color_average(img, [21, 123, 169])
        success = relate_list(success_avg, [1, 8, 7])
        # print("Took: %s " % str(timedelta(milliseconds=int(time()*1000 - start_time*1000))))
    # TESTING ENDS HERE

    if test_for_live_game:
        if time() - start_time < screenshot_interval:
            continue
        start_time = time()
        img = getScreenShot(hwnd, (1265, 760, 1295, 785))
        if not img:
            continue
        accept_avg = color_average(img, [76, 176, 80, 90, 203, 95])

        if relate_list(accept_avg, [1, 2, 1], l2=[1, 1, 2]):
            write("Trying to Accept", push=push_urgency + 1)

            test_for_success = True
            test_for_live_game = False
            accept_avg = []

            for _ in range(5):
                click(int(screen_width / 2), int(screen_height / 1.78))
                # sleep(0.5)
                # pass

            write("Trying to catch a loading map")
            playsound('sounds/accept_found.mp3')
            start_time = time()

    if test_for_success:
        if time() - start_time < 40:
            img = getScreenShot(hwnd, (2435, 65, 2555, 100))
            not_searching_avg = color_average(img, [6, 10, 10])
            searching_avg = color_average(img, [6, 163, 97, 4, 63, 35])

            not_searching = relate_list(not_searching_avg, [2, 5, 5])
            searching = relate_list(searching_avg, [2.7, 55, 35], l2=[1, 50, 35])

            img = getScreenShot(hwnd, (467, 1409, 1300, 1417))
            success_avg = color_average(img, [21, 123, 169])
            success = relate_list(success_avg, [1, 8, 7])

            if success:
                write("Took %s since pressing accept." % str(timedelta(seconds=int(time() - start_time))), add_time=False, push=push_urgency + 1)
                write("Took %s since trying to find a game." % str(timedelta(seconds=int(time() - time_searching))), add_time=False, push=push_urgency + 1)
                write("Game should have started", push=push_urgency + 2, push_now=True)
                test_for_success = False
                playsound('sounds/done_testing.mp3')

            if any([searching, not_searching]):
                write("Took: %s " % str(timedelta(seconds=int(time() - start_time))), add_time=False, push=push_urgency + 1)
                write("Game doesnt seem to have started. Continuing to search for accept Button!", push=push_urgency + 1, push_now=True)
                playsound('sounds/back_to_testing.mp3')
                test_for_success = False
                test_for_live_game = True

        else:
            write("40 Seconds after accept, did not find loading map nor searching queue")
            test_for_success = False
            print(success_avg)
            print(searching_avg)
            print(not_searching_avg)
            playsound('sounds/fail.mp3')
            img.save(os.path.expanduser("~") + '\\Unknown Error.png')
