from time import time
from datetime import datetime
from playsound import playsound
from PIL import Image, ImageChops, ImageGrab
from pushbullet import PushBullet
import configparser
import win32api
import win32con
import win32gui
import operator


def Avg(lst):
    return sum(lst) / len(lst)


def enum_cb(hwnd, results):
    winlist.append((hwnd, win32gui.GetWindowText(hwnd)))


def compare_list(l1, l2, relate=operator.le):
    if not l1:
        return False
    l3 = []
    for i, val in enumerate(l1, start=0):
        l3.append(relate(val, l2[i]))
    return all(l3)


def color_average(image, x1, y1, x2, y2, compare_images=True, org_image=0):
    average = []
    r, g, b = [], [], []
    if compare_images:
        data = ImageChops.difference(org_image, image).getdata()
    else:
        data = image.getdata()
    for y in range(y1, y2 + 1):
        for x in range(x1, x2 + 1):
            r.append(data[y * 2560 + x][0])
            g.append(data[y * 2560 + x][1])
            b.append(data[y * 2560 + x][2])
    average.append(Avg(r))
    average.append(Avg(g))
    average.append(Avg(b))
    return average


def getScreenShot(window_id):
    win32gui.ShowWindow(window_id, win32con.SW_MAXIMIZE)
    try:
        bbox = win32gui.GetWindowRect(window_id)
    except pywintypes.error:
        return 0
    image = ImageGrab.grab(bbox)
    if not image:
        return 0
    i_width, i_height = image.size
    if i_width != 2650 and i_height != 1440:
        image = image.resize([2560, 1440])
    return image


def click(x, y):
    win32api.SetCursorPos((x, y))
    win32api.mouse_event(win32con.MOUSEEVENTF_LEFTDOWN, x, y, 0, 0)
    win32api.mouse_event(win32con.MOUSEEVENTF_LEFTUP, x, y, 0, 0)


def push_note(message):
    push = str(datetime.now().strftime("%H:%M:%S")) + "    " + str(message)
    device.push_note("CSGO AUTO ACCEPT", push)


def write(message, pushing=False):
    print(datetime.now().strftime("%H:%M:%S") + "    " + message)
    if pushing:
        device.push_note("CSGO AUTO ACCEPT", str(datetime.now().strftime("%H:%M:%S")) + "    " + str(message))


screen_width, screen_height = win32api.GetSystemMetrics(0), win32api.GetSystemMetrics(1)
toplist, winlist = [], []
hwnd = 0

test_for_live_game, test_for_success, debugging, push_active = False, False, False, False
accept_avg = []

img_accept = Image.open("images/accept.jpg")
img_not_searching = Image.open("images/not_searching.jpg")
start_time = time()
write("Ready")

while True:
    if win32api.GetAsyncKeyState(0x78) & 1:  # F9 (ACTIVATE / DEACTIVATE SCRIPT)
        test_for_live_game = not test_for_live_game
        write("TESTING: %s" % test_for_live_game)
        accept_avg = []
        if test_for_live_game:
            playsound('sounds/activated.mp3')
            time_searching = time()
        else:
            playsound('sounds/deactivated.mp3')

    if win32api.GetAsyncKeyState(0x77) & 1:  # F8 (ACTIVATE / DEACTIVATE PUSH NOTIFICATION)
        push_active = not push_active
        write("Pushing: %s" % push_active)

        config = configparser.ConfigParser()
        config.read("config.ini")

        PushBulletDeviceName = config.get('Pushbullet', 'DeviceName')
        PushBulletAPIKey = config.get('Pushbullet', 'API Key')
        device = PushBullet(PushBulletAPIKey).get_device(PushBulletDeviceName)

    if win32api.GetAsyncKeyState(0x76) & 1:  # F7 (DEBUGGING)
        debugging = not debugging
        print("debugging: ", debugging)

    if win32api.GetAsyncKeyState(0x24) & 1:  # POS1/HOME Key
        write("Exiting Script")
        break

    winlist = []
    win32gui.EnumWindows(enum_cb, toplist)
    csgo = [(hwnd, title) for hwnd, title in winlist if 'counter-strike: global offensive' in title.lower()]
    if not csgo:
        continue
    hwnd = csgo[0][0]

    # TESTING HERE
    if win32api.GetAsyncKeyState(0x75) & 1:  # F6, TEST CODE
        write("Executing TestCode")
        test_for_success = not test_for_success
        start_time = time()

    # TESTING ENDS HERE

    if test_for_live_game:
        if time() - start_time < 4:
            continue
        start_time = time()
        img = getScreenShot(hwnd)
        if not img:
            continue
        accept_avg = color_average(img, 1265, 760, 1295, 785, org_image=img_accept)

        if debugging:
            print("Avg: ", accept_avg)
            print(time() - start_time)

    if compare_list(accept_avg, [15, 30, 15]):
        write("Trying to Accept", push_active)

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
            img = getScreenShot(hwnd)
            success_avg = color_average(img, 467, 1409, 1300, 1417, compare_images=False)

            searching_avg = color_average(img, 2435, 55, 2550, 100, org_image=img_accept)
            not_searching_avg = color_average(img, 2435, 55, 2550, 100, org_image=img_not_searching)
            solo_not_searching_avg = color_average(img, 2435, 115, 2555, 135, org_image=img_not_searching)
            no_success_truth = [compare_list(searching_avg, [0.7, 12, 10]), compare_list(not_searching_avg, [8, 9, 9]), compare_list(solo_not_searching_avg, [1, 1.5, 2])]

            if compare_list(success_avg, [17, 100, 150], relate=operator.ge):
                write("Game should have started", push_active)
                took_for_accept = round(time() - start_time, 2)
                took_for_searching = str(round(time() - time_searching, 2))
                print("Took %s s since pressing accept." % took_for_accept)
                print("Took %s s since trying to find a game." % took_for_searching)
                test_for_success = False
                playsound('sounds/done_testing.mp3')

            if any(no_success_truth):
                write("Game doesnt seem to have started. Continuing to search for accept Button!", push_active)
                # write("Searching again: "+str(no_success_truth[0]))
                print("Took: ", round(time() - start_time, 2))
                playsound('sounds/back_to_testing.mp3')
                test_for_success = False
                test_for_live_game = True
                time_searching = time()
        else:
            write("Unknown Error")
            test_for_success = False
            print(success_avg)
            print(searching_avg)
            print(not_searching_avg)
            print(solo_not_searching_avg)
            img.save("Unknown Error.png")
            playsound('sounds/fail.mp3')
            