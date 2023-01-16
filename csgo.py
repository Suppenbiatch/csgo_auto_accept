import http.server
import json
import os.path
import queue
import re
import socketserver
import statistics
import time
from dataclasses import dataclass, field
from datetime import datetime
from threading import Thread
from typing import List, Union
from urllib.parse import unquote_plus

import win32api
import win32con
import win32gui
import websocket
from pytz import utc

import cs
from ConsoleInteraction import TelNetConsoleReader
from csgostats.csgostats_updater import CSGOStatsUpdater
from objects.Screenshot import grep_and_send
from write import *
from utils import wait_until


class WebHookHandler(http.server.BaseHTTPRequestHandler):
    def log_request(self, code='-', size='-'):
        return

    def _set_response(self):
        self.send_response(200)
        self.send_header('Content-type', 'text/plain')
        self.end_headers()

    def do_GET(self):
        self._set_response()
        webhook_parser.queue.put(self.parse_path())

    def parse_path(self):
        path = re.search(r'/([^/?&]+)', self.path)
        if path is None:
            path = ''
        else:
            path = path.group(1)
        items = re.findall(r'[?&]([^=]+)=([^&]+)', self.path)
        if len(items) != 0:
            query = dict(items)
            for key, value in query.items():
                _str = unquote_plus(value)
                try:
                    value = json.loads(_str)
                except json.JSONDecodeError:
                    value = _str
                query[key] = value
        else:
            query = {}
        return RequestItem(path, query)


class WebServer(Thread):
    def __init__(self, ip: str, port: int):
        self.ip = ip
        self.port = port
        super().__init__(name='WebHookServer', daemon=True)

    def run(self) -> None:
        with socketserver.TCPServer((self.ip, self.port), WebHookHandler) as httpd:
            # print("serving at port", PORT)
            httpd.serve_forever()


class ResultParser(Thread):
    def __init__(self):
        self.queue = queue.Queue()
        self.launch = time.time()
        super().__init__(name='ResultParser', daemon=True)

    def run(self) -> None:
        while True:
            try:
                item: RequestItem = self.queue.get(block=True)
                if item.path == 'minimize':
                    hk_minimize_csgo()
                elif item.path == 'activate':
                    hk_activate()
                elif item.path == 'pushbullet':
                    cs.activate_afk_message()
                elif item.path == 'upload':
                    hk_upload_match()
                elif item.path == 'switch_accounts':
                    hk_switch_accounts()
                elif item.path == 'mute':
                    cs.mute_csgo(2)
                elif item.path == 'discord_toggle':
                    hk_discord_toggle()
                elif item.path == 'end':
                    query = item.query
                    delay = int(query.get('delay', 0))
                    if (time.time() - self.launch) < delay:
                        write(orange('canceled exit request because of delay parameter'))
                        continue
                    hk_kill_main_loop()
                elif item.path == 'fetch_status':
                    hk_fetch_status()
                elif item.path == 'devmode':
                    hk_activate_devmode()
                elif item.path == 'console':
                    hk_console(item.query)
                elif item.path == 'autobuy':
                    hk_autobuy()
                elif item.path == 'seek':
                    new_pos, old_pos = cs.log_reader.re_seek()
                    write(f're-sought from {old_pos:,} to {new_pos:,}')
                elif item.path == 'afk':
                    cs.anti_afk_tel(telnet, is_active=False)  # activate anti afk
                    afk.anti_afk_active = True
                elif item.path == 'force_minimize':
                    query = list(item.query.values())
                    if len(query) == 0:
                        continue
                    if query[0].lower().startswith('min'):
                        hk_minimize_csgo(force='min')
                    elif query[0].lower().startswith('max'):
                        hk_minimize_csgo(force='max')
                elif item.path == 'clear_queue':
                    global retryer
                    if len(retryer) == 0:
                        continue
                    elif len(retryer) == 1:
                        write(orange(f'Removed 1 match from queue'))
                    else:
                        write(orange(f'Removed {len(retryer)} matches from queue'))
                    retryer = []
                    continue
                elif item.path == 'update_sounds':
                    if cs.cfg.web_sounds is False:
                        write(yellow('Updating sounds with "Use Web Sounds" set to false will not do anything'))
                        continue
                    cs.sounds = cs.get_sounds()
                elif item.path == 'toggle_autobuy':
                    truth.autobuy_active = not truth.autobuy_active
                    if truth.autobuy_active:
                        write(purple(f'AutoBuy enabled'))
                    else:
                        write(purple(f'AutoBuy disabled'))
                elif item.path == 'fullbuy':
                    kevlar = str(item.query.get('kevlar', None))
                    if kevlar.lower() in ('true', 't', 'y', 'yes', '1'):
                        prefer_kevlar = True
                    else:
                        prefer_kevlar = False
                    hk_fullbuy(prefer_kevlar=prefer_kevlar)
            except BaseException as e:
                write(red(f'Ignoring Exception in ResultParser - {repr(e)}'))


def on_ws_message(ws, message):
    data = json.loads(message)
    if data['action'] == 'chat_message':
        msg = data.get('message', '')
        if not msg.startswith('.'):
            return
        msg = msg.lstrip('.')
        r = msg.split('.', maxsplit=1)
        target = r[1] if len(r) == 2 else ''
        command = r[0].rstrip(' ')

        if not cs.account.name.lower().startswith(target):
            ws_send({'action': 'acknowledge', 'executed': False, 'reason': 'target did not match'})
            return

        if command == 'fullbuy':
            t = Thread(target=hk_fullbuy, args=(True,), daemon=True)
            t.start()
        elif command == 'grep':
            url = f'http://{cs.cfg.server_ip}:{cs.cfg.server_port}/recv'
            t = Thread(target=grep_and_send, args=(url,))
            t.start()
        elif command == 'afk':
            cs.anti_afk_tel(telnet, is_active=False)  # activate anti afk
            afk.anti_afk_active = True
        elif command.lower().startswith(('exit', 'disconnect')):
            write(red(f'Skipped {command}'))
            ws_send({'action': 'acknowledge', 'executed': False, 'reason': 'Command ignored'})
            return
        else:
            commands = command.split(';')
            t = Thread(target=execute_chatcommand, args=(commands,))
            t.start()
        ws_send({'action': 'acknowledge', 'executed': True})


def on_ws_error(ws, error):
    write(red('WebSocket Error: ' + repr(error)))


def on_ws_close(ws, close_status_code, close_msg):
    ws_sender_thread.is_ready = False
    write(red("WebSocket connection closed"))


def on_ws_open(ws):
    name = f'{os.getlogin()}@{os.environ["COMPUTERNAME"]}'
    name = name.encode(encoding='utf-8').decode(encoding='ascii', errors='ignore').lower()
    data = {'action': 'set_nick', 'new_name': f'{name}_script'}
    write(green(f'WebSocket connection established as "{name}"'))
    ws_sender_thread.websocket_connection = ws
    ws_sender_thread.is_ready = True
    ws_send(data)


ws_con = websocket.WebSocketApp(f"ws://{cs.cfg.server_ip}:{cs.cfg.server_port}/chat",
                                on_open=on_ws_open,
                                on_message=on_ws_message,
                                on_error=on_ws_error,
                                on_close=on_ws_close)

class WebSocketSender(Thread):
    def __init__(self, ws: websocket.WebSocketApp):
        self.websocket_connection: websocket.WebSocketApp = ws
        super().__init__()
        self.daemon = True
        self.name = 'WebSocketSender'
        self.queue = queue.Queue()
        self.is_ready = False
        self.later = []

    def status(self):
        return self.is_ready

    def send(self, data: Union[str, dict]):
        if isinstance(data, str):
            data = {'message': data}
        elif not isinstance(data, dict):
            return
        if self.is_ready is False:
            ts = round(datetime.now(tz=utc).timestamp() * 1000)
            data['script_ts'] = ts
            self.later.append(data)
            return
        self.queue.put(data)

    def run(self) -> None:
        while True:
            while not self.is_ready:
                time.sleep(0.2)
            data = self.queue.get(block=True, timeout=None)
            if data.get('action') == 'player_status':
                data_hash = hash(json.dumps(data['data'], ensure_ascii=True, sort_keys=True))
            else:
                data_hash = None
            ts = round(datetime.now(tz=utc).timestamp() * 1000)
            default_data = {'action': 'script_action', 'script_ts': ts, 'steam_id': cs.steam_id, 'player': cs.account.name}
            send_data = {**default_data, **data}
            if data_hash is not None:
                send_data['hash'] = data_hash
            try:
                self.websocket_connection.send(json.dumps(send_data))
                if self.later:
                    for item in self.later:
                        self.queue.put(item)
                    self.later = []
            except websocket.WebSocketConnectionClosedException:
                self.later.append(data)


@dataclass()
class RequestItem:
    path: str
    query: dict


@dataclass()
class Truth:
    test_for_accept_button: bool = False
    test_for_warmup: bool = False
    test_for_success: bool = False
    still_in_warmup: bool = False
    test_for_server: bool = False
    first_freezetime: bool = True
    game_over: bool = False
    monitoring_since_start: bool = False
    players_still_connecting: bool = False
    first_game_over: bool = True
    disconnected_form_last: bool = False
    c4_round_first: bool = True
    steam_error: bool = False
    game_minimized_freezetime: bool = False
    game_minimized_warmup: bool = False
    discord_output: bool = True
    gsi_first_launch: bool = True
    upload_thread_active: bool = False
    first_autobuy: bool = True
    autobuy_active: bool = True


@dataclass()
class Time:
    csgostats_retry: float = time.time()
    search_started: float = time.time()
    console_read: float = time.time()
    timed_execution_time: float = time.time()
    match_accepted: float = time.time()
    match_started: float = time.time()
    freezetime_started: float = time.time()
    join_warmup_time: float = 0.0
    warmup_seconds: int = 0
    warmup_started: float = time.time()


@dataclass()
class AFK:
    time: float = time.time()
    still_afk: List[float] = field(default_factory=list)
    start_time: float = time
    seconds_afk: float = 0.0
    per_round: float = 0.0
    steam_id: int = 0
    state: dict = field(default_factory=dict)
    round_values: List[float] = field(default_factory=list)
    anti_afk_active: bool = False
    since_last_afk: float = time


@dataclass()
class WindowStatus:
    server_found: int = 2
    in_game: int = 0


@dataclass()
class GameState:
    map_phase: str = None
    round_phase: str = None


@dataclass()
class Scoreboard:
    CT: int = 0
    T: int = 0
    last_round_info: dict = None
    last_round_winner: str = ''
    last_round_key: str = '0'
    last_round_text: str = ''
    extra_round_info: str = ''
    max_rounds: int = 30
    buy_time: int = 20
    freeze_time: int = 15
    player: dict = None
    weapons: List[dict] = None
    c4: str = ''
    total_score: int = 0
    raw_team: str = ''
    raw_opposing_team = ''
    team: str = ''
    opposing_team: str = ''
    current_weapons: List[dict] = None  # same as weapons, will update until player has c4 or freeze time is over
    has_c4: bool = False
    money: int = 0
    round_message: str = ''


def hk_activate():
    if game_state.map_phase not in ['live', 'warmup']:
        truth.test_for_server = not truth.test_for_server
        write(magenta(f'Looking for match: {truth.test_for_server}'), overwrite='1')
        if truth.test_for_server:
            cs.sound_player.play(cs.sounds.activated, block=False)
            times.search_started = time.time()
            cs.mute_csgo(1)
        elif not truth.test_for_server:
            cs.sound_player.play(cs.sounds.deactivated, block=False)
            cs.mute_csgo(0)


# noinspection PyShadowingNames
def hk_upload_match():
    write('Uploading / Getting status on newest match')
    t = Thread(target=upload_matches, args=(True, None), name='UploadThread')
    t.start()


def hk_switch_accounts():
    cs.current_steam_account += 1
    if cs.current_steam_account > len(cs.accounts) - 1:
        cs.current_steam_account = 0
    cs.account = cs.accounts[cs.current_steam_account]
    cs.steam_id = cs.account.steam_id
    cs.check_userdata_autoexec(cs.account.steam_id_3)
    updater.new_account(cs.account)
    write(f'current account is: {cs.account.name}', add_time=False, overwrite='3')


def hk_discord_toggle():
    truth.discord_output = not truth.discord_output
    if truth.discord_output:
        write(green('Discord output activated'), add_time=False, overwrite='13')
    else:
        write(red('Discord output deactivated'), add_time=False, overwrite='13')
    return


def hk_kill_main_loop():
    global running
    running = False


def hk_minimize_csgo(force: str = None):
    global hwnd, afk, telnet
    if hwnd == 0:
        return
    try:
        current_placement = win32gui.GetWindowPlacement(hwnd)
    except BaseException as e:
        if e.args[1] == 'GetWindowPlacement':
            return
        else:
            print(f'failed mini/maximizing csgo with {e}')
            return

    if force == 'min':
        cs.minimize_csgo(hwnd)
        return
    elif force == 'max':
        win32gui.ShowWindow(hwnd, win32con.SW_NORMAL)
        return

    if current_placement[1] == 2:
        if afk.anti_afk_active:
            cs.anti_afk_tel(telnet, is_active=True)
            afk.anti_afk_active = False

        win32gui.ShowWindow(hwnd, win32con.SW_NORMAL)
    else:
        cs.minimize_csgo(hwnd)
    return


def hk_fetch_status():
    global hwnd, telnet
    if hwnd == 0:
        return
    telnet.send('status')
    thread_ = cs.MatchRequest()
    thread_.start()


def hk_activate_devmode():
    global hwnd, telnet
    if hwnd == 0:
        return
    telnet.send('sv_max_allowed_developer 1')
    telnet.send('developer 1')


def hk_console(query: dict):
    global hwnd, telnet
    if hwnd == 0:
        return
    commands = query.get('input', None)
    if commands is None:
        return
    if not isinstance(commands, list):
        raise TypeError(f'Expected list of commands got {type(commands)}')
    for command in commands:
        telnet.send(command)
    return


def hk_autobuy():
    global gsi_server, scoreboard
    if cs.account.autobuy is None:
        return
    p = gsi_server.get_info('player')
    try:
        if p and p['steamid'] == cs.steam_id:
            scoreboard.player = p
        else:
            return
    except NameError:
        # globlus bad
        return
    try:
        scoreboard.weapons = list(scoreboard.player['weapons'].values())
        scoreboard.money = scoreboard.player['state']['money']
        scoreboard.raw_team = scoreboard.player['team']
    except TypeError:
        return
    if any(weapon.get('type') in main_weapons for weapon in scoreboard.weapons):
        return
    for player_money, auto_script, target_team in cs.account.autobuy:
        if scoreboard.money >= player_money and scoreboard.raw_team in target_team:
            telnet.send(auto_script)
            truth.first_autobuy = False
            break


def hk_fullbuy(prefer_kevlar: bool = False):
    global gsi_server
    p = gsi_server.get_info('player')
    if not p or p['steamid'] != cs.steam_id:
        return
    _team = p['team']
    if _team is None:
        return
    _inv = list(p['weapons'].values())
    _state = p['state']
    if not isinstance(_state, dict):
        return
    data = {'team': _team, 'inventory': _inv, 'state': _state, 'kevlar': prefer_kevlar}
    try:
        command = cs.get_fullbuy_from_bot(data)
    except BaseException as e:
        write(red(f'failed to get "fullbuy" options from server - {e.__class__.__name__}'))
        return
    if command is None:
        return
    telnet.send(command)


def execute_chatcommand(commands: list[str]):
    for command in commands:
        if not command.startswith('!'):
            if command.lower().startswith(('exit', 'disconnect')):
                write(red(f'Caught {command} - Ignored'))
                continue
            telnet.send(command)
            continue
        if command.startswith('!delay'):
            delay = int(re.sub(r'\D', '', command))
            time.sleep(delay / 1000)


def gsi_server_status():
    global gsi_server
    if gsi_server.running:
        write(green('CS:GO GSI Server status: running'), overwrite='8')
    else:
        write(green('CS:GO GSI Server status: not running'), overwrite='8')
    return gsi_server.running


def upload_matches(look_for_new: bool = True, stats=None):
    global retryer
    if truth.upload_thread_active:
        write(magenta('Another Upload-Thread is still active'))
        return
    truth.upload_thread_active = True
    if look_for_new is True:
        try:
            latest_sharecode = cs.get_old_sharecodes(-1)
        except ValueError:
            write(red('no match token in config, aborting'))
            truth.upload_thread_active = False
            return

        new_sharecodes = cs.get_new_sharecodes(latest_sharecode[0], stats=stats)

        for new_code in new_sharecodes:
            retryer.append(new_code) if new_code['sharecode'] not in [old_code['sharecode'] for old_code in retryer] else retryer

    times.csgostats_retry = time.time()
    if not retryer:
        write(yellow('no new sharecodes found, aborting'))
        truth.upload_thread_active = False
        return
    retryer = updater.update_csgo_stats(retryer, discord_output=truth.discord_output)
    times.csgostats_retry = time.time()
    truth.upload_thread_active = False
    return


def read_telnet():
    console_strs = []
    while not telnet.received.empty():
        console_strs.append(telnet.received.get_nowait())

    with open(os.path.join(cs.path_vars.appdata, 'console.log'), 'a', encoding='utf-8') as fp:
        for line in console_strs:
            fp.write(f'{line}\n')

    return cs.ConsoleLog.from_log(console_strs)


afk = AFK()
truth = Truth()
times = Time()
scoreboard = Scoreboard()
game_state = GameState()
truth.autobuy_active = cs.cfg.autobuy_active

join_dict = {'t_full': False, 'ct_full': False}
team = yellow('Unknown')
main_weapons = ['Machine Gun', 'Rifle', 'Shotgun', 'SniperRifle', 'Submachine Gun']
player_stats = {}

window_enum = cs.WindowEnumerator('csgo.exe', 'counter-strike', sleep_interval=0.75)
window_enum.start()
gsi_server = window_enum.restart_gsi_server(None)

afk_sender = SendDiscordMessage(cs.cfg.discord_user_id, cs.cfg.server_ip, cs.cfg.server_port)
afk_sender.start()

telnet = TelNetConsoleReader(cs.cfg.telnet_ip, cs.cfg.telnet_port)  # start thread when game is running

hwnd_old = 0
window_status = WindowStatus()

updater = CSGOStatsUpdater(cs.cfg, cs.account, cs.path_vars.db)
retryer = []
server_online = updater.check_status()
if server_online:
    write(green('CSGO Discord Bot ONLINE'))
else:
    write(red('CSGO Discord Bot OFFLINE'))

webhook = WebServer(cs.cfg.webhook_ip, cs.cfg.webhook_port)
webhook_parser = ResultParser()
webhook_parser.start()
webhook.start()

cs.mute_csgo(0)

ws_thread = Thread(target=ws_con.run_forever, kwargs={'reconnect': 5}, daemon=True, name='WebSocketThread')
ws_thread.start()

ws_sender_thread = WebSocketSender(ws_con)
ws_sender_thread.start()
ws_send = ws_sender_thread.send

if not wait_until(ws_sender_thread.status, 5.0):
    write(red('WebSocket did not respond within 5 seconds!'))


write(green('READY'))
running = True

while running:
    if retryer and not truth.upload_thread_active:
        if time.time() - times.csgostats_retry > cs.cfg.auto_retry_interval:
            t = Thread(target=upload_matches, args=(False, None), name='UploadThread')
            t.start()

    hwnd = window_enum.hwnd

    if hwnd != 0 and hwnd_old != hwnd:

        truth.test_for_server = False
        hwnd_old = hwnd
        cs.steam_id = cs.get_current_steam_user()
        try:
            cs.account = [account for account in cs.accounts if cs.steam_id == account.steam_id][0]
            cs.check_userdata_autoexec(cs.account.steam_id_3)
        except IndexError:
            write('Account is not in the config.ini!\nScript will not work properly!', add_time=False, overwrite='9')
            cs.sound_player.play(cs.sounds.fail, block=False)
            exit('Update config.ini!')
        updater.new_account(cs.account)
        write(f'Current account is: {cs.account.name}', add_time=False, overwrite='9')
        ws_send(f'Game launched')

        if cs.check_for_forbidden_programs(window_enum.window_ids):
            write('A forbidden program is still running...', add_time=False)
            cs.sound_player.play(cs.sounds.fail, block=False)

        gsi_server = window_enum.restart_gsi_server(gsi_server)
        truth.gsi_first_launch = True

    if truth.gsi_first_launch and gsi_server.running:
        write(green('GSI Server running'), overwrite='8')
        ws_send('GSI Server running')
        truth.gsi_first_launch = False

    if not gsi_server.running:
        time.sleep(cs.sleep_interval)
        continue

    if telnet.closed is None:
        telnet.start()
        while True:
            if telnet.closed is False:
                write(green('TelNet connection established'))
                ws_send('TelNet connection established')
                telnet.send('sv_max_allowed_developer 1')
                telnet.send('developer 1')
                break
            elif telnet.closed is True:
                write(red(f'Failed to connect to the csgo client, make sure -netconport {cs.cfg.telnet_port} is set as a launch option'))
                cs.sound_player.play(cs.sounds.fail)
                exit('Check launch options')
            time.sleep(0.2)
    elif telnet.closed is True:
        write(red('TelNet connection closed, assuming game closed'))
        ws_send('TelNet connection closed')
        gsi_server = window_enum.restart_gsi_server(gsi_server)
        telnet = TelNetConsoleReader(cs.cfg.telnet_ip, cs.cfg.telnet_port)

    console = read_telnet()

    if console.messages:
        for author, msg in console.messages:
            if not msg.startswith('.'):
                continue
            msg = msg.lstrip('.')
            r = msg.split('.', maxsplit=1)
            target = r[1] if len(r) == 2 else ''
            command = r[0].rstrip(' ')

            if not cs.account.name.lower().startswith(target):
                continue
            if command == 'fullbuy':
                t = Thread(target=hk_fullbuy, args=(True,), daemon=True)
                t.start()
            elif command.lower().startswith(('exit', 'disconnect')):
                write(red(f'Skipped {command}'))
            else:
                commands = command.split(';')
                t = Thread(target=execute_chatcommand, args=(commands,))
                t.start()

    if console.update:
        if console.update[-1] == '1':
            if not truth.test_for_server:
                truth.test_for_server = True
                times.search_started = time.time()
                write(magenta(f'Looking for match: {truth.test_for_server}'), overwrite='1')
                ws_send(f'Looking for match: {truth.test_for_server}')
            cs.sound_player.play(cs.sounds.activated, block=False)
            cs.mute_csgo(1)
        elif console.update[-1] == '0' and truth.test_for_server:
            cs.mute_csgo(0)

    if truth.test_for_server:
        if console.server_found:
            cs.sound_player.play(cs.sounds.server_found, block=False)
            ws_send('Server found')
            truth.test_for_success = True
        if console.server_ready:
            truth.test_for_accept_button = True
            cs.sleep_interval = cs.sleep_interval_looking_for_accept
            window_status.server_found = win32gui.GetWindowPlacement(hwnd)[1]
            win32gui.ShowWindow(hwnd, win32con.SW_MAXIMIZE)

    if truth.test_for_accept_button:
        img = cs.get_screenshot(hwnd, (1300, 550, 1310, 570))
        accept_avg = cs.color_average(img, [(76, 175, 80), (90, 203, 94)])
        if cs.relate_list(accept_avg, (2, 2, 2)):
            truth.test_for_accept_button = False
            cs.sleep_interval = cs.cfg.sleep_interval

            current_cursor_position = win32api.GetCursorPos()
            for _ in range(5):
                win32gui.ShowWindow(hwnd, win32con.SW_MAXIMIZE)
                cs.click((int(win32api.GetSystemMetrics(0) / 2), int(win32api.GetSystemMetrics(1) / 2.4)))
            if window_status.server_found == 2:  # was minimized when a server was found
                time.sleep(0.075)
                cs.minimize_csgo(hwnd)
            else:
                cs.set_mouse_position(current_cursor_position)

            cs.sound_player.play(cs.sounds.button_found, block=False)
            ws_send('Accept Button found and clicked')

    if truth.test_for_accept_button or truth.test_for_success:
        if console.msg is not None:
            if 'Match confirmed' in console.msg:
                write(green(f'All Players accepted - Match has started - Took {cs.timedelta(times.search_started)} since start'), add_time=False, overwrite='11')
                ws_send('All Player accepted')
                truth.test_for_warmup = True
                truth.first_game_over = True
                truth.game_over = False

                truth.disconnected_form_last = False
                truth.first_freezetime = False
                truth.test_for_server = False
                truth.test_for_accept_button = False

                cs.sleep_interval = cs.cfg.sleep_interval
                truth.test_for_success = False
                truth.monitoring_since_start = True
                cs.mute_csgo(0)
                cs.sound_player.play(cs.sounds.all_accepted, block=False)
                times.match_accepted = time.time()

                afk.time = times.match_accepted
                afk.start_time = times.match_accepted
                afk.seconds_afk = 0.0
                afk.round_values = []

            if list((item for item in console.msg for cmp in ('Other players failed to connect', 'Failed to ready up') if cmp in item)):
                truth.test_for_server = True
                truth.test_for_accept_button = False
                cs.sleep_interval = cs.cfg.sleep_interval
                truth.test_for_success = False
                if 'Other players failed to connect' in console.msg:
                    msg = red('Match has not started! Continuing to search for a Server!')
                    write(msg, overwrite='11')
                    if cs.afk_message is True:
                        afk_sender.queue.put(msg)
                    ws_send('Players failed to accept')
                    cs.sound_player.play(cs.sounds.not_all_accepted, block=False)
                    cs.mute_csgo(1)
                elif 'Failed to ready up' in console.msg:
                    msg = red('You or a group member failed to accept! Restart searching!')
                    write(msg, overwrite='11')
                    ws_send(decolor(msg))
                    if cs.afk_message is True:
                        afk_sender.queue.put(msg)
                    cs.sound_player.play(cs.sounds.accept_failed)
                    cs.mute_csgo(0)

        if console.players_accepted is not None:
            for i in console.players_accepted:
                i = i.split('/')
                players_accepted = str(int(i[1]) - int(i[0]))
                write(f'{players_accepted} Players of {i[1]} already accepted.', add_time=False, overwrite='11')

    if truth.players_still_connecting:
        # not working without developer 1
        if console.lobby_data is not None:
            lobby_data = '\n'.join(console.lobby_data)
            lobby_info = cs.lobby_info.findall(lobby_data)
            lobby_data = [(info, int(num.strip("'\n"))) for info, num in lobby_info]
            for i in lobby_data:
                if i[0] == 'Players':
                    write(f'{i[1]} players joined.', add_time=False, overwrite='7')
                if i[0] == 'TSlotsFree' and i[1] == 0:
                    join_dict['t_full'] = True
                if i[0] == 'CTSlotsFree' and i[1] == 0:
                    join_dict['ct_full'] = True
                if join_dict['t_full'] and join_dict['ct_full']:
                    best_of = red(f"MR{scoreboard.max_rounds}")
                    msg = f'Server full, All Players connected. ' \
                          f'{best_of}, ' \
                          f'Took {cs.timedelta(times.warmup_started)} since match start.'
                    write(msg, overwrite='7')
                    if cs.afk_message is True:
                        afk_sender.queue.put(msg)
                    cs.sound_player.play(cs.sounds.minute_warning, block=True)
                    truth.players_still_connecting = False
                    join_dict['t_full'], join_dict['ct_full'] = False, False
                    break

    if console.server_abandon is not None:
        if list((msg for msg in console.server_abandon if 'Disconnect' in msg)):
            if not truth.game_over:
                write(red('Server disconnected'))
                ws_send('Server disconnected')
                cs.sound_player.play(cs.sounds.fail, block=False)
            gsi_server = window_enum.restart_gsi_server(gsi_server)

            truth.disconnected_form_last = True
            truth.players_still_connecting = False
            truth.game_minimized_warmup = False
            truth.game_minimized_freezetime = False

            afk.time = time.time()
            hk_activate_devmode()

    game_state = GameState(gsi_server.get_info('map', 'phase'), gsi_server.get_info('round', 'phase'))

    if console.server_settings is not None:
        try:
            scoreboard.max_rounds = [int(re.sub(r'\D', '', line)) for line in console.server_settings if 'maxrounds' in line][0]
        except IndexError:
            pass
        try:
            scoreboard.buy_time = [int(re.sub(r'\D', '', line)) for line in console.server_settings if 'buytime' in line][0]
        except IndexError:
            pass
        try:
            scoreboard.freeze_time = [int(re.sub(r'\D', '', line)) for line in console.server_settings if 'freezetime' in line][0]
        except IndexError:
            pass

    if truth.first_freezetime:
        if game_state.map_phase == 'live' and game_state.round_phase == 'freezetime':

            truth.first_game_over = True
            truth.game_over = False
            truth.disconnected_form_last = False
            truth.first_autobuy = True
            truth.first_freezetime = False

            times.freezetime_started = time.time()
            scoreboard.CT = gsi_server.get_info('map', 'team_ct')['score']
            scoreboard.T = gsi_server.get_info('map', 'team_t')['score']
            scoreboard.last_round_info = gsi_server.get_info('map', 'round_wins')
            scoreboard.player = gsi_server.get_info('player')

            scoreboard.money = scoreboard.player['state']['money']
            money = f'{scoreboard.money:,}$'

            scoreboard.weapons = list(scoreboard.player['weapons'].values())
            scoreboard.c4 = ' - Bomb Carrier' if 'weapon_c4' in [weapon['name'] for weapon in scoreboard.weapons] else ''
            scoreboard.total_score = scoreboard.CT + scoreboard.T

            scoreboard.raw_team = scoreboard.player['team']
            scoreboard.raw_opposing_team = 'CT' if scoreboard.raw_team == 'T' else 'T'

            scoreboard.team = red('T') if scoreboard.raw_team == 'T' else cyan('CT')
            scoreboard.opposing_team = cyan('CT') if scoreboard.raw_team == 'T' else red('T')

            afk.round_values.append(round(afk.seconds_afk, 3))

            try:
                afk.per_round = statistics.mean(afk.round_values)
            except statistics.StatisticsError:
                afk.per_round = 0.0
            afk.seconds_afk = 0.0

            try:
                scoreboard.last_round_key = list(scoreboard.last_round_info.keys())[-1]
                scoreboard.last_round_winner = scoreboard.last_round_info[scoreboard.last_round_key].split('_')[0].upper()
                if int(scoreboard.last_round_key) == scoreboard.max_rounds / 2:
                    scoreboard.last_round_winner = 'T' if scoreboard.last_round_winner == 'CT' else 'CT'
                scoreboard.last_round_text = f'{scoreboard.team} {green("won")} the last round' \
                    if scoreboard.raw_team == scoreboard.last_round_winner \
                    else f'{scoreboard.team} {yellow("lost")} the last round'

            except AttributeError:
                scoreboard.last_round_text = f'You {scoreboard.team}, no info on the last round'

            if scoreboard.total_score == scoreboard.max_rounds / 2 - 1:
                scoreboard.extra_round_info = f' - {yellow("Half-Time")}'
                cs.sound_player.play(cs.sounds.ding, block=True)
            elif scoreboard.CT == scoreboard.max_rounds / 2 or scoreboard.T == scoreboard.max_rounds / 2:
                scoreboard.extra_round_info = f' - {yellow("Match Point")}'

            else:
                scoreboard.extra_round_info = ''

            write(f'Freeze Time - {scoreboard.last_round_text} - {getattr(scoreboard, scoreboard.raw_team):02d}:{getattr(scoreboard, scoreboard.raw_opposing_team):02d}'
                  f'{scoreboard.extra_round_info}{scoreboard.c4} - AFK: {cs.timedelta(seconds=afk.per_round)} - {purple(money)}',
                  overwrite='7')

            if win32gui.GetWindowPlacement(hwnd)[1] == 2:
                truth.game_minimized_freezetime = True
                cs.sound_player.play(cs.sounds.ready, block=True)

        elif game_state.map_phase == 'live' and gsi_server.get_info('player', 'steamid') == cs.steam_id:
            player_stats = gsi_server.get_info('player', 'match_stats')

    elif game_state.map_phase == 'live' and game_state.round_phase != 'freezetime':
        truth.first_freezetime = True
        truth.c4_round_first = True
        if time.time() - times.freezetime_started >= 20 and win32gui.GetWindowPlacement(hwnd)[1] == 2:
            cs.sound_player.play(cs.sounds.ready, block=False)

    if truth.game_minimized_warmup:
        try:
            best_of = red(f"MR{scoreboard.max_rounds}")
            message = f'Warmup is over! Map: {green(" ".join(gsi_server.get_info("map", "name").split("_")[1:]).title())}, Team: {team}, {best_of}, Took: {cs.timedelta(seconds=times.warmup_seconds)}'
            if time.time() - times.freezetime_started > scoreboard.freeze_time + scoreboard.buy_time - 2:
                if cs.account.autobuy and truth.first_autobuy and truth.autobuy_active:
                    telnet.send(cs.account.autobuy[-1][1])  # use the lowest defined autobuy, ignoring teams
                    truth.first_autobuy = False
                if truth.first_autobuy is False:
                    message += f' - {cyan("AutoBuy")}'
            truth.game_minimized_warmup = cs.round_start_msg(message, game_state.round_phase, times.freezetime_started, win32gui.GetWindowPlacement(hwnd)[1] == 2, scoreboard)
            scoreboard.CT = gsi_server.get_info('map', 'team_ct')['score']
            scoreboard.T = gsi_server.get_info('map', 'team_t')['score']
            if scoreboard.CT != 0 or scoreboard.T != 0:
                truth.game_minimized_warmup = False
        except AttributeError:
            pass

    elif game_state.map_phase == 'live':
        scoreboard.player = gsi_server.get_info('player')
        if scoreboard.player['steamid'] == cs.steam_id:
            scoreboard.weapons = list(scoreboard.player['weapons'].values())
            scoreboard.money = scoreboard.player['state']['money']
            # not getting team as `last_round_text` and `score` is also missing

            if scoreboard.raw_team and scoreboard.raw_opposing_team:
                money = f'{scoreboard.money:,}$'
                message = f'Freeze Time - {scoreboard.last_round_text} - {getattr(scoreboard, scoreboard.raw_team):02d}:{getattr(scoreboard, scoreboard.raw_opposing_team):02d}' \
                          f'{scoreboard.extra_round_info}{scoreboard.c4} - AFK: {cs.timedelta(seconds=afk.per_round)} - {purple(money)}'

                if time.time() - times.freezetime_started > scoreboard.freeze_time + scoreboard.buy_time - 2:
                    if cs.account.autobuy is not None and truth.first_autobuy and truth.game_minimized_freezetime:
                        if not any(weapon.get('type') in main_weapons for weapon in scoreboard.weapons):
                            for min_money, script, autobuy_team in cs.account.autobuy:
                                if scoreboard.money >= min_money and scoreboard.raw_team in autobuy_team and truth.autobuy_active:
                                    telnet.send(script)
                                    truth.first_autobuy = False
                                    break
                if truth.first_autobuy is False:
                    message += f' - {cyan("AutoBuy")}'

                health: int = scoreboard.player['state']['health']
                if scoreboard.player['steamid'] != cs.steam_id:
                    alive = f' - {red("0HP")}'
                elif health == 0:
                    alive = f' - {red("0HP")}'
                else:
                    alive = f' - {green(f"{health}HP")}'
                message += alive

                ws_data = {'state': scoreboard.player['state'], 'match_stats': scoreboard.player['match_stats'],
                           'weapons': tuple(scoreboard.weapons), 'afk_per_round': afk.per_round,
                           'afk_total': sum(afk.round_values) + afk.seconds_afk, 'minimized': window_status.in_game == 2}
                ws_send({'action': 'player_status', 'data': ws_data})

                if truth.game_minimized_freezetime is True:
                    truth.game_minimized_freezetime = cs.round_start_msg(message, game_state.round_phase, times.freezetime_started, win32gui.GetWindowPlacement(hwnd)[1] == 2, scoreboard)
                    # returns true if in freezetime or not tabbed in
                if truth.game_minimized_freezetime is False:
                    # remove timer after player tabbed in-game, keep health up-to-date
                    if scoreboard.round_message != message:
                        write(message, overwrite='7')
                        scoreboard.round_message = message
        else:
            truth.game_minimized_freezetime = False
            ws_data = {'afk_per_round': afk.per_round,
                       'afk_total': sum(afk.round_values) + afk.seconds_afk,
                       'minimized': window_status.in_game == 2}
            ws_send({'action': 'player_status', 'data': ws_data})

    if game_state.round_phase == 'freezetime' and truth.c4_round_first:
        scoreboard.current_weapons = list(gsi_server.get_info('player', 'weapons').values())
        scoreboard.has_c4 = True if 'weapon_c4' in [weapon['name'] for weapon in scoreboard.current_weapons] else False
        if scoreboard.has_c4:
            cs.sound_player.play(cs.sounds.ding, block=False)
            truth.c4_round_first = False

    if truth.still_in_warmup:
        if game_state.map_phase == 'live':
            truth.still_in_warmup = False
            truth.players_still_connecting = False
            team = red('T') if gsi_server.get_info('player', 'team') == 'T' else cyan('CT')
            times.warmup_seconds = int(time.time() - times.warmup_started)
            msg = 'Warmup is over! Map: {map}, Team: {team}, Took: {time}'.format(team=team,
                                                                                  map=green(' '.join(gsi_server.get_info('map', 'name').split('_')[1:]).title()),
                                                                                  time=cs.timedelta(seconds=times.warmup_seconds))
            write(msg, overwrite='7')
            if cs.afk_message is True:
                afk_sender.queue.put(msg)

            times.match_started = time.time()
            times.freezetime_started = time.time()
            if win32gui.GetWindowPlacement(hwnd)[1] == 2:
                truth.game_minimized_warmup = True
                cs.sound_player.play(cs.sounds.ready, block=False)
            afk.start_time = time.time()
            afk.seconds_afk = 0.0
            afk.round_values = []

        if game_state.map_phase is None:
            truth.still_in_warmup = False
            msg = red('Match did not start')
            write(msg, overwrite='1')
            if cs.afk_message is True:
                afk_sender.queue.put(msg)

    if game_state.map_phase in ['live', 'warmup'] and not truth.game_over and not truth.disconnected_form_last:
        try:
            window_status.in_game = win32gui.GetWindowPlacement(hwnd)[1]
        except BaseException as e:
            if e.args[1] == 'GetWindowPlacement':
                window_status.in_game = 2

        current_time = time.time()

        afk.still_afk.append(window_status.in_game == 2)  # True if minimized
        afk.still_afk = [all(afk.still_afk)]  # True if was minimized and still is minimized
        if not afk.still_afk[0]:  # player has tabbed into game or still is in-game
            afk.still_afk = []  # reset still_afk, if the player tabs out we do not want to wait for `afk_delay`
            if afk.anti_afk_active:  # stop spinning
                cs.anti_afk_tel(telnet, is_active=True)
                afk.anti_afk_active = False

            if current_time - afk.since_last_afk >= cs.cfg.afk_reset_delay:
                # player was in-game for more than `afk_delay`
                # reset time until spinning starts
                afk.time = current_time
        else:
            afk.since_last_afk = current_time

        if current_time - afk.time >= cs.cfg.anti_afk_delay and not afk.anti_afk_active:
            if window_status.in_game == 2:
                # only start spinning if player is tabbed out
                afk.anti_afk_active = True
                cs.anti_afk_tel(telnet, is_active=False)  # activate anti afk

        if window_status.in_game != 2:
            afk.start_time = current_time

        if game_state.map_phase == 'live' and window_status.in_game == 2:
            afk.seconds_afk += current_time - afk.start_time
            afk.start_time = current_time

    if game_state.map_phase == 'gameover':
        truth.game_over = True

    if truth.game_over and truth.first_game_over:
        truth.game_minimized_warmup = False
        truth.game_minimized_freezetime = False
        time.sleep(2)
        team = str(gsi_server.get_info('player', 'team')), 'CT' if gsi_server.get_info('player', 'team') == 'T' else 'T'
        score = {'CT': gsi_server.get_info('map', 'team_ct')['score'],
                 'T': gsi_server.get_info('map', 'team_t')['score'],
                 'map': ' '.join(gsi_server.get_info('map', 'name').split('_')[1:]).title()}

        if gsi_server.get_info('player', 'steamid') == cs.steam_id:
            player_stats = gsi_server.get_info('player', 'match_stats')

        average = cs.get_avg_match_time(cs.steam_id)
        try:
            afk_round = statistics.mean(afk.round_values)
        except statistics.StatisticsError:
            afk_round = 0.0
        timings = {'match': time.time() - times.match_started,
                   'search': times.match_accepted - times.search_started,
                   'afk': sum(afk.round_values), 'afk_round': afk_round}

        write(red(f'The match is over! - {score[team[0]]:02d}:{score[team[1]]:02d}'))

        write(f'Match duration: {cs.time_output(timings["match"], average["match_time"][0])}', add_time=False)
        write(f'Search-time:    {cs.time_output(timings["search"], average["search_time"][0])}', add_time=False)
        write(f'AFK-time:       {cs.time_output(timings["afk"], average["afk_time"][0])}', add_time=False)
        write(f'AFK per Round:  {cs.time_output(timings["afk_round"], average["afk_time"][2])}', add_time=False)
        write(f'                {(timings["afk"] / timings["match"]):.1%} of match duration', add_time=False)

        ws_send({'action': 'gameover', 'message': 'Match is Over'})

        round_wins = cs.round_wins_since_reset(cs.steam_id)
        round_wins += score[team[0]]

        normal_xp = 90
        reduced_xp = 205

        if round_wins <= normal_xp:
            write(f'Normal XP:      {round_wins}/{normal_xp}, {round_wins / normal_xp:.0%}, {normal_xp - round_wins} round wins missing', add_time=False)
        elif round_wins <= reduced_xp:
            write(f'Reduced XP:     {round_wins}/{reduced_xp}, {round_wins / reduced_xp:.0%}, {reduced_xp - round_wins} round wins missing', add_time=False)

        if gsi_server.get_info('map', 'mode') == 'competitive' and game_state.map_phase == 'gameover' and not truth.test_for_warmup and not truth.still_in_warmup:
            if truth.monitoring_since_start:
                match_time = timings['match']
                search_time = timings['search']
                afk_time = timings['afk']
            else:
                match_time, search_time, afk_time = None, None, None

            total_time = (f'Time in competitive matchmaking: {cs.timedelta(seconds=average["match_time"][1])}',
                          f'Time in the searching queue: {cs.timedelta(seconds=average["search_time"][1])}',
                          f'Time afk while being ingame: {cs.timedelta(seconds=average["afk_time"][1])}')
            for time_str in total_time:
                write(time_str, add_time=False)

            player_stats['map'] = score['map']

            try:
                player_stats['match_time'] = round(float(match_time))
            except TypeError:
                player_stats['match_time'] = None

            try:
                player_stats['wait_time'] = round(float(search_time))
            except TypeError:
                player_stats['wait_time'] = None

            try:
                player_stats['afk_time'] = round(float(afk_time))
            except TypeError:
                player_stats['afk_time'] = None

            t = Thread(target=upload_matches, args=(True, player_stats), name='UploadThread')
            t.start()

        truth.game_over = False
        truth.first_game_over = False
        truth.monitoring_since_start = False
        times.match_started, times.match_accepted = time.time(), time.time()
        afk.seconds_afk = 0.0
        afk.time = time.time()
        afk.round_values = []

    if truth.test_for_warmup:
        times.warmup_started = time.time()
        if console.map is not None:
            saved_map = console.map[-1]
        else:
            saved_map = ''
        while True:
            times.warmup_started = time.time()
            if not saved_map:
                console = read_telnet()
                if console.map is not None:
                    saved_map = console.map[-1]
            elif gsi_server.get_info('map', 'phase') == 'warmup':
                player_team = gsi_server.get_info('player', 'team')
                if player_team is not None:
                    team = red(player_team) if player_team == 'T' else cyan(player_team)
                    msg = f'You will play on {green(" ".join(saved_map.split("_")[1:]).title())} as {team} in the first half. ' \
                          f'Last Games: {cs.match_win_list(cs.cfg.match_list_length, cs.steam_id, time_difference=7_200)}'
                    write(msg, add_time=True, overwrite='12')
                    if cs.afk_message is True:
                        msg = f'You will play on `{" ".join(saved_map.split("_")[1:]).title()}` as `{team}` in the first half. ' \
                              f'Last Games: `{cs.match_win_list(cs.cfg.match_list_length, cs.steam_id, time_difference=7_200, replace_chars=True)}`'
                        afk_sender.queue.put(msg)

                    truth.still_in_warmup = True
                    truth.test_for_warmup = False
                    truth.players_still_connecting = True
                    times.warmup_started = time.time()
                    if cs.cfg.status_requester:
                        telnet.send('status')
                        thread = cs.MatchRequest()
                        thread.start()
                    break
            elif saved_map:
                write(f'You will play on {green(" ".join(saved_map.split("_")[1:]).title())}', overwrite='12')
                game_mode = gsi_server.get_info('map', 'mode')
                if game_mode not in ['competitive', 'wingman', None]:
                    write(yellow(f'{game_mode} is not supported'), overwrite='1')
                    truth.test_for_warmup = False
                    truth.first_game_over = False
                    break
            time.sleep(cs.sleep_interval)
    time.sleep(cs.sleep_interval)

telnet.close()
print('')
if gsi_server.running:
    gsi_server.shutdown()
exit('ENDED BY USER')
