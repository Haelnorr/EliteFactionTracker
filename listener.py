import zlib
import zmq
import simplejson
import sys
import time
from . import bgsapi
from . import database
from . import log
from datetime import datetime

# config
__relayEDDN = 'tcp://eddn.edcd.io:9500'
__timeoutEDDN = 600000

__TIME_FMT = '%Y-%m-%dT%H:%M:%SZ'


# start
def receiver(pipeline, shutdown):
    """
    Starts listening to the EDDN relay
    :return: null
    """

    log.info('Starting up Listener')

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
    log.info('Shutting down Listener')


def consumer(pipeline, shutdown):
    log.info('Starting up Consumer')
    db_conn = database.connect()
    while not shutdown.is_set() or not pipeline.empty():
        if not pipeline.empty():
            message = pipeline.get()

            system_name = message['StarSystem']

            try:
                system_db = database.fetch_system(db_conn, system_name)
                log.info('System match found: %s; processing data' % system_db.name)
                process_data(system_db, message)

            except TypeError:
                log.debug('System match not found: %s; moving onto next message' % system_name)

    log.info('Shutting down Consumer')
    db_conn.close()


def process_data(system_db, message):
    db_conn = database.connect()
    # system is tracked in the database
    cached = True
    factions = []
    master = 0

    # debounce data
    for faction in message['Factions']:
        influence = faction['Influence']
        faction_name = faction['Name']
        if 'Pilots\' Federation Local Branch' not in faction_name:
            try:
                faction_db = database.fetch_faction(db_conn, faction_name)

                presence_db = database.fetch_presence(db_conn, sys_id=system_db.system_id, fac_id=faction_db.faction_id)
                if not influence == presence_db.influence[1] or not influence == presence_db.influence[2]:
                    cached = False

                if faction_db.master is 0:
                    master = faction_db.master

                # group old and new data together and add to list
                factions.append((faction, faction_db, presence_db))
            except TypeError:
                log.debug('Faction not tracked: %s' % faction_name)

                # add to list with 'False' flag to indicate its not tracked
                factions.append((faction, False))

    if cached:
        log.info('Message has old data, moving to next message')
    else:
        log.info('Message has new data')

        # extract data
        timestamp = convert_time(message['timestamp'])

        # update the system data
        system_entry = (
            message['SystemFaction']['Name'],
            timestamp,
            system_db.system_id
        )

        database.update_system(db_conn, system_entry)
        log.info('System updated: %s' % system_db.name)

        # update conflicts
        try:
            for conflict in message['Conflicts']:
                try:
                    conflict_db = database.fetch_conflict(db_conn, sys_id=system_db.system_id, fac_name=conflict['Faction1']['Name'])

                    if conflict['Status'] == '':
                        database.delete_conflict(db_conn, conflict_db.conflict_id)
                        log.debug('Deleted conflict for %s in %s' % (conflict['Faction1']['Name'], system_db.name))
                    else:
                        # assume faction1 is faction1 in database
                        faction1 = conflict['Faction1']['WonDays']
                        faction2 = conflict['Faction2']['WonDays']

                        # reverse if its not
                        if conflict['Faction1']['Name'] in conflict_db.faction_name_2:
                            faction1 = conflict['Faction2']['WonDays']
                            faction2 = conflict['Faction1']['WonDays']

                        conflict_entry = (
                            faction1,
                            faction2,
                            conflict['Status'],
                            timestamp,
                            conflict_db.conflict_id
                        )
                        database.update_conflict(db_conn, conflict_entry)
                        log.info('Conflict updated: %s' % conflict_db.conflict_id)
                except TypeError:
                    # conflict not in database
                    if not conflict['Status'] == '':
                        conflict_entry = (
                            system_db.system_id,
                            conflict['Faction1']['Name'],
                            conflict['Faction2']['Name'],
                            conflict['Faction1']['WonDays'],
                            conflict['Faction2']['WonDays'],
                            conflict['Faction1']['Stake'],
                            conflict['Faction2']['Stake'],
                            timestamp,
                            conflict['Status'],
                            timestamp
                        )
                        database.new_conflict(db_conn, conflict_entry)
                        log.info('New conflict found')
        except KeyError:
            log.debug('No conflict found in %s' % system_db.name)

        # update factions and presences
        for faction in factions:
            if faction[1] is not False:  # 'not tracked' flag was not set

                # check states
                try:
                    for state in faction[0]['PendingStates']:
                        if state['State'] in 'Expansion':
                            # expansion found
                            try:
                                database.fetch_expansion(db_conn, faction[1].faction_id)
                                expansion_entry = (
                                    'Pending',
                                    timestamp,
                                    faction[1].faction_id
                                )
                                database.update_expansion(db_conn, expansion_entry)
                                log.info('Updated expansion for: %s' % faction[1].name)
                            except TypeError:
                                # new expansion found
                                expansion_entry = (
                                    faction[1].faction_id,
                                    None,
                                    timestamp,
                                    'Pending',
                                    timestamp
                                )
                                database.new_expansion(db_conn, expansion_entry)
                                log.info('New expansion found: %s' % faction[1].name)

                        elif state['State'] in 'Retreat':
                            # retreat found
                            try:
                                # retreat exists
                                retreat_db = database.fetch_retreat(db_conn, faction[1].faction_id, sys_id=system_db.system_id)
                                retreat_entry = (
                                    'Pending',
                                    timestamp,
                                    retreat_db.retreat_id
                                )
                                database.update_retreat(db_conn, retreat_entry)
                                log.info('Updated retreat for %s in %s' % (faction[1].name, system_db.name))
                            except TypeError:
                                # new retreat found
                                retreat_entry = (
                                    system_db.system_id,
                                    faction[1].faction_id,
                                    timestamp,
                                    'Pending',
                                    timestamp
                                )
                                database.new_retreat(db_conn, retreat_entry)
                                log.info('New retreat found for %s in %s' % (faction[1].name, system_db.name))
                except KeyError:
                    # no pending states found
                    log.debug('No pending states for %s' % faction[1].name)

                try:
                    for state in faction[0]['ActiveStates']:
                        if state['State'] in 'Expansion':
                            # expansion found
                            try:
                                database.fetch_expansion(db_conn, faction[1].faction_id)
                                expansion_entry = (
                                    'Active',
                                    timestamp,
                                    faction[1].faction_id
                                )
                                database.update_expansion(db_conn, expansion_entry)
                                log.info('Updated expansion for: %s' % faction[1].name)

                            except TypeError:
                                # new expansion found
                                expansion_entry = (
                                    faction[1].faction_id,
                                    None,
                                    timestamp,
                                    'Active',
                                    timestamp
                                )
                                database.new_expansion(db_conn, expansion_entry)
                                log.info('New expansion found: %s' % faction[1].name)

                        elif state['State'] in 'Retreat':
                            # retreat found
                            try:
                                # retreat exists
                                retreat_db = database.fetch_retreat(db_conn, faction[1].faction_id, sys_id=system_db.system_id)
                                retreat_entry = (
                                    'Active',
                                    timestamp,
                                    retreat_db.retreat_id
                                )
                                database.update_retreat(db_conn, retreat_entry)
                                log.info('Updated retreat for %s in %s' % (faction[1].name, system_db.name))
                            except TypeError:
                                # new retreat found
                                retreat_entry = (
                                    system_db.system_id,
                                    faction[1].faction_id,
                                    timestamp,
                                    'Active',
                                    timestamp
                                )
                                database.new_retreat(db_conn, retreat_entry)
                                log.info('New retreat found for %s in %s' % (faction[1].name, system_db.name))
                except KeyError:
                    # no active states found
                    log.debug('No active states for %s' % faction[1].name)

                try:
                    for state in faction[0]['RecoveringStates']:
                        if 'Expansion' in state['State']:
                            # expansion found
                            try:
                                database.fetch_expansion(db_conn, faction[1].faction_id)
                                database.delete_expansion(db_conn, faction[1].faction_id)
                                log.debug('Deleted expansion for: %s' % faction[1].name)

                            except TypeError:
                                # new expansion found
                                log.debug('Recovering expansion found: %s' % faction[1].name)
                        elif state['State'] in 'Retreat':
                            # retreat found
                            try:
                                retreat_db = database.fetch_retreat(db_conn, faction[1].faction_id, sys_id=system_db.system_id)
                                database.delete_retreat(db_conn, retreat_db.retreat_id)
                                log.debug('Deleted expansion for: %s' % faction[1].name)

                            except TypeError:
                                # new retreat found
                                log.debug('Recovering retreat found for %s in %s' % (faction[1].name, system_db.name))
                except KeyError:
                    # no recovering states found
                    log.debug('No recovering states for %s' % faction[1].name)

                # update faction
                conflict_db = database.fetch_conflict(db_conn, fac_name=faction[1].name)
                conflict_flags = 0
                for conflict in conflict_db:
                    conflict_flags += 2 ** conflict.conflict_id
                expansion = 0
                try:
                    database.fetch_expansion(db_conn, faction[1].faction_id)
                    expansion = 1
                except TypeError:
                    log.debug('No expansion found for %s' % faction[1].name)
                faction_entry = (
                    expansion,
                    conflict_flags,
                    timestamp,
                    faction[1].faction_id
                )
                database.update_faction(db_conn, faction_entry)
                log.info('Faction updated: %s' % faction[1].name)

                # update presence
                presence_entry = (
                    faction[0]['Influence'],
                    faction[2].influence[0],
                    faction[2].influence[1],
                    timestamp,
                    faction[2].system_id,
                    faction[2].faction_id
                )
                database.update_presence(db_conn, presence_entry)
                log.info('Presence updated: %s, %s' % (faction[1].name, system_db.name))

            else:
                # faction wasn't tracked, add to database
                faction_api = bgsapi.faction(faction[0]['Name'])
                faction_entry = (
                    faction_api['id'],
                    faction_api['name'],
                    faction_api['home_system_id'],
                    timestamp,
                    master
                )
                database.new_faction(db_conn, faction_entry)
                log.info('New faction added: %s' % faction[0]['Name'])
                presence_entry = (
                    system_db.system_id,
                    faction_api['id'],
                    faction[0]['Influence'],
                    faction[0]['Influence'],
                    faction[0]['Influence'],
                    timestamp
                )
                database.new_presence(db_conn, presence_entry)
                log.info('Presence of %s in %s added' % (faction[0]['Name'], system_db.name))

        log.info('Completed system update: %s ' % system_db.name)


def convert_time(timestamp):
    """
    Converts Listener timestamp to database timestamp
    :param timestamp: the timestamp from the Listener
    :return: database friendly timestamp
    """
    converted = datetime.strftime(datetime.strptime(timestamp, __TIME_FMT), database.DATETIME_FMT)
    return converted
