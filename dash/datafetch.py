from .. import database
from datetime import datetime
import atexit
from math import floor
from calendar import monthrange
from .. import classes

__conn = database.connect()


def get_alerts(anonymous):
    """
    Generate alerts from the database
    :return: list of alerts
    """
    alerts = []
    alert_count = 0

    factions = database.fetch_faction(__conn)
    # loop through all factions
    for faction in factions:
        alert_entry = {
            'id': faction.faction_id,
            'name': faction.name,
            'alerts': []
        }
        presences = database.fetch_presence(__conn, fac_id=faction.faction_id)
        for presence in presences:
            system = database.fetch_system(__conn, presence.system_id)
            # check if faction is in retreat
            try:
                retreat = database.fetch_retreat(__conn, fac_id=faction.faction_id, sys_id=system.system_id)
                date_detected = retreat.detected_on.split()[0]
                alert = '{stage} retreat in {system} detected on {detected}'
                alert = alert.format(stage=retreat.stage, system=system.name, detected=date_detected)
                alert_entry['alerts'].append((alert, 'warning'))
            except TypeError:
                pass
            # check if there was a large influence swing
            inf_difference = round((presence.influence[0] - presence.influence[1]) * 100, 1)
            if abs(inf_difference) > 2:
                alert = 'Influence swung by {swing}% in {system}'
                alert = alert.format(swing=inf_difference, system=system.name)
                level = 'bonus'
                if inf_difference < 0:
                    level = 'warning'
                alert_entry['alerts'].append((alert, level))
            if not presence.system_id == faction.home_system_id:
                # check if influence is in danger of retreat state
                influence = round(presence.influence[0]*100, 1)
                if influence < 9:
                    # check conflicts
                    if not faction.conflict_flags == 0:
                        try:
                            conflict = database.fetch_conflict(__conn, sys_id=system.system_id, fac_name=faction.name)
                            opponent = conflict.faction_name_1
                            if faction.name in opponent:
                                opponent = conflict.faction_name_2
                            alert = 'Influence may drop below 5% if conflict against {opponent} is lost in {system}'
                            alert = alert.format(opponent=opponent, system=system.name)
                            alert_entry['alerts'].append((alert, 'warning'))
                        except TypeError:
                            pass
                    elif influence < 5:
                        alert = 'Influence below 5% in {system}'
                        alert = alert.format(system=system.name)
                        alert_entry['alerts'].append((alert, 'warning'))
        try:
            expansion = database.fetch_expansion(__conn, fac_id=faction.faction_id)
            date_detected = expansion.detected_on.split()[0]
            alert = '{stage} expansion detected on {detected}'
            alert = alert.format(stage=expansion.stage, detected=date_detected)
            alert_entry['alerts'].append((alert, 'bonus'))
            if expansion.system_id is None and anonymous is False:
                alert = 'Expansion is not being tracked (WIP)'
                alert_entry['alerts'].append((alert, 'info'))
        except TypeError:
            pass
        conflicts = database.fetch_conflict(__conn, fac_name=faction.name)
        for conflict in conflicts:
            opponent = conflict.faction_name_1
            score1, score2 = conflict.faction_score_2, conflict.faction_score_1
            if faction.name in opponent:
                opponent = conflict.faction_name_2
                score1, score2 = score2, score1
            system = database.fetch_system(__conn, conflict.system_id)
            alert = '{stage} conflict against {opponent} in {system}. Score: {score1} - {score2}'
            alert = alert.format(stage=conflict.stage.capitalize(), opponent=opponent, system=system.name,
                                 score1=score1, score2=score2)
            alert_entry['alerts'].append((alert, 'conflict'))
        if len(alert_entry['alerts']) > 0:
            alert_entry['alerts'] = sorted(alert_entry['alerts'], key=lambda s: s[1])
            alerts.append(alert_entry)
            alert_count += len(alert_entry['alerts'])
    alerts = sorted(alerts, key=lambda s: s['name'])
    return alerts, alert_count


def get_system(system):
    """
    Get all relevant data on a system from the database
    :param system: name or ID of the system
    :return: system name, list of factions, list of conflicts
    """
    system_db = database.fetch_system(__conn, system)

    presence_db = database.fetch_presence(__conn, sys_id=system_db.system_id)

    results = [system_db.name]
    sys_results = []
    for presence in presence_db:
        faction = database.fetch_faction(__conn, presence.faction_id)

        home_system = {
            'id': faction.home_system_id
        }
        try:
            home_system_db = database.fetch_system(__conn, home_system['id'])
            home_system['name'] = home_system_db.name
        except (TypeError, AttributeError):
            home_system['name'] = None

        expansion = None
        if faction.expansion is 1:
            try:
                expansion_db = database.fetch_expansion(__conn, faction.faction_id)
                expansion = expansion_db.stage
            except TypeError:
                pass

        conflict = None
        if faction.conflict_flags is not 0:
            try:
                conflict_db = database.fetch_conflict(__conn, sys_id=system_db.system_id, fac_name=faction.name)
                conflict = conflict_db.stage
            except TypeError:
                pass

        retreat = None
        try:
            retreat_db = database.fetch_retreat(__conn, fac_id=presence.faction_id, sys_id=system_db.system_id)
            retreat = retreat_db.stage
        except TypeError:
            pass

        update = time_since(presence.updated_at)

        row = {
            'id': faction.faction_id,
            'name': faction.name,
            'influence1': str(round(presence.influence[0]*100, 1)) + '%',
            'influence2': str(round(presence.influence[1]*100, 1)) + '%',
            'influence3': str(round(presence.influence[2]*100, 1)) + '%',
            'home_system': home_system,
            'expansion': expansion,
            'conflict': conflict,
            'retreat': retreat,
            'updated': update
        }
        sys_results.append(row)

    systems_sorted = sorted(sys_results, key=lambda f: float(f['influence1'].strip('%')), reverse=True)

    conflicts = database.fetch_conflict(__conn, sys_id=system_db.system_id)

    for conflict in conflicts:
        conflict.updated_at = time_since(conflict.updated_at)
        conflict.date_started = datetime.strftime(datetime.strptime(conflict.date_started, database.DATETIME_FMT),
                                                  '%d/%b/%y')
        if conflict.faction_stake_1 == '':
            conflict.faction_stake_1 = 'None'
        if conflict.faction_stake_2 == '':
            conflict.faction_stake_2 = 'None'

    results.append(systems_sorted)
    results.append(conflicts)
    return results


def get_all_systems():
    """
    Gets a list of all systems
    :return: system name, ID and number of factions as a list of dicts
    """
    sql = 'SELECT * FROM System'
    systems = database.query(__conn, sql)
    results = []
    for system in systems:
        system = classes.System(system)
        faction_count = len(database.fetch_presence(__conn, sys_id=system.system_id))
        updated = time_since(system.updated_at)
        data = {
            'name': system.name,
            'id': system.system_id,
            'num_factions': faction_count,
            'updated': updated
        }
        results.append(data)
    return results


def get_faction(faction):
    """
    Gets all relevant data on a faction
    :param faction: the name or ID of the faction
    :return: faction name, list of systems the faction is in, list of conflicts
    """
    faction_db = database.fetch_faction(__conn, faction)
    presence_db = database.fetch_presence(__conn, fac_id=faction_db.faction_id)
    conflict_db = database.fetch_conflict(__conn, fac_name=faction_db.name)

    results = [faction_db.name]
    sys_results = []
    for presence in presence_db:
        system = database.fetch_system(__conn, presence.system_id)
        states = []
        if faction_db.conflict_flags is not 0:
            try:
                conflict = database.fetch_conflict(__conn, sys_id=system.system_id, fac_name=faction_db.name)
                states.append('Conflict ({})'.format(conflict.stage))
            except TypeError:
                pass
        if faction_db.expansion is not 0:
            try:
                expansion = database.fetch_expansion(__conn, faction_db.faction_id)
                states.append('Expansion ({})'.format(expansion.stage))
            except TypeError:
                pass
        try:
            retreat = database.fetch_retreat(__conn, fac_id=faction_db.faction_id, sys_id=system.system_id)
            states.append('Retreat ({})'.format(retreat.stage))
        except TypeError:
            pass
        update = time_since(presence.updated_at)
        influence = str(round(presence.influence[0]*100, 1)) + '%'
        row = {
            'id': system.system_id,
            'name': system.name,
            'influence': influence,
            'states': states,
            'updated': update,
        }
        sys_results.append(row)
    systems_sorted = sorted(sys_results, key=lambda f: float(f['influence'].strip('%')), reverse=True)
    results.append(systems_sorted)

    conflicts = []
    for conflict in conflict_db:
        opponent = conflict.faction_name_1
        days_won = conflict.faction_score_2
        days_lost = conflict.faction_score_1
        stake_at_risk = conflict.faction_stake_2
        stake_to_win = conflict.faction_stake_1
        if opponent == faction_db.name:
            opponent = conflict.faction_name_2
            days_won, days_lost = days_lost, days_won
            stake_at_risk, stake_to_win = stake_to_win, stake_at_risk

        opponent_db = database.fetch_faction(__conn, opponent)
        system = database.fetch_system(__conn, conflict.system_id)
        date_started = datetime.strftime(datetime.strptime(conflict.date_started, database.DATETIME_FMT), '%d/%b/%y')
        update = time_since(conflict.updated_at)
        conflict_data = {
            'system_id': system.system_id,
            'system_name': system.name,
            'stake_at_risk': stake_at_risk,
            'score': '{} - {}'.format(days_won, days_lost),
            'opponent': opponent,
            'opponent_id': opponent_db.faction_id,
            'stake_to_win': stake_to_win,
            'stage': conflict.stage,
            'date_started': date_started,
            'updated_at': update
        }
        conflicts.append(conflict_data)
    results.append(conflicts)
    return results


def get_tracked_factions():
    """
    Gets a list of all master factions
    :return: a list of factions
    """
    sql = 'SELECT * FROM Faction WHERE master=0'
    factions = database.query(__conn, sql)
    result = []
    for faction in factions:
        faction = classes.Faction(faction)
        systems = len(database.fetch_presence(__conn, fac_id=faction.faction_id))
        sql = 'SELECT system_id FROM System WHERE controlling_faction=?'
        controlling = len(database.query(__conn, sql, (faction.name,)))
        expansion = 'Not active'
        try:
            expansion = database.fetch_expansion(__conn, faction.faction_id)
            expansion = expansion.stage
        except TypeError:
            pass
        data = {
            'id': faction.faction_id,
            'name': faction.name,
            'systems': systems,
            'controlling': controlling,
            'conflicts': faction.conflict_flags,
            'expansion': expansion
        }
        result.append(data)
    return result


def get_all_factions():
    """
    Gets a list of all factions
    :return: two list of factions: master factions and child factions
    """
    sql = 'SELECT * FROM Faction'
    factions = database.query(__conn, sql)
    master = []
    child = []
    for faction in factions:
        faction = classes.Faction(faction)
        update = time_since(faction.updated_at)
        data = {
            'id': faction.faction_id,
            'name': faction.name,
            'updated': update
        }
        if faction.master is 0:
            master.append(data)
        else:
            child.append(data)
    return master, child


def time_since(timestamp):
    """
    Calculates the time since the timestamp provided from the database
    :param timestamp: timestamp from the database
    :return: clean 'time since' string
    """
    now = datetime.utcnow()

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
