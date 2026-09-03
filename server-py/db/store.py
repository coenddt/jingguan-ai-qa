# 画廊数据层入口 - 注册画廊 schema（全新库，_id 为 generateId 字符串，无需 ObjectId 包装）
from db.mongo_store import init, store
from schema.agent_audit import AGENT_AUDIT_SCHEMA
from schema.api_key import AGENT_KEY_SCHEMA
from schema.artwork import ARTWORK_SCHEMA
from schema.order_record import ORDER_RECORD_SCHEMA
from schema.post_record import POST_RECORD_SCHEMA
from schema.series import SERIES_SCHEMA

store.register(SERIES_SCHEMA)
store.register(ARTWORK_SCHEMA)
store.register(POST_RECORD_SCHEMA)
store.register(ORDER_RECORD_SCHEMA)
store.register(AGENT_KEY_SCHEMA)
store.register(AGENT_AUDIT_SCHEMA)


def registered_names():
    return store.list()


__all__ = ['store', 'init', 'registered_names']
