from typing import Any, cast

from app.db.mongo_store import store
from app.models.schema import ALL_SCHEMAS

REGISTERED: list[str] = []
MODEL_TABLE: dict[str, dict] = {}

# AI 查询仅允许触达的业务模型白名单（system 模型 schema.read 不含 query，双重封死）
BUSINESS_MODELS = [
    'CommercialLedger', 'PplLedger', 'GoalLedger', 'ReportOverall',
    'ReportProduct', 'ReportSolution', 'ReportIndustry', 'ReportKeyUnit',
]

SCHEMA_VER = 'v1'


def register_all() -> None:
    """统一注册入口（唯一事实源），幂等"""
    if REGISTERED:
        return
    for s in ALL_SCHEMAS:
        sd = cast(dict[str, Any], s)
        store.register(sd)
        REGISTERED.append(sd['name'])
        MODEL_TABLE[sd['name']] = sd
