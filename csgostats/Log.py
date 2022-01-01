import base64
import hmac
import pickle
from dataclasses import dataclass
from typing import Union, List
import re
import os


@dataclass
class LogInfo:
    server: str
    map: str
    max_rounds: Union[int, None]
    steam_ids: List[int]
    caller: int = None

    def to_web_request(self, key: bytes, caller: int):
        self.caller = int(caller)
        obj = pickle.dumps(self, protocol=pickle.HIGHEST_PROTOCOL)
        key = hmac.digest(key, obj, digest='sha256')
        b64_key = base64.urlsafe_b64encode(key).decode('ascii')
        b64_obj = base64.urlsafe_b64encode(obj).decode('ascii')
        return {'object': b64_obj, 'key': b64_key}


def to_steam_id(steam_id3, account_id) -> int:
    return int(account_id) * 2 + 76561197960265728 + int(steam_id3)


class LogReader:
    def __init__(self, path):
        self.read_pos = 0
        self.path = path
        self.maxrounds_pattern = re.compile(br'SetConVar: mp_maxrounds = "(\d+)"')
        self.convar_pattern = re.compile(br'SetConVar:\s+([^ =]+) = "(.+)"')
        self.status_pattern = re.compile(br'Connected to =\[[a-zA-Z0-9:]+]:\d+?[\r\n]+.+?[\r\n]+#end\r?\n',
                                         flags=re.DOTALL)
        self.player_pattern = re.compile(
            r'#\s+(\d+)\s(\d+)\s"(.+?)"\sSTEAM_\d:(\d:\d+)\s(\d+:\d+)\s(\d+)\s(\d+)\s([a-zA-Z]+)\s(\d+)')

    def get_log_info(self):
        with open(self.path, 'rb') as fp:
            fp.seek(0, os.SEEK_END)
            end = fp.tell()
            if self.read_pos > end:
                self.read_pos = 0
            fp.seek(self.read_pos, os.SEEK_SET)
            data = fp.read()

            max_rounds_obj = self.maxrounds_pattern.search(data)
            max_rounds = int(max_rounds_obj.group(1)) if max_rounds_obj is not None else None
            status_obj = self.status_pattern.search(data)
            if status_obj is not None:
                self.read_pos += status_obj.regs[0][1]
                status = [line.decode('utf-8') for line in status_obj.group(0).splitlines()]
            else:
                status = None
            if status is None:
                return None
            csv_lines = [line for line in status if line.startswith('#')]
            players = []
            header = csv_lines[0].lstrip('# ').split(' ')
            header.insert(1, 'num')
            for player in csv_lines[1:]:
                player_data = self.player_pattern.search(player)
                if player_data is not None:
                    players.append(dict(zip(header, player_data.groups())))
            steam_ids = []
            for player_dict in players:
                steam3, align_num = player_dict['uniqueid'].split(':')
                steam_id = to_steam_id(steam3, align_num)
                steam_ids.append(steam_id)
            server = _map = None
            for line in status:
                if server is None:
                    server = re.search(r'hostname: Valve CS:GO (.+ Server)', line)
                    server = server.group(1) if server is not None else None
                if _map is None:
                    _map = re.search(r'map\s+:\s(.+)', line)
                    _map = _map.group(1) if _map is not None else None
            return LogInfo(server, _map, max_rounds, steam_ids)


if __name__ == '__main__':
    reader = LogReader(r"C:\Users\Suppe\Desktop\status.txt")
    data = reader.get_log_info()
    print(data)
