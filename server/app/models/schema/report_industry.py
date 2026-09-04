from app.models.schema.common import _BIZ_RW

REPORT_INDUSTRY_SCHEMA = {
    'name': 'ReportIndustry', 'collection': 'report_industry',
    'idPrefix': 'RI', 'timestamps': True,
    'fields': {
        'year': 'int',
        'industry': {'type': 'string', 'default': ''},
        'income': {'type': 'float', 'default': 0.0},
        'gcIncome': {'type': 'float', 'default': 0.0},
        'znIncome': {'type': 'float', 'default': 0.0},
        'bsIncome': {'type': 'float', 'default': 0.0},
    },
    'indexes': [{'keys': {'year': 1, 'industry': 1}, 'options': {'unique': True}}],
    **_BIZ_RW,
}
