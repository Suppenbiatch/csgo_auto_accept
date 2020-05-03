from time import sleep, time
from datetime import datetime
from playsound import playsound
import win32api
import win32con
import win32gui
from PIL import Image, ImageChops, ImageGrab
import operator


def Avg(lst):
    return sum(lst) / len(lst)


def enum_cb(hwnd, results):
    winlist.append((hwnd, win32gui.GetWindowText(hwnd)))


def color_average(img, x1, y1, x2, y2):
    average = []
    r, g, b = [], [], []
    data = img.getdata()
    for y in range(y1, y2 + 1):
        for x in range(x1, x2 + 1):
            r.append(data[y * 2560 + x][0])
            g.append(data[y * 2560 + x][1])
            b.append(data[y * 2560 + x][2])
    average.append(Avg(r))
    average.append(Avg(g))
    average.append(Avg(b))
    return average


def compare_list(l1, l2, relate):
    if not l1:
        return False
    l3 = []
    for i, val in enumerate(l1, start=0):
        l3.append(relate(val, l2[i]))
    return all(l3)


def getScreenShot(hwnd):
    win32gui.ShowWindow(hwnd, win32con.SW_MAXIMIZE)
    try:
        bbox = win32gui.GetWindowRect(hwnd)
    except pywintypes.error:
        return 0
    image = ImageGrab.grab(bbox)
    i_width, i_height = image.size
    if i_width != 2650 and i_height != 1440:
        image = image.resize([2560, 1440])
    return image


def click(x, y):
    win32api.SetCursorPos((x, y))
    win32api.mouse_event(win32con.MOUSEEVENTF_LEFTDOWN, x, y, 0, 0)
    win32api.mouse_event(win32con.MOUSEEVENTF_LEFTUP, x, y, 0, 0)


screen_width, screen_height = win32api.GetSystemMetrics(0), win32api.GetSystemMetrics(1)
toplist, winlist = [], []
hwnd = 0
test_for_live_game, test_for_success, debugging = False, False, False
accept_avg, success_avg = [], []
img_acc = Image.open("accept.jpg")
start_time = time()
print(datetime.now().strftime("%H:%M:%S"), "    Ready")

while True:
    if win32api.GetAsyncKeyState(0x78) & 1:  # F9
        test_for_live_game = not test_for_live_game
        print(datetime.now().strftime("%H:%M:%S"), "    TESTING: ", test_for_live_game)
        if test_for_live_game:
            playsound('active.mp3')
        else:
            playsound('deactivated.mp3')

    if win32api.GetAsyncKeyState(0x77) & 1:  # F8 (DEBUGGING)
        try:
            print("Avg: ", accept_avg)
        except NameError:
            continue
        img_difference.show()
        img_difference.save("dif.png")

    if win32api.GetAsyncKeyState(0x76) & 1:  # F7 (DEBUGGING)
        debugging = not debugging
        print("debugging: ", debugging)

    if win32api.GetAsyncKeyState(0x75) & 1:  # F6 (DEBUGGING)
        #test_for_success = True
        #start_time = time()
        print("debugging: test_for_success:")

    if win32api.GetAsyncKeyState(0x24) & 1:  # POS1/HOME Key
        print(datetime.now().strftime("%H:%M:%S"), "    Exiting Script")
        break

    winlist = []
    win32gui.EnumWindows(enum_cb, toplist)
    csgo = [(hwnd, title) for hwnd, title in winlist if 'counter-strike: global offensive' in title.lower()]
    if not csgo:
        continue
    hwnd = csgo[0][0]

    if test_for_live_game:
        if time() - start_time < 4:
            continue
        start_time = time()

        img = getScreenShot(hwnd)
        if not img:
            continue
        img_difference = ImageChops.difference(img_acc, img)
        accept_avg = color_average(img_difference, 1265, 760, 1295, 785)

        if debugging:
            print("Avg: ", accept_avg)
            # img.save("img.png")
            # img_difference.save("img_dif.png")

    if compare_list(accept_avg, [15, 30, 15], operator.le):
        print(datetime.now().strftime("%H:%M:%S"), "    Trying to Accept")

        test_for_success = True
        test_for_live_game = False
        start_time = time()

        for _ in range(5):
            click(int(screen_width / 2), int(screen_height / 1.78))
            sleep(0.5)
        print(datetime.now().strftime("%H:%M:%S"), "    Trying to catch a loading map")
        # print(accept_avg)
        accept_avg = []
        # img.save("img_acc.png")
        playsound('beep.mp3')

    if test_for_success:
        if time() - start_time < 30:
            img = getScreenShot(hwnd)
            success_avg = color_average(img, 467, 1409, 1300, 1417)
            if compare_list(success_avg, [17, 100, 150], operator.ge):
                print(datetime.now().strftime("%H:%M:%S"), "    Game should have started")
                print("Took: ", time() - start_time)
                test_for_success = False
                # img.save("img_start.png")
                playsound('2beep.mp3')
        else:
            print(datetime.now().strftime("%H:%M:%S"), "    Game doesnt seem to have started. Continuing to search for accept Button")
            test_for_success = False
            test_for_live_game = True
            playsound('nope.mp3')
