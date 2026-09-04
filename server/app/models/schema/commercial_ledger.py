from app.models.schema.common import _BIZ_RW

COMMERCIAL_LEDGER_SCHEMA = {
    'name': 'CommercialLedger', 'collection': 'commercial_ledger',
    'idPrefix': 'CL', 'timestamps': True,
    'fields': {
        'signDate': {'type': 'string', 'default': ''},
        'year': 'int', 'quarter': 'int', 'month': 'int',
        'unit': {'type': 'string', 'default': ''},
        'industry': {'type': 'string', 'default': ''},
        'productLine': {'type': 'string', 'default': ''},
        'productModel': {'type': 'string', 'default': ''},
        'contractAmt': {'type': 'float', 'default': 0.0},
        'income': {'type': 'float', 'default': 0.0},
        'customer': {'type': 'string', 'default': ''},
    },
    'indexes': [
        {'keys': {'year': 1, 'unit': 1}},
        {'keys': {'year': 1, 'industry': 1}},
        {'keys': {'year': 1, 'productLine': 1}},
        {'keys': {'year': 1, 'month': 1}},
    ],
    **_BIZ_RW,
}
