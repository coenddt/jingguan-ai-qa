"""模型配置：CRUD + 启用切换 + 连接测试（apiKey 出参脱敏）"""

from urllib.parse import urlparse

from fastapi import APIRouter
from pydantic import BaseModel

from app.db.mongo_store import store
from app.errors import BusinessError
from app.services import llm_client

router = APIRouter(prefix='/api/models', tags=['models'])


class ModelIn(BaseModel):
    platform: str = 'deepseek'
    baseUrl: str = ''
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
    rows = await store.query('AiModel($sort:@s0) { _id, name, platform, baseUrl, apiKey, modelName, enabled }',
                             {'s0': {'createdAt': 1}})
    return [_mask(r) for r in rows]


@router.post('')
async def add_model(body: ModelIn):
    if body.platform not in llm_client.PLATFORM_PRESETS:
        raise BusinessError(f'不支持的大模型平台：{body.platform}', 400)
    try:
        base_url = llm_client.resolve_base_url(body.platform, body.baseUrl)
    except ValueError as e:
        raise BusinessError(str(e), 400)
    name = body.modelName
    if await store.exists('AiModel', {'name': name}):
        host = urlparse(base_url).netloc or 'host'
        name = f'{host}-{body.modelName}'
    s = await store.insert('AiModel', {
        'name': name, 'platform': body.platform, 'baseUrl': base_url, 'apiKey': body.apiKey,
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
    if body.platform not in llm_client.PLATFORM_PRESETS:
        return {'ok': False, 'error': f'不支持的大模型平台：{body.platform}'}
    try:
        ret = await llm_client.chat(
            [{'role': 'user', 'content': 'ping'}],
            base_url=llm_client.resolve_base_url(body.platform, body.baseUrl),
            api_key=body.apiKey, model=body.modelName,
        )
        return {'ok': True, 'latency_ms': int(ret['elapsed_s'] * 1000)}
    except Exception as e:  # noqa: BLE001  # 连通性探测：平台异常类型异构，统一兜底返回
        return {'ok': False, 'error': str(e)[:200]}
