import queue
import concurrent.futures
import traceback
from . import log
from . import database
from . import bgsapi
import threading
from .listener import receiver
from .listener import parser
import time
from datetime import datetime
import signal
import sys

filename = 'tracker-%s' % datetime.strftime(datetime.now(), '%Y-%m-%d-%H-%M-%S')

log.start(filename)
conn = database.connect()
shutdown = threading.Event()


def signal_handler(sig, frame):
    shutdown.set()


signal.signal(signal.SIGINT, signal_handler)


def main():
    log.info('Tracker starting...')

    # check if the database is populated
    data_exists = True
    r = database.query(conn, 'SELECT * FROM Faction')
    if len(r) > 0:
        data_exists = False

    if data_exists:
        new_fac = input('There are no factions tracked yet. Please enter the name of a faction you wish to track: ')
        bgsapi.new_faction(new_fac)

    log.info('Tracker ready')

    # tracker is ready to receive updates

    pipeline = queue.Queue(maxsize=100)

    # start producing/consumer threading

    with concurrent.futures.ThreadPoolExecutor(max_workers=2) as executor:
        _receiver = executor.submit(receiver, pipeline, shutdown)
        _parser = executor.submit(parser, pipeline, shutdown)

        while not shutdown.is_set():
            if not _receiver.running():
                log.error('Listener Exception: %s' % _receiver.exception())
                time.sleep(5)
                _receiver = executor.submit(receiver, pipeline, shutdown)
            elif not _parser.running():
                log.error('Consumer Exception: %s' % _parser.exception())
                time.sleep(5)
                _parser = executor.submit(parser, pipeline, shutdown)

        conn.close()  # close database connection when program ends
    # listener is running
    # it receives messages and sends them to the consumer through pipeline for processing
    # exec(input()) opens the console to the user while the threads are running
    # shutdown() will shutdown the application


if __name__ == "__main__":
    main()
