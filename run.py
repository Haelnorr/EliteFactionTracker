import queue
import concurrent.futures
from . import log
from . import database
from . import bgsapi
import threading
from . import listener
import time

log.start('tracker')
conn = database.connect()
shutdown = threading.Event()


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
        _listener = executor.submit(listener.receiver, pipeline, shutdown)
        _consumer = executor.submit(listener.consumer, pipeline, shutdown)

        while not shutdown.is_set():
            if not _listener.running():
                log.error('Listener Exception: %s' % _listener.exception())
                time.sleep(5)
                _listener = executor.submit(listener.receiver, pipeline, shutdown)
            elif not _consumer.running():
                log.error('Consumer Exception: %s' % _consumer.exception())
                time.sleep(5)
                _consumer = executor.submit(listener.consumer, pipeline, shutdown)

        conn.close()  # close database connection when program ends
    # listener is running
    # it receives messages and sends them to the consumer through pipeline for processing
    # exec(input()) opens the console to the user while the threads are running
    # shutdown() will shutdown the application


if __name__ == "__main__":
    main()
