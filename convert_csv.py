import csv
import os


def update_csv(csv_path, header):
    with open(csv_path, 'r', newline='') as f:
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

    with open(csv_path, 'w', newline='') as f:
        writer = csv.DictWriter(f, fieldnames=header, delimiter=';', lineterminator='\n')
        writer.writeheader()
        writer.writerows(rows)
    return rows


path = os.path.join(os.getenv('APPDATA'), 'CSGO AUTO ACCEPT')

(_, _, filenames) = next(os.walk(path))
files = [(os.path.join(path, file) , file) for file in filenames if file.endswith('.csv')]

new_header = ['sharecode', 'match_id', 'map', 'team_score', 'enemy_score', 'match_time', 'wait_time', 'afk_time', 'mvps', 'points', 'kills', 'assists', 'deaths', '5k', '4k', '3k', '2k', '1k', 'K/D', 'ADR', 'HS%', 'HLTV', 'rank', 'username']

for path, filename in files:
    print(f'Updating {filename} at {path}')
    update_csv(path, new_header)
