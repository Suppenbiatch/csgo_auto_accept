import asyncio
import re
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime
from datetime import timedelta
from functools import partial
from typing import List, Union

import pyppeteer.browser
from bs4 import BeautifulSoup
from pyppeteer import launch
from pyppeteer.errors import TimeoutError as PyTimeoutError
from pyppeteer.page import Page, ElementHandle
from pyppeteer_stealth import stealth

from async_csgostats.csgostats_objects import Rank


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


async def multiple_ranks(steam_ids: List[Union[int, str]]):
    browser = await launch(headless=False)
    funcs = [partial(get_rank_for_steamid, browser, steam_id) for steam_id in steam_ids]
    ranks = await asyncio.gather(*[func() for func in funcs])
    await browser.close()
    return ranks


async def single_rank(steam_id: Union[int, str]):
    browser = await launch(headless=False)
    rank = await get_rank_for_steamid(browser, steam_id)
    await browser.close()
    return rank


async def get_rank_for_steamid(browser: pyppeteer.browser.Browser, steam_id):
    url = f'https://csgostats.gg/player/{steam_id}?date_start=1546297200&date_end=1546383599'
    page = await browser.newPage()
    await stealth(page)
    await page.goto(url)
    await wait_for_ready(page)
    text = await page.evaluate('document.body.innerHTML')
    loop = asyncio.get_running_loop()
    with ThreadPoolExecutor() as pool:
        r = await loop.run_in_executor(pool, parse_player_profile, text)
    await page.close()
    return r


def parse_player_profile(text):
    page_soup = BeautifulSoup(text, 'lxml')
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
    else:
        comp_matches_played = 0

    rank = Rank(rank_int, last_game, days_ago, comp_matches_played)
    return rank


def parse_last_match_date(datetime_str: str) -> datetime:
    """
    :param datetime_str: A date/time string of a player profile from csgostats.gg
    :return: corresponding datetime object
    """
    minutes = re.search('(\d+) minutes? ago', datetime_str)
    if minutes is not None:
        return datetime.now() - timedelta(minutes=int(minutes.group(1)))
    hours = re.search('(\d+) hours? ago', datetime_str)
    if hours is not None:
        return datetime.now() - timedelta(hours=int(hours.group(1)))
    if 'Yesterday' in datetime_str:
        return datetime.now() - timedelta(days=1)

    clean_date = re.sub(r'(\d)(st|nd|rd|th)', r'\1', datetime_str)
    date_obj = re.search('Last Game [\w]+, (.+)', clean_date)
    week_obj = re.search('Last Game (\d+) days? ago', clean_date)

    if date_obj is None and week_obj is None:
        # print(f'debug: {clean_date}, {datetime_str}')
        return datetime.now()

    if date_obj is not None:
        date = date_obj.group(1)

        year_obj = re.search('(\d+ \w+, \d+)', date)
        if year_obj is not None:  # YEAR is included in date string
            dt_obj = datetime.strptime(year_obj.group(1), '%d %b, %y')
            dt_obj = dt_obj.replace(hour=11, minute=00)
        else:  # YEAR IS NOT INCLUDED:
            dt_obj = datetime.strptime(f'{date}, {datetime.now().year}', '%d %b, %Y')
    else:
        dt_obj = datetime.now() - timedelta(days=int(week_obj.group(1)))

    return dt_obj


def dt_to_str_shortcut(dt_obj: datetime) -> tuple:
    """
    :param dt_obj: a datetime object
    :return: an abbreviation and time difference
    """
    time_dif = (datetime.now() - dt_obj).days
    if time_dif < 0:
        dt_obj = dt_obj.replace(year=dt_obj.year - 1)
        time_dif = (datetime.now() - dt_obj).days
    if time_dif == 0:
        return 'D', time_dif
    elif time_dif <= 7:
        return 'W', time_dif
    elif time_dif <= 31:
        return 'M', time_dif
    elif time_dif <= 365:
        return 'Y', time_dif
    else:
        return 'Y+', time_dif


if __name__ == '__main__':
    pass
