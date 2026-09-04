from app.models.schema.common import _SYS_RW

QUERY_EXAMPLE_SCHEMA = {
    'name': 'QueryExample', 'collection': 'query_example',
    'idPrefix': 'QE', 'timestamps': True,
    'fields': {
        'question': {'type': 'string', 'default': ''},
        'qnorm': {'type': 'string', 'default': ''},
        'template': {'type': 'object', 'default': {}},
        'favor': {'type': 'int', 'default': 1},
        'hit': {'type': 'int', 'default': 0},
        'schemaVer': {'type': 'string', 'default': ''},
    },
    'indexes': [{'keys': {'qnorm': 1}, 'options': {'unique': True}}, {'keys': {'hit': -1}}],
    **_SYS_RW,
}
