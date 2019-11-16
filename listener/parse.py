from .. import bgsapi
from .. import database
from .. import log
from datetime import datetime

__TIME_FMT = '%Y-%m-%dT%H:%M:%SZ'


def parser(pipeline, shutdown):
    """
    Receives messages from the EDDN receiver, checks if they are valid, parses the data and stores in the database
    :param pipeline: the message queue
    :param shutdown: the shutdown event
    :return: null
    """
    log.info('Starting up Parser')
    db_conn = database.connect()
    while not shutdown.is_set() or not pipeline.empty():
        if not pipeline.empty():
            message = pipeline.get()

            system_name = message['StarSystem']

            try:
                system_db = database.fetch_system(db_conn, system_name)
                log.info('System match found: %s; parsing data' % system_db.name)
                __parse_data(system_db, message)

            except TypeError:
                log.debug('System match not found: %s; moving onto next message' % system_name)

    log.info('Shutting down Parser')
    db_conn.close()


def __parse_data(system_db, message):
    db_conn = database.connect()
    # system is tracked in the database
    cached = True
    factions = []
    master = 0

    # debounce influence data
    for faction in message['Factions']:
        influence = faction['Influence']
        faction_name = faction['Name']
        # exclude pilots fed local branch (present in all systems)
        if 'Pilots\' Federation Local Branch' not in faction_name:
            try:    # attempt to pull the faction from the database
                faction_db = database.fetch_faction(db_conn, faction_name)

                presence_db = database.fetch_presence(db_conn, sys_id=system_db.system_id, fac_id=faction_db.faction_id)

                if not influence == presence_db.influence[1] or not influence == presence_db.influence[2]:
                    cached = False

                # work on method of debouncing more accurately

                if faction_db.master is 0:
                    master = faction_db.faction_id

                # group old and new data together and add to list
                factions.append((faction, faction_db, presence_db))
            except TypeError:   # faction wasn't in the database
                log.debug('Faction not tracked: %s' % faction_name)

                # add to list with 'False' flag to indicate its not tracked
                factions.append((faction, False))

    # debounce conflicts if influences are static
    try:
        for conflict in message['Conflicts']:
            try:
                conflict_db = database.fetch_conflict(db_conn, sys_id=system_db.system_id,
                                                      fac_name=conflict['Faction1']['Name'])

                totaldays_message = int(conflict['Faction1']['WonDays']) + int(conflict['Faction2']['WonDays'])
                totaldays_db = conflict_db.faction_score_1 + conflict_db.faction_score_2
                if totaldays_message > totaldays_db:
                    cached = False
            except TypeError:
                pass
    except KeyError:
        pass

    timestamp = get_utc_now()
    if cached:
        log.info('Message has old data, moving to next message')
        system_entry = (
            system_db.controlling_faction,
            timestamp,
            system_db.system_id
        )
        database.update_system(db_conn, system_entry)
        log.info('System updated: %s' % system_db.name)

    else:
        log.info('Message has new data')

        # update the system data
        system_entry = (
            message['SystemFaction']['Name'],
            timestamp,
            system_db.system_id
        )
        database.update_system(db_conn, system_entry)
        log.info('System updated: %s' % system_db.name)

        # update conflicts
        current_list = []
        try:
            for conflict in message['Conflicts']:
                try:
                    conflict_db = database.fetch_conflict(db_conn, sys_id=system_db.system_id,
                                                          fac_name=conflict['Faction1']['Name'])

                    if conflict['Status'] == '':
                        database.delete_conflict(db_conn, conflict_db.conflict_id)
                        log.debug('Deleted conflict for %s in %s' % (conflict['Faction1']['Name'], system_db.name))
                    else:
                        current_list.append(conflict_db.conflict_id)
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
                        try:
                            conflict_db = database.fetch_conflict(db_conn, sys_id=system_db.system_id,
                                                                  fac_name=conflict['Faction1']['Name'])
                            current_list.append(conflict_db.conflict_id)
                        except TypeError:
                            pass
                        log.info('New conflict found')
        except KeyError:
            log.debug('No conflict found in %s' % system_db.name)

        # delete any conflicts that missed the retreat stage deletion
        conflicts_db = database.fetch_conflict(db_conn, sys_id=system_db.system_id)
        if not len(conflicts_db) == len(current_list):
            for conflict in conflicts_db:
                if conflict.conflict_id not in current_list:
                    database.delete_conflict(db_conn, conflict.conflict_id)

        # update factions and presences
        current_list = []
        for faction in factions:
            expansion = False
            retreat = False
            if faction[1] is not False:  # 'not tracked' flag was not set
                current_list.append(faction[1].faction_id)
                # check states
                try:    # check for pending states
                    for state in faction[0]['PendingStates']:
                        if state['State'] in 'Expansion':
                            # expansion found
                            expansion = True
                            try:    # check if expansion is in database and update
                                database.fetch_expansion(db_conn, faction[1].faction_id)
                                expansion_entry = (
                                    'Pending',
                                    timestamp,
                                    faction[1].faction_id
                                )
                                database.update_expansion(db_conn, expansion_entry)
                                log.info('Updated expansion for: %s' % faction[1].name)
                            except TypeError:   # expansion not in database
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

                        if state['State'] in 'Retreat':
                            retreat = True
                            # retreat found
                            try:    # check if retreat is in database and update
                                # retreat exists
                                retreat_db = database.fetch_retreat(db_conn, faction[1].faction_id,
                                                                    sys_id=system_db.system_id)
                                retreat_entry = (
                                    'Pending',
                                    timestamp,
                                    retreat_db.retreat_id
                                )
                                database.update_retreat(db_conn, retreat_entry)
                                log.info('Updated retreat for %s in %s' % (faction[1].name, system_db.name))
                            except TypeError:   # retreat not in database, add it
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

                try:    # check for active states
                    for state in faction[0]['ActiveStates']:
                        if state['State'] in 'Expansion':
                            expansion = True
                            # expansion found
                            try:    # check if expansion is in database and update it
                                database.fetch_expansion(db_conn, faction[1].faction_id)
                                expansion_entry = (
                                    'Active',
                                    timestamp,
                                    faction[1].faction_id
                                )
                                database.update_expansion(db_conn, expansion_entry)
                                log.info('Updated expansion for: %s' % faction[1].name)

                            except TypeError:   # expansion not in database, add it
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

                        if state['State'] in 'Retreat':
                            retreat = True
                            # retreat found
                            try:    # check if retreat is in database and update
                                # retreat exists
                                retreat_db = database.fetch_retreat(db_conn, faction[1].faction_id,
                                                                    sys_id=system_db.system_id)
                                retreat_entry = (
                                    'Active',
                                    timestamp,
                                    retreat_db.retreat_id
                                )
                                database.update_retreat(db_conn, retreat_entry)
                                log.info('Updated retreat for %s in %s' % (faction[1].name, system_db.name))
                            except TypeError:   # retreat not in database, add it
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

                try:    # check for recovering states
                    for state in faction[0]['RecoveringStates']:
                        if 'Expansion' in state['State']:
                            # expansion found
                            try:    # check if expansion is in database
                                database.fetch_expansion(db_conn, faction[1].faction_id)
                                database.delete_expansion(db_conn, faction[1].faction_id)
                                log.debug('Deleted expansion for: %s' % faction[1].name)

                            except TypeError:   # expansion not in database
                                # new expansion found
                                log.debug('Recovering expansion found: %s' % faction[1].name)
                        if state['State'] in 'Retreat':
                            # retreat found
                            try:    # check if retreat is in database and delete
                                retreat_db = database.fetch_retreat(db_conn, faction[1].faction_id,
                                                                    sys_id=system_db.system_id)
                                database.delete_retreat(db_conn, retreat_db.retreat_id)
                                log.debug('Deleted retreat for: %s' % faction[1].name)

                            except TypeError:   # retreat not in database
                                # new retreat found
                                log.debug('Recovering retreat found for %s in %s' % (faction[1].name, system_db.name))
                except KeyError:
                    # no recovering states found
                    log.debug('No recovering states for %s' % faction[1].name)

                if expansion is False:
                    try:
                        expansion_db = database.fetch_expansion(db_conn, faction[1].faction_id)
                        database.delete_expansion(db_conn, expansion_db.faction_id)
                    except TypeError:
                        pass

                if retreat is False:
                    try:
                        retreat_db = database.fetch_retreat(db_conn, sys_id=system_db.system_id,
                                                            fac_id=faction[1].faction_id)
                        database.delete_retreat(db_conn, retreat_db.retreat_id)
                    except TypeError:
                        pass

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
                try:
                    database.new_faction(db_conn, faction_entry)
                    log.info('New faction added: %s' % faction[0]['Name'])
                except database.sqlite3.IntegrityError:
                    log.debug('Faction already exists in the database')

                presence_entry = (
                    system_db.system_id,
                    faction_api['id'],
                    faction[0]['Influence'],
                    faction[0]['Influence'],
                    faction[0]['Influence'],
                    timestamp
                )
                try:
                    database.new_presence(db_conn, presence_entry)
                    log.info('Presence of %s in %s added' % (faction[0]['Name'], system_db.name))
                except database.sqlite3.IntegrityError:
                    log.debug('Faction presence already exists in the database')

        # remove retreated factions
        presences = database.fetch_presence(db_conn, sys_id=system_db.system_id)
        if not len(presences) == len(factions):
            for presence in presences:
                if presence.faction_id not in current_list:
                    database.query(db_conn, 'DELETE FROM Presence WHERE system_id=? AND faction_id=?',
                                   (presence.system_id, presence.faction_id))
                    try:
                        retreat_db = database.fetch_retreat(db_conn, sys_id=presence.system_id,
                                                            fac_id=presence.faction_id)
                        database.delete_retreat(db_conn, retreat_db.retreat_id)
                    except TypeError:
                        pass

        log.info('Completed system update: %s ' % system_db.name)


def get_utc_now():
    """
    Get the time in UTC in a database friendly format
    :return: database friendly timestamp
    """
    utc_now = datetime.strftime(datetime.utcnow(), database.DATETIME_FMT)
    return utc_now
