from app.models.schema.common import _SYS_RW

QA_SESSION_SCHEMA = {
    'name': 'QaSession', 'collection': 'qa_session',
    'idPrefix': 'QS', 'timestamps': True,
    'fields': {
        'title': {'type': 'string', 'default': ''},
        'pinned': {'type': 'boolean', 'default': False},
        'userName': {'type': 'string', 'default': '管理员'},
        'msgCount': {'type': 'int', 'default': 0},
    },
    'indexes': [{'keys': {'pinned': -1, 'updatedAt': -1}}],
    **_SYS_RW,
}
