import zlib
import zmq
import simplejson
import sys
import time
from .. import log

# config
__relayEDDN = 'tcp://eddn.edcd.io:9500'
__timeoutEDDN = 600000


def receiver(pipeline, shutdown):
    """
    Starts listening to the EDDN relay
    :param pipeline: the message pipeline
    :param shutdown: the shutdown event
    :return: null
    """

    log.info('Starting up Receiver')

    context = zmq.Context()
    subscriber = context.socket(zmq.SUB)

    subscriber.setsockopt(zmq.SUBSCRIBE, b"")
    subscriber.setsockopt(zmq.RCVTIMEO, __timeoutEDDN)

    while not shutdown.is_set():
        try:
            subscriber.connect(__relayEDDN)
            log.info('Connect to ' + __relayEDDN)

            while not shutdown.is_set():
                __message = subscriber.recv()

                if __message is False:
                    subscriber.disconnect(__relayEDDN)
                    log.warn('Disconnect from ' + __relayEDDN)
                    break

                # log.debug('Message received from EDDN')
                __message = zlib.decompress(__message)
                if __message is False:
                    log.warn('Failed to decompress message')

                __json = simplejson.loads(__message)
                if __json is False:
                    log.warn('Failed to parse message as json')

                if __json['$schemaRef'] == 'https://eddn.edcd.io/schemas/journal/1'and 'Factions' in __json['message']:
                    log.debug('Valid message received')
                    pipeline.put(__json['message'])
                    log.debug('Message stored in queue')
                sys.stdout.flush()

        except zmq.ZMQError as e:
            log.error('ZMQSocketException: ' + str(e))
            sys.stdout.flush()
            subscriber.disconnect(__relayEDDN)
            time.sleep(5)

    subscriber.disconnect(__relayEDDN)
    log.info('Disconnected from relay: %s' % __relayEDDN)
    log.info('Shutting down Receiver')
