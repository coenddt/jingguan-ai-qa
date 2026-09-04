from app.models.schema.common import _BIZ_RW

REPORT_PRODUCT_SCHEMA = {
    'name': 'ReportProduct', 'collection': 'report_product',
    'idPrefix': 'RP', 'timestamps': True,
    'fields': {
        'year': 'int',
        'productLine': {'type': 'string', 'default': ''},
        'income': {'type': 'float', 'default': 0.0},
        'yoy': {'type': 'float', 'default': 0.0},
    },
    'indexes': [{'keys': {'year': 1, 'productLine': 1}, 'options': {'unique': True}}],
    **_BIZ_RW,
}
