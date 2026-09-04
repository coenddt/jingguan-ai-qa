"""问数域路由：会话/消息/提问/日志/数据源/常问"""

import time

from fastapi import APIRouter
from pydantic import BaseModel, Field

from app.agent.prompt_builder import build_retry_prompt, build_system_prompt
from app.agent.step_tracker import StepTracker
from app.db.mongo_store import store
from app.errors import BusinessError
from app.services import llm_client, query_cache, query_executor
from app.services import qa_service
from app.services.query_guard import GuardError, verify
from app.services.pagination import paged_query

router = APIRouter(prefix='/api/qa', tags=['qa'])


class AskIn(BaseModel):
    question: str = Field(min_length=1)
    session_id: str | None = None
    source_keys: list[str] = []


class SessionIn(BaseModel):
    title: str = '新对话'


class SessionPatch(BaseModel):
    pinned: bool | None = None
    title: str | None = None


SOURCES = [
    {'group': '台账', 'items': [
        {'key': 'commercial', 'name': '商业签约台账', 'label': '签约明细与产品线收入', 'group': '台账', 'selected': True},
        {'key': 'ppl', 'name': '项目储备台账', 'label': '在途项目阶段与风险', 'group': '台账', 'selected': True},
        {'key': 'goal', 'name': '经营目标台账', 'label': '各单元年度目标', 'group': '台账', 'selected': True},
    ]},
    {'group': '统计报表', 'items': [
        {'key': 'overall', 'name': '整体达成', 'label': '中国区整体及各经营单元达成', 'group': '统计报表', 'selected': True},
        {'key': 'product', 'name': '产品线达成', 'label': '各产品线收入与同比', 'group': '统计报表', 'selected': True},
        {'key': 'solution', 'name': '商解达成', 'label': '商解收入与目标', 'group': '统计报表', 'selected': True},
        {'key': 'industry', 'name': '行业达成', 'label': '各行业收入与拆分', 'group': '统计报表', 'selected': True},
        {'key': 'keyunit', 'name': '重点单元', 'label': '订单/未收款/高风险', 'group': '统计报表', 'selected': True},
    ]},
]

_PRESET_HOT = ['政企行业收入3000万-5000万数据', '北京代表处今年达成情况']


@router.get('/sources')
async def get_sources():
    return SOURCES


@router.get('/sessions')
async def list_sessions():
    items = await store.query(
        'QaSession($sort:@s0,$limit:@l) { _id, title, pinned, userName, msgCount, updatedAt }',
        {'s0': {'updatedAt': -1}, 'l': 100},
    )
    items.sort(key=lambda x: (not x.get('pinned'), -x.get('updatedAt', 0)))
    return [{'id': s['_id'], 'title': s.get('title', ''), 'pinned': s.get('pinned', False),
             'userName': s.get('userName', ''), 'msgCount': s.get('msgCount', 0),
             'updatedAt': s.get('updatedAt')} for s in items]


@router.post('/sessions')
async def create_session(body: SessionIn):
    s = await store.insert('QaSession', {'title': body.title[:20]})
    return {'id': s['_id'], 'title': s['title']}


@router.patch('/sessions/{sid}')
async def patch_session(sid: str, body: SessionPatch):
    data = {k: v for k, v in body.model_dump().items() if v is not None}
    if not data:
        raise BusinessError('无可更新字段')
    r = await store.update('QaSession', {'_id': sid}, data)
    if not r:
        raise BusinessError('会话不存在', 404)
    return {'ok': True}


@router.delete('/sessions/{sid}')
async def delete_session(sid: str):
    await store.remove('QaMessage', {'sessionId': sid})
    r = await store.remove('QaSession', {'_id': sid})
    if not r.get('deletedCount'):
        raise BusinessError('会话不存在', 404)
    return {'ok': True}


@router.get('/sessions/{sid}/messages')
async def list_messages(sid: str):
    msgs = await store.query(
        'QaMessage($condition:@c0,$sort:@s0) { _id, role, content, aiMeta, createdAt }',
        {'c0': {'sessionId': sid}, 's0': {'createdAt': 1}},
    )
    return [{'id': m['_id'], 'role': m.get('role'), 'content': m.get('content', ''),
             'aiMeta': m.get('aiMeta') or None, 'createdAt': m.get('createdAt')} for m in msgs]


@router.post('/ask')
async def ask(body: AskIn):
    return await qa_service.ask(body.question, body.session_id, body.source_keys)


@router.get('/quick-asks')
async def quick_asks():
    hot_cfg = await store.query_one('AppConfig($condition:@c0) { value }',
                                    {'c0': {'key': 'hotRecommend'}})
    conf = (hot_cfg or {}).get('value') or {}
    enabled = bool(conf.get('enabled', True))
    threshold = int(conf.get('threshold', 3))
    hot = []
    if enabled:
        rows = await store.query(
            'QueryExample($condition:@c0,$sort:@s0,$limit:@l) { question, hit }',
            {'c0': {'hit': {'$gte': threshold}, 'favor': {'$gte': 1}}, 's0': {'hit': -1}, 'l': 10},
        )
        hot = [{'question': r['question'], 'hit': r['hit']} for r in rows]
    if not hot:
        hot = [{'question': q, 'hit': 0} for q in _PRESET_HOT]
    return {'enabled': enabled, 'hot': hot}


@router.get('/log')
async def qa_log(page: int = 1, pageSize: int = 20, days: int = 30,
                 kw: str = '', userName: str = ''):
    since = (time.time() - days * 86400) * 1000
    cond: dict = {'role': 'user', 'createdAt': {'$gte': since}}
    if kw:
        cond['content'] = {'$regex': kw}
    if userName:
        matched = await store.query('QaSession($condition:@c0) { _id }',
                                    {'c0': {'userName': {'$regex': userName}}})
        ids = [s['_id'] for s in matched]
        if not ids:
            return {'items': [], 'total': 0}
        cond['sessionId'] = {'$in': ids}
    result = await paged_query('QaMessage', cond, page, pageSize,
                               '_id, sessionId, content, createdAt')
    if result['items']:
        sids = {r['sessionId'] for r in result['items']}
        srows = await store.query('QaSession($condition:@c0) { _id, title, userName }',
                                  {'c0': {'_id': {'$in': list(sids)}}})
        smap = {s['_id']: s for s in srows}
        result['items'] = [{**r, 'question': r['content'],
                            'userName': smap.get(r['sessionId'], {}).get('userName', ''),
                            'title': smap.get(r['sessionId'], {}).get('title', '')}
                           for r in result['items']]
    return result
