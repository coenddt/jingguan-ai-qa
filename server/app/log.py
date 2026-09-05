"""requestId 关联 + 结构化耗时日志（跨请求唯一追踪）

- `_request_id`：contextvar，每个 HTTP 请求独占一个 id（取请求头 X-Request-Id 或 uuid4 短码）。
- `log()`：打印日志时自动并入当前 requestId，供 pm2 日志里按 `req=` 串联同一次问数链路。
- `request_id_middleware`：FastAPI 中间件，注入 requestId、记录请求开始/结束耗时、回写响应头。

用途：供 `qa_service.ask_stream` 逐步骤打点耗时，锁定问数慢点；全局日志统一出处。
"""

import logging
import sys
import time
import uuid
from contextvars import ContextVar

from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request

_request_id: ContextVar[str] = ContextVar('request_id', default='-')
_configured = False

FORMAT = '%(asctime)s %(levelname)s req=%(request_id)s %(message)s'


class _RequestIdFilter(logging.Filter):
    """把当前 contextvar 的 requestId 注入每条日志 record"""

    def filter(self, record: logging.LogRecord) -> bool:
        record.request_id = _request_id.get()
        return True


def configure_logging() -> None:
    """初始化全局日志（幂等）：输出到 stdout，供 pm2 捕获；统一带 request_id"""
    global _configured
    if _configured:
        return
    handler = logging.StreamHandler(sys.stdout)
    handler.setFormatter(logging.Formatter(FORMAT))
    handler.addFilter(_RequestIdFilter())
    root = logging.getLogger('jingguan')
    root.setLevel(logging.INFO)
    root.addHandler(handler)
    root.propagate = False
    _configured = True


def get_request_id() -> str:
    return _request_id.get()


def bind_request_id(rid: str) -> None:
    _request_id.set(rid)


def log(level: str, msg: str, **fields) -> None:
    """打印日志并附带结构化字段；level ∈ info/warn/error/debug"""
    logger = logging.getLogger('jingguan')
    fn = getattr(logger, level, logger.info)
    suffix = ' | ' + ' '.join(f'{k}={v}' for k, v in fields.items()) if fields else ''
    fn(f'{msg}{suffix}')


class RequestIdMiddleware(BaseHTTPMiddleware):
    """注入 requestId + 记录请求开始/结束耗时"""

    async def dispatch(self, request: Request, call_next):
        rid = request.headers.get('X-Request-Id') or uuid.uuid4().hex[:12]
        bind_request_id(rid)
        t0 = time.monotonic()
        log('info', 'request_start', method=request.method, path=request.url.path)
        response = await call_next(request)
        response.headers['X-Request-Id'] = rid
        log('info', 'request_end', method=request.method, path=request.url.path,
            status=response.status_code, total_ms=round((time.monotonic() - t0) * 1000))
        return response