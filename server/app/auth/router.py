from fastapi import APIRouter, HTTPException, Request, Response

from app.auth.service import TOKEN_TTL, issue_token, verify_token
from app.config import cfg
from pydantic import BaseModel

router = APIRouter(prefix='/api/auth', tags=['auth'])


class LoginIn(BaseModel):
    username: str
    password: str


@router.post('/login')
async def login(body: LoginIn, response: Response):
    if body.username != cfg.ADMIN_USER or body.password != cfg.ADMIN_PASS:
        raise HTTPException(status_code=401, detail='用户名或密码错误')
    token = issue_token(body.username)
    response.set_cookie(
        'jg_token', token, max_age=TOKEN_TTL, httponly=True,
        samesite='lax', path='/',
    )
    return {'ok': True, 'user': body.username}


@router.get('/check')
async def check(request: Request):
    payload = verify_token(request.cookies.get('jg_token'))
    if not payload:
        raise HTTPException(status_code=401, detail='未登录或登录已过期')
    return {'ok': True, 'user': payload.get('usr')}


@router.post('/logout')
async def logout(response: Response):
    response.delete_cookie('jg_token', path='/')
    return {'ok': True}
