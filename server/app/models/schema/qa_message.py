from app.models.schema.common import _SYS_RW

QA_MESSAGE_SCHEMA = {
    'name': 'QaMessage', 'collection': 'qa_message',
    'idPrefix': 'QM', 'timestamps': True,
    'fields': {
        'sessionId': {'type': 'string', 'default': ''},
        'role': {'type': 'string', 'default': 'user'},
        'content': {'type': 'string', 'default': ''},
        'aiMeta': {'type': 'object', 'default': {}},
    },
    'indexes': [{'keys': {'sessionId': 1}}, {'keys': {'createdAt': -1}}],
    **_SYS_RW,
}
