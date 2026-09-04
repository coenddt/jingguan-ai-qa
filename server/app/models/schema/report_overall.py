from app.models.schema.common import _BIZ_RW

REPORT_OVERALL_SCHEMA = {
    'name': 'ReportOverall', 'collection': 'report_overall',
    'idPrefix': 'RO', 'timestamps': True,
    'fields': {
        'year': 'int',
        'unit': {'type': 'string', 'default': ''},
        'income': {'type': 'float', 'default': 0.0},
        'gcIncome': {'type': 'float', 'default': 0.0},
        'znIncome': {'type': 'float', 'default': 0.0},
        'bsIncome': {'type': 'float', 'default': 0.0},
    },
    'indexes': [{'keys': {'year': 1, 'unit': 1}, 'options': {'unique': True}}],
    **_BIZ_RW,
}
