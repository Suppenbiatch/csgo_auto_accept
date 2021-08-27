import csv
import os.path
import sqlite3
from datetime import datetime

import consts


def epoch_to_iso(epoch_time):
    return datetime.fromtimestamp(float(epoch_time), datetime.now().astimezone().tzinfo).isoformat()


def write_data_csv(path, data, header):
    with open(path, 'w', encoding='utf-8', newline='') as f:
        writer = csv.DictWriter(f, fieldnames=header, restval='', delimiter=';')
        writer.writeheader()
        writer.writerows(data)
    return


def get_csv_list(path, header=None):
    if header is None:
        header = consts.csv_header

    if not os.path.isfile(path):
        with open(path, 'w', newline='', encoding='utf-8') as f:
            writer = csv.DictWriter(f, fieldnames=header, delimiter=';', lineterminator='\n')
            writer.writeheader()

    with open(path, 'r', newline='', encoding='utf-8') as f:
        data = list(csv.DictReader(f, fieldnames=header, delimiter=';', restval=''))
    first_element = tuple(data[0].values())
    if all(head == first_element[i] for i, head in enumerate(header)):  # File has a valid header
        del data[0]  # Remove the header from the data
        return data

    # rewrite file with the new header and reuse all the old values
    with open(path, 'r', newline='', encoding='utf-8') as f:
        data = list(csv.DictReader(f, delimiter=';', restval=''))
    rows = []
    for i in data:
        row_dict = {}
        for key in header:
            try:
                row_dict[key] = i[key]
            except KeyError:
                row_dict[key] = ''
        rows.append(row_dict)
    write_data_csv(path, rows, header)
    return rows


def find_dict(lst: list, key: str, value):
    for i, dic in enumerate(lst):
        if dic[key] == value:
            return i
    return None


def convert_string_to_list(_str: str) -> list:
    return list(map(int, _str.lstrip('[').rstrip(']').split(', ')))


def csv_path_for_steamid(steamid):
    return os.path.join(os.path.join(os.getenv('APPDATA'), 'CSGO AUTO ACCEPT', f'last_game_{steamid}.csv'))


def avg(lst: list, non_return=None):
    if not lst:
        return non_return
    return sum(lst) / len(lst)


def create_table(db_path):
    if os.path.isfile(db_path):
        return
    with sqlite3.connect(db_path) as db:
        db.execute("""CREATE TABLE IF NOT EXISTS players (
                                steam_id integer,
                                name text,
                                match_ids text,
                                match_count integer,
                                timestamp integer
                                )""")
        db.commit()


def get_players_from_db(db_path, steam_ids):
    insertions = ('? , ' * len(steam_ids)).strip(' , ')
    sql = f"""select * from players where steam_id in ({insertions})"""
    with sqlite3.connect(db_path) as db:
        db.row_factory = sqlite3.Row
        cur = db.execute(sql, steam_ids)
        results = cur.fetchall()
    rows = [dict(row) for row in results]
    for player in rows:
        player['match_ids'] = player['match_ids'].split(';')
    return rows


def add_and_update_players(db_path, updated_players, new_players):
    with sqlite3.connect(db_path) as db:
        for player in updated_players:
            sql = f"""UPDATE players 
                SET name = ?, 
                    match_ids = ?,
                    match_count = ?,
                    timestamp = ?
                WHERE 
                    steam_id = ?"""
            db.execute(sql, (player['name'], player['match_ids'], player['match_count'], player['timestamp'], player['steam_id']))

        new_players_tuple = [(player['steam_id'], player['name'], player['match_ids'], player['match_count'], player['timestamp']) for player in new_players]
        db.executemany("""INSERT INTO players (steam_id, name, match_ids, match_count, timestamp) VALUES (?, ?, ?, ?, ?)""", new_players_tuple)
        db.commit()
