import re

from dataclasses import dataclass

@dataclass()
class Message:
    dead: bool
    team: str
    location: str
    sender: str
    message: str

def extract_chat(filepath):
    chat = re.compile('(?P<dead>\*DEAD\*)?(?:\((?P<team>(?:Counter-)?Terrorist)\))? ?(?P<name>.+)\u200e(?: @ (?P<location>.+))? : +(?P<msg>.+)')
    messages = []
    with open(filepath, 'r', encoding='utf-8') as fp:
        for line in fp:
            r = chat.search(line)
            if r is not None:
                if r.group('team') is not None:
                    team = r.group('team')
                else:
                    team = None
                if r.group('location') is not None:
                    location = r.group('location')
                else:
                    location = None
                msg_dict = {'dead': r.group('dead') is not None, 'team': team, 'location': location, 'sender': r.group('name'), 'message': r.group('msg')}
                messages.append(Message(**msg_dict))
    return messages
