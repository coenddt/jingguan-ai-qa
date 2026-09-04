from app.models.schema.common import _SYS_RW

AI_MODEL_SCHEMA = {
    'name': 'AiModel', 'collection': 'ai_model',
    'idPrefix': 'M', 'timestamps': True,
    'fields': {
        'name': {'type': 'string', 'default': ''},
        'platform': {'type': 'string', 'default': 'deepseek'},
        'baseUrl': {'type': 'string', 'default': ''},
        'apiKey': {'type': 'string', 'default': ''},
        'modelName': {'type': 'string', 'default': ''},
        'enabled': {'type': 'boolean', 'default': False},
    },
    **_SYS_RW,
}
