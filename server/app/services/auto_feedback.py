"""自动反馈记录：纵深防御告警闭环（堡垒思想落地）。

任何兜底、越界、防护拦截一旦触发，都必须自动写入一条 AutoFeedback，
写明触发原因、命中哪层防护、上一步哪里出了问题、如何修复（供 AI 子代理
复制后直接探查与修复），禁止静默失守。

写入走 run_as_internal（AutoFeedback schema 全程 internal，_SYS_RW），
业务角色只读不可写；record 内部自吞异常并打日志，绝不让告警本身击穿调用方。
"""

import json

from app.db.mongo_store import store
from app.log import get_request_id, log


async def record(*, category: str, trigger_point: str, reason: str,
                 layer: str, upstream: str, fix_hint: str,
                 question: str = '', query_raw: dict | None = None) -> None:
    """写入一条自动反馈。category ∈ guard/fallback/input；不受限但请按此枚举."""
    doc = {
        'category': category,
        'triggerPoint': trigger_point,
        'reason': reason,
        'layer': layer,
        'upstream': upstream,
        'fixHint': fix_hint,
        'question': question,
        'queryRaw': json.dumps(query_raw, ensure_ascii=False) if query_raw else '',
        'requestId': get_request_id(),
        'userName': '系统',
    }
    async def _write():
        return await store.insert('AutoFeedback', doc)
    try:
        await store.run_as_internal(_write)
    except Exception as e:  # noqa: BLE001  # 告警本身失败不能击穿调用方：只记日志，暴露写失败征象
        log('error', 'auto_feedback_fail', error=str(e),
            category=category, trigger=trigger_point)