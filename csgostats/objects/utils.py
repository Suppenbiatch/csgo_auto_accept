import asyncio
import logging
import re
from datetime import datetime, timedelta
from functools import reduce
from itertools import islice
from typing import Sequence, Iterator

from pyppeteer.page import Page
from pytz import utc

logger = logging.getLogger('csgostats_utils')


def grouped(iterable: Sequence, n: int):
    """
    Takes an iterable and returns a list of list sliced in n sized chunks with no padding
    """
    it = iter(iterable)
    return iter(lambda: tuple(islice(it, n)), ())


async def wait_for_ready(page: Page):
    async def load_page():
        while True:
            info = await page.evaluate("document.readyState")
            if info == 'complete':
                break
            await asyncio.sleep(0.05)

    try:
        await asyncio.wait_for(load_page(), timeout=1.0)
    except asyncio.TimeoutError:
        logger.warning('page loading timeout')
    return


def parse_last_match_date(datetime_str: str) -> datetime:
    """
    :param datetime_str: A date/time string of a player profile from csgostats.gg
    :return: corresponding datetime object
    """

    now = datetime.now(tz=utc)
    minutes = re.search(r'(\d+) minutes? ago', datetime_str)
    if minutes is not None:
        return now - timedelta(minutes=int(minutes.group(1)))
    hours = re.search(r'(\d+) hours? ago', datetime_str)
    if hours is not None:
        return now - timedelta(hours=int(hours.group(1)))
    if 'Yesterday' in datetime_str:
        return now - timedelta(days=1)

    clean_date = re.sub(r'(\d)(st|nd|rd|th)', r'\1', datetime_str)
    date_obj = re.search(r'Last Game [\w]+, (.+)', clean_date)
    week_obj = re.search(r'Last Game (\d+) days? ago', clean_date)

    if date_obj is not None:
        date = date_obj.group(1)
        year_obj = re.search(r'(\d+ \w+, \d+)', date)
        if year_obj is not None:  # YEAR is included in date string
            dt = datetime.strptime(year_obj.group(1), '%d %b, %y')
            dt = dt.replace(hour=11, minute=00, tzinfo=utc)
        else:  # YEAR IS NOT INCLUDED:
            dt = datetime.strptime(f'{date}, {datetime.now().year}', '%d %b, %Y')
            dt = dt.replace(tzinfo=utc)
    else:
        dt = now - timedelta(days=int(week_obj.group(1)))
    return dt


def uniq(iterable: Iterator, key=lambda x: hash(x)):
    """
    Remove duplicates from an iterable. Preserves order.
    """

    # Enumerate the list to restore order lately; reduce the sorted list; restore order
    def append_unique(acc, item):
        return acc if key(acc[-1][1]) == key(item[1]) else acc.append(item) or acc

    srt_enum = sorted(enumerate(iterable), key=lambda item: key(item[1]))
    return [item[1] for item in sorted(reduce(append_unique, srt_enum, [srt_enum[0]]))]
