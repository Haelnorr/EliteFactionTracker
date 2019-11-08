import logging
from .definitions import ROOT_DIR
from datetime import datetime
from os import path

__datetime_fmt = '%Y-%m-%d %H:%M:%S'

__print_to_console = False   # set 'True' for logging to console
__DEBUG = False            # set 'True' for debug messages


def start(filename):
    log_file = path.join(ROOT_DIR, 'logs', '{filename}.log'.format(filename=filename))
    log_level = logging.INFO
    if __DEBUG:
        log_level = logging.DEBUG
    logging.basicConfig(filename=log_file, filemode='w', level=log_level)
    info('Logging started')


def info(message):
    logging.info(log_timestamp() + message)
    if __print_to_console:
        print('INFO:%s%s' % (log_timestamp(), message))


def warn(message):
    logging.warning(log_timestamp() + message)
    if __print_to_console:
        print('WARNING:%s%s' % (log_timestamp(), message))


def error(message):
    logging.error(log_timestamp() + message)
    if __print_to_console:
        print('ERROR:%s%s' % (log_timestamp(), message))


def debug(message):
    logging.debug(log_timestamp() + message)
    if __print_to_console and __DEBUG:
        print('DEBUG:%s%s' % (log_timestamp(), message))


def log_timestamp():
    now = datetime.now()
    timestamp = '[' + datetime.strftime(now, __datetime_fmt) + ']:'
    return timestamp

