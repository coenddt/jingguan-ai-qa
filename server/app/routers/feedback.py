"""回复校对：提交/列表/处理"""

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from app.db.mongo_store import store
from app.services import qa_service

router = APIRouter(prefix='/api/feedback', tags=['feedback'])


class FeedbackIn(BaseModel):
    sessionId: str = ''
    question: str = ''
    answer: str = ''
    description: str = ''


class FeedbackPut(BaseModel):
    status: str = '已处理'
    remark: str = ''


@router.post('')
async def create(body: FeedbackIn):
    s = await store.insert('Feedback', {
        'sessionId': body.sessionId, 'question': body.question,
        'answer': body.answer, 'description': body.description,
        'status': '待处理',
    })
    if body.question:
        await qa_service.downvote(body.question)
    return s


@router.get('')
async def list_feedback(page: int = 1, pageSize: int = 10,
                        search: str = '', userSearch: str = '', status: str = ''):
    cond: dict = {}
    if search:
        cond['question'] = {'$regex': search}
    if userSearch:
        cond['userName'] = {'$regex': userSearch}
    if status:
        cond['status'] = status
    total = await store.count('Feedback', cond)
    rows = await store.query(
        'Feedback($condition:@c0,$sort:@s0,$skip:@sk,$limit:@l) '
        '{ _id, question, answer, userName, description, status, remark, createdAt }',
        {'c0': cond, 's0': {'createdAt': -1}, 'sk': (page - 1) * pageSize, 'l': pageSize},
    )
    return {'items': [{**r, 'id': r['_id']} for r in rows], 'total': total}


@router.put('/{fid}')
async def update_feedback(fid: str, body: FeedbackPut):
    r = await store.update('Feedback', {'_id': fid}, {'status': body.status, 'remark': body.remark})
    if not r:
        raise HTTPException(status_code=404, detail='反馈不存在')
    return {'ok': True}
