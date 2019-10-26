import sqlite3
from sqlite3 import Error
import os.path
from . import classes
from . import log
from .definitions import ROOT_DIR

DATETIME_FMT = '%Y-%m-%d %H:%M:%S'


def connect():
    """
    Creates a connection to the database
    :return: database connection object
    """
    conn = None
    file_path = os.path.join(ROOT_DIR, 'db', 'data.db')

    # checking if the database exists
    exists = True
    if not os.path.isfile(file_path):
        exists = False
        log.info('Database not found, generating new database...')

    # attempt to connect to the database
    try:
        conn = sqlite3.connect(file_path, check_same_thread=False)
        log.info('Connected to database file: ' + file_path)
    except Error as e:
        log.error(str(e))

    # if the database didn't already exist, create the tables
    if not exists:
        __create_tables(conn)
    return conn


def __create_tables(conn):
    # sql strings for creating the tables
    sql_create_systems_table = """
    CREATE TABLE System (
        system_id INTEGER NOT NULL PRIMARY KEY,
        name VARCHAR(50) COLLATE nocase,
        controlling_faction VARCHAR(50) COLLATE nocase,
        pos_x REAL,
        pos_y REAL,
        pos_z REAL,
        population INTEGER,
        updated_at TIMESTAMP,

        UNIQUE (system_id, name)
    ) WITHOUT ROWID;
    """
    sql_create_factions_table = """
    CREATE TABLE Faction (
        faction_id INTEGER NOT NULL PRIMARY KEY,
        name VARCHAR(100) COLLATE nocase,
        home_system_id INTEGER,
        expansion INTEGER DEFAULT 0,
        conflict_flags INTEGER DEFAULT 0,
        updated_at TIMESTAMP,
        master INTEGER,
        
        UNIQUE (faction_id, name)
    ) WITHOUT ROWID;
    """
    # master is the ID of the tracked faction the entry is tied to; 0 if the faction is the master
    # expansion is boolean value for if the faction is in expansion; 1 for true, 0 for false
    # conflict_flags is the additive ID's of the conflicts the faction is in
    # conflict ID's are used as the indices of base 2 (2^ID), added together and stored as binary
    sql_create_conflicts_table = """
    CREATE TABLE Conflict (
        conflict_id INTEGER NOT NULL PRIMARY KEY AUTOINCREMENT,
        system_id INTEGER NOT NULL,
        faction_name_1 VARCHAR(50) COLLATE nocase,
        faction_name_2 VARCHAR(50) COLLATE nocase,
        faction_score_1 INTEGER,
        faction_score_2 INTEGER,
        faction_stake_1 VARCHAR(50),
        faction_stake_2 VARCHAR(50),
        date_started DATETIME,
        stage VARCHAR(11),
        updated_at TIMESTAMP,
        
        FOREIGN KEY (system_id) REFERENCES System(system_id)
            ON UPDATE CASCADE ON DELETE CASCADE
    );
    """
    sql_create_presence_table = """
    CREATE TABLE Presence (
        system_id INTEGER NOT NULL,
        faction_id INTEGER NOT NULL,
        influence REAL,
        influence_old_1 REAL,
        influence_old_2 REAL,
        updated_at TIMESTAMP,

        PRIMARY KEY (system_id, faction_id),

        FOREIGN KEY (system_id) REFERENCES System(system_id)
            ON UPDATE CASCADE ON DELETE CASCADE,
        FOREIGN KEY (faction_id) REFERENCES Faction(faction_id)
            ON UPDATE CASCADE ON DELETE CASCADE
    ) WITHOUT ROWID;
    """
    # influence_old_1 and influence_old_2 are used for swing calculations and EDDN debouncing
    sql_create_expansion_table = """
    CREATE TABLE Expansion (
        faction_id INTEGER NOT NULL UNIQUE,
        system_id INTEGER,
        detected_on TIMESTAMP,
        stage VARCHAR(11),
        updated_at TIMESTAMP,

        PRIMARY KEY (faction_id),

        FOREIGN KEY (system_id) REFERENCES System(system_id)
            ON UPDATE CASCADE ON DELETE CASCADE,
        FOREIGN KEY (faction_id) REFERENCES Faction(faction_id)
            ON UPDATE CASCADE ON DELETE CASCADE
    ) WITHOUT ROWID;
    """
    sql_create_retreats_table = """
        CREATE TABLE Retreat (
            retreat_id INTEGER NOT NULL PRIMARY KEY AUTOINCREMENT,
            system_id INTEGER NOT NULL,
            faction_id INTEGER NOT NULL,
            detected_on DATETIME,
            stage VARCHAR(11),
            updated_at TIMESTAMP,

            FOREIGN KEY (system_id) REFERENCES System(system_id)
                ON UPDATE CASCADE ON DELETE CASCADE,
            FOREIGN KEY (faction_id) REFERENCES Faction(faction_id)
                ON UPDATE CASCADE ON DELETE CASCADE
        );
        """

    # create the tables
    try:
        c = conn.cursor()
        log.info("Creating tables...")
        c.execute(sql_create_systems_table)
        c.execute(sql_create_factions_table)
        c.execute(sql_create_conflicts_table)
        c.execute(sql_create_presence_table)
        c.execute(sql_create_expansion_table)
        c.execute(sql_create_retreats_table)
        conn.commit()
        log.info('Database initialised')
    except Error as e:
        log.error(str(e))


def update_system(conn, data):
    """
    Updates the system database with the provided data
    :param conn: the database connection object
    :param data: the data to update (controlling_faction, updated_at, system_id)
    :return: null
    """
    sql = '''UPDATE System
    SET controlling_faction = ? ,
        updated_at = ?
    WHERE system_id = ?
    '''
    cur = conn.cursor()
    cur.execute(sql, data)
    conn.commit()


def new_system(conn, data):
    """
    Inserts a new system entry into the database
    :param conn: the database connection object
    :param data: the data to insert (system_id, name, controlling_faction, pos_x, pos_y, pos_z, population, updated_at)
    :return: null
    """
    sql = '''INSERT INTO System(system_id, name, controlling_faction, pos_x, pos_y, pos_z, population, updated_at)
        VALUES(?,?,?,?,?,?,?,?)
    '''
    cur = conn.cursor()
    cur.execute(sql, data)
    conn.commit()


def fetch_system(conn, system):
    """
    Fetches data from the database on the specified system
    :param conn: the database connection object
    :param system: the ID or name of the system
    :return: 'System' object
    """
    cur = conn.cursor()
    try:
        int(system)
        cur.execute("SELECT * FROM System WHERE system_id=?", (system,))
    except ValueError:
        cur.execute("SELECT * FROM System WHERE name=?", (system,))

    s = classes.System(cur.fetchone())

    return s


def update_faction(conn, data):
    """
    Updates the faction database with the provided data
    :param conn: the database connection object
    :param data: the data to update (expansion, conflict_flags, updated_at, faction_id)
    :return: null
    """
    sql = '''UPDATE Faction
    SET expansion = ? ,
        conflict_flags = ? ,
        updated_at = ?
    WHERE faction_id = ?
    '''
    cur = conn.cursor()
    cur.execute(sql, data)
    conn.commit()


def new_faction(conn, data):
    """
    Inserts a new faction entry into the database
    :param conn: the database connection object
    :param data: the data to insert (faction_id, name, home_system_id, updated_at, master)
    :return: null
    """
    sql = '''INSERT INTO Faction(faction_id, name, home_system_id, updated_at, master)
        VALUES(?,?,?,?,?)
    '''
    cur = conn.cursor()
    cur.execute(sql, data)
    conn.commit()


def fetch_faction(conn, faction=None):
    """
    Fetches data from the database on a specified faction
    :param conn: the database connection object
    :param faction: the ID or name of the faction
    :return: 'Faction' object
    """
    cur = conn.cursor()
    f = []
    if faction is not None:
        try:
            int(faction)
            cur.execute('SELECT * FROM Faction WHERE faction_id=?', (faction,))
        except ValueError:
            cur.execute('SELECT * FROM Faction WHERE name=?', (faction,))
        f = classes.Faction(cur.fetchone())
    else:
        cur.execute('SELECT * FROM Faction')
        for faction in cur.fetchall():
            f.append(classes.Faction(faction))

    return f


def update_presence(conn, data):
    """
    Updates the presence database with the provided data
    :param conn: the database connection object
    :param data: the data to update (influence, influence_old_1, influence_old_2, updated_at, system_id, faction_id)
    :return: null
    """
    sql = '''UPDATE Presence
    SET influence = ? ,
        influence_old_1 = ? ,
        influence_old_2 = ? ,
        updated_at = ?
    WHERE system_id = ? AND faction_id = ?'''
    cur = conn.cursor()
    cur.execute(sql, data)
    conn.commit()


def new_presence(conn, data):
    """
    Inserts a new presence entry into the database
    :param conn: the database connection object
    :param data: the data to insert (system_id, faction_id, influence, influence_old_1, influence_old_2, updated_at)
    :return: null
    """
    sql = '''INSERT INTO Presence(system_id, faction_id, influence, influence_old_1, influence_old_2, updated_at)
            VALUES(?,?,?,?,?,?)
        '''
    cur = conn.cursor()
    cur.execute(sql, data)
    conn.commit()


def fetch_presence(conn, sys_id=None, fac_id=None):
    """
    Fetches data from the database on a presence entry for a specified faction or system.
    :param conn: the database connection object
    :param sys_id: (Optional) the 'system_id' to search for or 'ALL' for all systems
    :param fac_id: (Optional) the 'faction_id' to search for or 'ALL' for all factions
    :return: Returns all results as list of 'Presence' objects. If single result, returns single object
    """
    cur = conn.cursor()
    result = []
    if sys_id is None and fac_id is not None:
        sql = 'SELECT * FROM Presence WHERE faction_id=?'
        cur.execute(sql, (fac_id,))
        _list = cur.fetchall()
        for r in _list:
            result.append(classes.Presence(r))
    elif sys_id is not None and fac_id is None:
        sql = 'SELECT * FROM Presence WHERE system_id=?'
        cur.execute(sql, (sys_id,))
        _list = cur.fetchall()
        for r in _list:
            result.append(classes.Presence(r))
    elif sys_id is not None and fac_id is not None:
        sql = 'SELECT * FROM Presence WHERE system_id=? AND faction_id=?'
        cur.execute(sql, (sys_id, fac_id))
        result = classes.Presence(cur.fetchone())
    else:
        sql = 'SELECT * FROM Presence'
        cur.execute(sql)
        for presence in cur.fetchall():
            result.append(classes.Presence(presence))
    return result


def update_expansion(conn, data):
    """
    Updates the expansion database with the provided data
    :param conn: the database connection object
    :param data: the data to update (stage, updated_at, faction_id)
    :return: null
    """
    sql = '''UPDATE Expansion
    SET stage = ? ,
    updated_at = ?
    WHERE faction_id = ?'''
    cur = conn.cursor()
    cur.execute(sql, data)
    conn.commit()


def new_expansion(conn, data):
    """
    Inserts a new expansion entry into the database
    :param conn: the database connection object
    :param data: the data to insert (faction_id, system_id, detected_on, stage, updated_at)
    :return: null
    """
    sql = '''INSERT INTO Expansion(faction_id, system_id, detected_on, stage, updated_at)
        VALUES(?,?,?,?,?)
    '''
    cur = conn.cursor()
    cur.execute(sql, data)
    conn.commit()


def fetch_expansion(conn, fac_id=None):
    """
    Fetches data on expansions from the database
    :param conn: the database connection object
    :param fac_id: (Optional) the ID of the faction
    :return: list of 'Expansion' objects or single object if fac_id is specified
    """
    cur = conn.cursor()
    e = []
    if fac_id is not None:
        sql = '''SELECT * FROM Expansion WHERE faction_id=?'''
        cur.execute(sql, (fac_id,))
        e = classes.Expansion(cur.fetchone())
    else:
        sql = '''SELECT * FROM Expansion'''
        cur.execute(sql)
        for expansion in cur.fetchall():
            e.append(classes.Expansion(expansion))
    return e


def delete_expansion(conn, fac_id):
    """
    Deletes an expansion entry from the database
    :param conn: the database connection object
    :param fac_id: the ID of the faction
    :return: null
    """
    sql = '''DELETE FROM Expansion WHERE faction_id=?'''
    cur = conn.cursor()
    cur.execute(sql, (fac_id,))
    conn.commit()


def update_conflict(conn, data):
    """
    Updates the conflict database with the provided data
    :param conn: the database connection object
    :param data: the data to update (faction_score_1, faction_score_2, stage, updated_at)
    :return: null
    """
    sql = '''UPDATE Conflict
    SET faction_score_1 = ? ,
        faction_score_2 = ? ,
        stage = ? ,
        updated_at = ?
    WHERE conflict_id = ?
    '''
    cur = conn.cursor()
    cur.execute(sql, data)
    conn.commit()


def new_conflict(conn, data):
    """
    Inserts a new conflict entry into the database
    :param conn: the database connection object
    :param data: the data to insert (system_id, faction_name_1, faction_name_2, faction_score_1, faction_score_2, faction_stake_1, faction_stake_2, date_started, stage, updated_at)
    :return: null
    """
    sql = '''INSERT INTO Conflict(system_id, faction_name_1, faction_name_2, faction_score_1, faction_score_2, faction_stake_1, faction_stake_2, date_started, stage, updated_at)
    VALUES(?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    '''
    cur = conn.cursor()
    cur.execute(sql, data)
    conn.commit()


def fetch_conflict(conn, con_id=None, sys_id=None, fac_name=None):
    """
    Fetches data from the database on conflict entries
    MUST SPECIFY AT LEAST ONE OPTIONAL PARAMETER
    :param conn: the database connection object
    :param con_id: (Optional) the ID of the conflict
    :param sys_id: (Optional) the ID of the system
    :param fac_name: (Optional) the name of a faction
    :ar
    :return: 'Conflict' object or list of 'Conflict' objects
    """
    cur = conn.cursor()
    c = None
    if con_id is not None:
        sql = '''SELECT * FROM Conflict WHERE conflict_id=?'''
        cur.execute(sql, (con_id,))
        c = classes.Conflict(cur.fetchone())
    elif sys_id is not None:
        if fac_name is None:
            sql = '''SELECT * FROM Conflict WHERE system_id=?'''
            cur.execute(sql, (sys_id,))
            c = []
            for conflict in cur.fetchall():
                c.append(classes.Conflict(conflict))
        else:
            sql = '''SELECT * FROM Conflict WHERE system_id=? AND (faction_name_1=? OR faction_name_2=?)'''
            cur.execute(sql, (sys_id, fac_name, fac_name))
            c = classes.Conflict(cur.fetchone())
    elif fac_name is not None:
        sql = '''SELECT * FROM Conflict WHERE faction_name_1=? or faction_name_2=?'''
        cur.execute(sql, (fac_name, fac_name))
        c = []
        for conflict in cur.fetchall():
            c.append(classes.Conflict(conflict))

    return c


def delete_conflict(conn, con_id):
    """
    Deletes a confict entry from the database
    :param conn: the database connection object
    :param con_id: the ID of the conflict
    :return: null
    """
    sql = '''DELETE FROM Conflict WHERE conflict_id=?'''
    cur = conn.cursor()
    cur.execute(sql, (con_id,))
    conn.commit()


def update_retreat(conn, data):
    """
    Updates the retreat database with the provided data
    :param conn: the database connection object
    :param data: the data to update (stage, updated_at, retreat_id)
    :return: null
    """
    sql = '''UPDATE Retreat
    SET stage = ? ,
    updated_at = ?
    WHERE retreat_id = ?'''
    cur = conn.cursor()
    cur.execute(sql, data)
    conn.commit()


def new_retreat(conn, data):
    """
    Inserts a new retreat entry into the database
    :param conn: the database connection object
    :param data: the data to insert (system_id, faction_id, detected_on, stage, updated_at)
    :return: null
    """
    sql = '''INSERT INTO Retreat(system_id, faction_id, detected_on, stage, updated_at)
        VALUES(?,?,?,?,?)
    '''
    cur = conn.cursor()
    cur.execute(sql, data)
    conn.commit()


def fetch_retreat(conn, fac_id=None, sys_id=None):
    """
    Fetches data of retreats from the database
    :param conn: the database connection object
    :param fac_id: (Optional) the ID of the faction
    :param sys_id: (Optional) the ID of the system (fac_id must be specified)
    :return: list of 'Retreat' objects, or single retreat object if sys_id is specified
    """
    cur = conn.cursor()
    r = []
    if fac_id is not None:
        if sys_id is None:
            sql = '''SELECT * FROM Retreat WHERE faction_id=?'''
            cur.execute(sql, (fac_id,))
            for retreat in cur.fetchall():
                r.append(classes.Retreat(retreat))
        else:
            sql = '''SELECT * FROM Retreat WHERE faction_id=? AND system_id=?'''
            cur.execute(sql, (fac_id, sys_id))
            r = classes.Retreat(cur.fetchone())
    else:
        sql = '''SELECT * FROM Retreat'''
        cur.execute(sql)
        for retreat in cur.fetchall():
            r.append(classes.Retreat(retreat))

    return r


def delete_retreat(conn, retreat_id):
    """
    Deletes a retreat entry from the database
    :param conn: the database connection object
    :param retreat_id: the ID of the faction
    :return: null
    """
    sql = '''DELETE FROM Retreat WHERE retreat_id=?'''
    cur = conn.cursor()
    cur.execute(sql, (retreat_id,))
    conn.commit()


def query(conn, sql, values=None):
    """
    Queries the database with supplied query
    :param conn: the database connection object
    :param sql: the query to execute
    :param values: (Optional) the values for the query
    :return: If query was a 'SELECT' query, returns results as a list of entries as tuples of the fields
    """
    cur = conn.cursor()
    if values is None:
        cur.execute(sql)
    else:
        cur.execute(sql, values)

    if 'SELECT' in sql:
        return cur.fetchall()
    else:
        conn.commit()
