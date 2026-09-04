from app.models.schema.common import _BIZ_RW

GOAL_LEDGER_SCHEMA = {
    'name': 'GoalLedger', 'collection': 'goal_ledger',
    'idPrefix': 'GL', 'timestamps': True,
    'fields': {
        'year': 'int',
        'unit': {'type': 'string', 'default': ''},
        'commercialGoal': {'type': 'float', 'default': 0.0},
        'solutionGoal': {'type': 'float', 'default': 0.0},
    },
    'indexes': [{'keys': {'year': 1, 'unit': 1}, 'options': {'unique': True}}],
    **_BIZ_RW,
}
