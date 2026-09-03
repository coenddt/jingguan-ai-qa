"""应用配置读写（AppConfig 单文档 per key）"""

from fastapi import APIRouter

from app.db.mongo_store import store

router = APIRouter(prefix='/api', tags=['config'])

DEFAULTS = {
    'greeting': {'text': '你好，我是经管之星·AI问数助手。', 'questions': []},
    'suggestions': True, 'tts': False, 'stt': False, 'modelConfig': True,
    'hotRecommend': {'enabled': True, 'threshold': 3},
}


async def _load_all() -> dict:
    rows = await store.query('AppConfig { key, value }')
    data = {k: (dict(v) if isinstance(v, dict) else v) for k, v in DEFAULTS.items()}
    for r in rows:
        if r['key'] in data and isinstance(r.get('value'), dict) and isinstance(data[r['key']], dict):
            data[r['key']].update(r['value'])
        elif r['key'] in data:
            data[r['key']] = r['value']
    return data


@router.get('/config')
async def get_config():
    return await _load_all()


@router.put('/config')
async def put_config(body: dict):
    for k, v in body.items():
        if k not in DEFAULTS:
            continue
        await store.upsert('AppConfig', {'key': k}, {'value': v})
    return await _load_all()
