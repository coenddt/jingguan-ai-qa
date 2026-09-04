"""问法缓存（保守形态三原则）：
① 检索命中不直接驱动执行——仅精确命中复用模板且复用后必过 query_guard；
② 模糊检索只作 few-shot 注入 prompt，不直接执行；
③ 自学习保守回写——仅成功且未差评才 upsert，差评降权。零外部依赖（纯 Python 相似度）。
"""

import re

from app.config import FUZZY_MIN_SCORE, FUZZY_TOP_K, SIM_JACCARD_W, SIM_LEV_W
from app.db.mongo_store import store
from app.models.registry import SCHEMA_VER


def qnorm(q: str) -> str:
    """归一化唯一键：小写、去空白/标点、全半角归一"""
    table = str.maketrans('，。？！、：；（）％', ',.?!,:;()%')
    s = (q or '').translate(table).lower()
    return re.sub(r'[\s\W_]+', '', s)


async def exact_hit(question: str) -> dict | None:
    """L1 精确热缓存：命中返回 template（hit+1）；调用方仍必须过 query_guard"""
    key = qnorm(question)
    if not key:
        return None
    ex = await store.query_one(
        'QueryExample($condition:@c0) { _id, question, qnorm, template, favor, hit }',
        {'c0': {'qnorm': key, 'schemaVer': SCHEMA_VER, 'favor': {'$gte': 1}}},
    )
    if not ex or not ex.get('template'):
        return None
    await store.run_as_internal(
        lambda: store.update('QueryExample', {'_id': ex['_id']}, {'$inc': {'hit': 1}})
    )
    return ex


def _bigrams(s: str) -> set:
    return {s[i:i + 2] for i in range(len(s) - 1)} if len(s) > 1 else {s}


def _levenshtein(a: str, b: str) -> int:
    if len(a) < len(b):
        a, b = b, a
    prev = list(range(len(b) + 1))
    for i, ca in enumerate(a):
        cur = [i + 1]
        for j, cb in enumerate(b):
            cur.append(min(prev[j + 1] + 1, cur[j] + 1, prev[j] + (ca != cb)))
        prev = cur
    return prev[-1]


def _score(a: str, b: str) -> float:
    if not a or not b:
        return 0.0
    ba, bb = _bigrams(a), _bigrams(b)
    jac = len(ba & bb) / len(ba | bb) if ba | bb else 0.0
    lev = 1 - _levenshtein(a, b) / max(len(a), len(b))
    return SIM_JACCARD_W * jac + SIM_LEV_W * lev


async def top_k_fuzzy(question: str, k: int = FUZZY_TOP_K,
                      min_score: float = FUZZY_MIN_SCORE) -> list[dict]:
    """L2 模糊示例检索（只作 few-shot，不直接执行）"""
    key = qnorm(question)
    if not key:
        return []
    rows = await store.query(
        'QueryExample($condition:@c0) { question, qnorm, template }',
        {'c0': {'schemaVer': SCHEMA_VER, 'favor': {'$gte': 1}}},
    )
    scored = sorted(
        [{'question': r['question'], 'template': r['template'], 'score': _score(key, r['qnorm'])} for r in rows],
        key=lambda x: -x['score'],
    )
    return [s for s in scored if s['score'] >= min_score][:k]


async def upsert(question: str, template: dict, success: bool) -> None:
    """③ 保守自学习：成功才写入/升级；失败降权，favor<0 剔除"""
    key = qnorm(question)
    if not key:
        return

    async def _op() -> None:
        if success and not template:
            return
        ex = await store.query_one('QueryExample($condition:@c0) { _id, favor, hit }',
                                   {'c0': {'qnorm': key}})
        if success:
            if ex:
                await store.update('QueryExample', {'_id': ex['_id']},
                                   {'$inc': {'favor': 1, 'hit': 1},
                                    '$set': {'template': template, 'schemaVer': SCHEMA_VER,
                                             'question': question}})
            else:
                await store.insert('QueryExample', {
                    'question': question, 'qnorm': key, 'template': template,
                    'favor': 1, 'hit': 1, 'schemaVer': SCHEMA_VER,
                })
        elif ex:
            new_favor = int(ex.get('favor', 0)) - 2
            await store.update('QueryExample', {'_id': ex['_id']}, {'favor': max(new_favor, 0)})

    await store.run_as_internal(_op)
