class NullFaction(Exception):
    """The faction requested is not tracked in the database."""
    pass


class NullPresence(Exception):
    """The presence entry requested is not in the database"""
    pass
