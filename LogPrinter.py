import glob
import os.path
import re
from datetime import datetime

from typing import List


def sort_log_files() -> List[str]:
    files = glob.glob('Logs/*.log')
    if len(files) == 0:
        print('No Log files found!')
        return []
    sort_lst = []
    for file in files:
        filename = os.path.basename(file)
        dt = datetime.strptime(filename, 'AALog-%Y%m%d-%H%M%S.log')
        sort_lst.append((file, dt))
    sort_lst.sort(key=lambda x: x[1])
    sorted_files, _ = list(zip(*sort_lst))
    return list(sorted_files)


def print_all_logs():
    files = sort_log_files()
    for file in files:
        print(f'File: {file}')
        print_file(file)
        print('')


def print_file(path: str):
    with open(path, 'r', encoding='utf-8') as fp:
        for line in fp:
            print(line.strip())


def print_on_regex(regex: List[str]):
    regs = [re.compile(reg) for reg in regex]
    files = sort_log_files()
    for file in files:
        with open(file, 'r', encoding='utf-8') as fp:
            for line in fp:
                for reg in regs:
                    obj = reg.search(line)
                    if obj is None:
                        continue
                    print(line.strip())


if __name__ == '__main__':
    # print_all_logs()
    print_on_regex([r'The match is over!', r'You will play on .+? as'])
