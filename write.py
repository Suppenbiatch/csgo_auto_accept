import re
import sys
from datetime import datetime
from typing import Dict, Union, Tuple

from color import FgColor, colorize
from pushbullet import pushbullet


def write(message, add_time: bool = True, push: int = 0, push_now: bool = False, output: bool = True, overwrite: str = '0', color: FgColor = FgColor.Null):  # last overwrite key used: 11
    message = str(message)
    push_message = decolor.sub('', message)
    if output:
        if add_time:
            message = datetime.now().strftime('%H:%M:%S') + ': ' + message
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

        overwrite_dict = {'key': overwrite, 'msg': decolor.sub('', message), 'end': ending}

        message = colorize(10, 10, color, message)
        print(message, end=ending)

    if push >= 3:
        if message:
            pushbullet_dict['note'] = pushbullet_dict['note'] + str(push_message.strip('\r').strip('\n')) + '\n'
        if push_now:
            pushbullet_dict['device'].push_note('CSGO AUTO ACCEPT', pushbullet_dict['note'])
            pushbullet_dict['note'] = ''


overwrite_dict = {'key': '0', 'msg': '', 'end': '\n'}
if not sys.stdout.isatty():
    console_window = {'prefix': '\r', 'suffix': '', 'isatty': False}
else:
    console_window = {'prefix': '', 'suffix': '\r', 'isatty': True}

decolor = re.compile(r'\033\[[0-9;]+m')

pushbullet_dict: Dict[str, Union[str, int, pushbullet.Device, Tuple[str, str, str, str]]] = \
    {'note': '', 'urgency': 0, 'device': None, 'push_info': ('not active', 'on if accepted', 'all game status related information', 'all information (game status/csgostats.gg information)')}
