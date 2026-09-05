"""多候选查询并发生成 + 守卫校验筛选（阶段二）

把 qa_service 原有「单条生成 + 校验失败串行回传 LLM 重试」替换为：
并行生成 N 个候选查询 → 全部本地守卫校验 → 调用方按序取首个通过者执行；
多出的候选可直接作为执行失败的备选，无需再调 LLM。

并发生成注意：
- N 路并行打 LLM 会放大供应商限流与成本，用并发上限（QA_QUERY_CANDIDATE_CONCURRENCY）限制。
- 单路候选生成失败只记该路失败，不阻断其余；整体仍交由调用方串行错误回传兜底。
"""

import asyncio
import time

from app.agent.prompts import build_messages
from app.services import llm_client
from app.services.query_guard import GuardError, verify

# 预热输出上限：极短回复即可把 query_gen 的 system 前缀写入供应商缓存，少烧 token
_PREHEAT_MAX_TOKENS = 8


async def generate_candidates(question: str, few_shots: list, model_conf: dict,
                              n: int, concurrency: int,
                              preheat: bool = False) -> tuple[list[tuple[dict | None, dict]], dict | None]:
    """并行生成 n 个候选查询（原始 query，未校验）。

    多样性：候选 0 携带 few_shots，其余不带，避免同 prompt 同质。
    返回 ([(query | None, meta), ...], prime_meta)：
      - 候选 meta = {idx, ok, elapsed_s, tokens|cache_hit|cache_miss|error}
      - prime_meta = 预热请求结果（preheat=False 时为 None；失败置 ok=False，不阻断候选）。

    preheat=True 时与候选同一 asyncio.gather 并发发起，不占关键路径：
    把 query_gen 恒定 system 前缀先打进 LLM 缓存，供本批/后续同前缀请求缓存命中。
    """
    sem = asyncio.Semaphore(max(int(concurrency), 1))

    def _base_args():
        return dict(
            base_url=llm_client.resolve_base_url(model_conf['platform'], model_conf.get('baseUrl')),
            api_key=model_conf.get('apiKey'),
            model=model_conf.get('modelName'),
        )

    async def _one(i: int):
        variables = {'question': question, 'few_shots': few_shots if i == 0 else []}
        async with sem:
            t0 = time.monotonic()
            try:
                q, ret = await llm_client.invoke('query_gen', variables, model_conf)
                return q, {'idx': i, 'ok': True, 'elapsed_s': ret.get('elapsed_s'),
                           'tokens': ret.get('total_tokens'),
                           'cache_hit': ret.get('cache_hit_tokens'),
                           'cache_miss': ret.get('cache_miss_tokens')}
            except Exception as e:  # 单候选失败不阻断其余
                return None, {'idx': i, 'ok': False, 'error': str(e),
                              'elapsed_s': round(time.monotonic() - t0, 2)}

    async def _prime():
        async with sem:
            t0 = time.monotonic()
            try:
                # 用空问题渲染以触发 system 前缀（模型清单+示例恒定，few_shots 置空即最长公共前缀）
                msgs = build_messages('query_gen', {'question': '', 'few_shots': []})
                ret = await llm_client.chat(msgs, **_base_args(),
                                            temperature=0.1, max_tokens=_PREHEAT_MAX_TOKENS)
                return {'ok': True, 'elapsed_s': ret.get('elapsed_s'),
                        'cache_hit': ret.get('cache_hit_tokens'),
                        'cache_miss': ret.get('cache_miss_tokens')}
            except Exception as e:
                return {'ok': False, 'error': str(e),
                        'elapsed_s': round(time.monotonic() - t0, 2)}

    tasks = [_one(i) for i in range(max(int(n), 1))]
    if preheat:
        tasks.append(_prime())
    gathered = await asyncio.gather(*tasks)
    cands = gathered[:len(tasks) - (1 if preheat else 0)]
    prime = gathered[-1] if preheat else None
    return cands, prime


def pick_checked(candidates: list[tuple[dict | None, dict]]) -> tuple[list[dict], list[dict]]:
    """对所有候选做本地守卫校验（快，纯同步），返回 (通过的有序 checked 列表, 每候选状态)。

    status ∈ 'pass' | 'guard_error' | 'empty'(生成失败)；供调用方日志与择优。
    """
    checked_list: list[dict] = []
    statuses: list[dict] = []
    for cand, meta in candidates:
        idx = meta.get('idx')
        if not meta.get('ok') or cand is None:
            statuses.append({'idx': idx, 'status': 'empty', 'error': meta.get('error', '')})
            continue
        try:
            checked_list.append(verify(cand))
            statuses.append({'idx': idx, 'status': 'pass'})
        except GuardError as e:
            statuses.append({'idx': idx, 'status': 'guard_error', 'error': str(e)})
    return checked_list, statuses