class System:
    """A 'System' object for use with the database 'System' table
    :param data: the data of the system entry
    """
    def __init__(self, data):

        self.system_id = data[0]
        self.name = data[1]
        self.controlling_faction = data[2]
        self.pos_x = data[3]
        self.pos_y = data[4]
        self.pos_z = data[5]
        self.population = data[6]
        self.updated_at = data[7]


class Faction:
    """A 'Faction' object for use with the database 'Faction' table
        :param data: the data of the faction entry
        """
    def __init__(self, data):

        self.faction_id = data[0]
        self.name = data[1]
        self.home_system_id = data[2]
        self.expansion = data[3]
        self.conflict_flags = data[4]
        self.updated_at = data[5]
        self.master = data[6]


class Presence:
    """A 'Presence' object for use with the database 'Presence' table
        :param data: the data of the presence entry
        """
    def __init__(self, data):

        self.system_id = data[0]
        self.faction_id = data[1]
        self.influence = [
            data[2],
            data[3],
            data[4]
        ]
        self.updated_at = data[5]


class Conflict:
    """A 'Conflict' object for use with the database 'Conflict' table
        :param data: the data of the conflict entry
        """
    def __init__(self, data):

        self.conflict_id = data[0]
        self.system_id = data[1]
        self.faction_name_1 = data[2]
        self.faction_name_2 = data[3]
        self.faction_score_1 = data[4]
        self.faction_score_2 = data[5]
        self.faction_stake_1 = data[6]
        self.faction_stake_2 = data[7]
        self.date_started = data[8]
        self.stage = data[9]
        self.updated_at = data[10]


class Expansion:
    """An 'Expansion' object for use with the database 'Expansion' table
        :param data: the data of the expansion entry
        """
    def __init__(self, data):

        self.faction_id = data[0]
        self.system_id = data[1]
        self.detected_on = data[2]
        self.stage = data[3]
        self.updated_at = data[4]


class Retreat:
    """A 'Retreat' object for use with the database 'Retreat' table
        :param data: the data of the retreat entry
        """
    def __init__(self, data):

        self.retreat_id = data[0]
        self.system_id = data[1]
        self.faction_id = data[2]
        self.detected_on = data[3]
        self.stage = data[4]
        self.updated_at = data[5]
