import http.server
import queue
import re
import socketserver
import statistics
import time
from threading import Thread

import win32api
import win32con
import win32gui
from playsound import playsound

import cs
from csgostats.csgostats_updater import CSGOStatsUpdater
from write import *


class WebHookHandler(http.server.BaseHTTPRequestHandler):
    def log_request(self, code='-', size='-'):
        return

    def _set_response(self):
        self.send_response(200)
        self.send_header('Content-type', 'text/html')
        self.end_headers()

    def do_GET(self):
        self._set_response()
        obj = re.search(r'^/(\w+)$', self.path)
        if obj is not None:
            q.put(obj.group(1))


class WebServer(Thread):
    def __init__(self, port: int):
        self.port = port
        super().__init__(name='WebHookServer', daemon=True)

    def run(self) -> None:
        with socketserver.TCPServer(("127.0.0.1", self.port), WebHookHandler) as httpd:
            # print("serving at port", PORT)
            httpd.serve_forever()


class ResultParser(Thread):
    def __init__(self, queue_):
        self.queue = queue_
        super().__init__(name='ResultParser', daemon=True)

    def run(self) -> None:
        while True:
            while True:
                try:
                    item = q.get(block=False)
                    if item == 'minimize':
                        hk_minimize_csgo(cs.cfg.taskbar_position)
                    elif item == 'activate':
                        hk_activate()
                    elif item == 'pushbullet':
                        cs.activate_afk_message()
                    elif item == 'upload':
                        hk_upload_match()
                    elif item == 'switch_accounts':
                        hk_switch_accounts()
                    elif item == 'mute':
                        cs.mute_csgo(2)
                    elif item == 'discord_toggle':
                        hk_discord_toggle()
                    elif item == 'end':
                        hk_kill_main_loop()
                    elif item == 'fetch_status':
                        hk_fetch_status()
                except queue.Empty:
                    break
            time.sleep(0.1)


def hk_activate():
    if not game_state['map_phase'] in ['live', 'warmup']:
        truth_table['test_for_server'] = not truth_table['test_for_server']
        write(f'Looking for game: {truth_table["test_for_server"]}', overwrite='1')
        if truth_table['test_for_server']:
            playsound('sounds/activated.wav', block=False)
            time_table['search_started'] = time.time()
            cs.mute_csgo(1)
        elif not truth_table['test_for_server']:
            playsound('sounds/deactivated.wav', block=False)
            cs.mute_csgo(0)


# noinspection PyShadowingNames
def hk_upload_match():
    global retryer, time_table, truth_table
    write('Uploading / Getting status on newest match')
    t = Thread(target=upload_matches, args=(True, None), name='UploadThread')
    t.start()


def hk_switch_accounts():
    cs.current_steam_account += 1
    if cs.current_steam_account > len(cs.accounts) - 1:
        cs.current_steam_account = 0
    cs.account = cs.accounts[cs.current_steam_account]
    cs.steam_id = cs.account['steam_id']
    cs.check_userdata_autoexec(cs.account['steam_id_3'])
    updater.new_account(cs.account)
    write(f'current account is: {cs.account["name"]}', add_time=False, overwrite='3')


def hk_discord_toggle():
    truth_table['discord_output'] = not truth_table['discord_output']
    if truth_table['discord_output']:
        write(green('Discord output activated'), add_time=False, overwrite='13')
    else:
        write(red('Discord output deactivated'), add_time=False, overwrite='13')
    return


def hk_kill_main_loop():
    global running
    running = False


def hk_minimize_csgo(reset_position: tuple):
    global hwnd
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

    if current_placement[1] == 2:
        win32gui.ShowWindow(hwnd, win32con.SW_NORMAL)
    else:
        cs.minimize_csgo(hwnd)
    return


def hk_fetch_status():
    global hwnd
    if hwnd == 0:
        return
    cs.request_status_command(hwnd, cs.cfg.taskbar_position, key=cs.cfg.status_key)
    thread_ = cs.MatchRequest()
    thread_.start()


def gsi_server_status():
    global gsi_server
    if gsi_server.running:
        write(green('CS:GO GSI Server status: running'), overwrite='8')
    else:
        write(green('CS:GO GSI Server status: not running'), overwrite='8')
    return gsi_server.running


def upload_matches(look_for_new: bool = True, stats=None):
    global retryer, time_table, truth_table
    if truth_table['upload_thread_active']:
        write(magenta('Another Upload-Thread is still active'))
        return
    truth_table['upload_thread_active'] = True
    if look_for_new is True:
        try:
            latest_sharecode = cs.get_old_sharecodes(-1)
        except ValueError:
            write(red('no match token in config, aborting'))
            truth_table['upload_thread_active'] = False
            return

        new_sharecodes = cs.get_new_sharecodes(latest_sharecode[0], stats=stats)

        for new_code in new_sharecodes:
            retryer.append(new_code) if new_code['sharecode'] not in [old_code['sharecode'] for old_code in retryer] else retryer

    time_table['csgostats_retry'] = time.time()
    if not retryer:
        write(yellow('no new sharecodes found, aborting'))
        truth_table['upload_thread_active'] = False
        return
    retryer = updater.update_csgo_stats(retryer, discord_output=truth_table['discord_output'])
    time_table['csgostats_retry'] = time.time()
    truth_table['upload_thread_active'] = False
    return


# BOOLEAN, TIME INITIALIZATION
truth_table = {'test_for_accept_button': False, 'test_for_warmup': False, 'test_for_success': False, 'testing': False, 'first_push': True, 'still_in_warmup': False, 'test_for_server': False, 'first_freezetime': True,
               'game_over': False, 'monitoring_since_start': False, 'players_still_connecting': False, 'first_game_over': True, 'disconnected_form_last': False, 'c4_round_first': True, 'steam_error': False,
               'game_minimized_freezetime': False, 'game_minimized_warmup': False, 'discord_output': True, 'gsi_first_launch': True, 'upload_thread_active': False}

# remove console_read and timed_execution_time
time_table = {'csgostats_retry': time.time(), 'search_started': time.time(), 'console_read': time.time(), 'timed_execution_time': time.time(), 'match_accepted': time.time(),
              'match_started': time.time(), 'freezetime_started': time.time(), 'join_warmup_time': 0.0, 'warmup_seconds': 0}
matchmaking = {'msg': [], 'update': [], 'players_accepted': [], 'lobby_data': [], 'server_found': False, 'server_ready': False, 'server_settings': []}
afk_dict = {'time': time.time(), 'still_afk': [], 'start_time': time.time(), 'seconds_afk': 0.0, 'per_round': 0.0, 'player_info': {'steamid': 0, 'state': {}}, 'round_values': []}
join_dict = {'t_full': False, 'ct_full': False}
scoreboard = {'CT': 0, 'T': 0, 'last_round_info': '', 'last_round_key': '0', 'extra_round_info': '', 'player': {}, 'max_rounds': 30, 'buy_time': 20, 'freeze_time': 15}
team = yellow('Unknown')
player_stats = {}

gsi_server = cs.restart_gsi_server(None)

window_enum = cs.WindowEnumerator()
window_enum.start()

q = queue.Queue()
webhook = WebServer(cs.cfg.webhook_port)
webhook_parser = ResultParser(q)
webhook.start()
webhook_parser.start()

afk_sender = SendDiscordMessage(cs.cfg.discord_user_id, cs.cfg.server_ip, cs.cfg.server_port, message_queue)
afk_sender.start()

hwnd, hwnd_old = 0, 0
csgo_window_status = {'server_found': 2, 'new_tab': 2, 'in_game': 0}
csgo = []

updater = CSGOStatsUpdater(cs.cfg, cs.account, cs.path_vars['db_path'])
retryer = []

game_state = {'map_phase': []}
cs.mute_csgo(0)

write(green('READY'))
running = True

while running:

    if retryer and not truth_table['upload_thread_active']:
        if time.time() - time_table['csgostats_retry'] > cs.cfg.auto_retry_interval:
            t = Thread(target=upload_matches, args=(False, None), name='UploadThread')
            t.start()

    csgo = [(hwnd, title) for hwnd, title in cs.window_ids if 'counter-strike: global offensive' == title.lower()]

    if not csgo:
        time.sleep(0.5)
        continue
    hwnd = csgo[0][0]

    if hwnd_old != hwnd:
        truth_table['test_for_server'] = False
        hwnd_old = hwnd
        cs.steam_id = cs.get_current_steam_user()
        try:
            cs.account = [i for i in cs.accounts if cs.steam_id == i['steam_id']][0]
            cs.steam_id = cs.account['steam_id']
            cs.check_userdata_autoexec(cs.account['steam_id_3'])
        except IndexError:
            write('Account is not in the config.ini!\nScript will not work properly!', add_time=False, overwrite='9')
            playsound('sounds/fail.wav', block=False)
            exit('Update config.ini!')
        updater.new_account(cs.account)
        write(f'Current account is: {cs.account["name"]}', add_time=False, overwrite='9')

        if cs.check_for_forbidden_programs(cs.window_ids):
            write('A forbidden program is still running...', add_time=False)
            playsound('sounds/fail.wav', block=False)

        gsi_server = cs.restart_gsi_server(gsi_server)
        truth_table['gsi_first_launch'] = True

    if truth_table['gsi_first_launch'] and gsi_server.running:
        write(green('GSI Server running'), overwrite='8')
        truth_table['gsi_first_launch'] = False

    if not gsi_server.running:
        time.sleep(cs.sleep_interval)
        continue

    matchmaking = cs.read_console()

    if matchmaking['update']:
        if matchmaking['update'][-1] == '1':
            if not truth_table['test_for_server']:
                truth_table['test_for_server'] = True
                time_table['search_started'] = time.time()
                write(magenta(f'Looking for match: {truth_table["test_for_server"]}'), overwrite='1')
            playsound('sounds/activated.wav', block=False)
            cs.mute_csgo(1)
        elif matchmaking['update'][-1] == '0' and truth_table['test_for_server']:
            cs.mute_csgo(0)

    if truth_table['test_for_server']:
        if matchmaking['server_found']:
            playsound('sounds/server_found.wav', block=False)
            truth_table['test_for_success'] = True
        if matchmaking['server_ready']:
            truth_table['test_for_accept_button'] = True
            cs.sleep_interval = cs.sleep_interval_looking_for_accept
            csgo_window_status['server_found'] = win32gui.GetWindowPlacement(hwnd)[1]
            win32gui.ShowWindow(hwnd, win32con.SW_MAXIMIZE)

    if truth_table['test_for_accept_button']:
        img = cs.get_screenshot(hwnd, (1300, 550, 1310, 570))
        accept_avg = cs.color_average(img, [(76, 175, 80), (90, 203, 94)])
        if cs.relate_list(accept_avg, (2, 2, 2)):
            truth_table['test_for_accept_button'] = False
            cs.sleep_interval = cs.cfg.sleep_interval

            current_cursor_position = win32api.GetCursorPos()
            for _ in range(5):
                win32gui.ShowWindow(hwnd, win32con.SW_MAXIMIZE)
                cs.click((int(win32api.GetSystemMetrics(0) / 2), int(win32api.GetSystemMetrics(1) / 2.4)))
            if csgo_window_status['server_found'] == 2:  # was minimized when a server was found
                time.sleep(0.075)
                cs.minimize_csgo(hwnd)
            else:
                cs.set_mouse_position(current_cursor_position)

            playsound('sounds/accept_found.wav', block=False)

    if truth_table['test_for_accept_button'] or truth_table['test_for_success']:
        if cs.str_in_list(['Match confirmed'], matchmaking['msg']):
            write(green(f'All Players accepted - Match has started - Took {cs.timedelta(time_table["search_started"])} since start'), add_time=False, overwrite='11')
            truth_table['test_for_warmup'] = True
            truth_table['first_game_over'], truth_table['game_over'] = True, False
            truth_table['disconnected_form_last'] = False
            truth_table['first_freezetime'] = False
            truth_table['test_for_server'] = False
            truth_table['test_for_accept_button'] = False
            cs.sleep_interval = cs.cfg.sleep_interval
            truth_table['test_for_success'] = False
            truth_table['monitoring_since_start'] = True
            cs.mute_csgo(0)
            playsound('sounds/done_testing.wav', block=False)
            time_table['match_accepted'] = time.time()
            afk_dict['time'] = time.time()
            afk_dict['start_time'] = time.time()
            afk_dict['seconds_afk'] = 0.0
            afk_dict['round_values'] = []

        for i in matchmaking['players_accepted']:
            i = i.split('/')
            players_accepted = str(int(i[1]) - int(i[0]))
            write(f'{players_accepted} Players of {i[1]} already accepted.', add_time=False, overwrite='11')

        if cs.str_in_list(['Other players failed to connect', 'Failed to ready up'], matchmaking['msg']):
            truth_table['test_for_server'] = True
            truth_table['test_for_accept_button'] = False
            cs.sleep_interval = cs.cfg.sleep_interval
            truth_table['test_for_success'] = False
            if 'Other players failed to connect' in matchmaking['msg']:
                msg = red('Match has not started! Continuing to search for a Server!')
                write(msg, overwrite='11')
                if cs.afk_message is True:
                    message_queue.put(msg)
                playsound('sounds/back_to_testing.wav', block=False)
                cs.mute_csgo(1)
            elif 'Failed to ready up' in matchmaking['msg']:
                msg = red('You failed to accept! Restart searching!')
                write(red('You failed to accept! Restart searching!'), overwrite='11')
                if cs.afk_message is True:
                    message_queue.put(msg)
                playsound('sounds/failed_to_accept.wav')
                cs.mute_csgo(0)

    if truth_table['players_still_connecting']:
        lobby_data = ''.join(matchmaking['lobby_data'])
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
                best_of = red(f"BR{scoreboard['max_rounds']}")
                msg = f'Server full, All Players connected. ' \
                      f'{best_of}, '  \
                      f'Took {cs.timedelta(time_table["warmup_started"])} since match start.'
                write(msg, overwrite='7')
                if cs.afk_message is True:
                    message_queue.put(msg)
                red('You failed to accept! Restart searching!')
                playsound('sounds/minute_warning.wav', block=True)
                truth_table['players_still_connecting'] = False
                join_dict['t_full'], join_dict['ct_full'] = False, False
                break

    if any(True for i in matchmaking['server_abandon'] if 'Disconnect' in i):
        if not truth_table['game_over']:
            write(red('Server disconnected'))
            playsound('sounds/fail.wav', block=False)
        gsi_server = cs.restart_gsi_server(gsi_server)
        truth_table['disconnected_form_last'] = True
        truth_table['players_still_connecting'] = False
        afk_dict['time'] = time.time()

    game_state = {'map_phase': gsi_server.get_info('map', 'phase'), 'round_phase': gsi_server.get_info('round', 'phase')}

    if len(matchmaking['server_settings']) != 0:
        try:
            scoreboard['max_rounds'] = [int(re.sub('\D', '', line)) for line in matchmaking['server_settings'] if 'maxrounds' in line][0]
        except IndexError:
            pass
        try:
            scoreboard['buy_time'] = [int(re.sub('\D', '', line)) for line in matchmaking['server_settings'] if 'buytime' in line][0]
        except IndexError:
            pass
        try:
            scoreboard['freeze_time'] = [int(re.sub('\D', '', line)) for line in matchmaking['server_settings'] if 'freezetime' in line][0]
        except IndexError:
            pass

    if truth_table['first_freezetime']:
        if game_state['map_phase'] == 'live' and game_state['round_phase'] == 'freezetime':
            truth_table['first_game_over'], truth_table['game_over'] = True, False
            truth_table['disconnected_form_last'] = False
            truth_table['first_freezetime'] = False
            time_table['freezetime_started'] = time.time()
            scoreboard['CT'] = gsi_server.get_info('map', 'team_ct')['score']
            scoreboard['T'] = gsi_server.get_info('map', 'team_t')['score']
            scoreboard['last_round_info'] = gsi_server.get_info('map', 'round_wins')
            scoreboard['player'] = gsi_server.get_info('player')
            scoreboard['weapons'] = [inner for outer in scoreboard['player']['weapons'].values() for inner in outer.items()]
            scoreboard['c4'] = ' - Bomb Carrier' if 'weapon_c4' in [i for _, i in scoreboard['weapons']] else ''
            scoreboard['total_score'] = scoreboard['CT'] + scoreboard['T']

            scoreboard['team'] = red('T') if scoreboard['player']['team'] == 'T' else cyan('CT')
            scoreboard['opposing_team'] = cyan('CT') if decolor(scoreboard['team']) == 'T' else red('T')

            afk_dict['round_values'].append(afk_dict['seconds_afk'])
            afk_dict['round_values'] = [round(time_afk, 3) for time_afk in afk_dict['round_values']]
            try:
                afk_dict['per_round'] = statistics.mean(afk_dict['round_values'])
            except statistics.StatisticsError:
                afk_dict['per_round'] = 0.0
            afk_dict['seconds_afk'] = 0.0

            try:
                scoreboard['last_round_key'] = list(scoreboard['last_round_info'].keys())[-1]
                scoreboard['last_round_info'] = scoreboard['last_round_info'][scoreboard['last_round_key']].split('_')[0].upper()
                if int(scoreboard['last_round_key']) == scoreboard['max_rounds'] / 2:
                    scoreboard['last_round_info'] = 'T' if scoreboard['last_round_info'] == 'CT' else 'CT'
                scoreboard['last_round_info'] = f'{scoreboard["team"]} {green("won")} the last round' if decolor(scoreboard['team']) == scoreboard['last_round_info'] else f'{scoreboard["team"]} {yellow("lost")} the last round'
            except AttributeError:
                scoreboard['last_round_info'] = f'You {scoreboard["team"]}, no info on the last round'

            if scoreboard['total_score'] == scoreboard['max_rounds'] / 2 - 1:
                scoreboard['extra_round_info'] = yellow(' - Half-Time')
                playsound('sounds/ding.wav', block=True)
            elif scoreboard['CT'] == scoreboard['max_rounds'] / 2 or scoreboard['T'] == scoreboard['max_rounds'] / 2:
                scoreboard['extra_round_info'] = yellow(' - Match Point')
            else:
                scoreboard['extra_round_info'] = ''

            write(f'Freeze Time - {scoreboard["last_round_info"]} - {scoreboard[decolor(scoreboard["team"])]:02d}:{scoreboard[decolor(scoreboard["opposing_team"])]:02d}'
                  f'{scoreboard["extra_round_info"]}{scoreboard["c4"]} - AFK: {cs.timedelta(seconds=afk_dict["per_round"])}',
                  overwrite='7')

            if win32gui.GetWindowPlacement(hwnd)[1] == 2:
                truth_table['game_minimized_freezetime'] = True
                playsound('sounds/ready_up.wav', block=True)

        elif game_state['map_phase'] == 'live' and gsi_server.get_info('player', 'steamid') == cs.steam_id:
            player_stats = gsi_server.get_info('player', 'match_stats')

    elif game_state['map_phase'] == 'live' and game_state['round_phase'] != 'freezetime':
        truth_table['first_freezetime'] = True
        truth_table['c4_round_first'] = True
        if time.time() - time_table['freezetime_started'] >= 20 and win32gui.GetWindowPlacement(hwnd)[1] == 2:
            playsound('sounds/ready_up.wav', block=False)

    if truth_table['game_minimized_freezetime']:
        message = f'Freeze Time - {scoreboard["last_round_info"]} - {scoreboard[decolor(scoreboard["team"])]:02d}:{scoreboard[decolor(scoreboard["opposing_team"])]:02d}' \
                  f'{scoreboard["extra_round_info"]}{scoreboard["c4"]} - AFK: {cs.timedelta(seconds=afk_dict["per_round"])}'
        truth_table['game_minimized_freezetime'] = cs.round_start_msg(message, game_state['round_phase'], time_table['freezetime_started'], truth_table['game_minimized_freezetime'], win32gui.GetWindowPlacement(hwnd)[1] == 2, scoreboard)
    elif truth_table['game_minimized_warmup']:
        try:
            best_of = red(f"BR{scoreboard['max_rounds']}")
            message = f'Warmup is over! Map: {green(" ".join(gsi_server.get_info("map", "name").split("_")[1:]).title())}, Team: {team}, {best_of}, Took: {cs.timedelta(seconds=time_table["warmup_seconds"])}'
            truth_table['game_minimized_warmup'] = cs.round_start_msg(message, game_state['round_phase'], time_table['freezetime_started'], truth_table['game_minimized_warmup'], win32gui.GetWindowPlacement(hwnd)[1] == 2, scoreboard)
        except AttributeError:
            pass

    if game_state['round_phase'] == 'freezetime' and truth_table['c4_round_first']:
        scoreboard['c_weapons'] = [inner for outer in gsi_server.get_info('player', 'weapons').values() for inner in outer.items()]
        scoreboard['has_c4'] = True if 'weapon_c4' in [i for _, i in scoreboard['c_weapons']] else False
        if scoreboard['has_c4']:
            playsound('sounds/ding.wav', block=False)
            truth_table['c4_round_first'] = False

    if truth_table['still_in_warmup']:
        if game_state['map_phase'] == 'live':

            truth_table['still_in_warmup'] = False
            truth_table['players_still_connecting'] = False
            team = red('T') if gsi_server.get_info('player', 'team') == 'T' else cyan('CT')
            time_table['warmup_seconds'] = int(time.time() - time_table['warmup_started'])
            msg = 'Warmup is over! Map: {map}, Team: {team}, Took: {time}'.format(team=team,
                                                                                  map=green(' '.join(gsi_server.get_info('map', 'name').split('_')[1:]).title()),
                                                                                  time=cs.timedelta(seconds=time_table['warmup_seconds']))
            write(msg, overwrite='7')
            if cs.afk_message is True:
                message_queue.put(msg)

            time_table['match_started'] = time.time()
            time_table['freezetime_started'] = time.time()
            if win32gui.GetWindowPlacement(hwnd)[1] == 2:
                truth_table['game_minimized_warmup'] = True
                playsound('sounds/ready_up_warmup.wav', block=False)
            afk_dict['start_time'] = time.time()
            afk_dict['seconds_afk'] = 0.0
            afk_dict['round_values'] = []

        if game_state['map_phase'] is None:
            truth_table['still_in_warmup'] = False
            msg = red('Match did not start')
            write(msg, overwrite='1')
            if cs.afk_message is True:
                message_queue.put(msg)

    if game_state['map_phase'] in ['live', 'warmup'] and not truth_table['game_over'] and not truth_table['disconnected_form_last']:
        try:
            csgo_window_status['in_game'] = win32gui.GetWindowPlacement(hwnd)[1]
        except BaseException as e:
            if e.args[1] == 'GetWindowPlacement':
                csgo_window_status['in_game'] = 2
        afk_dict['still_afk'].append(csgo_window_status['in_game'] == 2)  # True if minimized
        afk_dict['still_afk'] = [all(afk_dict['still_afk'])]  # True if was minimized and still is minimized
        if not afk_dict['still_afk'][0]:
            afk_dict['still_afk'] = []
            afk_dict['time'] = time.time()
        if time.time() - afk_dict['time'] >= 180:
            while True:
                afk_dict['player_info'] = gsi_server.get_info('player')
                afk_dict['round_phase'] = gsi_server.get_info('round', 'phase')
                if afk_dict['round_phase'] is None:
                    afk_dict['round_phase'] = 'warmup'
                if afk_dict['player_info']['steamid'] == cs.steam_id and afk_dict['player_info']['state']['health'] > 0 and afk_dict['round_phase'] not in ['freezetime', None]:
                    write('Ran Anti-Afk Script.', overwrite='10')
                    cs.anti_afk(hwnd)
                    break
                if win32gui.GetWindowPlacement(hwnd)[1] != 2:
                    break
            afk_dict['still_afk'] = []
            afk_dict['time'] = time.time()

        if csgo_window_status['in_game'] != 2:
            afk_dict['start_time'] = time.time()

        if game_state['map_phase'] == 'live' and csgo_window_status['in_game'] == 2:
            afk_dict['seconds_afk'] += time.time() - afk_dict['start_time']
            afk_dict['start_time'] = time.time()

    if game_state['map_phase'] == 'gameover':
        truth_table['game_over'] = True

    if truth_table['game_over'] and truth_table['first_game_over']:
        time.sleep(2)
        team = str(gsi_server.get_info('player', 'team')), 'CT' if gsi_server.get_info('player', 'team') == 'T' else 'T'
        score = {'CT': gsi_server.get_info('map', 'team_ct')['score'], 'T': gsi_server.get_info('map', 'team_t')['score'], 'map': ' '.join(gsi_server.get_info('map', 'name').split('_')[1:]).title()}

        if gsi_server.get_info('player', 'steamid') == cs.steam_id:
            player_stats = gsi_server.get_info('player', 'match_stats')

        average = cs.get_avg_match_time(cs.steam_id)
        try:
            afk_round = statistics.mean(afk_dict['round_values'])
        except statistics.StatisticsError:
            afk_round = 0.0
        timings = {'match': time.time() - time_table['match_started'], 'search': time_table['match_accepted'] - time_table['search_started'], 'afk': sum(afk_dict['round_values']), 'afk_round': afk_round}

        write(red(f'The match is over! - {score[team[0]]:02d}:{score[team[1]]:02d}'))

        write(f'Match duration: {cs.time_output(timings["match"], average["match_time"][0])}', add_time=False)
        write(f'Search-time:    {cs.time_output(timings["search"], average["search_time"][0])}', add_time=False)
        write(f'AFK-time:       {cs.time_output(timings["afk"], average["afk_time"][0])}', add_time=False)
        write(f'AFK per Round:  {cs.time_output(timings["afk_round"], average["afk_time"][2])}', add_time=False)
        write(f'                {(timings["afk"] / timings["match"]):.1%} of match duration', add_time=False)

        if gsi_server.get_info('map', 'mode') == 'competitive' and game_state['map_phase'] == 'gameover' and not truth_table['test_for_warmup'] and not truth_table['still_in_warmup']:
            if truth_table['monitoring_since_start']:
                match_time = timings['match']
                search_time = timings['search']
                afk_time = timings['afk']
            else:
                match_time, search_time, afk_time = '', '', ''

            total_time = (f'Time in competitive matchmaking: {cs.timedelta(seconds=average["match_time"][1])}',
                          f'Time in the searching queue: {cs.timedelta(seconds=average["search_time"][1])}',
                          f'Time afk while being ingame: {cs.timedelta(seconds=average["afk_time"][1])}')
            for time_str in total_time:
                write(time_str, add_time=False)

            player_stats['map'] = score['map']
            player_stats['match_time'] = round(float(match_time))
            player_stats['wait_time'] = round(float(search_time))
            player_stats['afk_time'] = round(float(afk_time))

            t = Thread(target=upload_matches, args=(True, player_stats), name='UploadThread')
            t.start()

        truth_table['game_over'] = False
        truth_table['first_game_over'] = False
        truth_table['monitoring_since_start'] = False
        time_table['match_started'], time_table['match_accepted'] = time.time(), time.time()
        afk_dict['seconds_afk'], afk_dict['time'] = 0.0, time.time()
        afk_dict['round_values'] = []

    if truth_table['test_for_warmup']:
        time_table['warmup_started'] = time.time()
        try:
            saved_map = matchmaking['map'][-1]
        except IndexError:
            saved_map = ''
        while True:
            time_table['warmup_started'] = time.time()
            if not saved_map:
                try:
                    saved_map = cs.read_console()['map'][-1]
                except IndexError:
                    pass
            elif gsi_server.get_info('map', 'phase') == 'warmup':
                player_team = gsi_server.get_info('player', 'team')
                if player_team is not None:
                    team = red(player_team) if player_team == 'T' else cyan(player_team)
                    msg = f'You will play on {green(" ".join(saved_map.split("_")[1:]).title())} as {team} in the first half. ' \
                          f'Last Games: {cs.match_win_list(cs.cfg.match_list_lenght, cs.steam_id, time_difference=7_200)}'
                    write(msg, add_time=True, overwrite='12')
                    if cs.afk_message is True:
                        msg = f'You will play on {green(" ".join(saved_map.split("_")[1:]).title())} as {team} in the first half. ' \
                              f'Last Games: {cs.match_win_list(cs.cfg.match_list_lenght, cs.steam_id, time_difference=7_200, replace_chars=True)}'
                        message_queue.put(msg)

                    truth_table['still_in_warmup'] = True
                    truth_table['test_for_warmup'] = False
                    truth_table['players_still_connecting'] = True
                    time_table['warmup_started'] = time.time()
                    if cs.cfg.status_key:
                        cs.request_status_command(hwnd, cs.cfg.taskbar_position, key=cs.cfg.status_key)
                        thread = cs.MatchRequest()
                        thread.start()
                    break
            elif saved_map:
                write(f'You will play on {green(" ".join(saved_map.split("_")[1:]).title())}', overwrite='12')
                game_mode = gsi_server.get_info('map', 'mode')
                if game_mode not in ['competitive', 'wingman', None]:
                    write(yellow(f'{game_mode} is not supported'), overwrite='1')
                    truth_table['test_for_warmup'] = False
                    truth_table['first_game_over'] = False
                    break
            time.sleep(cs.sleep_interval)
    time.sleep(cs.sleep_interval)

window_enum.kill()
if cs.overwrite_dict['end'] != '\n':
    print('')
if gsi_server.running:
    gsi_server.shutdown()
exit('ENDED BY USER')
