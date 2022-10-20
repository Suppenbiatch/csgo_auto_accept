from configparser import ConfigParser
import os.path
import logging

config_file: str = 'config.ini'
default_config: str = 'config_clean.ini'


class CustomFormatter(logging.Formatter):
    grey = "\x1b[38;20m"
    green = "\x1b[32;20m"
    yellow = "\x1b[33;20m"
    red = "\x1b[31;20m"
    bold_red = "\x1b[31;1m"
    reset = "\x1b[0m"
    format = "%(levelname)s - %(message)s"

    FORMATS = {
        logging.DEBUG: grey + format + reset,
        logging.INFO: green + format + reset,
        logging.WARNING: yellow + format + reset,
        logging.ERROR: red + format + reset,
        logging.CRITICAL: bold_red + format + reset
    }

    def format(self, record):
        log_fmt = self.FORMATS.get(record.levelno)
        formatter = logging.Formatter(log_fmt)
        return formatter.format(record)


logger = logging.getLogger('ConfigValidator')
logger.setLevel(logging.DEBUG)

ch = logging.StreamHandler()
ch.setLevel(logging.DEBUG)
ch.setFormatter(CustomFormatter())

logger.addHandler(ch)


def fix_config():

    user_cfg = ConfigParser()
    default_cfg = ConfigParser()
    default_cfg.read(default_config)
    if os.path.isfile(config_file):
        logger.info(f'found existing config file')
        user_cfg.read(config_file)
    else:
        logger.critical(f'failed to find existing config file, create one!')
        return

    accounts_in_cfg = 0
    default_acc = default_cfg['Account 1']

    for section in user_cfg.sections():
        if section.lower().startswith('account'):
            account = user_cfg[section]
            for key in default_acc.keys():
                if key.lower().startswith('autobuy'):
                    continue
                if key not in account:
                    logger.warning(f'missing key "{key}" in "{section}" section')
                    account[key] = ''
                elif not account[key]:
                    logger.warning(f'missing value for "{key}" in "{section}"')
            accounts_in_cfg += 1
    if accounts_in_cfg == 0:
        logger.error(f'No Account in config! Add at least one!')
    else:
        logger.info(f'Found {accounts_in_cfg} accounts in config file')

    for section in default_cfg.sections():
        if section.lower().startswith('account'):
            continue
        logger.info(f'checking section: "{section}"')
        check_section(default_cfg, user_cfg, section)
        logger.info(f'finished section: "{section}"')

    with open(config_file, 'w') as fp:
        user_cfg.write(fp)


def check_section(default_cfg: ConfigParser, user_cfg: ConfigParser, section_key: str):
    def_section = default_cfg[section_key]
    if section_key in user_cfg:
        user_section = user_cfg[section_key]
        for key, value in def_section.items():
            if key not in user_section:
                logger.error(f'Missing key "{key}" in {section_key} section!')
                if value:
                    logger.info(f'Adding default value "{value}" for "{key}" in "{section_key}" section')
                    user_section[key] = value
                else:
                    logger.critical(f'No default value for "{key}" in "{section_key}" section provided!')
                    user_section[key] = ''
            elif not user_section[key]:
                logger.warning(f'No value set for "{key}" in "{section_key}"')
                if value:
                    logger.info(f'Adding default value "{value}" for "{key}" in "{section_key}" section')
                    user_section[key] = value
                else:
                    logger.error(f'No default value for "{key}" in "{section_key}" section provided!')
    else:
        logger.error(f'Missing "{section_key}" section in config!')
        user_cfg[section_key] = {}
        for key, value in def_section.items():
            logger.info(f'Adding "{value}" for "{key}" in "{section_key}"')
            user_cfg[section_key][key] = value

    for key, value in user_cfg[section_key].items():
        if key not in def_section:
            logger.warning(f'Removing un-used key "{key}" = "{value}" in {section_key}')
            del user_cfg[section_key][key]


def main():
    fix_config()


if __name__ == '__main__':
    main()
