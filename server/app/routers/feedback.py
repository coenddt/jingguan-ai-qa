"""回复校对：提交/列表/处理"""

from fastapi import APIRouter
from pydantic import BaseModel

from app.db.mongo_store import store
from app.errors import BusinessError
from app.services.pagination import paged_query
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
    return await paged_query('Feedback', cond, page, pageSize,
                             '_id, question, answer, userName, description, status, remark, createdAt')


@router.put('/{fid}')
async def update_feedback(fid: str, body: FeedbackPut):
    r = await store.update('Feedback', {'_id': fid}, {'status': body.status, 'remark': body.remark})
    if not r:
        raise BusinessError('反馈不存在', 404)
    return {'ok': True}
