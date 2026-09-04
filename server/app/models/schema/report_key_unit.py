from app.models.schema.common import _BIZ_RW

REPORT_KEY_UNIT_SCHEMA = {
    'name': 'ReportKeyUnit', 'collection': 'report_key_unit',
    'idPrefix': 'RKU', 'timestamps': True,
    'fields': {
        'year': 'int',
        'unit': {'type': 'string', 'default': ''},
        'orderAmt': {'type': 'float', 'default': 0.0},
        'notRecvAmt': {'type': 'float', 'default': 0.0},
        'riskCount': {'type': 'int', 'default': 0},
    },
    'indexes': [{'keys': {'year': 1, 'unit': 1}, 'options': {'unique': True}}],
    **_BIZ_RW,
}
