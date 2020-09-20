import time
import webbrowser

import win32api
import win32con
import win32gui
from color import uncolorize, FgColor, red, green, yellow, blue, magenta, cyan
from playsound import playsound

import cs
from GSI import server
from cs import write


# noinspection PyShadowingNames,PyUnusedLocal
def enum_cb(hwnd, results):
    winlist.append((hwnd, win32gui.GetWindowText(hwnd)))


def restart_gsi_server():
    global gsi_server
    if gsi_server.running:
        gsi_server.shutdown()
    gsi_server = server.GSIServer(('127.0.0.1', 3000), "IDONTUSEATOKEN")
    gsi_server.start_server()


# BOOLEAN, TIME INITIALIZATION
truth_table = {'test_for_accept_button': False, 'test_for_warmup': False, 'test_for_success': False, 'first_ocr': True, 'testing': False, 'first_push': True, 'still_in_warmup': False, 'test_for_server': False, 'first_freezetime': True,
               'gsi_server_running': False, 'game_over': False, 'monitoring_since_start': False, 'players_still_connecting': False, 'first_game_over': True, 'disconnected_form_last': False, 'c4_round_first': True, 'steam_error': False,
               'is_not_ingame_round_start': False, 'discord_output': True}
time_table = {'csgostats_retry': time.time(), 'warmup_test_timer': time.time(), 'search_started': time.time(), 'console_read': time.time(), 'timed_execution_time': time.time(), 'match_accepted': time.time(),
              'match_started': time.time(), 'freezetime_started': time.time(), 'join_warmup_time': 0.0}
matchmaking = {'msg': [], 'update': [], 'players_accepted': [], 'lobby_data': [], 'server_found': False, 'server_ready': False}
afk_dict = {'time': time.time(), 'still_afk': [], 'start_time': time.time(), 'seconds_afk': 0, 'player_info': {'steamid': 0, 'state': {}}}
join_dict = {'t_full': False, 'ct_full': False}
scoreboard = {'CT': 0, 'T': 0, 'last_round_info': '', 'last_round_key': '0', 'extra_round_info': '', 'player': {}}
player_stats = {}

gsi_server = server.GSIServer(('127.0.0.1', 3000), "IDONTUSEATOKEN")

hwnd, hwnd_old = 0, 0
csgo_window_status = {'server_found': 2, 'new_tab': 2, 'in_game': 0}
toplist, csgo = [], []

current_account = 0
retryer = []

game_state = {'map_phase': []}
cs.mute_csgo(0)

blue(), magenta()
write('READY', color=FgColor.Green)


while True:
    if win32api.GetAsyncKeyState(cs.cfg['activate_script']) & 1 and not game_state['map_phase'] in ['live', 'warmup']:  # F9 (ACTIVATE / DEACTIVATE SCRIPT)
        truth_table['test_for_server'] = not truth_table['test_for_server']
        write(f'Looking for game: {truth_table["test_for_server"]}', overwrite='1')
        if truth_table['test_for_server']:
            playsound('sounds/activated.wav', block=False)
            time_table['search_started'] = time.time()
            cs.mute_csgo(1)
        elif not truth_table['test_for_server']:
            playsound('sounds/deactivated.wav', block=False)
            cs.mute_csgo(0)

    if win32api.GetAsyncKeyState(cs.cfg['activate_push_notification']) & 1:  # F8 (ACTIVATE / DEACTIVATE PUSH NOTIFICATION)
        cs.activate_pushbullet()

    if win32api.GetAsyncKeyState(cs.cfg['info_newest_match']) & 1:  # F7 Key (UPLOAD NEWEST MATCH)
        write('Uploading / Getting status on newest match')
        queue_difference = []
        new_sharecodes = cs.getNewCSGOSharecodes(cs.getOldSharecodes(-1)[0])

        '''# HOPEFULLY TEMPORARY CSGOSTATS FIX, HAVE TO ADD GAMES MANUALLY
        write(new_sharecodes[-1]['sharecode'], color=FgColor.Magenta)
        try:
            pyperclip.copy(new_sharecodes[-1]['sharecode'])
        except (pyperclip.PyperclipWindowsException, pyperclip.PyperclipTimeoutException):
            pass
        # DONE HERE'''

        for new_code in new_sharecodes:
            retryer.append(new_code) if new_code['sharecode'] not in [old_code['sharecode'] for old_code in retryer] else retryer
        retryer = cs.UpdateCSGOstats(retryer, discord_output=truth_table['discord_output'])
        time_table['csgostats_retry'] = time.time()

    if win32api.GetAsyncKeyState(cs.cfg['open_live_tab']) & 1:  # F17 Key (OPEN WEB BROWSER ON LIVE GAME TAB)
        if hwnd:
            csgo_window_status['new_tab'] = win32gui.GetWindowPlacement(hwnd)[1]
        if csgo_window_status['new_tab'] != 2:
            win32gui.ShowWindow(hwnd, win32con.SW_MAXIMIZE)
        webbrowser.open_new_tab(f'https://csgostats.gg/player/{cs.steam_id}#/live')
        # write('new tab opened', add_time=False)
        if csgo_window_status['new_tab'] != 2:
            time.sleep(0.5)
            win32gui.ShowWindow(hwnd, win32con.SW_MAXIMIZE)

    if win32api.GetAsyncKeyState(cs.cfg['switch_accounts']) & 1:  # F16 (SWITCH ACCOUNTS)
        current_account += 1
        if current_account > len(cs.accounts) - 1:
            current_account = 0
        cs.account = cs.accounts[current_account]
        cs.CheckUserDataAutoExec(cs.account['steam_id_3'])
        write(f'current account is: {cs.account["name"]}', add_time=False, overwrite='3')

    if win32api.GetAsyncKeyState(cs.cfg['mute_csgo_toggle']) & 1:  # F6 (TOGGLE MUTE CSGO)
        write('Mute toggled!', add_time=False)
        cs.mute_csgo(2)

    if win32api.GetAsyncKeyState(cs.cfg['end_script']) & 1:  # UNBOUND (END SCRIPT)
        write('Exiting Script!')
        break

    if win32api.GetAsyncKeyState(cs.cfg['discord_key']) & 1:  # F15 (DISCORD TOGGLE)
        if cs.cfg['discord_url']:
            truth_table['discord_output'] = not truth_table['discord_output']
            if truth_table['discord_output']:
                write('Discord output activated', add_time=False, color=FgColor.Green, overwrite='13')
            else:
                write('Discord output deactivated', add_time=False, color=FgColor.Red, overwrite='13')
        else:
            write('Discord Webhook URL not set in config', color=FgColor.Yellow)

    if retryer:
        if time.time() - time_table['csgostats_retry'] > cs.cfg['auto_retry_interval']:
            retryer = cs.UpdateCSGOstats(retryer, discord_output=truth_table['discord_output'])
            time_table['csgostats_retry'] = time.time()

    winlist = []
    win32gui.EnumWindows(enum_cb, toplist)
    csgo = [(hwnd, title) for hwnd, title in winlist if 'counter-strike: global offensive' == title.lower()]

    if not csgo:
        continue
    hwnd = csgo[0][0]

    if hwnd_old != hwnd:
        truth_table['test_for_server'] = False
        hwnd_old = hwnd
        cs.steam_id = cs.getCurrentSteamUser()
        try:
            cs.account = [i for i in cs.accounts if cs.steam_id == i['steam_id']][0]
            cs.steam_id = cs.account['steam_id']
            cs.CheckUserDataAutoExec(cs.account['steam_id_3'])
        except IndexError:
            write('Account is not in the config.ini!\nScript will not work properly!', add_time=False, overwrite='9')
            playsound('sounds/fail.wav', block=False)
            exit('Update config.ini!')
        write(f'Current account is: {cs.account["name"]}', add_time=False, overwrite='9')

        if cs.check_for_forbidden_programs(winlist):
            write('A forbidden program is still running...', add_time=False)
            playsound('sounds/fail.wav', block=False)

    if not truth_table['gsi_server_running']:
        write('CS:GO GSI Server starting..', overwrite='8', color=FgColor.Yellow)
        restart_gsi_server()
        truth_table['gsi_server_running'] = True
        write('CS:GO GSI Server running..', overwrite='8', color=FgColor.Green)

    # TESTING HERE
    if win32api.GetAsyncKeyState(0x00) & 1:  # UNBOUND, 6f == '\' TEST CODE
        truth_table['testing'] = not truth_table['testing']
        # truth_table['test_for_warmup'] = True
        # write('TestCode active: %s.' % str(truth_table['testing']), add_time=False, overwrite='test_code')

    if time.time() - time_table['console_read'] > 0.2:
        time_table['console_read'] = time.time()
        matchmaking = cs.read_console()
    else:
        matchmaking = {'msg': [], 'update': [], 'players_accepted': [], 'lobby_data': [], 'server_found': False, 'server_ready': False, 'server_abandon': [], 'map': []}

    if matchmaking['update']:
        if matchmaking['update'][-1] == '1':
            if not truth_table['test_for_server']:
                truth_table['test_for_server'] = True
                write(f'Looking for match: {truth_table["test_for_server"]}', overwrite='1')
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
            # write('Server found, starting to look for accept button.', overwrite='1')
            truth_table['test_for_accept_button'] = True
            csgo_window_status['server_found'] = win32gui.GetWindowPlacement(hwnd)[1]
            win32gui.ShowWindow(hwnd, win32con.SW_MAXIMIZE)

    if truth_table['test_for_accept_button']:
        img = cs.getScreenShot(hwnd, (1265, 760, 1295, 785))
        accept_avg = cs.color_average(img, [(76, 175, 80), (90, 203, 94)])
        if cs.relate_list(accept_avg, (2, 2, 2)):
            # write('Trying to Accept.', push=pushbullet_dict['urgency'] + 1, overwrite='1')
            truth_table['test_for_accept_button'] = False

            current_cursor_position = win32api.GetCursorPos()
            for _ in range(5):
                win32gui.ShowWindow(hwnd, win32con.SW_MAXIMIZE)
                cs.click(int(win32api.GetSystemMetrics(0) / 2), int(win32api.GetSystemMetrics(1) / 1.78))
            if csgo_window_status['server_found'] == 2:  # was minimized when a server was found
                time.sleep(0.075)
                win32gui.ShowWindow(hwnd, 2)
                time.sleep(0.025)
                cs.click(0, 0)
                win32api.SetCursorPos(current_cursor_position)
            else:
                win32api.SetCursorPos(current_cursor_position)

            # write('Trying to catch a loading map.', overwrite='1')
            playsound('sounds/accept_found.wav', block=False)

    if truth_table['test_for_accept_button'] or truth_table['test_for_success']:
        if cs.str_in_list(['Match confirmed'], matchmaking['msg']):
            write(f'All Players accepted - Match has started - Took {cs.timedelta(time_table["search_started"])} since start', add_time=False, overwrite='11', color=FgColor.Green)
            truth_table['test_for_warmup'] = True
            truth_table['first_game_over'], truth_table['game_over'] = True, False
            truth_table['disconnected_form_last'] = False
            truth_table['warmup_started'] = False
            truth_table['first_freezetime'] = False
            truth_table['test_for_server'] = False
            truth_table['test_for_accept_button'] = False
            truth_table['test_for_success'] = False
            truth_table['monitoring_since_start'] = True
            cs.mute_csgo(0)
            playsound('sounds/done_testing.wav', block=False)
            time_table['match_accepted'] = time.time()
            afk_dict['time'] = time.time()
            afk_dict['start_time'] = time.time()

        for i in matchmaking['players_accepted']:
            i = i.split('/')
            players_accepted = str(int(i[1]) - int(i[0]))
            write(f'{players_accepted} Players of {i[1]} already accepted.', add_time=False, overwrite='11')

        if cs.str_in_list(['Other players failed to connect', 'Failed to ready up'], matchmaking['msg']):
            truth_table['test_for_server'] = True
            truth_table['test_for_accept_button'] = False
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
        # time_table['match_started'], time_table['match_accepted'] = time.time(), time.time()
        if not truth_table['game_over']:
            write('Server disconnected', overwrite='1')
        restart_gsi_server()
        truth_table['disconnected_form_last'] = True
        truth_table['players_still_connecting'] = False
        afk_dict['time'] = time.time()

    if time.time() - time_table['timed_execution_time'] > .5:
        time_table['timed_execution_time'] = time.time()
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

                try:
                    scoreboard['last_round_key'] = list(scoreboard['last_round_info'].keys())[-1]
                    scoreboard['last_round_info'] = scoreboard['last_round_info'][scoreboard['last_round_key']].split('_')[0].upper()
                    scoreboard['last_round_info'] = f'{scoreboard["team"]} {green("won")} the last round' if uncolorize(scoreboard['team']) == scoreboard['last_round_info'] else f'{scoreboard["team"]} {yellow("lost")} the last round'
                except AttributeError:
                    scoreboard['last_round_info'] = f'You {scoreboard["team"]}, no info on the last round'

                if scoreboard['total_score'] == 14:
                    scoreboard['extra_round_info'] = yellow(' - Half-Time')
                elif scoreboard['CT'] == 15 or scoreboard['T'] == 15:
                    scoreboard['extra_round_info'] = yellow(' - Match Point')
                else:
                    scoreboard['extra_round_info'] = ''

                write('Freeze Time - {} - {:02d}:{:02d}{}{}'.format(scoreboard['last_round_info'], scoreboard[uncolorize(scoreboard['team'])], scoreboard[uncolorize(scoreboard['opposing_team'])], scoreboard['extra_round_info'],
                                                                    scoreboard['c4']), overwrite='7')
                if win32gui.GetWindowPlacement(hwnd)[1] == 2:
                    truth_table['is_not_ingame_round_start'] = True
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

        if truth_table['is_not_ingame_round_start']:
            if win32gui.GetWindowPlacement(hwnd)[1] == 2:
                timer_stopped = ''
            else:
                truth_table['is_not_ingame_round_start'] = False
                timer_stopped = ' - ' + green('stopped')

            if game_state['round_phase'] == 'freezetime':
                time_str = green(cs.timedelta(seconds=time.time() - (time_table['freezetime_started'] + 15)))  # cs.timedelta(then=time_table['freezetime_started']) + ' - ' +
            elif time.time() - time_table['freezetime_started'] > 35:
                time_str = red(cs.timedelta(then=time_table['freezetime_started']))
            else:
                time_str = yellow(cs.timedelta(seconds=time.time() - (time_table['freezetime_started'] + 35)))  # cs.timedelta(then=time_table['freezetime_started']) + ' - ' +

            write('Freeze Time - {last_round} - {team:02d}:{enemy:02d}{extra_info}{c4_info} - {afk_time}{timer}'.format(
                last_round=scoreboard['last_round_info'],
                team=scoreboard[uncolorize(scoreboard['team'])],
                enemy=scoreboard[uncolorize(scoreboard['opposing_team'])],
                extra_info=scoreboard['extra_round_info'],
                c4_info=scoreboard['c4'],
                afk_time=time_str,
                timer=timer_stopped), overwrite='7')

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
                write('Warmup is over! Map: {map}, Team: {team}, Took: {time}'.format(team=team, map=green(gsi_server.get_info('map', 'name').split('_')[1].capitalize()), time=cs.timedelta(time_table['warmup_started'])),
                      push=cs.pushbullet_dict['urgency'] + 2, push_now=True, overwrite='7')
                time_table['match_started'] = time.time()
                time_table['freezetime_started'] = time.time()
                if win32gui.GetWindowPlacement(hwnd)[1] == 2:
                    playsound('sounds/ready_up_warmup.wav', block=False)
            if game_state['map_phase'] is None:
                truth_table['still_in_warmup'] = False
                playsound('sounds/fail.wav', block=True)
                write('Match did not start', overwrite='1', color=FgColor.Red)

        if game_state['map_phase'] in ['live', 'warmup'] and not truth_table['game_over'] and not truth_table['disconnected_form_last']:
            csgo_window_status['in_game'] = win32gui.GetWindowPlacement(hwnd)[1]
            afk_dict['still_afk'].append(csgo_window_status['in_game'] == 2)
            afk_dict['still_afk'] = [all(afk_dict['still_afk'])]
            if not afk_dict['still_afk'][0]:
                afk_dict['still_afk'] = []
                afk_dict['time'] = time.time()
            if time.time() - afk_dict['time'] >= 180:
                while True:
                    afk_dict['player_info'] = gsi_server.get_info('player')
                    afk_dict['round_phase'] = gsi_server.get_info('round', 'phase')
                    if afk_dict['round_phase'] is None:
                        afk_dict['round_phase'] = 'warmup'
                    if afk_dict['player_info']['steamid'] == cs.steam_id and afk_dict['player_info']['state']['health'] > 0 and afk_dict['round_phase'] != 'freezetime':
                        write('Ran Anti-Afk Script.', overwrite='10')
                        cs.anti_afk(hwnd)
                        break
                    if win32gui.GetWindowPlacement(hwnd)[1] != 2:
                        break
                afk_dict['still_afk'] = []
                afk_dict['time'] = time.time()

            if csgo_window_status['in_game'] != 2:
                afk_dict['start_time'] = time.time()
            elif game_state['map_phase'] == 'live':
                afk_dict['seconds_afk'] += time.time() - afk_dict['start_time']
                afk_dict['start_time'] = time.time()

        if game_state['map_phase'] == 'gameover':
            truth_table['game_over'] = True

        if truth_table['game_over'] and truth_table['first_game_over']:
            time.sleep(2)
            team = str(gsi_server.get_info('player', 'team')), 'CT' if gsi_server.get_info('player', 'team') == 'T' else 'T'
            score = {'CT': gsi_server.get_info('map', 'team_ct')['score'], 'T': gsi_server.get_info('map', 'team_t')['score'], 'map': gsi_server.get_info('map', 'name').split('_')[1].capitalize()}
            afk_dict['per_round'] = int(afk_dict['seconds_afk'] / (int(score['CT']) + int(score['T'])))
            if gsi_server.get_info('player', 'steamid') == cs.steam_id:
                player_stats = gsi_server.get_info('player', 'match_stats')
            write(f'The match is over! - {score[team[0]]:02d}:{score[team[1]]:02d}', color=FgColor.Red)
            write(f'Match duration: {cs.timedelta(time_table["match_started"])}', add_time=False)
            write(f'Search-time:    {cs.timedelta(seconds=time_table["match_accepted"] - time_table["search_started"])}', add_time=False)
            write('Time AFK:       {}, {}s per round, {:.1%} of match duration.'.format(cs.timedelta(seconds=afk_dict['seconds_afk']), afk_dict['per_round'], afk_dict['seconds_afk'] / (time.time() - time_table['match_started'])), add_time=False)

            if gsi_server.get_info('map', 'mode') == 'competitive' and game_state['map_phase'] == 'gameover' and not truth_table['test_for_warmup'] and not truth_table['still_in_warmup']:
                if truth_table['monitoring_since_start']:
                    match_time = str(int(time.time() - time_table['match_started']))
                    search_time = str(int(time_table['match_started'] - time_table['search_started']))
                    afk_time = str(int(afk_dict['seconds_afk']))
                else:
                    match_time, search_time, afk_time = '', '', ''

                average_match_time = cs.getAvgMatchTime(cs.steam_id)
                this_game_time = (time.time() - time_table['match_started'], time_table['match_accepted'] - time_table['search_started'], afk_dict['seconds_afk'], afk_dict['per_round'])
                game_time_output_strings = (('The match was {} ' + red('longer') + ' than the average match with {}', 'The match was {} ' + green('shorter') + ' than the average match with {}'),
                                            ('The search-time was {} ' + red('longer') + ' than the average search-time with {}', 'The search-time was {} ' + green('shorter') + ' than the average search-time with {}'),
                                            ('The time afk was {} ' + red('longer') + ' than the average time afk with {}', 'The time afk was {} ' + green('shorter') + ' than the average time afk with {}'),
                                            ('The time afk per round was {} ' + red('longer') + ' than the average time afk per round with {}', 'The time afk per round was {} ' + green('shorter') + ' than the average time afk per round with {}'),
                                            'Time in competitive matchmaking: {}', 'Time in the searching queue: {}', 'Time afk while being ingame: {}')
                for i, val in enumerate(average_match_time):
                    if isinstance(val, int):
                        avg_time_difference = this_game_time[i] - val
                        if avg_time_difference >= 0:
                            write(game_time_output_strings[i][0].format(cs.timedelta(seconds=avg_time_difference), cs.timedelta(seconds=val)), add_time=False)
                        else:
                            write(game_time_output_strings[i][1].format(cs.timedelta(seconds=avg_time_difference), cs.timedelta(seconds=val)), add_time=False)
                    elif isinstance(val, str):
                        write(game_time_output_strings[i].format(val), add_time=False)

                new_sharecodes = cs.getNewCSGOSharecodes(cs.getOldSharecodes(-1)[0],
                                                         played_map=score['map'],
                                                         team_score=score[team[0]],
                                                         enemy_score=score[team[1]],
                                                         match_time=match_time,
                                                         wait_time=search_time,
                                                         afk_time=afk_time,
                                                         player_stats=player_stats)

                '''# HOPEFULLY TEMPORARY CSGOSTATS FIX, HAVE TO ADD GAMES MANUALLY
                [write(i['sharecode'], add_time=False, color=FgColor.Magenta) for i in new_sharecodes]
                try:
                    pyperclip.copy(new_sharecodes[-1]['sharecode'])
                except (pyperclip.PyperclipWindowsException, pyperclip.PyperclipTimeoutException):
                    pass
                # DONE HERE'''

                try:
                    for new_code in new_sharecodes:
                        retryer.append(new_code) if new_code['sharecode'] not in [old_code['sharecode'] for old_code in retryer] else retryer
                    retryer = cs.UpdateCSGOstats(retryer, discord_output=truth_table['discord_output'])
                    time_table['csgostats_retry'] = time.time()

                except TypeError:
                    write('ERROR IN GETTING NEW MATCH CODE! TRY PRESSING "F7" to add it manually')

            truth_table['game_over'] = False
            truth_table['first_game_over'] = False
            truth_table['monitoring_since_start'] = False
            time_table['match_started'], time_table['match_accepted'] = time.time(), time.time()
            afk_dict['seconds_afk'], afk_dict['time'] = 0, time.time()

    if truth_table['testing']:
        pass

    if truth_table['test_for_warmup']:
        time_table['warmup_started'] = time.time()
        try:
            saved_map = matchmaking['map'][-1]
        except IndexError:
            saved_map = ''
        while True:
            if time.time() - time_table['warmup_started'] > 1:
                time_table['warmup_started'] = time.time()
                if not saved_map:
                    try:
                        saved_map = cs.read_console()['map'][-1]
                    except IndexError:
                        pass
                elif gsi_server.get_info('map', 'phase') == 'warmup' and gsi_server.get_info('map', 'name') == saved_map:
                    # write('Warmup detected', overwrite='12')
                    if gsi_server.get_info('player', 'team') is not None:
                        team = red(gsi_server.get_info('player', 'team')) if gsi_server.get_info('player', 'team') == 'T' else cyan(gsi_server.get_info('player', 'team'))
                        write(f'You will play on {green(saved_map.split("_")[1].capitalize())} as {team} in the first half.', add_time=True, push=cs.pushbullet_dict['urgency'] + 2, push_now=True, overwrite='12')
                        truth_table['still_in_warmup'] = True
                        truth_table['players_still_connecting'] = True
                        time_table['warmup_started'] = time.time()
                        truth_table['test_for_warmup'] = False
                        break
                elif saved_map:
                    write(f'You will play on {green(saved_map.split("_")[1].capitalize())}', overwrite='12')
                    game_mode = gsi_server.get_info('map', 'mode')
                    if game_mode not in ['competitive', 'wingman', None]:
                        write(f'{game_mode} is not supported', color=FgColor.Yellow, overwrite='1')
                        truth_table['test_for_warmup'] = False
                        truth_table['first_game_over'] = False
                        break

if cs.console_window['isatty']:
    if cs.overwrite_dict['end'] != '\n':
        print('')
if gsi_server.running:
    gsi_server.shutdown()
exit('ENDED BY USER')
