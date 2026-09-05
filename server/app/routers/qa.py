"""问数域路由：会话/消息/提问/日志/数据源/常问"""

import json
import re
import time

from fastapi import APIRouter
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, Field

from app.config import (
    APP_CONFIG_DEFAULTS,
    QA_HOT_LIMIT,
    QA_PRESET_HOT,
    QA_SOURCES,
    QA_TITLE_MAX,
)
from app.db.mongo_store import store
from app.errors import BusinessError
from app.services import qa_service
from app.services.pagination import paged_query

router = APIRouter(prefix='/api/qa', tags=['qa'])


class AskIn(BaseModel):
    question: str = Field(min_length=1, max_length=2000)
    session_id: str | None = None
    source_keys: list[str] = []


class SessionIn(BaseModel):
    title: str = '新对话'


class SessionPatch(BaseModel):
    pinned: bool | None = None
    title: str | None = None


@router.get('/sources')
async def get_sources():
    return QA_SOURCES


@router.get('/sessions')
async def list_sessions():
    items = await store.query(
        'QaSession($sort:@s0,$limit:@l) { _id, title, pinned, userName, msgCount, createdAt, updatedAt }',
        {'s0': {'updatedAt': -1}, 'l': 100},
    )
    items.sort(key=lambda x: (not x.get('pinned'), -x.get('updatedAt', 0)))
    # 聚合各会话反馈：userFeedback=是否已反馈，adminFeedback=处理状态
    ids = [s['_id'] for s in items]
    fb: dict = {}
    if ids:
        fbs = await store.query(
            'Feedback($condition:@c0,$sort:@s1) { sessionId, status }',
            {'c0': {'sessionId': {'$in': ids}}, 's1': {'createdAt': -1}},
        )
        for f in fbs:
            fb.setdefault(f.get('sessionId', ''), f)
    return [{'id': s['_id'], 'title': s.get('title', ''), 'pinned': s.get('pinned', False),
             'userName': s.get('userName', ''), 'msgCount': s.get('msgCount', 0),
             'userFeedback': '已反馈' if s['_id'] in fb else '',
             'adminFeedback': fb.get(s['_id'], {}).get('status', ''),
             'updatedAt': s.get('updatedAt'), 'createdAt': s.get('createdAt')} for s in items]


@router.post('/sessions')
async def create_session(body: SessionIn):
    s = await store.insert('QaSession', {'title': body.title[:QA_TITLE_MAX]})
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
    """流式问数（SSE）：分析步骤/结果块逐个推送，前端逐块渲染"""

    async def gen():
        async for ev in qa_service.ask_stream(body.question, body.session_id, body.source_keys):
            yield f'data: {json.dumps(ev, ensure_ascii=False)}\n\n'

    return StreamingResponse(gen(), media_type='text/event-stream',
                             headers={'Cache-Control': 'no-cache', 'X-Accel-Buffering': 'no'})


@router.get('/quick-asks')
async def quick_asks():
    hot_default = APP_CONFIG_DEFAULTS['hotRecommend']
    hot_cfg = await store.query_one('AppConfig($condition:@c0) { value }',
                                    {'c0': {'key': 'hotRecommend'}})
    conf = (hot_cfg or {}).get('value') or {}
    enabled = bool(conf.get('enabled', hot_default['enabled']))
    threshold = int(conf.get('threshold', hot_default['threshold']))
    hot = []
    if enabled:
        rows = await store.query(
            'QueryExample($condition:@c0,$sort:@s0,$limit:@l) { question, hit }',
            {'c0': {'hit': {'$gte': threshold}, 'favor': {'$gte': 1}}, 's0': {'hit': -1}, 'l': QA_HOT_LIMIT},
        )
        hot = [{'question': r['question'], 'hit': r['hit']} for r in rows]
    if not hot:
        hot = [{'question': q, 'hit': 0} for q in QA_PRESET_HOT]
    return {'enabled': enabled, 'hot': hot}


@router.get('/log')
async def qa_log(page: int = 1, pageSize: int = 20, days: int = 30,
                 kw: str = '', userName: str = ''):
    since = (time.time() - days * 86400) * 1000
    cond: dict = {'role': 'user', 'createdAt': {'$gte': since}}
    if kw:
        cond['content'] = {'$regex': re.escape(kw)}  # 用户输入转义：仅字面量子串匹配，防灾难回溯
    if userName:
        matched = await store.query('QaSession($condition:@c0) { _id }',
                                    {'c0': {'userName': {'$regex': re.escape(userName)}}})
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
