import re
from datetime import datetime, timedelta


def parse_match_date(datetime_str: str) -> int:
    """
    :param datetime_str: A date/time string form a match from csgostats.gg
    :return: the unix epcho timestamp from set date
    """
    clean_date = re.sub(r'(\d)(st|nd|rd|th)', r'\1', datetime_str)
    dt_obj = datetime.strptime(f'{clean_date} +0000', '%d %b %Y %H:%M:%S %z')
    return int(datetime.timestamp(dt_obj))


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


def email_decode(encoded_string: str) -> str:
    """
    :param encoded_string: a cloudflare encode email address
    :return: an decoded email address
    """
    r = int(encoded_string[:2], 16)
    email = ''.join([chr(int(encoded_string[i:i + 2], 16) ^ r) for i in range(2, len(encoded_string), 2)])
    return email


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
