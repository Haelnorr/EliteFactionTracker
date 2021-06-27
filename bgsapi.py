from datetime import datetime
from urllib import parse
from requests import get
from . import database
from . import log

__API_DATE_FMT = '%Y-%m-%dT%H:%M:%S.000Z'
api_url = 'https://elitebgs.app/api/ebgs/v5/'


def system_request(name):
    # requests data from the API on the system specified
    log.info('API system data requested: ' + name)
    query = '?name=' + parse.quote(name, safe='')
    api = api_url + 'systems'
    r = get(api + query)
    data = r.json()
    log.info('API system data received')

    system_data = data['docs'][0]

    processed = {
        'id': system_data['eddb_id'],
        'name': system_data['name'],
        'controlling_faction': system_data['controlling_minor_faction'],
        'x': system_data['x'],
        'y': system_data['y'],
        'z': system_data['z'],
        'population': system_data['population'],
        'updated_at': system_data['updated_at'],
        'conflicts': system_data['conflicts'],
        'factions': system_data['factions']
    }
    return processed


def faction(name):
    """
    Returns data on a faction from the EliteBGS API
    :param name: the name of the faction
    :return: the data of the faction
    """
    log.info('API faction data requested: ' + name)
    query = '?name=' + parse.quote(name, safe='')
    api = api_url + 'factions'
    r = get(api + query)
    data = r.json()
    log.info('API faction data received')

    faction_data = data['docs'][0]

    home_system = __faction_get_home_system(name)
    processed = {
        'id': faction_data['eddb_id'],
        'name': faction_data['name'],
        'home_system_id': home_system,
        'presence': faction_data['faction_presence'],
        'updated_at': faction_data['updated_at']
    }
    return processed


def __faction_get_home_system(factionname):
    # gets the ID of a faction's home system
    r = get('https://eddbapi.kodeblox.com/api/v4/factions?name='+parse.quote(factionname, safe=''))
    data = r.json()
    system_id = data['docs'][0]['home_system_id']
    return system_id


def __stations(system_name):
    # gets data from the API of all the stations in a specified system (currently unused)
    query = '?system=' + system_name
    api = api_url + 'stations'
    r = get(api + query)
    data = r.json()

    stations_list = data['docs']
    return stations_list


def new_faction(faction_name):
    """
    Fetch and process all data on a faction from the EliteBGS API and store in the database
    :param faction_name: The name of the faction
    :return: null
    """
    __conn = database.connect()

    _faction = faction(faction_name)  # return data from faction lookup

    _expansion = [False, 'none']

    _secondary_factions = []

    # store faction in database

    # convert update time to database friendly format
    timestamp = datetime.strftime(datetime.strptime(_faction['updated_at'], __API_DATE_FMT), database.DATETIME_FMT)
    faction_entry = (
        _faction['id'],
        _faction['name'],
        _faction['home_system_id'],
        timestamp,
        0
    )
    try:
        database.new_faction(__conn, faction_entry)
        log.info('Faction entered into database: ' + _faction['name'])
    except database.sqlite3.IntegrityError:
        log.info('Faction already in database: ' + _faction['name'])
        faction_db = database.fetch_faction(__conn, _faction['id'])
        if faction_db.master is not 0:
            database.query(__conn, 'UPDATE Faction SET master=0 WHERE faction_id=?', (_faction['id'],))

    # get data on relevant systems
    for system in _faction['presence']:
        _system = system_request(system['system_name'])   # return data from system lookup

        # add secondary factions to list
        for __faction in _system['factions']:
            if __faction['name'] not in _secondary_factions:
                _secondary_factions.append(__faction['name'])

        # process data on conflicts
        if len(system['conflicts']) > 0:  # found conflict for the faction
            for _conflict in _system['conflicts']:  # check all conflicts in system for the relevant conflict
                if _conflict['faction1']['name'] in _faction['name'] or _conflict['faction2']['name'] in _faction['name']:
                    # correct conflict data found

                    # convert update time to database friendly format
                    timestamp = datetime.strftime(datetime.strptime(_system['updated_at'], __API_DATE_FMT), database.DATETIME_FMT)
                    conflict_entry = (
                        _system['id'],
                        _conflict['faction1']['name'],
                        _conflict['faction2']['name'],
                        _conflict['faction1']['days_won'],
                        _conflict['faction2']['days_won'],
                        _conflict['faction1']['stake'],
                        _conflict['faction2']['stake'],
                        timestamp,
                        _conflict['status'].capitalize(),
                        timestamp
                    )
                    try:
                        database.new_conflict(__conn, conflict_entry)
                        log.info('Conflict added to database: %s, %s' % (_faction['name'], _system['name']))
                    except database.sqlite3:
                        log.warn('Error adding conflict to database: %s, %s' % (_faction['name'], _system['name']))

        # convert update time to database friendly format
        timestamp = datetime.strftime(datetime.strptime(_system['updated_at'], __API_DATE_FMT), database.DATETIME_FMT)

        # format system data ready to be stored in database
        system_entry = (
            _system['id'],
            _system['name'],
            _system['controlling_faction'],
            _system['x'],
            _system['y'],
            _system['z'],
            _system['population'],
            timestamp
        )
        # store data
        try:
            database.new_system(__conn, system_entry)
            log.info('System entered into database: ' + _system['name'])
        except database.sqlite3.IntegrityError:
            log.info('System already in database: ' + _system['name'])

        # format factions presence in system ready to be stored in database
        presence_entry = (
            _system['id'],
            _faction['id'],
            system['influence'],
            system['influence'],
            system['influence'],
            system['influence'],
            system['influence'],
            system['influence'],
            system['influence'],
            timestamp
        )
        # store data
        try:
            database.new_presence(__conn, presence_entry)
            log.info('Presence entered into database: ' + _faction['name'] + ', ' + _system['name'])
        except database.sqlite3.IntegrityError:
            log.info('Presence already in database: ' + _faction['name'] + ', ' + _system['name'])

        # check states for expansions
        if _expansion[0] is False:
            for pending in system['pending_states']:
                if 'expansion' in pending['state']:
                    _expansion[0] = True
                    _expansion[1] = 'Pending'
            for active in system['active_states']:
                if 'expansion' in active['state']:
                    _expansion[0] = True
                    _expansion[1] = 'Active'

    # do expansion check
    if _expansion[0] is True:
        _timestamp = datetime.strftime(datetime.now(), database.DATETIME_FMT)
        expansion_entry = (
            _faction['id'],
            None,
            _timestamp,
            _expansion[1],
            _timestamp
        )
        try:
            database.new_expansion(__conn, expansion_entry)
            _query = 'UPDATE Faction SET expansion=1 WHERE faction_id=?'
            database.query(__conn, _query, (_faction['id'],))
            log.info('Expansion entered into database: ' + _faction['name'])
        except database.sqlite3.IntegrityError:
            log.info('Expansion already in database: ' + _faction['name'])

    # process secondary faction data
    for __faction in _secondary_factions:
        _secondary_faction = faction(__faction)
        timestamp = datetime.strftime(datetime.strptime(_secondary_faction['updated_at'], __API_DATE_FMT), database.DATETIME_FMT)
        # enter secondary faction into database
        secondary_faction_entry = (
            _secondary_faction['id'],
            _secondary_faction['name'],
            _secondary_faction['home_system_id'],
            timestamp,
            _faction['id']
        )
        try:
            database.new_faction(__conn, secondary_faction_entry)
            log.info('Faction entered into database: ' + _secondary_faction['name'])
        except database.sqlite3.IntegrityError:
            log.info('Faction already in database: ' + _secondary_faction['name'])

        # faction presence
        for system in _secondary_faction['presence']:
            try:
                log.info('Looking up system in the database: %s' % system['system_name'])
                _query = 'SELECT system_id FROM System WHERE name=?'
                _system_id = database.query(__conn, _query, ("%s" % system['system_name'],))[0][0]
                presence_entry = (
                    _system_id,
                    _secondary_faction['id'],
                    system['influence'],
                    system['influence'],
                    system['influence'],
                    system['influence'],
                    system['influence'],
                    system['influence'],
                    system['influence'],
                    timestamp
                )
                # store data
                try:
                    database.new_presence(__conn, presence_entry)
                    log.info('Presence entered into database: ' + _secondary_faction['name'] + ', ' + system['system_name'])
                except database.sqlite3.IntegrityError:
                    log.info('Presence already in database: ' + _secondary_faction['name'] + ', ' + system['system_name'])
            except IndexError:
                log.info('System not tracked, ignoring: %s' % system['system_name'])

    __conn.close()  # close local database connection before exiting function


def track_system(system_name):
    __conn = database.connect()
    system = system_request(system_name)  # return data from system lookup
    # convert update time to database friendly format
    timestamp = datetime.strftime(datetime.strptime(system['updated_at'], __API_DATE_FMT), database.DATETIME_FMT)

    # format system data ready to be stored in database
    system_entry = (
        system['id'],
        system['name'],
        system['controlling_faction'],
        system['x'],
        system['y'],
        system['z'],
        system['population'],
        timestamp
    )
    # store data
    try:
        database.new_system(__conn, system_entry)
        log.info('System entered into database: ' + system['name'])
    except database.sqlite3.IntegrityError:
        log.info('System already in database: ' + system['name'])
    __conn.close()
