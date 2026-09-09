"""应用配置读写（AppConfig 单文档 per key）"""

from fastapi import APIRouter

from app.config import APP_CONFIG_DEFAULTS
from mongo_store import store

router = APIRouter(prefix='/api', tags=['config'])


async def _load_all() -> dict:
    rows = await store.query('AppConfig { key, value }')
    data = {k: (dict(v) if isinstance(v, dict) else v) for k, v in APP_CONFIG_DEFAULTS.items()}
    for r in rows:
        key = str(r['key'])
        val = r.get('value')
        if key in data:
            cur = data[key]
            if isinstance(val, dict) and isinstance(cur, dict):
                cur.update(val)
            else:
                data[key] = val
    return data


@router.get('/config')
async def get_config():
    return await _load_all()


@router.put('/config')
async def put_config(body: dict):
    for k, v in body.items():
        if k not in APP_CONFIG_DEFAULTS:
            continue
        await store.upsert('AppConfig', {'key': k}, {'value': v})
    return await _load_all()
