from app.models.schema.common import _BIZ_RW

PPL_LEDGER_SCHEMA = {
    'name': 'PplLedger', 'collection': 'ppl_ledger',
    'idPrefix': 'PPL', 'timestamps': True,
    'fields': {
        'year': 'int',
        'projectName': {'type': 'string', 'default': ''},
        'unit': {'type': 'string', 'default': ''},
        'industry': {'type': 'string', 'default': ''},
        'contractAmt': {'type': 'float', 'default': 0.0},
        'stage': {'type': 'string', 'default': ''},
        'riskLevel': {'type': 'string', 'default': '中'},
    },
    'indexes': [{'keys': {'year': 1, 'riskLevel': 1}}],
    **_BIZ_RW,
}
