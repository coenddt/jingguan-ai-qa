from app.models.schema.common import _SYS_RW

FEEDBACK_SCHEMA = {
    'name': 'Feedback', 'collection': 'feedback',
    'idPrefix': 'FB', 'timestamps': True,
    'fields': {
        'sessionId': {'type': 'string', 'default': ''},
        'question': {'type': 'string', 'default': ''},
        'answer': {'type': 'string', 'default': ''},
        'userName': {'type': 'string', 'default': '管理员'},
        'description': {'type': 'string', 'default': ''},
        'status': {'type': 'string', 'default': '待处理'},
        'remark': {'type': 'string', 'default': ''},
    },
    'indexes': [{'keys': {'status': 1, 'createdAt': -1}}],
    **_SYS_RW,
}
