from app.models.schema.common import _SYS_RW

# 自动反馈：纵深防御告警闭环载体。任何兜底/越界/防护拦截一旦触发即写入一条，
# 写明触发原因、命中层、上游病灶、修复指引，供 AI 子代理复制后直接探查与修复。
# 区别于 Feedback（用户手动差评）——本模型由系统自动写入，_SYS_RW 全程 internal。
AUTO_FEEDBACK_SCHEMA = {
    'name': 'AutoFeedback', 'collection': 'auto_feedback',
    'idPrefix': 'AF', 'timestamps': True,
    'fields': {
        'category': {'type': 'string', 'default': 'guard'},
        'triggerPoint': {'type': 'string', 'default': ''},
        'reason': {'type': 'string', 'default': ''},
        'layer': {'type': 'string', 'default': ''},
        'upstream': {'type': 'string', 'default': ''},
        'fixHint': {'type': 'string', 'default': ''},
        'question': {'type': 'string', 'default': ''},
        'queryRaw': {'type': 'string', 'default': ''},
        'requestId': {'type': 'string', 'default': ''},
        'status': {'type': 'string', 'default': '待处理'},
        'remark': {'type': 'string', 'default': ''},
        'userName': {'type': 'string', 'default': '系统'},
    },
    'indexes': [
        {'keys': {'status': 1, 'createdAt': -1}},
        {'keys': {'category': 1, 'createdAt': -1}},
    ],
    **_SYS_RW,
}