"""模型配置：CRUD + 启用切换 + 连接测试（apiKey 出参脱敏）"""

from urllib.parse import urlparse

from fastapi import APIRouter
from pydantic import BaseModel

from app.db.mongo_store import store
from app.errors import BusinessError
from app.services import llm_client

router = APIRouter(prefix='/api/models', tags=['models'])


class ModelIn(BaseModel):
    baseUrl: str
    apiKey: str
    modelName: str


class ModelPatch(BaseModel):
    enabled: bool


def _mask(m: dict) -> dict:
    out = {k: v for k, v in m.items() if k != '_id'}
    out['id'] = m['_id']
    out['apiKey'] = 'sk-***' if m.get('apiKey') else ''
    return out


@router.get('')
async def list_models():
    rows = await store.query('AiModel($sort:@s0) { _id, name, baseUrl, apiKey, modelName, enabled }',
                             {'s0': {'createdAt': 1}})
    return [_mask(r) for r in rows]


@router.post('')
async def add_model(body: ModelIn):
    name = body.modelName
    exists = await store.exists('AiModel', {'name': name})
    if exists:
        host = urlparse(body.baseUrl).netloc or 'host'
        name = f'{host}-{body.modelName}'
    s = await store.insert('AiModel', {
        'name': name, 'baseUrl': body.baseUrl, 'apiKey': body.apiKey,
        'modelName': body.modelName, 'enabled': False,
    })
    return _mask({**s, '_id': s['_id']})


@router.patch('/{mid}')
async def enable_model(mid: str, body: ModelPatch):
    target = await store.query_one('AiModel($condition:@c0) { _id }', {'c0': {'_id': mid}})
    if not target:
        raise BusinessError('模型不存在', 404)
    if body.enabled:
        rows = await store.query('AiModel($condition:@c0) { _id }', {'c0': {'enabled': True}})
        for r in rows:
            await store.update('AiModel', {'_id': r['_id']}, {'enabled': False})
    await store.update('AiModel', {'_id': mid}, {'enabled': body.enabled})
    return {'ok': True}


@router.delete('/{mid}')
async def delete_model(mid: str):
    r = await store.remove('AiModel', {'_id': mid})
    if not r.get('deletedCount'):
        raise BusinessError('模型不存在', 404)
    return {'ok': True}


@router.post('/test')
async def test_model(body: ModelIn):
    try:
        ret = await llm_client.chat(
            [{'role': 'user', 'content': 'ping'}],
            base_url=body.baseUrl, api_key=body.apiKey, model=body.modelName,
        )
        return {'ok': True, 'latency_ms': int(ret['elapsed_s'] * 1000)}
    except Exception as e:
        return {'ok': False, 'error': str(e)[:200]}
