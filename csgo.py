import time
import webbrowser
from threading import Thread

import keyboard
import win32api
import win32con
import win32gui
from color import uncolorize, FgColor, red, green, yellow, blue, magenta, cyan
from playsound import playsound

import cs
from cs import write


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


# noinspection PyShadowingNames
def hk_new_tab():
    if hwnd:
        try:
            csgo_window_status['new_tab'] = win32gui.GetWindowPlacement(hwnd)[1]
        except BaseException as e:
            if e.args[1] == 'GetWindowPlacement':
                csgo_window_status['new_tab'] = 2
    if csgo_window_status['new_tab'] != 2:
        win32gui.ShowWindow(hwnd, win32con.SW_MAXIMIZE)
    webbrowser.open_new_tab(f'https://csgostats.gg/player/{cs.steam_id}#/live')
    if csgo_window_status['new_tab'] != 2:
        time.sleep(0.5)
        win32gui.ShowWindow(hwnd, win32con.SW_MAXIMIZE)


def hk_switch_accounts():
    cs.current_steam_account += 1
    if cs.current_steam_account > len(cs.accounts) - 1:
        cs.current_steam_account = 0
    cs.account = cs.accounts[cs.current_steam_account]
    cs.steam_id = cs.account['steam_id']
    cs.check_userdata_autoexec(cs.account['steam_id_3'])
    write(f'current account is: {cs.account["name"]}', add_time=False, overwrite='3')


def hk_discord_toggle():
    if cs.cfg['discord_url']:
        truth_table['discord_output'] = not truth_table['discord_output']
        if truth_table['discord_output']:
            write('Discord output activated', add_time=False, color=FgColor.Green, overwrite='13')
        else:
            write('Discord output deactivated', add_time=False, color=FgColor.Red, overwrite='13')
    else:
        write('Discord Webhook URL not set in config', color=FgColor.Yellow)


def hk_force_restart():
    global gsi_server
    truth_table['gsi_first_launch'] = True
    write('GSI Server restarting', color=FgColor.Yellow, overwrite='8')
    gsi_server = cs.restart_gsi_server(gsi_server)


def hk_kill_main_loop():
    global running
    running = False


def hk_minimize_csgo(reset_position: tuple):
    global hwnd
    if hwnd == 0:
        return None
    current_placement = win32gui.GetWindowPlacement(hwnd)
    if current_placement[1] == 2:
        win32gui.ShowWindow(hwnd, win32con.SW_NORMAL)
    else:
        cs.minimize_csgo(hwnd, reset_position)
    return None


def hk_cancel_csgostats_retrying():
    global retryer
    retryer = []
    write('canceled csgostats.gg retrying', overwrite='4', color=FgColor.Yellow)
    return


def gsi_server_status():
    global gsi_server
    if gsi_server.running:
        write('CS:GO GSI Server status: running', color=FgColor.Green, overwrite='8')
    else:
        write('CS:GO GSI Server status: not running', color=FgColor.Red, overwrite='8')
    return gsi_server.running


def upload_matches(look_for_new: bool = True, stats=None):
    global retryer, time_table, truth_table
    if truth_table['upload_thread_active']:
        write('Another Upload-Thread is still active', color=FgColor.Magenta)
        return None
    truth_table['upload_thread_active'] = True
    if look_for_new:
        latest_sharecode = cs.get_old_sharecodes(-1)
        empty_csv = False
        if not latest_sharecode:
            write('Failed to retrive lastest old sharecode', color=FgColor.Yellow)
            csv_path = cs.csv_path_for_steamid(cs.steam_id)
            data = cs.get_csv_list(csv_path)
            if len(data) != 1:
                write('more then one game has been added, yet no sharecode found; wut?', color=FgColor.Red)
                truth_table['upload_thread_active'] = False
                return
            if not cs.account['match_token']:
                write('no match token in config, aborting', color=FgColor.Red)
                return
            data[0]['sharecode'] = cs.account['match_token']
            cs.write_data_csv(csv_path, data, cs.csv_header)
            latest_sharecode = [cs.account['match_token']]
            empty_csv = True
        new_sharecodes = cs.get_new_sharecodes(latest_sharecode[0], stats=stats)
        if empty_csv:
            new_sharecodes.insert(0, {'sharecode': latest_sharecode[0], 'queue_pos': None})

        for new_code in new_sharecodes:
            retryer.append(new_code) if new_code['sharecode'] not in [old_code['sharecode'] for old_code in retryer] else retryer
    time_table['csgostats_retry'] = time.time()
    retryer = cs.update_csgo_stats(retryer, discord_output=truth_table['discord_output'])
    time_table['csgostats_retry'] = time.time()
    truth_table['upload_thread_active'] = False
    return None


# BOOLEAN, TIME INITIALIZATION
truth_table = {'test_for_accept_button': False, 'test_for_warmup': False, 'test_for_success': False, 'first_ocr': True, 'testing': False, 'first_push': True, 'still_in_warmup': False, 'test_for_server': False, 'first_freezetime': True,
               'game_over': False, 'monitoring_since_start': False, 'players_still_connecting': False, 'first_game_over': True, 'disconnected_form_last': False, 'c4_round_first': True, 'steam_error': False,
               'game_minimized_freezetime': False, 'game_minimized_warmup': False, 'discord_output': True, 'gsi_first_launch': True, 'upload_thread_active': False}


# remove console_read and timed_execution_time
time_table = {'csgostats_retry': time.time(), 'search_started': time.time(), 'console_read': time.time(), 'timed_execution_time': time.time(), 'match_accepted': time.time(),
              'match_started': time.time(), 'freezetime_started': time.time(), 'join_warmup_time': 0.0, 'warmup_seconds': 0}
matchmaking = {'msg': [], 'update': [], 'players_accepted': [], 'lobby_data': [], 'server_found': False, 'server_ready': False}
afk_dict = {'time': time.time(), 'still_afk': [], 'start_time': time.time(), 'seconds_afk': 0.0, 'per_round': 0.0, 'player_info': {'steamid': 0, 'state': {}}, 'round_values': []}
join_dict = {'t_full': False, 'ct_full': False}
scoreboard = {'CT': 0, 'T': 0, 'last_round_info': '', 'last_round_key': '0', 'extra_round_info': '', 'player': {}}
team = yellow('Unknown')
player_stats = {}

gsi_server = cs.restart_gsi_server(None)

window_enum = cs.WindowEnumerator()
window_enum.start()

hwnd, hwnd_old = 0, 0
csgo_window_status = {'server_found': 2, 'new_tab': 2, 'in_game': 0}
csgo = []


retryer = []

game_state = {'map_phase': []}
cs.mute_csgo(0)

blue(), magenta()

if cs.cfg['activate_script']:
    keyboard.add_hotkey(cs.cfg['activate_script'], hk_activate)
if cs.cfg['activate_push_notification']:
    keyboard.add_hotkey(cs.cfg['activate_push_notification'], cs.activate_pushbullet)
if cs.cfg['info_newest_match']:
    keyboard.add_hotkey(cs.cfg['info_newest_match'], hk_upload_match)
if cs.cfg['open_live_tab']:
    keyboard.add_hotkey(cs.cfg['open_live_tab'], hk_new_tab)
if cs.cfg['switch_accounts']:
    keyboard.add_hotkey(cs.cfg['switch_accounts'], hk_switch_accounts)
if cs.cfg['mute_csgo_toggle']:
    keyboard.add_hotkey(cs.cfg['mute_csgo_toggle'], cs.mute_csgo, args=[2])  # LvL 2 is toggle
if cs.cfg['discord_key']:
    keyboard.add_hotkey(cs.cfg['discord_key'], hk_discord_toggle)
if cs.cfg['end_script']:
    keyboard.add_hotkey(cs.cfg['end_script'], hk_kill_main_loop)
if cs.cfg['minimize_key']:
    keyboard.add_hotkey(cs.cfg['minimize_key'], hk_minimize_csgo, args=[cs.cfg['taskbar_position']])
if cs.cfg['cancel_csgostats']:
    keyboard.add_hotkey(cs.cfg['cancel_csgostats'], hk_cancel_csgostats_retrying)

write('READY', color=FgColor.Green)
running = True

while running:
    if retryer and not truth_table['upload_thread_active']:
        if time.time() - time_table['csgostats_retry'] > cs.cfg['auto_retry_interval']:
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
        write(f'Current account is: {cs.account["name"]}', add_time=False, overwrite='9')

        if cs.check_for_forbidden_programs(cs.window_ids):
            write('A forbidden program is still running...', add_time=False)
            playsound('sounds/fail.wav', block=False)

        gsi_server = cs.restart_gsi_server(gsi_server)
        truth_table['gsi_first_launch'] = True

    if truth_table['gsi_first_launch'] and gsi_server.running:
        write('GSI Server running', overwrite='8', color=FgColor.Green)
        truth_table['gsi_first_launch'] = False

    if not gsi_server.running:
        time.sleep(cs.sleep_interval)
        continue

    matchmaking = cs.read_console()

    if matchmaking['update']:
        if matchmaking['update'][-1] == '1':
            if not truth_table['test_for_server']:
                truth_table['test_for_server'] = True
                write(f'Looking for match: {truth_table["test_for_server"]}', overwrite='1', color=FgColor.Magenta)
                time_table['search_started'] = time.time()
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
        img = cs.get_screenshot(hwnd, (1265, 760, 1295, 785))
        accept_avg = cs.color_average(img, [(76, 175, 80), (90, 203, 94)])
        if cs.relate_list(accept_avg, (2, 2, 2)):
            truth_table['test_for_accept_button'] = False
            cs.sleep_interval = cs.cfg['sleep_interval']

            current_cursor_position = win32api.GetCursorPos()
            for _ in range(5):
                win32gui.ShowWindow(hwnd, win32con.SW_MAXIMIZE)
                cs.click((int(win32api.GetSystemMetrics(0) / 2), int(win32api.GetSystemMetrics(1) / 1.78)))
            if csgo_window_status['server_found'] == 2:  # was minimized when a server was found
                time.sleep(0.075)
                cs.minimize_csgo(hwnd, cs.cfg['taskbar_position'])
            else:
                cs.set_mouse_position(current_cursor_position)

            playsound('sounds/accept_found.wav', block=False)

    if truth_table['test_for_accept_button'] or truth_table['test_for_success']:
        if cs.str_in_list(['Match confirmed'], matchmaking['msg']):
            write(f'All Players accepted - Match has started - Took {cs.timedelta(time_table["search_started"])} since start', add_time=False, overwrite='11', color=FgColor.Green)
            truth_table['test_for_warmup'] = True
            truth_table['first_game_over'], truth_table['game_over'] = True, False
            truth_table['disconnected_form_last'] = False
            truth_table['first_freezetime'] = False
            truth_table['test_for_server'] = False
            truth_table['test_for_accept_button'] = False
            cs.sleep_interval = cs.cfg['sleep_interval']
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
            cs.sleep_interval = cs.cfg['sleep_interval']
            truth_table['test_for_success'] = False
            if 'Other players failed to connect' in matchmaking['msg']:
                write('Match has not started! Continuing to search for a Server!', push=cs.pushbullet_dict['urgency'] + 1, push_now=True, overwrite='11', color=FgColor.Red)
                playsound('sounds/back_to_testing.wav', block=False)
                cs.mute_csgo(1)
            elif 'Failed to ready up' in matchmaking['msg']:
                write('You failed to accept! Restart searching!', push=cs.pushbullet_dict['urgency'] + 2, push_now=True, overwrite='11', color=FgColor.Red)
                playsound('sounds/failed_to_accept.wav')
                cs.mute_csgo(0)

    if truth_table['players_still_connecting']:
        lobby_data = ''.join(matchmaking['lobby_data'])
        lobby_info = cs.re_pattern['lobby_info'].findall(lobby_data)
        lobby_data = [(info, int(num.strip("'\n"))) for info, num in lobby_info]
        for i in lobby_data:
            if i[0] == 'Players':
                write(f'{i[1]} players joined.', add_time=False, overwrite='7')
            if i[0] == 'TSlotsFree' and i[1] == 0:
                join_dict['t_full'] = True
            if i[0] == 'CTSlotsFree' and i[1] == 0:
                join_dict['ct_full'] = True
            if join_dict['t_full'] and join_dict['ct_full']:
                write(f'Server full, All Players connected. Took {cs.timedelta(time_table["warmup_started"])} since match start.', push=cs.pushbullet_dict['urgency'] + 2, push_now=True, overwrite='7')
                playsound('sounds/minute_warning.wav', block=True)
                truth_table['players_still_connecting'] = False
                join_dict['t_full'], join_dict['ct_full'] = False, False
                break

    if any(True for i in matchmaking['server_abandon'] if 'Disconnect' in i):
        if not truth_table['game_over']:
            write('Server disconnected', color=FgColor.Red)
        gsi_server = cs.restart_gsi_server(gsi_server)
        truth_table['disconnected_form_last'] = True
        truth_table['players_still_connecting'] = False
        afk_dict['time'] = time.time()

    game_state = {'map_phase': gsi_server.get_info('map', 'phase'), 'round_phase': gsi_server.get_info('round', 'phase')}

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
            scoreboard['opposing_team'] = cyan('CT') if uncolorize(scoreboard['team']) == 'T' else red('T')

            afk_dict['round_values'].append(afk_dict['seconds_afk'])
            afk_dict['round_values'] = [round(time_afk, 3) for time_afk in afk_dict['round_values']]
            afk_dict['per_round'] = cs.avg(afk_dict['round_values'], 0.0)
            afk_dict['seconds_afk'] = 0.0

            try:
                scoreboard['last_round_key'] = list(scoreboard['last_round_info'].keys())[-1]
                scoreboard['last_round_info'] = scoreboard['last_round_info'][scoreboard['last_round_key']].split('_')[0].upper()
                if int(scoreboard['last_round_key']) == 15:
                    scoreboard['last_round_info'] = 'T' if scoreboard['last_round_info'] == 'CT' else 'CT'
                scoreboard['last_round_info'] = f'{scoreboard["team"]} {green("won")} the last round' if uncolorize(scoreboard['team']) == scoreboard['last_round_info'] else f'{scoreboard["team"]} {yellow("lost")} the last round'
            except AttributeError:
                scoreboard['last_round_info'] = f'You {scoreboard["team"]}, no info on the last round'

            if scoreboard['total_score'] == 14:
                scoreboard['extra_round_info'] = yellow(' - Half-Time')
            elif scoreboard['CT'] == 15 or scoreboard['T'] == 15:
                scoreboard['extra_round_info'] = yellow(' - Match Point')
            else:
                scoreboard['extra_round_info'] = ''

            write(f'Freeze Time - {scoreboard["last_round_info"]} - {scoreboard[uncolorize(scoreboard["team"])]:02d}:{scoreboard[uncolorize(scoreboard["opposing_team"])]:02d}'
                  f'{scoreboard["extra_round_info"]}{scoreboard["c4"]} - AFK: {cs.timedelta(seconds=afk_dict["per_round"])}',
                  overwrite='7')

            if win32gui.GetWindowPlacement(hwnd)[1] == 2:
                truth_table['game_minimized_freezetime'] = True
                playsound('sounds/ready_up.wav', block=True)
            if 'Half-Time' in uncolorize(scoreboard['extra_round_info']):
                playsound('sounds/ding.wav', block=True)

        elif game_state['map_phase'] == 'live' and gsi_server.get_info('player', 'steamid') == cs.steam_id:
            player_stats = gsi_server.get_info('player', 'match_stats')

    elif game_state['map_phase'] == 'live' and game_state['round_phase'] != 'freezetime':
        truth_table['first_freezetime'] = True
        truth_table['c4_round_first'] = True
        if time.time() - time_table['freezetime_started'] >= 20 and win32gui.GetWindowPlacement(hwnd)[1] == 2:
            playsound('sounds/ready_up.wav', block=False)

    if truth_table['game_minimized_freezetime']:
        message = f'Freeze Time - {scoreboard["last_round_info"]} - {scoreboard[uncolorize(scoreboard["team"])]:02d}:{scoreboard[uncolorize(scoreboard["opposing_team"])]:02d}' \
                  f'{scoreboard["extra_round_info"]}{scoreboard["c4"]} - AFK: {cs.timedelta(seconds=afk_dict["per_round"])}'
        truth_table['game_minimized_freezetime'] = cs.round_start_msg(message, game_state['round_phase'], time_table['freezetime_started'], truth_table['game_minimized_freezetime'], win32gui.GetWindowPlacement(hwnd)[1] == 2)
    elif truth_table['game_minimized_warmup']:
        try:
            message = f'Warmup is over! Map: {green(" ".join(gsi_server.get_info("map", "name").split("_")[1:]).title())}, Team: {team}, Took: {cs.timedelta(seconds=time_table["warmup_seconds"])}'
            truth_table['game_minimized_warmup'] = cs.round_start_msg(message, game_state['round_phase'], time_table['freezetime_started'], truth_table['game_minimized_warmup'], win32gui.GetWindowPlacement(hwnd)[1] == 2)
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
            write('Warmup is over! Map: {map}, Team: {team}, Took: {time}'.format(team=team, map=green(' '.join(gsi_server.get_info('map', 'name').split('_')[1:]).title()), time=cs.timedelta(seconds=time_table['warmup_seconds'])),
                  push=cs.pushbullet_dict['urgency'] + 2, push_now=True, overwrite='7')
            time_table['match_started'] = time.time()
            time_table['freezetime_started'] = time.time()
            if win32gui.GetWindowPlacement(hwnd)[1] == 2:
                truth_table['game_minimized_warmup'] = True
                playsound('sounds/ready_up_warmup.wav', block=False)
            afk_dict['round_values'] = []

        if game_state['map_phase'] is None:
            truth_table['still_in_warmup'] = False
            playsound('sounds/fail.wav', block=True)
            write('Match did not start', overwrite='1', color=FgColor.Red, push=cs.pushbullet_dict['urgency'] + 2, push_now=True)

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
                    cs.anti_afk(hwnd, cs.cfg['taskbar_position'])
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
        timings = {'match': time.time() - time_table['match_started'], 'search': time_table['match_accepted'] - time_table['search_started'], 'afk': sum(afk_dict['round_values']), 'afk_round': cs.avg(afk_dict['round_values'], 0.0)}

        write(f'The match is over! - {score[team[0]]:02d}:{score[team[1]]:02d}', color=FgColor.Red)

        write(f'Match duration: {cs.time_output(timings["match"], average["match_time"][0])}', add_time=False)
        write(f'Search-time:    {cs.time_output(timings["search"], average["search_time"][0])}', add_time=False)
        write(f'AFK-time:       {cs.time_output(timings["afk"], average["afk_time"][0])}', add_time=False)
        write(f'AFK per Round:  {cs.time_output(timings["afk_round"], average["afk_time"][2])}', add_time=False)
        write(f'                {(timings["afk"] / timings["match"]):.1%} of match duration', add_time=False)

        if gsi_server.get_info('map', 'mode') == 'competitive' and game_state['map_phase'] == 'gameover' and not truth_table['test_for_warmup'] and not truth_table['still_in_warmup']:
            if truth_table['monitoring_since_start']:
                match_time = str(round(time.time() - time_table['match_started']))
                search_time = str(round(time_table['match_accepted'] - time_table['search_started']))
                afk_time = str(round(sum(afk_dict['round_values'])))
            else:
                match_time, search_time, afk_time = '', '', ''

            total_time = (f'Time in competitive matchmaking: {cs.timedelta(seconds=average["match_time"][1])}',
                          f'Time in the searching queue: {cs.timedelta(seconds=average["search_time"][1])}',
                          f'Time afk while being ingame: {cs.timedelta(seconds=average["afk_time"][1])}')
            for time_str in total_time:
                write(time_str, add_time=False)

            player_stats['map'] = score['map']
            player_stats['match_score'] = score[team[0]], score[team[1]]
            player_stats['match_time'] = match_time
            player_stats['wait_time'] = search_time
            player_stats['afk_time'] = afk_time

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
                    write(f'You will play on {green(" ".join(saved_map.split("_")[1:]).title())} as {team} in the first half. Last Games: {cs.match_win_list(8, cs.steam_id)}',
                          add_time=True, push=cs.pushbullet_dict['urgency'] + 2, push_now=True, overwrite='12')
                    truth_table['still_in_warmup'] = True
                    truth_table['test_for_warmup'] = False
                    truth_table['players_still_connecting'] = True
                    time_table['warmup_started'] = time.time()
                    if cs.cfg['player_webhook']:
                        cs.request_status_command(hwnd, cs.cfg['taskbar_position'], key=cs.cfg['status_key'])
                        player_check = {'content': f'!check {cs.steam_id}',
                                        'avatar_url': cs.account['avatar_url']}
                        cs.send_discord_msg(player_check, cs.cfg['player_webhook'], username=f'{cs.account["name"]} - Player Info')
                    break
            elif saved_map:
                write(f'You will play on {green(" ".join(saved_map.split("_")[1:]).title())}', overwrite='12')
                game_mode = gsi_server.get_info('map', 'mode')
                if game_mode not in ['competitive', 'wingman', None]:
                    write(f'{game_mode} is not supported', color=FgColor.Yellow, overwrite='1')
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
