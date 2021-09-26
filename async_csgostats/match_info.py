import asyncio
import re
from datetime import datetime
from functools import partial
from typing import List, Tuple, Any, Optional

from bs4 import BeautifulSoup, Tag
from pyppeteer import launch
from pyppeteer.browser import Browser
from pyppeteer.errors import TimeoutError as PyTimeoutError
from pyppeteer.page import Page, ElementHandle
from pyppeteer_stealth import stealth

from async_csgostats.csgostats_objects import Rank, Match, CSSPlayer, Stats


async def wait_for_ready(page: Page):
    while True:
        info = await page.evaluate("document.readyState")
        if info == 'complete':
            break
        await asyncio.sleep(0.5)
    try:
        await page.waitForSelector('div[id*=usercentrics-root]', visible=True, timeout=1000)
    except PyTimeoutError:
        return
    button = await page.evaluateHandle("""() => document.querySelector('#usercentrics-root').shadowRoot.querySelector('button[data-testid="uc-accept-all-button"]')""")
    if isinstance(button, ElementHandle):
        await button.click()
    return


async def multiple_match_info(ids: List[Tuple[int, int, str]], use_signal: bool = True):
    browser = await launch(headless=False,
                           handleSIGINT=use_signal,
                           handleSIGTERM=use_signal,
                           handleSIGHUP=use_signal)
    funcs = [partial(get_match_infos, browser, match_id, steam_id) for match_id, steam_id, _ in ids]
    matches = await asyncio.gather(*[func() for func in funcs])

    await browser.close()
    for i, match in enumerate(matches):
        match.sharecode = ids[i][2]
    return matches


async def single_match_info(match_id, steam_id, use_signal: bool = True):
    browser = await launch(headless=False,
                           handleSIGINT=use_signal,
                           handleSIGTERM=use_signal,
                           handleSIGHUP=use_signal)
    match = await get_match_infos(browser, match_id, steam_id)
    await browser.close()
    return match


async def multiple_team_indicators(ids: List[Tuple[Any, Any, Any]]):
    browser = await launch(headless=False)
    funcs = [partial(get_player_status, browser, match_id, steam_id, compared_to) for match_id, steam_id, compared_to in ids]
    indicators = await asyncio.gather(*[func() for func in funcs])
    await browser.close()
    return indicators


async def get_player_status(browser: Browser, match_id, steam_id, compared_to) -> str:
    """
    gets whether steam_id was in compared_to team or not
    :param browser: a pyppeteer browser instance
    :param match_id: a csgostats match id
    :param steam_id: a steam_id
    :param compared_to: a steam_id
    :return: 'T' if steam_id was in compared_to team 'E' if not
    """
    match_info = await get_match_infos(browser, str(match_id), str(compared_to))
    if match_info is None:
        print(f'failed to get match data for {steam_id} in {match_id}')
        return 'U'

    all_player_ids = [player.steam_id for player in match_info.players[0]]

    if str(steam_id) in all_player_ids:
        if str(compared_to) in all_player_ids:
            player_relation = 'T'
        else:
            player_relation = 'E'
    else:
        if str(compared_to) in all_player_ids:
            player_relation = 'E'
        else:
            player_relation = 'T'
    return player_relation


async def get_match_infos(browser: Browser, match_id, steam_id):
    url = f'https://csgostats.gg/match/{match_id}'
    page = await browser.newPage()
    await stealth(page)
    await page.goto(url, timeout=0)
    await wait_for_ready(page)
    text = await page.evaluate('document.body.innerHTML')
    loop = asyncio.get_running_loop()
    r = await loop.run_in_executor(None, parse_match, text, match_id, steam_id)
    await page.close()
    return r


def parse_match(text, match_id, steam_id) -> Optional[Match]:
    """
    :param text: html of a csgostats match page
    :param match_id: the match id for the requested page
    :param steam_id: a steam id in the match
    :return: a dict of match info and player info
    """

    page_soup = BeautifulSoup(text, 'lxml')
    match_details = page_soup.select_one('div[id*="match-details"]')
    scoreboard = page_soup.select_one('table[id*="match-scoreboard"]')

    teams = (scoreboard.contents[3], scoreboard.contents[9])  # teams are stored in unnamed table rows, no better way then hard-coding the used rows
    scoreboard_header: Tag = scoreboard.contents[1]
    hltv_version = scoreboard_header.select_one('tr[class*="absolute-spans"]').find('span', {'data-original-title': re.compile('HLTV')}).attrs['data-original-title']
    all_players = [team.find_all(name='tr') for team in teams]
    players = []
    for team in all_players:
        # also has "useless" score info, we need to remove that
        players.append([player for player in team if 'class' in player.attrs])

    match = Match(match_id)
    match.map = match_details.select_one('div[class*="map-text"]').text.split('_', maxsplit=1)[1].replace('_', ' ').title()
    match.score = tuple(int(score.text) for score in match_details.select('span[class*="team-score-number"]'))
    match.server = match_details.select_one('div[class*="server-loc-text"]').text
    match.timestamp = parse_match_date(match_details.select_one('div[class*="match-date-text"]').text)

    hltv_tooltip = {'version': hltv_version, 'rounds_played': sum(match.score)}
    match.players = get_player_info(players, hltv_tooltip)

    for i, team in enumerate(match.players):
        for player in team:
            if player.steam_id == str(steam_id):
                match.player = player
                score = (match.score[0], match.score[1]) if i == 0 else (match.score[1], match.score[0])
                match.score = score
                match.outcome = get_outcome(match_details.select('div[class*="team-score team"]'), team_id=i)
                match.started_as = 'T' if i == 0 else 'CT'
                break
    return match


def get_player_info(raw_players: List[List[Tag]], hltv_format: dict) -> list:
    """
    :param raw_players: a list of BeautifulSoup Tags
    :param hltv_format: indicates weather its hltv2.0 or 1.0
    :return: list of player stats
    """
    players = [[], []]

    if hltv_format['version'] == 'HLTV Rating 1.0':
        # for older matches a HLTV1.0 rating is calculated and now UtilityStats are present
        stat_keys = ['K', 'D', 'A', 'K_dif', 'KD', 'ADR', 'HS', 'KAST', 'HLTV',
                     'FK_FD_DIF', 'FK', 'FD', 'FK_T', 'FD_T', 'FK_CT', 'FD_CT',
                     'Trade_K', 'Trade_D', 'Trade_FK', 'Trade_FD',
                     'Trade_FK_T', 'Trade_FD_T', 'Trade_FK_CT', 'Trade_FD_CT',
                     'VX', 'V5', 'V4', 'V3', 'V2', 'V1',
                     'K3plus', 'K5', 'K4', 'K3', 'K2', 'K1']
    else:
        stat_keys = ['K', 'D', 'A', 'K_dif', 'KD', 'ADR', 'HS', 'KAST', 'HLTV2',
                     'EF', 'FA', 'EBT', 'UD',
                     'FK_FD_DIF', 'FK', 'FD', 'FK_T', 'FD_T', 'FK_CT', 'FD_CT',
                     'Trade_K', 'Trade_D', 'Trade_FK', 'Trade_FD',
                     'Trade_FK_T', 'Trade_FD_T', 'Trade_FK_CT', 'Trade_FD_CT',
                     'VX', 'V5', 'V4', 'V3', 'V2', 'V1',
                     'K3plus', 'K5', 'K4', 'K3', 'K2', 'K1']

    for i, team in enumerate(raw_players):
        for player_tag in team:
            info = player_tag.select_one('a[class*="player-link"]')
            steam_id = re.search(r'/player/(\d+)', info.attrs['href']).group(1)
            player = CSSPlayer(steam_id)

            player.username = info.text.lstrip('\n').rstrip('\n')
            # rank = player_tag.find(name='img', src=True, attrs={'width': 40})
            rank = player_tag.select_one('img.rank')
            if rank is not None:
                player.rank = Rank(int(re.search(r'ranks/(\d+)\.png', rank.attrs['src']).group(1)))
            else:
                player.rank = Rank(0)
            rank_change = player_tag.select_one('span[class*="glyphicon-chevron"]')
            if rank_change is not None:
                change = re.search(r'glyphicon-chevron-(up|down)', ' '.join(rank_change.attrs['class']))
                if change == 'up':
                    player.rank.rank_change += '+'
                elif change == 'down':
                    player.rank.rank_change += '-'
                else:
                    pass  # un-reachable

            stat_tags = player_tag.find_all(name='td', align='center')
            del stat_tags[0]
            stat_values = [re.sub(r'\n\s*', '', val.text) for val in stat_tags]
            player.stats = Stats(dict(zip(stat_keys, stat_values)))

            if hltv_format['version'] != 'HLTV Rating 1.0':
                hltv_consts = {'AvgKPR': 0.679, 'AvgSPR': 0.317, 'AvgRMK': 1.277}
                rounds = hltv_format['rounds_played']
                hltv_rating = (int(player.stats.K) / rounds / hltv_consts['AvgKPR']
                               + 0.7 * (rounds - int(player.stats.D)) / rounds / hltv_consts['AvgSPR']
                               + (int(player.stats.K1) + 4 * int(player.stats.K2) + 9 * int(player.stats.K3) + 16 * int(player.stats.K4) + 25 * int(player.stats.K5))
                               / rounds / hltv_consts['AvgRMK']) / 2.7
                player.stats.HLTV = round(hltv_rating, 2)
            players[i].append(player)
    return players


def get_outcome(winning_info_classes: List[Tag], team_id: int):
    if winning_info_classes:
        winning_info = winning_info_classes[team_id]
        if 'winning-team' in winning_info.attrs['class']:
            outcome = 'W'
        elif 'losing-team' in winning_info.attrs['class']:
            outcome = 'L'
        elif 'tied-team' in winning_info.attrs['class']:
            outcome = 'D'
        else:
            print(f'failed to find outcome in {winning_info.attrs}')
            outcome = 'U'
    else:
        print('failed to find outcome class')
        outcome = 'U'
    return outcome


def parse_match_date(datetime_str: str) -> int:
    """
    :param datetime_str: A date/time string form a match from csgostats.gg
    :return: the unix epcho timestamp from set date
    """
    clean_date = re.sub(r'(\d)(st|nd|rd|th)', r'\1', datetime_str)
    dt_obj = datetime.strptime(f'{clean_date} +0000', '%d %b %Y %H:%M:%S %z')
    return int(datetime.timestamp(dt_obj))


async def generate_csv_match(steam_id, csv_str):
    csv_header = ['sharecode', 'match_id', 'map', 'team_score', 'enemy_score', 'outcome', 'start_team',
                  'match_time', 'wait_time', 'afk_time', 'mvps', 'points', 'kills', 'assists', 'deaths',
                  '5k', '4k', '3k', '2k', '1k', 'K/D', 'ADR', 'HS%', 'KAST', 'HLTV', 'rank', 'username', 'server', 'timestamp']
    data = dict(zip(csv_header, csv_str.split(';')))
    if not data['match_id']:
        return

    match = await single_match_info(data['match_id'], steam_id)
    player_stats: Stats = match.player.stats
    data['match_id'] = match.match_id
    data['map'] = match.map
    data['team_score'] = match.score[0]
    data['enemy_score'] = match.score[1]
    data['outcome'] = match.outcome
    data['start_team'] = match.started_as
    data['kills'] = player_stats.K
    data['assists'] = player_stats.A
    data['deaths'] = player_stats.D
    data['5k'] = player_stats.K5
    data['4k'] = player_stats.K4
    data['3k'] = player_stats.K3
    data['2k'] = player_stats.K2
    data['1k'] = player_stats.K1
    data['ADR'] = round(float(player_stats.ADR))
    data['HS%'] = re.sub(r'\D', '', player_stats.HS)
    data['KAST'] = re.sub(r'\D', '', player_stats.KAST)
    data['HLTV'] = round(float(player_stats.HLTV) * 100)
    data['rank'] = f'{match.player.rank.rank_int}{match.player.rank.rank_change}'
    data['username'] = match.player.username
    data['server'] = match.server
    data['timestamp'] = match.timestamp

    try:
        data['K/D'] = round((float(player_stats.K) / float(player_stats.D)) * 100)
    except (ZeroDivisionError, ValueError):
        data['K/D'] = '∞'

    return data


async def main():
    r = await single_match_info(43409239, 76561199014843546)
    print(r)


if __name__ == '__main__':
    asyncio.run(main())
