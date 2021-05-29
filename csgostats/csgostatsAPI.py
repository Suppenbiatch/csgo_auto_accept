import itertools
from typing import Optional, List

import cloudscraper
from bs4 import BeautifulSoup, Tag

from csgostats.csgostats_utils import *
from csgostats.entities import *


class CSGOstatsAPI(cloudscraper.CloudScraper):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

    def get_match_info(self, match_id, steam_id) -> Optional[Match]:
        """
        :param match_id: a csgostats match id
        :param steam_id: a steam id in the match
        :return: a dict of match info and player info
        """
        url = f'https://csgostats.gg/match/{match_id}'
        try:
            r = self.get(url)
        except (cloudscraper.exceptions.CaptchaException, cloudscraper.exceptions.CloudflareChallengeError):
            print('Failed to get match data because of cloudflare captcha')
            return None
        if r.status_code != 200:
            print(f'Failed to retrieve match data with code {r.status_code} for {r.url}')
            return None

        page_soup = BeautifulSoup(r.text, 'lxml')

        match_details = page_soup.select_one('div[id*="match-details"]')
        scoreboard = page_soup.select_one('table[id*="match-scoreboard"]')

        teams = (scoreboard.contents[3], scoreboard.contents[9])  # teams are stored in unnamed table rows, no better way then hard-coding the used rows
        scoreboard_header: Tag = scoreboard.contents[1]
        hltv_version = scoreboard_header.select_one('tr[class*="absolute-spans"]').find('span', title=re.compile('HLTV')).attrs['title']
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

    def get_rank(self, steam_id: str) -> Rank:
        """
        :param steam_id: a steam id
        :return: returns a rank entity
        """

        comp_matches_played = 0
        try:
            r = self.get(f'https://csgostats.gg/player/{steam_id}?mode=comp&date_start=0&date_end=1')
        except BaseException as e:
            print(f'Error ignored, error msg: {e}')
            rank = Rank(0, last_game='E', rank_age=None)
            return rank
        if r.status_code == 200:
            page_soup = BeautifulSoup(r.text, 'lxml')
            rank = page_soup.find(name='img', src=True, width="92")
            if rank is not None:
                rank_int = int(re.search(r'ranks/(\d+)\.png', rank.attrs['src']).group(1))
            else:
                rank_int = 0
            last_game_element = page_soup.select_one('div[id*="last-game"]')
            last_game_text = re.search(r'(Last Game.+)', last_game_element.text)
            if last_game_text is not None:
                last_game, days_ago = dt_to_str_shortcut(parse_last_match_date(last_game_text.group(1)))
            else:
                last_game, days_ago = 'U', None

            comp_matches_element = page_soup.select_one('span[id*="competitve-wins"]')
            if comp_matches_element is not None:
                comp_matches_played = int(re.search(r'\nComp\. Wins\n(\d+)\n', comp_matches_element.text).group(1))

            rank = Rank(rank_int, last_game, days_ago, comp_matches_played)
        else:
            rank = Rank(0, 'E', None, 0)
        return rank

    def get_player_status(self, match_id, steam_id, compared_to) -> str:
        """
        gets whether steam_id was in compared_to team or not
        :param match_id: a csgostats match id
        :param steam_id: a steam_id
        :param compared_to: a steam_id
        :return: 'T' if steam_id was in compared_to team 'E' if not
        """
        match_info = self.get_match_info(str(match_id), str(compared_to))
        if match_info is None:
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

    def get_scrimmage_match_ids(self, steam_id) -> Optional[List[int]]:
        """
        :param steam_id: a valid steam id
        :return: a list of match ids that have been tracked as scrimmage matches
        """
        url = f'https://csgostats.gg/player/{steam_id}?mode=scrimmage&date_start=&date_end=#/'
        try:
            r = self.get(url)
        except (cloudscraper.exceptions.CaptchaException, cloudscraper.exceptions.CloudflareChallengeError):
            print('Failed to get csgostats data because of cloudflare captcha')
            return None
        if r.status_code != 200:
            print(f'Failed to retrieve match data with code {r.status_code}')
            return None
        if 'No matches have been added for this player' in r.text:
            return None
        match_str = re.search(r'"matches":\[[0-9, ]+]', r.text)
        if match_str is None:
            return []
        match_ids = re.findall(r'(\d+)[, ]*', match_str.group())
        return list(map(int, match_ids))

    def is_scrimmage_match(self, match_id, steam_id, ignored_ids=None, use_match_info: bool = True) -> bool:
        """
        :param match_id: a match id to check
        :param steam_id: a steam id from a player in the match
        :param ignored_ids: a list of steam ids that can be ignored
        :param use_match_info: If True the match id will first be request and then another player will be used to get scrimmage info
        :return: True if match_id is a scrimmage match False if not
        """
        if use_match_info:
            if ignored_ids is None:
                ignored_ids = [76561199014437353, 76561199014843546]
            ignored_ids.append(int(steam_id))
            ignored_ids = list(set(ignored_ids))

            match_info = self.get_match_info(match_id, None)
            players = [player for player in itertools.chain.from_iterable(match_info.players) if int(player.steam_id) not in ignored_ids]
            players.sort(key=lambda x: int(x.steam_id), reverse=True)  # crude sort by account age
            # youngest account first, has the highest chance for the fewest matches added, ergo fastest csgostats response
            for player in players:
                scrimmage_ids = self.get_scrimmage_match_ids(player.steam_id)
                if scrimmage_ids is not None:
                    break
            else:
                print('no player has returned a scrimmage id list using fallback')
                scrimmage_ids = self.get_scrimmage_match_ids(steam_id)
        else:
            scrimmage_ids = self.get_scrimmage_match_ids(steam_id)
        return int(match_id) in scrimmage_ids


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
            rank = player_tag.find(name='img', src=True, attrs={'width': 45})
            if rank is not None:
                player.rank = Rank(re.search(r'ranks/(\d+)\.png', rank.attrs['src']).group(1))
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


if __name__ == '__main__':
    pass
