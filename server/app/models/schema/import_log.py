from app.models.schema.common import _SYS_RW

IMPORT_LOG_SCHEMA = {
    'name': 'ImportLog', 'collection': 'import_log',
    'idPrefix': 'IL', 'timestamps': True,
    'fields': {
        'type': {'type': 'string', 'default': ''},
        'year': {'type': 'int', 'default': 0},
        'fileName': {'type': 'string', 'default': ''},
        'totalRows': {'type': 'int', 'default': 0},
        'successRows': {'type': 'int', 'default': 0},
        'status': {'type': 'string', 'default': ''},
        'detail': {'type': 'string', 'default': ''},
        'userName': {'type': 'string', 'default': '管理员'},
    },
    'indexes': [{'keys': {'createdAt': -1}}],
    **_SYS_RW,
}
