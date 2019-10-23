import database
from operator import itemgetter
from datetime import datetime
import atexit

__conn = database.connect()


def get_system(system):
    system_db = database.fetch_system(__conn, system)

    presence_db = database.fetch_presence(__conn, sys_id=system_db.system_id)

    results = []
    for presence in presence_db:
        faction = database.fetch_faction(__conn, presence.faction_id)

        home_system_id = faction.home_system_id
        try:
            home_system = database.fetch_system(__conn, home_system_id).system_id
        except TypeError:
            home_system = home_system_id

        expansion = False
        if faction.expansion is 1:
            expansion = True

        conflict = False
        if faction.conflict_flags is not 0:
            conflict = True

        timestamp = datetime.strptime(presence.updated_at, database.DATETIME_FMT)
        update = pretty_date(timestamp)

        row = (
            faction.name,
            str(round(presence.influence[0]*100, 1)) + '%',
            str(round(presence.influence[1]*100, 1)) + '%',
            str(round(presence.influence[2]*100, 1)) + '%',
            home_system,
            expansion,
            conflict,
            update
        )
        results.append(row)
    sorted(results, key=itemgetter(1))

    print('Showing results for System: %s' % system_db.name)
    print('Faction Name : Influence : Influence Old : Influence Old 2 : Home System : Expansion : Conflict : Updated at')
    for row in results:
        print(row)


def pretty_date(time=False):
    """
    Get a datetime object or a int() Epoch timestamp and return a
    pretty string like 'an hour ago', 'Yesterday', '3 months ago',
    'just now', etc
    """
    now = datetime.now()
    if type(time) is int:
        diff = now - datetime.fromtimestamp(time)
    elif isinstance(time, datetime):
        diff = now - time
    elif not time:
        diff = now - now
    second_diff = diff.seconds
    day_diff = diff.days

    if day_diff < 0:
        return ''

    if day_diff == 0:
        if second_diff < 10:
            return "just now"
        if second_diff < 60:
            return str(second_diff) + " seconds ago"
        if second_diff < 120:
            return "a minute ago"
        if second_diff < 3600:
            return str(second_diff / 60) + " minutes ago"
        if second_diff < 7200:
            return "an hour ago"
        if second_diff < 86400:
            return str(second_diff / 3600) + " hours ago"
    if day_diff == 1:
        return "Yesterday"
    if day_diff < 7:
        return str(day_diff) + " days ago"
    if day_diff < 31:
        return str(day_diff / 7) + " weeks ago"
    if day_diff < 365:
        return str(day_diff / 30) + " months ago"
    return str(day_diff / 365) + " years ago"


def close_db():
    __conn.close()


atexit.register(close_db)