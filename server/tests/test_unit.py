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
from app.services import llm_client
from app.services import query_cache, query_candidate, query_executor, query_guard
from app.services.llm_client import chat, resolve_base_url
from app.services.qa_service import (
    _active_model, _build_chart, _build_findings, _build_stats,
    _ensure_session, _round_rows, ask_stream)


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


# ---------- llm_client 纯逻辑 + mock ----------

def test_resolve_base_url_preset():
    assert llm_client.resolve_base_url('deepseek') == 'https://api.deepseek.com/v1'


def test_resolve_base_url_unknown_platform():
    with pytest.raises(ValueError):
        llm_client.resolve_base_url('no_such_platform')


def test_resolve_base_url_custom_same_host_ok():
    out = llm_client.resolve_base_url('deepseek', 'https://api.deepseek.com/v2')
    assert out == 'https://api.deepseek.com/v2'


def test_resolve_base_url_evil_host_rejected():
    with pytest.raises(ValueError):
        llm_client.resolve_base_url('deepseek', 'https://evil.com/v1')
    with pytest.raises(ValueError):  # 非 http(s) scheme
        llm_client.resolve_base_url('deepseek', 'file:///etc/passwd')


def test_extract_json_fenced():
    assert llm_client.extract_json('```json\n{"a": 1}\n```') == {'a': 1}


def test_extract_json_bare_with_trailing():
    assert llm_client.extract_json('{"a": 1} trailing text') == {'a': 1}


def test_extract_json_missing():
    with pytest.raises(ValueError):
        llm_client.extract_json('没有任何 JSON 的输出')


def test_resolve_reasoning_mapped():
    assert llm_client._resolve_reasoning('deepseek', 'disabled') == {'type': 'disabled'}


def test_resolve_reasoning_empty_flag():
    assert llm_client._resolve_reasoning('deepseek', '') is None


def test_resolve_reasoning_unmapped():
    assert llm_client._resolve_reasoning('deepseek', 'weird_flag') is None  # 落 warn 告警


def test_chat_success(monkeypatch):
    import asyncio
    class FakeResp:
        status_code = 200
        text = 'ok'
        def json(self):
            return {'choices': [{'message': {'content': 'hi'}}],
                    'usage': {'prompt_tokens': 10, 'completion_tokens': 5, 'total_tokens': 15}}
    class FakeClient:
        async def post(self, *a, **k):
            return FakeResp()
    monkeypatch.setattr(llm_client, '_client', FakeClient())
    out = asyncio.run(llm_client.chat([{'role': 'user', 'content': 'x'}],
                                      base_url='https://api.deepseek.com/v1', api_key='k', model='m'))
    assert out['content'] == 'hi' and out['total_tokens'] == 15


def test_chat_non_200(monkeypatch):
    import asyncio
    class FakeResp:
        status_code = 500
        text = 'boom'
        def json(self):
            return {}
    class FakeClient:
        async def post(self, *a, **k):
            return FakeResp()
    monkeypatch.setattr(llm_client, '_client', FakeClient())
    with pytest.raises(RuntimeError):
        asyncio.run(llm_client.chat([], base_url='https://api.deepseek.com/v1', api_key='k', model='m'))


# ---------- qa_service：私有纯函数 + store mock ----------

def test_round_rows_rounds_floats_keeps_others():
    out = _round_rows([{'a': 1.23456, 'b': 'x', 'c': 3}])
    assert out[0]['a'] == round(1.23456, 2) and out[0]['b'] == 'x' and out[0]['c'] == 3


def test_build_stats_empty_or_no_numeric():
    assert _build_stats([], None)['count'] == 0
    empty_vals = _build_stats([{'a': 'x'}, {'a': 'y'}], 'a')  # 无数值
    assert empty_vals['max'] == 0 and empty_vals['max_of'] == '-'


def test_build_stats_normal_with_max_of():
    stats = _build_stats([{'unit': 'a', 'income': 10}, {'unit': 'b', 'income': 20}], 'income')
    assert stats['count'] == 2 and stats['avg'] == 15.0 and stats['max'] == 20.0
    assert stats['max_of'] == 'b' and stats['min_of'] == 'a'


def test_build_chart_empty_rows():
    assert _build_chart('q', {'mode': 'list', 'fields': ['a']}, []) is None


def test_build_chart_aggregate_default_bar():
    from app.services.query_guard import measure_key as _mk
    q = {'mode': 'aggregate', 'groupBy': ['unit'], 'measures': [{'op': 'sum', 'field': 'income'}]}
    mk = _mk(q['measures'][0])
    rows = [{'unit': 'a', mk: 100}, {'unit': 'b', mk: 200}]
    chart = _build_chart('普通问题', q, rows)
    assert chart['type'] == 'bar' and chart['series'] == [100.0, 200.0]


def test_build_chart_aggregate_pie_by_keyword():
    q = {'mode': 'aggregate', 'groupBy': ['unit'], 'measures': [{'op': 'count', 'field': ''}]}
    rows = [{'unit': 'a', 'x': 1}]
    chart = _build_chart('各平台的占比', q, rows)
    assert chart['type'] == 'pie'


def test_build_chart_time_dim_line():
    q = {'mode': 'aggregate', 'groupBy': ['signDate'], 'measures': [{'op': 'sum', 'field': 'income'}]}
    rows = [{'signDate': '2024-01-01', 'v': 5}, {'signDate': '2024-01-02', 'v': 6}]
    assert _build_chart('趋势', q, rows)['type'] == 'line'


def test_build_chart_list_no_numeric_none():
    q = {'mode': 'list', 'fields': ['unit']}
    assert _build_chart('q', q, [{'unit': 'a'}]) is None


def test_build_chart_list_with_numeric():
    q = {'mode': 'list', 'fields': ['unit', 'income']}
    chart = _build_chart('q', q, [{'unit': 'a', 'income': 300}])
    assert chart['type'] == 'bar' and chart['series'] == [300.0]


def test_build_findings_empty():
    assert _build_findings({'count': 0}, 'income') == ['未查询到符合条件的数据']


def test_build_findings_normal():
    stats = {'count': 5, 'avg': 1.2, 'max': 3, 'max_of': 'b', 'min': 1, 'min_of': 'a'}
    out = _build_findings(stats, 'income')
    assert '共 5 条' in out[0] and '最大值 3' in out[1]


def test_active_model_ok(monkeypatch):
    import asyncio
    async def fake(gql, params=None):
        return {'enabled': True, 'name': 'M', 'platform': 'deepseek', 'baseUrl': '',
                'apiKey': 'k', 'modelName': 'deepseek-chat'}
    monkeypatch.setattr(store, 'query_one', fake)
    m = asyncio.run(_active_model())
    assert m['modelName'] == 'deepseek-chat'


def test_active_model_no_enabled(monkeypatch):
    import asyncio
    from app.errors import BusinessError
    async def fake(gql, params=None):
        return None
    monkeypatch.setattr(store, 'query_one', fake)
    with pytest.raises(BusinessError):
        asyncio.run(_active_model())


def test_active_model_bad_platform(monkeypatch):
    import asyncio
    from app.errors import BusinessError
    async def fake(gql, params=None):
        return {'enabled': True, 'name': 'M', 'platform': 'unknown', 'apiKey': 'k'}
    monkeypatch.setattr(store, 'query_one', fake)
    with pytest.raises(BusinessError):
        asyncio.run(_active_model())


def test_ensure_session_existing(monkeypatch):
    import asyncio
    async def fake(gql, params=None):
        return {'_id': 's1', 'title': 't'}
    monkeypatch.setattr(store, 'query_one', fake)
    s = asyncio.run(_ensure_session('s1', '问'))
    assert s['_id'] == 's1'


def test_ensure_session_missing(monkeypatch):
    import asyncio
    from app.errors import BusinessError
    async def fake(gql, params=None):
        return None
    monkeypatch.setattr(store, 'query_one', fake)
    with pytest.raises(BusinessError):
        asyncio.run(_ensure_session('gone', '问'))


def test_ensure_session_create(monkeypatch):
    import asyncio
    created = []
    async def fake_insert(schema_name, data):
        created.append((schema_name, data))
        return {'_id': 'new'}
    monkeypatch.setattr(store, 'insert', fake_insert)
    s = asyncio.run(_ensure_session(None, '新问题'))
    assert s['_id'] == 'new' and created[0][0] == 'QaSession'


# ---------- ask_stream 全链路 mock（SSE 事件流） ----------

def _ask_stream_mocks(monkeypatch, question='上月收入多少', rows=None, few=None):
    import asyncio
    from app.db.mongo_store import store as st
    if rows is None:
        rows = [{'unit': 'a', 'income': 100}]
    q = {'model': 'CommercialLedger', 'mode': 'list', 'condition': {},
         'fields': ['unit', 'income'], 'sort': {}, 'limit': 50}

    async def fake_run(checked):
        return (rows, False)
    async def fake_hit(question_):
        return None
    async def fake_few(question_):
        return few or []
    async def fake_gen(question_, f, conf, n, conc, **k):
        return ([(q, {'ok': True, 'tokens': 5, 'cache_hit': 0, 'cache_miss': 0})], None)
    async def fake_invoke(scenario, vars_, conf):
        if scenario == 'conclusion':
            return ({'text': '结论', 'follow_ups': ['追问1', '追问2']},
                    {'total_tokens': 12, 'elapsed_s': 0.1,
                     'cache_hit_tokens': 0, 'cache_miss_tokens': 0})
        return ({}, {'total_tokens': 3, 'elapsed_s': 0.1,
                     'cache_hit_tokens': 0, 'cache_miss_tokens': 0})
    async def fake_q1(gql, params=None):
        return {'enabled': True, 'name': 'M', 'platform': 'deepseek', 'baseUrl': '',
                'apiKey': 'k', 'modelName': 'deepseek-chat'}
    async def fake_q(gql, params=None):
        return []
    async def fake_insert(schema, data):
        return {'_id': 'x'}
    async def fake_count(schema, cond=None):
        return 1
    async def fake_update(*a, **k):
        return {'_id': 'x'}
    async def fake_upsert(*a, **k):
        return None

    monkeypatch.setattr(query_guard, 'verify', lambda x: x)
    monkeypatch.setattr(query_executor, 'run', fake_run)
    monkeypatch.setattr(query_cache, 'exact_hit', fake_hit)
    monkeypatch.setattr(query_cache, 'top_k_fuzzy', fake_few)
    monkeypatch.setattr(query_cache, 'upsert', fake_upsert)
    monkeypatch.setattr(query_candidate, 'generate_candidates', fake_gen)
    monkeypatch.setattr(query_candidate, 'pick_checked',
                        lambda cands: ([q], [{'idx': 0, 'status': 'pass'}]))
    monkeypatch.setattr(llm_client, 'invoke', fake_invoke)
    monkeypatch.setattr(st, 'query_one', fake_q1)
    monkeypatch.setattr(st, 'query', fake_q)
    monkeypatch.setattr(st, 'insert', fake_insert)
    monkeypatch.setattr(st, 'count', fake_count)
    monkeypatch.setattr(st, 'update', fake_update)
    return question, rows


def test_ask_stream_success_cold(monkeypatch):
    import asyncio
    question, _ = _ask_stream_mocks(monkeypatch)  # few=[] → cold tier
    events = []
    async def collect():
        async for ev in ask_stream(question, None, [], '管理员'):
            events.append(ev)
    asyncio.run(collect())
    types = [e['type'] for e in events]
    assert 'error' not in types, events[-1] if types else 'no events'
    assert 'done' in types
    done = next(e['data'] for e in events if e['type'] == 'done')
    assert done['row_count'] == 1 and done['query_source'] == 'llm'
    assert [e['type'] for e in events].count('step') >= 4  # 0,1,2,3,4 逐步事件


def test_ask_stream_success_warm(monkeypatch):
    import asyncio
    from app.config import QA_HOT_FUZZY_SCORE
    question, _ = _ask_stream_mocks(
        monkeypatch, few=[{'question': 'q', 'score': QA_HOT_FUZZY_SCORE + 0.1}])
    events = []
    async def collect():
        async for ev in ask_stream(question, None, [], '管理员'):
            events.append(ev)
    asyncio.run(collect())
    types = [e['type'] for e in events]
    assert 'error' not in types and 'done' in types


def test_ask_stream_exact_cache_hit(monkeypatch):
    import asyncio
    from app.db.mongo_store import store as st
    q = {'model': 'CommercialLedger', 'mode': 'list', 'condition': {},
         'fields': ['unit', 'income'], 'sort': {}, 'limit': 50}
    async def fake_hit(question_):
        return {'template': q, 'answer': '旧答案'}
    async def fake_run(checked):
        return ([{'unit': 'a', 'income': 100}], False)
    async def fake_q1(gql, params=None):
        return {'enabled': True, 'name': 'M', 'platform': 'deepseek',
                'baseUrl': '', 'apiKey': 'k', 'modelName': 'm'}
    async def fake_upsert(*a, **k):
        return None
    async def fake_insert(schema, data):
        return {'_id': 'x'}
    async def fake_count(schema, cond=None):
        return 1
    async def fake_update(*a, **k):
        return {'_id': 'x'}
    monkeypatch.setattr(query_guard, 'verify', lambda x: x)
    monkeypatch.setattr(query_executor, 'run', fake_run)
    monkeypatch.setattr(query_cache, 'exact_hit', fake_hit)
    monkeypatch.setattr(query_cache, 'top_k_fuzzy', lambda q_: [])
    monkeypatch.setattr(query_cache, 'upsert', fake_upsert)
    async def fake_gen(question_, f, conf, n, conc, **k):
        return ([(q, {'ok': True, 'tokens': 5, 'cache_hit': 0, 'cache_miss': 0})], None)
    monkeypatch.setattr(query_candidate, 'generate_candidates', fake_gen)
    monkeypatch.setattr(query_candidate, 'pick_checked',
                        lambda cands: ([q], [{'idx': 0, 'status': 'pass'}]))
    async def fake_invoke(scenario, v, c):
        return ({'text': 't', 'follow_ups': []},
                {'total_tokens': 5, 'elapsed_s': 0.1,
                 'cache_hit_tokens': 0, 'cache_miss_tokens': 0})
    monkeypatch.setattr(llm_client, 'invoke', fake_invoke)
    monkeypatch.setattr(st, 'query_one', fake_q1)
    async def fake_goal_query(*a, **k):
        return []
    monkeypatch.setattr(st, 'query', fake_goal_query)
    monkeypatch.setattr(st, 'insert', fake_insert)
    monkeypatch.setattr(st, 'count', fake_count)
    monkeypatch.setattr(st, 'update', fake_update)
    events = []
    async def collect():
        async for ev in ask_stream('同款问法', None, [], '管理员'):
            events.append(ev)
    asyncio.run(collect())
    errs = [e for e in events if e['type'] == 'error']
    assert not errs, errs
    assert 'done' in [e['type'] for e in events]
    done = next(e['data'] for e in events if e['type'] == 'done')
    assert done['query_source'] == 'exact_cache'
