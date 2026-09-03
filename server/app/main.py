"""仅组装：FastAPI 实例 / CORS / 路由注册 / 启动事件（禁业务逻辑）"""

from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from app.auth.router import router as auth_router
from app.database import close, connect
from app.db.mongo_store import store
from app.errors import BusinessError
from app.models.registry import register_all
from app.routers import config as config_router
from app.routers import feedback as feedback_router
from app.routers import import_data as import_router
from app.routers import models_mgr as models_router
from app.routers import qa as qa_router
from app.routers import tts as tts_router
from app.seed.generate_data import seed_if_empty
from app.services.query_guard import GuardError


@asynccontextmanager
async def lifespan(app: FastAPI):
    register_all()
    await connect()
    await seed_if_empty()
    yield
    await close()


app = FastAPI(title='经管之星·AI问数助手 API', lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=['http://localhost:5173'],
    allow_credentials=True,
    allow_methods=['*'],
    allow_headers=['*'],
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


app.include_router(auth_router)
app.include_router(qa_router.router)
app.include_router(config_router.router)
app.include_router(models_router.router)
app.include_router(feedback_router.router)
app.include_router(import_router.router)
app.include_router(tts_router.router)
