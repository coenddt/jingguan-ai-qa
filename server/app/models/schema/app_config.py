from app.models.schema.common import _SYS_RW

APP_CONFIG_SCHEMA = {
    'name': 'AppConfig', 'collection': 'app_config',
    'idPrefix': 'CFG', 'timestamps': True,
    'fields': {'key': {'type': 'string', 'default': ''}, 'value': {'type': 'any'}},
    'indexes': [{'keys': {'key': 1}, 'options': {'unique': True}}],
    **_SYS_RW,
}
