from time import sleep, time

import win32api
import win32con
import win32gui
from PIL import Image, ImageChops, ImageGrab


def Avg(lst):
    return sum(lst) / len(lst)


def enum_cb(hwnd, results):
    winlist.append((hwnd, win32gui.GetWindowText(hwnd)))


def click(x, y):
    win32api.SetCursorPos((x, y))
    win32api.mouse_event(win32con.MOUSEEVENTF_LEFTDOWN, x, y, 0, 0)
    win32api.mouse_event(win32con.MOUSEEVENTF_LEFTUP, x, y, 0, 0)


coordinate = x1, y1, x2, y2 = 1265, 760, 1295, 785
screen_width, screen_height = win32api.GetSystemMetrics(0), win32api.GetSystemMetrics(1)
toplist, winlist = [], []
test_for_live_game, accept = False, False
hwnd = 0
start_time = time()

while True:
    if win32api.GetAsyncKeyState(0x78) & 1:
        test_for_live_game = not test_for_live_game
        print("TESTING: ", test_for_live_game)

    if win32api.GetAsyncKeyState(0x2D) & 1:
        break
        print("Exiting Script")

    if test_for_live_game:
        winlist = []
        win32gui.EnumWindows(enum_cb, toplist)
        csgo = [(hwnd, title) for hwnd, title in winlist if 'counter-strike: global offensive' in title.lower()]
        if not csgo:
            continue
        hwnd = csgo[0][0]
        if time() - start_time < 4:
            continue
        start_time = time()
        win32gui.ShowWindow(hwnd, win32con.SW_MAXIMIZE)
        try:
            bbox = win32gui.GetWindowRect(hwnd)
        except pywintypes.error:
            continue
        img = ImageGrab.grab(bbox)
        i_width, i_height = img.size
        if i_width != 2650 and i_height != 1440:
            img = img.resize([2560, 1440])
        img_acc = Image.open("accept.jpg")
        img_difference = ImageChops.difference(img_acc, img)
        img_data = img_difference.getdata()

        # img_difference.show()
        # img_difference.save("dif.png")
        # img.save("img.png")

        pix, color_average = [], []
        r, g, b = [], [], []
        for y in range(y1, y2 + 1):
            for x in range(x1, x2 + 1):
                pix.append(img_data[y * 2560 + x])

        for i in pix:
            r.append(i[0])
            g.append(i[1])
            b.append(i[2])

        color_average.append(Avg(r))
        color_average.append(Avg(g))
        color_average.append(Avg(b))
        for i in color_average:
            accept = True
            if i >= 3:
                accept = False
    if accept:
        # test_for_live_game = False
        for _ in range(5):
            click(int(screen_width / 2), int(screen_height / 1.78))
            sleep(0.5)
        accept = False
