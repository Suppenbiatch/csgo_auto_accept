import urllib.parse
import json

from configparser import ConfigParser
from argparse import ArgumentParser

def command_converter(commands: list[str]):
    config = ConfigParser()
    config.read('../config.ini')
    ip_addr = config.get('HotKeys', 'webhook ip')
    port = config.get('HotKeys', 'webhook port')
    return f'http://{ip_addr}:{port}/console?input={urllib.parse.quote(json.dumps(commands))}'

def main():
    parser = ArgumentParser()
    parser.add_argument('commands', nargs='+', type=str)
    args = parser.parse_args()
    commands = ''.join(args.commands).split(', ')
    print(command_converter(commands))

if __name__ == '__main__':
    main()
