from app.models.schema.common import _BIZ_RW

REPORT_SOLUTION_SCHEMA = {
    'name': 'ReportSolution', 'collection': 'report_solution',
    'idPrefix': 'RS2', 'timestamps': True,
    'fields': {
        'year': 'int',
        'unit': {'type': 'string', 'default': ''},
        'solutionIncome': {'type': 'float', 'default': 0.0},
        'solutionGoal': {'type': 'float', 'default': 0.0},
    },
    'indexes': [{'keys': {'year': 1, 'unit': 1}, 'options': {'unique': True}}],
    **_BIZ_RW,
}
