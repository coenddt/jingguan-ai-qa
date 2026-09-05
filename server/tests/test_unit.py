"""单元测试（纯逻辑，无 DB）：守卫/认证/缓存归一化/pipeline 组装/prompt——部署后 pytest 运行"""

import pytest

from app.agent.prompts import build_messages
from app.agent.schema_registry import describe_models
from app.agent.step_tracker import StepTracker
from app.auth.service import issue_token, verify_token
from app.models.registry import register_all
from app.config import SIM_JACCARD_W, SIM_LEV_W
from app.services.query_cache import _bigrams, _levenshtein, _score, qnorm
from app.services.query_executor import _build_pipeline
from app.services.query_candidate import pick_checked
from app.services.auto_feedback import record
from app.services.json_schema_shell import ShellError, attach_schema, validate
from app.services.query_guard import GuardError, verify
from app.db.mongo_store import store


@pytest.fixture(scope='module', autouse=True)
def _register():
    register_all()


def test_guard_ok_query():
    q = {'model': 'CommercialLedger', 'mode': 'query',
         'condition': {'year': {'$eq': 2026}, 'industry': {'$eq': '政企'}},
         'fields': ['signDate', 'unit', 'income'], 'sort': {'income': -1}, 'limit': 50}
    c = verify(q)
    assert c['model'] == 'CommercialLedger' and c['limit'] == 50


def test_guard_ok_aggregate():
    q = {'model': 'ReportOverall', 'mode': 'aggregate', 'condition': {'year': 2026},
         'groupBy': ['unit'], 'measures': [{'op': 'sum', 'field': 'income'}],
         'sort': {'sum_income': -1}}
    c = verify(q)
    assert c['measures'][0]['op'] == 'sum'


def test_guard_reject_unknown_model():
    with pytest.raises(GuardError):
        verify({'model': 'AiModel', 'condition': {}})


def test_guard_reject_dangerous_op():
    with pytest.raises(GuardError):
        verify({'model': 'CommercialLedger', 'condition': {'$where': '1==1'}})


def test_guard_reject_dangerous_op_deep_nested():
    # 藏在被白名单操作符值里的危险操作符，全递归校验必须拦下
    cases = [
        {'year': {'$gt': {'$lookup': {'from': 'users'}}}},
        {'industry': {'$in': [{'$expr': {'$function': 'x'}}]}},
        {'customer': {'$regex': {'$where': '1==1'}}},
        {'$and': [{'year': 2026}, {'$unionWith': 'users'}]},
        {'unit': {'$gt': 0, '$or': [{'income': {'$ne': 1}}], '$not': {'year': 1}}},
    ]
    for cond in cases:
        # 注：pytest.raises 无 msg 参数（6.2+ 已移除），断言信息放 pytest.raises 外层
        with pytest.raises(GuardError) as excinfo:
            verify({'model': 'CommercialLedger', 'condition': cond})
        assert excinfo.value  # GuardError 已抛出即拦截成功


def test_guard_ok_deep_nested_allowed():
    # 合法的多层嵌套白名单操作符应放行
    c = verify({'model': 'CommercialLedger',
                'condition': {'industry': {'$eq': '政企'}, 'year': {'$in': [2025, 2026]}},
                'fields': ['unit', 'income'], 'sort': {'income': -1}, 'limit': 20})
    assert c['limit'] == 20


def test_guard_reject_unknown_field():
    with pytest.raises(GuardError):
        verify({'model': 'CommercialLedger', 'condition': {'hack': 1}})


def test_guard_reject_bad_measure():
    with pytest.raises(GuardError):
        verify({'model': 'ReportOverall', 'mode': 'aggregate', 'groupBy': ['unit'],
                'measures': [{'op': 'sum', 'field': 'unit'}]})


def test_guard_limit_capped():
    c = verify({'model': 'CommercialLedger', 'condition': {}, 'limit': 9999})
    assert c['limit'] == 200


def test_executor_pipeline_shape():
    c = verify({'model': 'ReportOverall', 'mode': 'aggregate', 'condition': {'year': 2026},
                'groupBy': ['unit'], 'measures': [{'op': 'sum', 'field': 'income'}],
                'sort': {'sum_income': -1}, 'limit': 21})
    pl = _build_pipeline(c)
    assert all(set(p) <= {'$match', '$group', '$sort', '$limit', '$project'} for p in pl)
    assert pl[0]['$match'] == {'year': 2026}


def test_auth_token_roundtrip():
    tk = issue_token('admin')
    assert verify_token(tk)['usr'] == 'admin'
    assert verify_token(tk + 'x') is None
    assert verify_token(None) is None


def test_qnorm():
    assert qnorm('政企行业 收入！') == qnorm('政企行业收入')


def test_prompt_contains_models():
    msgs = build_messages('query_gen', {'question': '各产品线销售情况'})
    p = '\n'.join(m['content'] for m in msgs)
    assert 'ReportOverall' in p and 'CommercialLedger' in p


def test_schema_registry_enums():
    ms = {m['model']: m for m in describe_models()}
    assert len(ms) == 8
    units = next(f for m in ms.values() for f in m['fields'] if f['name'] == 'unit')['enum']
    assert units and '北京代表处' in units


def test_step_tracker():
    t = StepTracker()
    t.done(0, 'ok')
    assert t.out()[0]['done'] is True and t.out()[1]['done'] is False


# ---------- pipeline 组装分支 ----------

def test_build_pipeline_default_sort_count():
    # 无 sort + count 聚合 → 默认按首个度量子降序，单分组投影用裸 $_id
    q = {'condition': {}, 'groupBy': ['unit'], 'measures': [{'op': 'count'}], 'limit': 5}
    pl = _build_pipeline(q)
    assert pl[0]['$group']['_id'] == '$unit'
    assert pl[0]['$group'].get('count_all') == {'$sum': 1}
    assert {'$sort': {'count_all': -1}} in pl  # 无 sort → 默认按度量子降序
    assert pl[-1]['$project'] == {'unit': '$_id', 'count_all': 1}


def test_build_pipeline_no_match_multi_groupby():
    # 有 condition 才加 $match；多分组投影用 _id.<field>，聚合字段名 sum_income
    q = {'condition': {'year': 2026}, 'groupBy': ['unit', 'year'],
         'measures': [{'op': 'sum', 'field': 'income'}], 'sort': {'sum_income': -1}, 'limit': 10}
    pl = _build_pipeline(q)
    assert pl[0] == {'$match': {'year': 2026}}
    assert pl[1]['$group']['_id'] == {'unit': '$unit', 'year': '$year'}
    assert pl[1]['$group']['sum_income'] == {'$sum': '$income'}
    assert pl[-1]['$project'] == {'unit': '$_id.unit', 'year': '$_id.year', 'sum_income': 1}


# ---------- 问法缓存相似度（纯逻辑） ----------

def test_cache_score_identical():
    assert _score('政企行业收入', '政企行业收入') == SIM_JACCARD_W + SIM_LEV_W


def test_cache_score_empty():
    assert _score('', 'abc') == 0.0
    assert _score(None or '', 'abc') == 0.0
    assert _score('abc', '') == 0.0


def test_cache_bigrams_levenshtein():
    assert _bigrams('ab') == {'ab'}
    assert _bigrams('a') == {'a'}
    assert _levenshtein('kitten', 'sitting') == 3


# ---------- 候选筛选（纯同步） ----------

def test_pick_checked_combos():
    ok_q = {'model': 'CommercialLedger', 'mode': 'query',
            'condition': {'year': {'$eq': 2026}}, 'fields': ['unit', 'income'], 'limit': 50}
    bad_q = {'model': 'Hack', 'condition': {}}
    cands = [
        (ok_q, {'idx': 0, 'ok': True}),
        (bad_q, {'idx': 1, 'ok': True}),
        (None, {'idx': 2, 'ok': False, 'error': 'boom'}),
    ]
    checked, statuses = pick_checked(cands)
    assert len(checked) == 1
    assert [s['status'] for s in statuses] == ['pass', 'guard_error', 'empty']


# ---------- token 边界 ----------

def _signed_token(exp: int) -> str:
    import base64, hashlib, hmac, json
    from app.config import cfg
    raw = base64.urlsafe_b64encode(json.dumps({'usr': 'x', 'exp': exp}).encode()).decode()
    sig = hmac.new(cfg.APP_SECRET_KEY.encode(), raw.encode(), hashlib.sha256).hexdigest()
    return f'{raw}.{sig}'


def test_auth_token_expired():
    import time
    assert verify_token(_signed_token(int(time.time()) - 10)) is None


def test_auth_token_malformed():
    import base64
    assert verify_token(None) is None
    assert verify_token('no-dot') is None
    assert verify_token('abc.def') is None  # 签名不符
    bad = base64.urlsafe_b64encode(b'not-json').decode() + '.x'
    assert verify_token(bad) is None  # payload 非 JSON


# ---------- JSON Schema 壳（纯函数） ----------

def test_validate_unregistered_passthrough():
    assert validate({'a': 1}, 'no_such_scenario') == {'a': 1}


def test_attach_schema_registered():
    out = attach_schema([{'role': 'user', 'content': 'hi'}], 'query_gen')
    assert len(out) == 2 and out[1]['role'] == 'system' and 'mode' in out[1]['content']


def test_attach_schema_unregistered():
    msgs = [{'role': 'user', 'content': 'hi'}]
    assert attach_schema(msgs, 'nope') is msgs


def test_validate_ok():
    p = {'mode': 'query', 'model': 'CommercialLedger', 'limit': 50,
         'measures': [{'op': 'count', 'field': ''}]}
    assert validate(p, 'query_gen') == p


def test_validate_missing_required():
    with pytest.raises(ShellError):  # model 必填缺失
        validate({'mode': 'query'}, 'query_gen')


def test_validate_type_mismatch():
    with pytest.raises(ShellError):
        validate({'mode': 123, 'model': 'x'}, 'query_gen')


def test_validate_enum_fail():
    with pytest.raises(ShellError):
        validate({'mode': 'raw', 'model': 'x'}, 'query_gen')


def test_validate_extra_key():
    with pytest.raises(ShellError):
        validate({'mode': 'query', 'model': 'x', 'hack': 1}, 'query_gen')


def test_validate_integer_excludes_bool():
    with pytest.raises(ShellError):  # bool 非 integer
        validate({'mode': 'query', 'model': 'x', 'limit': True}, 'query_gen')


def test_validate_non_object():
    with pytest.raises(ShellError):
        validate(['not', 'obj'], 'query_gen')


# ---------- 自动反馈（mock store） ----------

def test_auto_feedback_ok(monkeypatch):
    import asyncio
    captured = {}
    async def fake_insert(schema, doc):
        captured['doc'] = doc
        return {'_id': '1'}
    async def fake_rai(fn):
        return await fn()
    monkeypatch.setattr(store, 'insert', fake_insert)
    monkeypatch.setattr(store, 'run_as_internal', fake_rai)
    asyncio.run(record(category='guard', trigger_point='tp', reason='r', layer='l',
                       upstream='up', fix_hint='fh', question='q', query_raw={'m': 1}))
    assert captured['doc']['category'] == 'guard'
    assert captured['doc']['queryRaw'] != ''  # 有 query_raw → 序列化


def test_auto_feedback_swallow_failure(monkeypatch):
    import asyncio
    async def fake_bad(*a, **k):
        raise RuntimeError('boom')
    async def fake_rai(fn):
        return await fn()
    monkeypatch.setattr(store, 'insert', fake_bad)
    monkeypatch.setattr(store, 'run_as_internal', fake_rai)
    # 告警自身失败不能击穿调用方 → 不抛
    asyncio.run(record(category='fallback', trigger_point='tp', reason='r',
                       layer='l', upstream='up', fix_hint='fh'))
