import queue
import re
from datetime import datetime
from threading import Thread

import requests
from colorit import *

__all__ = ['red', 'orange', 'yellow', 'green', 'blue', 'purple', 'white', 'magenta', 'cyan', 'decolor', 'write', 'message_queue', 'color', 'SendDiscordMessage']


def red(text: str):
    return color(text, (255, 0, 0))


def orange(text: str):
    return color(text, Colors.orange)


def yellow(text: str):
    return color(text, (255, 255, 0))


def green(text: str):
    return color(text, Colors.green)


def blue(text: str):
    return color(text, Colors.blue)


def purple(text: str):
    return color(text, Colors.purple)


def white(text: str):
    return color(text, Colors.white)


def magenta(text: str):
    return color(text, (255, 0, 255))


def cyan(text: str):
    return color(text, (0, 255, 255))


def default_color(text: str):
    return color(text, (204, 204, 204))


def decolor(text: str):
    return decolor_pattern.sub('', text)


def extract_color(text: str):
    color_group = color_extract.search(text)
    if not color_group:
        return 204, 204, 204
    return tuple(map(int, color_group.groups()))


def write(message, *, add_time: bool = True, overwrite: str = '0'):  # last overwrite key used: 11
    message = str(message)
    if add_time:
        colors = decolor_pattern.findall(message)
        if len(colors) == 2:
            # message is in a single color
            r, g, b = extract_color(message)
            message = decolor(message)
        else:
            r = g = b = 204
        message = color(datetime.now().strftime('%H:%M:%S') + ': ' + message, (r, g, b))
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

    overwrite_dict = {'key': overwrite, 'msg': decolor(message), 'end': ending}
    print(message, end=ending)


overwrite_dict = {'key': '0', 'msg': '', 'end': '\n'}
decolor_pattern = re.compile(r'\x1B\[[0-9;]+m')
color_extract = re.compile(r'\x1B\[38;2;(\d{1,3});(\d{1,3});(\d{1,3})m')
if not sys.stdout.isatty():
    console_window = {'prefix': '\r', 'suffix': '', 'isatty': False}
else:
    console_window = {'prefix': '', 'suffix': '\r', 'isatty': True}

message_queue = queue.Queue()


class SendDiscordMessage(Thread):
    def __init__(self, user_id: int, bot_ip: str, bot_port: int, q: queue.Queue):
        self.url = f'http://{bot_ip}:{bot_port}/afk_message'
        super().__init__(name='DiscordMessageRequester', daemon=True)
        self.user_id = user_id
        self.q = q

    def run(self) -> None:
        with requests.Session() as session:
            while True:
                try:
                    item = self.q.get(block=True)
                    msg = f'{datetime.now():%H:%M:%S}: {decolor(str(item))}'
                    data = {'user_id': self.user_id, 'message': msg}
                    session.post(self.url, json=data)
                except queue.Empty:
                    pass
                except requests.ConnectionError:
                    pass
                except BaseException as e:
                    write(red(f'sending message failed with {repr(e)}'))


if __name__ == '__main__':
    write(yellow('Hello World'))
    write(f'{ColorsFG.BrightYellow}Hello World')
    write(f'{ColorsFG.Yellow}Hello World')
    write(f'{ColorsFG.Red}Hello World')
    write(f'{ColorsFG.BrightRed}Hello World')
    write(red('Hello World'))
