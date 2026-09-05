"""应用层登录校验依赖（内层防护罩）：nginx auth_request 之外的兜底防线

verify_token 校验 HMAC Cookie，无效 → 401（前端 axios 401 拦截统一跳登录，语义与 nginx 层一致）。
main.py 以「受保护路由组」挂载到除 login/check/logout 外的全部 /api 路由。
"""

from fastapi import HTTPException, Request

from app.auth.service import verify_token


async def require_login(request: Request) -> dict:
    payload = verify_token(request.cookies.get('jg_token'))
    if not payload:
        raise HTTPException(status_code=401, detail='未登录或登录已过期')
    return payload
