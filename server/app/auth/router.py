import time

from fastapi import APIRouter, HTTPException, Request, Response
from pydantic import BaseModel, Field

from app.auth.service import TOKEN_TTL, issue_token, verify_token
from app.config import cfg

router = APIRouter(prefix='/api/auth', tags=['auth'])

# 登录失败限速：单 IP 15 分钟窗口内失败 ≥5 次 → 429（内存态，单 worker；真实 IP 由 nginx X-Real-IP 透传）
_LOGIN_WINDOW_S = 900
_LOGIN_MAX_FAILS = 5
_login_failures: dict[str, list[float]] = {}


def _client_ip(request: Request) -> str:
    return request.headers.get('X-Real-IP') or (request.client.host if request.client else 'unknown')


def _login_locked(ip: str) -> bool:
    now = time.time()
    fails = [t for t in _login_failures.get(ip, []) if now - t < _LOGIN_WINDOW_S]
    _login_failures[ip] = fails
    return len(fails) >= _LOGIN_MAX_FAILS


class LoginIn(BaseModel):
    username: str = Field(min_length=1)
    password: str = Field(min_length=1)


@router.post('/login')
async def login(body: LoginIn, request: Request, response: Response):
    ip = _client_ip(request)
    if _login_locked(ip):
        raise HTTPException(status_code=429, detail='失败次数过多，请 15 分钟后再试')
    if body.username != cfg.ADMIN_USER or body.password != cfg.ADMIN_PASS:
        _login_failures.setdefault(ip, []).append(time.time())
        raise HTTPException(status_code=401, detail='用户名或密码错误')
    _login_failures.pop(ip, None)
    token = issue_token(body.username)
    response.set_cookie(
        'jg_token', token, max_age=TOKEN_TTL, httponly=True,
        samesite='lax', secure=cfg.COOKIE_SECURE, path='/',
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
