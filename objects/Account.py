import random
import re
from configparser import ConfigParser, SectionProxy

import requests
from typing import List, Tuple


class SteamAccount(object):
    def __init__(self, steam_id, auth_code: str, match_token: str, auto_buy):
        self.name = ''
        self.steam_id = str(steam_id)
        self.steam_id_3 = str(int(self.steam_id) - 76561197960265728)
        self.auth_code = str(auth_code)
        self.match_token = str(match_token)
        self.avatar_url = 'https://i.imgur.com/MhAf20U.png'
        self.avatar_hash = ''
        self.autobuy: List[Tuple[int, str]] = auto_buy
        self.color = 0

    def __eq__(self, other):
        if isinstance(other, SteamAccount):
            return self.steam_id == other.steam_id
        return self.steam_id == str(other)

    def __repr__(self):
        return f'SteamAccount(steam_id={self.steam_id}, name={self.name})'

    def __str__(self):
        return self.__repr__()

    def __hash__(self):
        return hash(self.steam_id)


def get_accounts_from_cfg(parser: ConfigParser) -> List[SteamAccount]:
    accounts = []
    for i in parser.sections():
        if i.lower().startswith('account'):
            section: SectionProxy = parser[i]
            auto_buy = []
            steam_id = section.get('Steam ID')
            auth_code = section.get('Authentication Code')
            match_token = section.get('Match Token')
            for key, value in section.items():
                equip_value = re.search(r'autobuy (\d+)', key)
                if equip_value is not None:
                    equip_value = int(equip_value.group(1))
                    auto_buy.append((equip_value, value))

            if not auto_buy:
                if 'AutoBuy' in section:
                    script = section.get('AutoBuy')
                    if script:
                        auto_buy = [(0, script)]
            else:
                auto_buy.sort(key=lambda x: x[0], reverse=True)
            if not auto_buy:
                auto_buy = None

            accounts.append(SteamAccount(steam_id, auth_code, match_token, auto_buy))
    steam_ids = ','.join([account.steam_id for account in accounts])
    steam_api_key = parser.get('csgostats.gg', 'API Key')
    steam_api_error = False
    try:
        r = requests.get(f'http://api.steampowered.com/ISteamUser/GetPlayerSummaries/v0002/?key={steam_api_key}&steamids={steam_ids}')
        r.raise_for_status()
        profiles = r.json()['response']['players']
        for profile in profiles:
            for account in accounts:
                if profile['steamid'] == account.steam_id:
                    account.name = profile['personaname']
                    account.avatar_url = profile['avatarfull']
                    account.avatar_hash = profile['avatarhash']
                    break
            else:
                steam_api_error = True
    except (TimeoutError, requests.ConnectionError):
        steam_api_error = True

    if steam_api_error:
        print('INVAILD STEAM API KEY or INTERNET CONNECTION ERROR, could not fetch usernames')
        for num, account in enumerate(accounts):
            account.name = f'Unknown Name {num}'
            account.avatar_hash = f'Unknown Avatar {num}'

    colors_1 = ['00{:02x}ff', '00ff{:02x}', '{:02x}00ff', '{:02x}00ff', 'ff00{:02x}', 'ff{:02x}00']
    colors_2 = ['{:02x}ffff', 'ff{:02x}ff', 'ffff{:02x}']
    two_part_numbers = list(set(int(pattern.format(i), 16) for pattern in colors_1 for i in range(256)))
    single_part_numbers = list(set(int(pattern.format(i), 16) for pattern in colors_2 for i in range(177)))
    numbers = list(set(two_part_numbers + single_part_numbers))

    for account in accounts:
        random.seed(f'{account.name}_{account.steam_id}_{account.avatar_hash}', version=2)
        account.color = numbers[random.randint(0, len(numbers))]

    return accounts
