"""仅组装：FastAPI 实例 / CORS / 路由注册 / 启动事件（禁业务逻辑）"""

from contextlib import asynccontextmanager

from fastapi import APIRouter, Depends, FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from app.auth.dependency import require_login
from app.auth.router import router as auth_router
from app.config import APP_TITLE, CORS_ORIGINS, validate_security
from app.database import close, connect
from app.db.mongo_store import store
from app.errors import BusinessError
from app.log import RequestIdMiddleware, configure_logging
from app.models.registry import register_all
from app.routers import config as config_router
from app.routers import feedback as feedback_router
from app.routers import import_data as import_router
from app.routers import models_mgr as models_router
from app.routers import qa as qa_router
from app.routers import tts as tts_router
from app.seed.generate_data import seed_if_empty
from app.services import llm_client
from app.services.query_guard import GuardError


@asynccontextmanager
async def lifespan(app: FastAPI):
    validate_security()  # 安全基线 fail-fast：密钥缺失/泄露默认值 → 拒绝启动
    register_all()
    await connect()
    await seed_if_empty()
    yield
    await close()
    await llm_client.aclose()


configure_logging()
app = FastAPI(title=APP_TITLE, lifespan=lifespan)

app.add_middleware(RequestIdMiddleware)

app.add_middleware(
    CORSMiddleware,
    allow_origins=CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=['GET', 'POST', 'PUT', 'PATCH', 'DELETE', 'OPTIONS'],
    allow_headers=['Content-Type', 'Authorization'],
)


@app.exception_handler(GuardError)
async def guard_error_handler(request: Request, exc: GuardError):
    return JSONResponse(status_code=403, content={'detail': f'查询被安全守卫拒绝: {exc}'})


@app.exception_handler(BusinessError)
async def business_error_handler(request: Request, exc: BusinessError):
    return JSONResponse(status_code=exc.status, content={'detail': str(exc)})


@app.exception_handler(store.PermissionError)
async def store_permission_handler(request: Request, exc: Exception):
    return JSONResponse(status_code=403, content={'detail': f'权限拒绝: {exc}'})


# 受保护路由组：除 login/check/logout 外全部 /api 强制登录（内层防护罩，与 nginx auth_request 互为冗余）
_protected = APIRouter(dependencies=[Depends(require_login)])
_protected.include_router(qa_router.router)
_protected.include_router(config_router.router)
_protected.include_router(models_router.router)
_protected.include_router(feedback_router.router)
_protected.include_router(import_router.router)
_protected.include_router(tts_router.router)

app.include_router(auth_router)  # login/check/logout 放行（nginx auth_request 依赖 check）
app.include_router(_protected)
