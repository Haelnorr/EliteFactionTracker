import database
from operator import itemgetter
from datetime import datetime
import atexit
from math import floor
from calendar import monthrange

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

        update = time_since(presence.updated_at)

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

    return results


def time_since(timestamp):
    """
    Calculates the time since the timestamp provided from the database
    :param timestamp: timestamp from the database
    :return: clean 'time since' string
    """
    now = datetime.now()

    # convert the time to datetime object and get time difference
    time = datetime.strptime(timestamp, database.DATETIME_FMT)
    diff = now - time
    second_diff = diff.seconds
    day_diff = diff.days

    # get the number of days in the previous 2 months
    last_month = now.month - 1
    if last_month < 1:
        last_month += 12

    before_last_month = now.month - 2
    if before_last_month < 1:
        before_last_month += 12

    month_days_1 = monthrange(now.year, last_month)[1]
    month_days_2 = monthrange(now.year, before_last_month)[1]

    # format the time difference for display
    if day_diff < 0:
        return ''

    if day_diff is 0:
        if second_diff < 60:
            return 'Just now'
        if second_diff < 120:
            return '1 minute'
        if second_diff < 3600:
            return str(floor(second_diff / 60)) + ' minutes'
        if second_diff < 7200:
            return '1 hour'
        if second_diff < 86400:
            return str(floor(second_diff / 3600)) + ' hours'
    if day_diff is 1:
        return '1 day'
    if day_diff < 7:
        return str(day_diff) + ' days'
    if day_diff is 7:
        return '1 week'
    if day_diff < month_days_1:
        return str(floor(day_diff / 7)) + ' weeks'
    if day_diff < month_days_1 + month_days_2:
        return '1 month'
    if day_diff < 365:
        if floor(day_diff / 30) < 12:
            return str(floor(day_diff / 30)) + ' months'
        else:
            return '1 year'
    if floor(day_diff / 365) < 2:
        return '1 year'
    return str(floor(day_diff / 365)) + ' years'


def close_db():
    __conn.close()


atexit.register(close_db)
