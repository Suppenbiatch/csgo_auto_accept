import glob
import os.path
from datetime import datetime


def print_all_logs():
    files = glob.glob('Logs/*.log')
    if len(files) == 0:
        print('No Log files found!')
        return
    sort_lst = []
    for file in files:
        filename = os.path.basename(file)
        dt = datetime.strptime(filename, 'AALog-%Y%m%d-%H%M%S.log')
        sort_lst.append((file, dt))
    sort_lst.sort(key=lambda x: x[1])
    sorted_files, _ = list(zip(*sort_lst))
    for file in sorted_files:
        print(f'File: {file}')
        print_file(file)
        print('')


def print_file(path: str):
    with open(path, 'r', encoding='utf-8') as fp:
        for line in fp:
            print(line.strip())


if __name__ == '__main__':
    print_all_logs()