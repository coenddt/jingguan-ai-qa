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


# ---------- 守卫内部纯函数（定向补测，杀存活变异） ----------

from app.services.query_guard import (
    _check_key, _clamp_limit, _descend_value, _group_by_checked,
    _load_model, _normalize_measure, _reject_op, _resolve_fields, _sort_checked,
    _verify_aggregate, measure_key,
)
from app.config import ALLOWED_OPS, DENIED_OPS, MAX_LIMIT


def test_guard_descend_scalar_no_recurse():
    # 标量/普通列表不递归：合法值直接通过，不抛错
    _descend_value(2026, {'year'}, 'root.year')
    _descend_value([1, 2, 'x'], {'year'}, 'root.year')
    _descend_value(None, {'year'}, 'root.year')


def test_guard_descend_list_of_dict_catches_deep():
    # 字典数组里藏危险操作符 → 带下标路径递归拦截
    with pytest.raises(GuardError):
        _descend_value([{'income': {'$where': '1'}}], {'income'}, 'root.arr')


def test_guard_descend_dict_passthrough():
    # 字典原样递归进 walk_condition
    with pytest.raises(GuardError):
        _descend_value({'year': {'$gte': 2026, '$merge': 'x'}}, {'year'}, 'root')


def test_guard_reject_op_denied_message():
    with pytest.raises(GuardError) as e:
        _reject_op('$where', '')
    assert '禁用' in str(e.value)
    with pytest.raises(GuardError) as e2:
        _reject_op('$lookup', 'a.b')
    assert '@ a.b' in str(e2.value)


def test_guard_reject_op_unknown_not_denied():
    # 不在 DENIED 也不算 ALLOWED 的野操作符 → 越界
    with pytest.raises(GuardError) as e:
        _reject_op('$set', '')
    assert '越界' in str(e.value)


def test_guard_check_key_non_string():
    with pytest.raises(GuardError):
        _check_key(123, {'year'}, '')


def test_guard_check_key_dollar_and_field():
    _check_key('$eq', ALLOWED_OPS, '')   # 允许的操作符放行
    _check_key('year', {'year'}, '')     # 白名单字段放行
    with pytest.raises(GuardError):
        _check_key('$or', ALLOWED_OPS, '')  # $or 在白名单但不在 ALLOWED_OPS
    with pytest.raises(GuardError):
        _check_key('hack', {'year'}, 'a.b')  # 未知字段携路径


def test_guard_sort_checked_empty_and_bad():
    assert _sort_checked({}, {'unit'}) == {}
    assert _sort_checked({'unit': -1}, {'unit'}) == {'unit': -1}
    with pytest.raises(GuardError):
        _sort_checked({'income': 1}, {'unit'})


def test_guard_resolve_fields_default_and_bad():
    names = {'unit', 'income'}
    assert sorted(_resolve_fields({'fields': []}, names)) == ['income', 'unit']
    assert _resolve_fields({'fields': ['unit']}, names) == ['unit']
    with pytest.raises(GuardError):
        _resolve_fields({'fields': ['hack']}, names)


def test_guard_clamp_limit():
    assert _clamp_limit({}) == MAX_LIMIT
    assert _clamp_limit({'limit': '10'}) == 10
    assert _clamp_limit({'limit': -5}) == -5  # 负数不放大宽，int 原样截断
    assert _clamp_limit({'limit': 99999}) == MAX_LIMIT


def test_guard_group_by_checked():
    assert _group_by_checked({'groupBy': ['unit']}, {'unit'}) == ['unit']
    with pytest.raises(GuardError):
        _group_by_checked({'groupBy': ['hack']}, {'unit'})
    with pytest.raises(GuardError):
        _group_by_checked({'groupBy': []}, {'unit'})


def test_guard_normalize_measure_boundaries():
    fd = {'income': {'type': 'float'}, 'unit': {'type': 'string'}}
    names = {'income', 'unit'}
    assert _normalize_measure({'op': 'sum', 'field': 'income'}, fd, names) == {'op': 'sum', 'field': 'income'}
    assert _normalize_measure({'op': 'count', 'field': ''}, fd, names)['field'] == ''
    with pytest.raises(GuardError):  # 算子越界
        _normalize_measure({'op': 'stddev', 'field': 'income'}, fd, names)
    with pytest.raises(GuardError):  # 非数值目标
        _normalize_measure({'op': 'sum', 'field': 'unit'}, fd, names)
    with pytest.raises(GuardError):  # 字段不在白名单
        _normalize_measure({'op': 'sum', 'field': 'hack'}, fd, names)


def test_guard_measure_key():
    assert measure_key({'op': 'sum', 'field': 'income'}) == 'sum_income'
    assert measure_key({'op': 'count', 'field': ''}) == 'count_all'


def test_guard_verify_aggregate_requires_measure():
    with pytest.raises(GuardError):
        _verify_aggregate({'groupBy': ['unit'], 'measures': []}, {}, {'unit'})


def test_guard_load_model_rejects_non_business():
    with pytest.raises(GuardError):
        _load_model({'model': 'QaSession', 'condition': {}})


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


def test_executor_sort_stage_explicit_vs_default_none():
    from app.services.query_executor import _sort_stage
    # 显式 sort 优先
    assert _sort_stage({'sort': {'unit': 1}}, {'_id': '$unit', 'count_all': {'$sum': 1}}) == {'$sort': {'unit': 1}}
    # 无 sort → 按首个聚合键倒序
    assert _sort_stage({'sort': {}}, {'_id': '$unit', 'count_all': {'$sum': 1}}) == {'$sort': {'count_all': -1}}
    # 既无 sort 也无聚合键 → None（跳过 sort 阶段）
    assert _sort_stage({'sort': {}}, {'_id': '$unit'}) is None


def test_executor_group_doc_single_multi_count():
    from app.services.query_executor import _group_doc
    # 单分组 → 裸 $_id
    assert _group_doc({'groupBy': ['unit'], 'measures': [{'op': 'count'}]})['_id'] == '$unit'
    # 多分组 → 对象 _id
    g = _group_doc({'groupBy': ['unit', 'year'], 'measures': [{'op': 'sum', 'field': 'income'}]})
    assert g['_id'] == {'unit': '$unit', 'year': '$year'} and g['sum_income'] == {'$sum': '$income'}
    # count → $sum:1
    assert _group_doc({'groupBy': ['unit'], 'measures': [{'op': 'count'}]})['count_all'] == {'$sum': 1}


def test_executor_project_stage_multi_count():
    from app.services.query_executor import _project_stage
    # 单分组 → _id 还原；多分组 → _id.<field>
    p1 = _project_stage({'groupBy': ['unit'], 'measures': [{'op': 'count'}]})
    assert p1 == {'unit': '$_id', 'count_all': 1}
    p2 = _project_stage({'groupBy': ['unit', 'year'], 'measures': [{'op': 'count'}]})
    assert p2 == {'unit': '$_id.unit', 'year': '$_id.year', 'count_all': 1}


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
    assert _bigrams('') == {''}
    assert _levenshtein('kitten', 'sitting') == 3
    assert _levenshtein('', 'abc') == 3
    assert _levenshtein('ab', 'ab') == 0
    assert _levenshtein('a', 'b') == 1


def test_cache_score_mixed():
    # 重叠字形越多分数越高（jaccard + lev 加权）
    s_high = _score('收入排行榜', '收入排行')
    s_low = _score('收入排行榜', '合同履约进度')
    assert s_high > s_low
    assert _score('完全', '不同') < 1.0


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


# ---------- mongo_store pipeline 纯函数（无 DB，内联 schema） ----------

from app.db.mongo_store import pipeline as ppl

# 构造与 schema.get() 输出同构的内联 schema（fields 为 {type, ...} 字典）
_PIPE_SRC = {
    'name': 'Source', 'collection': 'src', 'timestamps': True,
    'fields': {
        '_id': {'type': 'string'},
        'unit': {'type': 'string'},
        'tags': {'type': 'array'},
        'obj': {'type': 'object', 'fields': {'x': {'type': 'string'}, 'y': {'type': 'string'}}},
    },
    'relations': {'rows': {'model': 'Row', 'type': 'many', 'localField': '_id',
                           'foreignField': 'srcId'}},
    'computes': {},
}
_PIPE_ROW = {
    'name': 'Row', 'collection': 'row', 'timestamps': True,
    'fields': {'income': {'type': 'float'}, 'label': {'type': 'string'}},
    'relations': {}, 'computes': {},
}


def test_pipeline_tokenize():
    toks = ppl.tokenize('Model($condition:@c0) { a, b }')
    k = {t['v'] for t in toks}
    assert 'Model' in k and '@c0' in k and 'a' in k


def test_pipeline_parse_gql_ast():
    ast = ppl.parse_gql('Model($condition:@c0){a, Row{b, c}}')
    assert ast['model'] == 'Model'
    assert ast['params']['condition'] == '@c0'
    assert ast['fields'] == ['a']
    assert set(ast['relations']['Row']['fields']) == {'b', 'c'}  # 关系子体无参数
    assert ast['relations']['Row']['params'] == {}


def test_pipeline_parse_gql_relation_with_params_no_body():
    # 既有解析器局限：带参数的关系节点后不能接花括号子体（has_brace 在解析参数前取值）
    ast = ppl.parse_gql('Model{a, Row($sort:@s0)}')
    assert ast['relations']['Row']['params']['sort'] == '@s0'
    assert ast['relations']['Row']['fields'] == []


def test_pipeline_parse_error_at_eof():
    with pytest.raises(ValueError):
        ppl.parse_gql('Model{$condition:')  # 注释: 未闭合 → consume 到末尾抛错


def test_pipeline_flatten_object_fields():
    ast = {'fields': [], 'relations': {'obj': {'fields': ['x', 'y'], 'params': {}}}}
    ppl.flatten_object_fields(ast, _PIPE_SRC)
    assert ast['fields'] == ['obj.x', 'obj.y']
    assert 'obj' not in ast['relations']


def test_pipeline_flatten_object_skips_non_object():
    ast = {'fields': ['unit'], 'relations': {'rows': {'fields': ['income'], 'params': {}}}}
    ppl.flatten_object_fields(ast, _PIPE_SRC)
    # rows 是 many 关系非 object → 不被展平
    assert 'rows' in ast['relations'] and ast['fields'] == ['unit']


def test_pipeline_build_projection_basic():
    schema = {'fields': {'unit': {'type': 'string'}, 'income': {'type': 'float'}}, 'computes': {}}
    proj = ppl.build_projection({'fields': ['unit', 'income'], 'relations': {}}, schema)
    assert proj['_id'] == 1 and proj['unit'] == 1 and proj['income'] == 1


def test_pipeline_build_projection_empty_fields_none():
    assert ppl.build_projection({'fields': [], 'relations': {}}, {'fields': {}, 'computes': {}}) is None


def test_pipeline_build_projection_compute_with_depends():
    schema = {'fields': {'a': {'type': 'string'}, 'dep': {'type': 'string'}},
              'computes': {'total': {'type': 'float', 'fn': lambda r: 0, 'depends': ['dep']}}}
    proj = ppl.build_projection({'fields': ['a'], 'relations': {}}, schema)
    # 声明了 depends → 仅补依赖字段，计算列名不入投影
    assert proj['a'] == 1 and proj['dep'] == 1 and 'total' not in proj


def test_pipeline_build_projection_compute_no_depends_fallback():
    schema = {'fields': {'a': {'type': 'string'}, 'c': {'type': 'string'}},
              'computes': {'total': {'type': 'float', 'fn': lambda r: 0}}}
    proj = ppl.build_projection({'fields': ['a'], 'relations': {}}, schema)
    # 无 depends → 安全兜底包含所有 schema 字段
    assert proj['a'] == 1 and proj['c'] == 1


def test_pipeline_build_projection_dot_field():
    schema = {'fields': {'obj': {'type': 'object', 'fields': {'x': {}}}}, 'computes': {}}
    proj = ppl.build_projection({'fields': ['obj.x'], 'relations': {}}, schema)
    assert proj['obj.x'] == 1


def test_pipeline_build_projection_relations_included():
    schema = {'fields': {'unit': {'type': 'string'}}, 'computes': {},
              'relations': {'rows': {'model': 'Row'}}}
    proj = ppl.build_projection({'fields': ['unit'], 'relations': {'rows': {}}}, schema)
    assert proj['rows'] == 1


def test_pipeline_build_compute_lookup_stages():
    schema = {'computes': {
        'a': {'type': 'any'},
        'b': {'type': 'any', 'lookup': {'from': 'refs'}},
    }}
    stages = ppl.build_compute_lookup_stages(schema)
    assert len(stages) == 1 and stages[0]['$lookup']['from'] == 'refs'


def test_pipeline_build_empty_lookup_array_guard():
    rel_def = {'localField': 'tags', 'foreignField': 'tagId'}
    out = ppl.build_empty_lookup('tags', rel_def, {'collection': 'tag'},
                                 {'fields': {'tags': {'type': 'array'}}})
    let = out['$lookup']['let']['rel_tags']
    assert '$cond' in let  # 数组字段 → $cond/$isArray 守卫
    assert out['$lookup']['pipeline'][0]['$match']['$expr']['$in']


def test_pipeline_build_lookup_scalar_with_sort_limit():
    rel_def = {'localField': '_id', 'foreignField': 'srcId'}
    rel_ast = {'params': {'condition': '@c0', 'sort': '@s0', 'limit': '@l0'}, 'fields': ['income']}
    out = ppl.build_lookup('rows', rel_ast, {'c0': {'income': {'$gt': 0}}, 's0': {'income': -1}, 'l0': 5},
                           rel_def, _PIPE_ROW, _PIPE_SRC)
    pl = out['$lookup']['pipeline']
    assert pl[0]['$match']['$and'][0]['$expr']['$eq'] == ['$srcId', '$$rel__id']
    assert {'$sort': {'income': -1}} in pl and {'$limit': 5} in pl
    assert pl[-1]['$project']['income'] == 1


def test_pipeline_build_lookup_depth_guard_empty():
    rel_def = {'localField': '_id', 'foreignField': 'srcId'}
    rel_ast = {'params': {'limit': '@l0'}, 'fields': []}
    out = ppl.build_lookup('rows', rel_ast, {'l0': 1}, rel_def, _PIPE_ROW, _PIPE_SRC,
                           _depth=10, _paginated=0)  # 超 MAX_DEPTH → 空 lookup 降级
    assert len(out['$lookup']['pipeline']) == 1  # 仅 $match，不再嵌套/投影


def test_pipeline_build_lookup_nested_relation(monkeypatch):
    child_schema = {'name': 'Child', 'collection': 'child', 'relations': {}, 'computes': {},
                    'fields': {'name': {'type': 'string'}}}
    row_schema = {'name': 'Row', 'collection': 'row',
                  'relations': {'child': {'model': 'Child', 'type': 'one',
                                          'localField': '_id', 'foreignField': 'rowId'}},
                  'computes': {}, 'fields': {'income': {'type': 'float'}}}
    monkeypatch.setattr(ppl, 'get', lambda n: {'Child': child_schema, 'Row': row_schema}[n])
    rel_ast = {'params': {}, 'fields': ['income'],
               'relations': {'child': {'params': {}, 'fields': ['name']}}}
    rel_def = {'localField': '_id', 'foreignField': 'rowId'}
    out = ppl.build_lookup('rows', rel_ast, {}, rel_def, row_schema, _PIPE_SRC)
    # 嵌套 child + one 关系 → 追加 $unwind
    pl = out['$lookup']['pipeline']
    assert {'$unwind': {'path': '$child', 'preserveNullAndEmptyArrays': True}} in pl


def test_pipeline_build_add_fields(monkeypatch):
    schema = {'computes': {
        'b': {'type': 'any', 'lookup': {'from': 'refs', 'addFields': {'$size': ['$tags']}}},
    }}
    monkeypatch.setattr(ppl, 'get_readable_computes', lambda s, ctx: {'b'})
    out = ppl.build_add_fields(schema, {'roles': ['admin']})
    assert out['$addFields']['b'] == {'$size': ['$tags']}


def test_pipeline_build_pipeline_custom_mode(monkeypatch):
    monkeypatch.setattr(ppl, 'get',
                        lambda n: {'name': n, 'collection': 'c', 'fields': {}, 'relations': {}, 'computes': {}})
    ast = {'model': 'X', 'params': {'pipeline': '@p0', 'condition': '@c0', 'limit': '@l0'},
           'fields': [], 'relations': {}}
    out = ppl.build_pipeline(ast, {'p0': [{'$match': {}}, {'$limit': 10}], 'c0': {'a': 1}, 'l0': 50})
    assert out[0]['$match'] == {'a': 1}  # 自定义管道存在 $match → 原地替换
    assert {'$limit': 50} in out


def test_pipeline_build_pipeline_standard_no_ctx(monkeypatch):
    monkeypatch.setattr(ppl, 'get',
                        lambda n: {'name': n, 'collection': 'c', 'fields': {'a': {'type': 'int'}},
                                   'relations': {}, 'computes': {}})
    ast = {'model': 'X', 'params': {'condition': '@c0', 'limit': '@l0'},
           'fields': ['a'], 'relations': {}}
    out = ppl.build_pipeline(ast, {'c0': {'year': 2026}, 'l0': 10})
    assert out[0] == {'$match': {'year': 2026}}
    assert {'$limit': 10} in out


# ---------- mongo_store permission 纯逻辑 ----------

import app.db.mongo_store.permission as perm


def test_perm_evaluate_no_roles_ctx_none():
    assert perm.evaluate(None, None) is True       # 无上下文 → 权限放行
    assert perm.evaluate({'roles': ['buyer']}, None) is True  # 无白名单 + 已登录 → 放行
    assert perm.evaluate({'roles': ['guest']}, None) is False # 无白名单 + guest → 拒


def test_perm_evaluate_internal_always_pass():
    assert perm.evaluate({'internal': True}, ['seller']) is True
    assert perm.evaluate({'internal': True, 'roles': ['guest']}, ['seller']) is True


def test_perm_evaluate_role_match_and_creator():
    assert perm.evaluate({'roles': ['admin']}, ['super_admin', 'admin']) is True
    assert perm.evaluate({'roles': ['seller']}, ['admin']) is False
    assert perm.evaluate({'roles': ['seller']}, ['creator']) is True   # 新插入，doc=_MISSING
    assert perm.evaluate({'roles': [], 'userId': 'u1'}, ['creator'], {'createdBy': 'u1'}) is True
    assert perm.evaluate({'roles': [], 'userId': 'u1'}, ['creator'], {'createdBy': 'u2'}) is False


def test_perm_schema_read_write():
    s = {'read': ['admin'], 'write': ['seller']}
    assert perm.can_read_schema(s, {'roles': ['admin']}) is True
    assert perm.can_read_schema(s, {'roles': ['seller']}) is False
    assert perm.can_write_schema(s, {'roles': ['seller']}) is True
    # 游客无论配置如何均无写权限
    assert perm.can_write_schema(s, {'roles': ['guest']}) is False


def test_perm_owner_condition():
    # 无 userId / internal / admin → 不注入归属条件
    assert perm.merge_owner_condition({'read': ['creator']}, {'roles': ['admin']}, {}) == {}
    assert perm.merge_owner_condition({'read': ['creator']}, {'internal': True}, {'a': 1}) == {'a': 1}
    # seller + 仅 creator 可读 → 注入 createdBy
    out = perm.merge_owner_condition({'read': ['creator']}, {'roles': ['seller'], 'userId': 'u1'}, None)
    assert out == {'createdBy': 'u1'}
    out2 = perm.merge_owner_condition({'read': ['creator']}, {'roles': ['seller'], 'userId': 'u1'}, {'year': 1})
    assert out2 == {'$and': [{'year': 1}, {'createdBy': 'u1'}]}


def test_perm_readable_fields_computes():
    schema = {'fields': {'a': {'type': 'string'}, 'b': {'type': 'string', 'read': ['admin']}},
              'computes': {'c': {'type': 'any', 'read': ['admin']}, 'd': {'type': 'any'}}}
    assert perm.get_readable_fields(schema, None) is None
    f = perm.get_readable_fields(schema, {'roles': ['seller']})
    assert 'a' in f and 'b' not in f
    c = perm.get_readable_computes(schema, {'roles': ['admin']})
    assert 'c' in c and 'd' in c


def test_perm_scoped_roles_and_run_as_internal(monkeypatch):
    import asyncio
    perm.set_context(None)
    with perm.scoped_roles(['seller']):
        assert perm.get_context()['roles'] == ['seller']
    assert perm.get_context() is None  # 退出恢复原上下文
    async def coro():
        return perm.get_context().get('internal')
    out = asyncio.run(perm.run_as_internal(coro))
    assert out is True


def test_perm_filter_writable_data():
    schema = {'fields': {'a': {'type': 'string'}, 'b': {'type': 'string', 'write': ['admin']}},
              'read': ['admin'], 'write': ['seller', 'admin']}
    assert perm.filter_writable_data(schema, None, {'a': 1, 'b': 1}) == {'a': 1, 'b': 1}  # 无上下文不过滤
    key_seller = perm.get_writable_fields(schema, {'roles': ['seller']})
    assert 'a' in key_seller and 'b' not in key_seller  # 字段 b 写了 write 且有白名单 → 非白名单拒


# ---------- mongo_store computes 计算列引擎（纯逻辑） ----------

from app.db.mongo_store import computes as comp


def test_computes_resolve_default():
    assert comp._resolve_default(5) == 5 and comp._resolve_default('x') == 'x'
    lst = [1, 2]
    assert comp._resolve_default(lst) == [1, 2] and comp._resolve_default(lst) is not lst  # 新实例
    d = {'a': 1}
    out = comp._resolve_default(d)
    assert out == {'a': 1} and out is not d  # 新实例
    assert comp._resolve_default(lambda: 42) == 42  # callable 取调用结果


def test_computes_apply_defaults_and_computes():
    schema = {
        'fields': {
            'unit': {'type': 'string', 'default': '默认'},
            'income': {'type': 'float'},
            'obj': {'type': 'object', 'fields': {'x': {'type': 'int', 'default': 7}}},
        },
        'computes': {
            'total': {'type': 'float', 'fn': lambda r: (r.get('income') or 0) * 2},
        },
    }
    # 已有值不覆盖；fn 计算列生效
    out = comp.apply_defaults_and_computes({'unit': '', 'income': 10}, schema)
    assert out['unit'] == '' and out['total'] == 20
    # None 补零值 + 嵌套 object 子字段默认值
    out2 = comp.apply_defaults_and_computes({'income': None, 'obj': {'x': None}}, schema)
    assert out2['income'] == 0 and out2['obj']['x'] == 7


def test_computes_process_node_defaults_fn_prune():
    schema = {'name': 'T1',
              'fields': {'a': {'type': 'string', 'default': 'd'}, 'b': {'type': 'string'},
                         'income': {'type': 'float'}},
              'computes': {'total': {'type': 'float',
                                     'fn': lambda r: (r.get('income') or 0) * 2,
                                     'depends': ['income']}}}
    ast_node = {'fields': ['a', 'b', 'total'], 'relations': {}}
    doc = {'_id': '1', 'a': None, 'b': 'keep', 'income': 5}
    comp.process_node(doc, ast_node, schema, None)
    assert doc['a'] == 'd' and doc['b'] == 'keep' and doc['total'] == 10
    assert '_id' in doc and 'income' not in doc  # 依赖字段被裁，_id 保留


def test_computes_process_node_dot_prune():
    schema = {'name': 'T2', 'fields': {
        'obj': {'type': 'object', 'fields': {'x': {'type': 'string'}, 'y': {'type': 'string'}}},
    }, 'computes': {}}
    ast_node = {'fields': ['obj.x'], 'relations': {}}
    doc = {'_id': '1', 'obj': {'x': 'vx', 'y': 'vy'}, 'extra': 1}
    comp.process_node(doc, ast_node, schema, None)
    assert doc['obj'] == {'x': 'vx'} and 'extra' not in doc  # 点号子字段裁剪


def test_computes_process_node_nested_relation(monkeypatch):
    child = {'name': 'ChildR', 'fields': {'c': {'type': 'string', 'default': 'cd'}},
             'computes': {}, 'relations': {}}
    parent = {'name': 'ParentR', 'fields': {'p': {'type': 'string'}}, 'computes': {},
              'relations': {'child': {'model': 'ChildR', 'type': 'one'}}}
    monkeypatch.setattr(comp, '_get_schema', lambda n: child if n == 'ChildR' else parent)
    ast_node = {'fields': ['p'], 'relations': {'child': {'fields': ['c'], 'relations': {}}}}
    doc = {'_id': '1', 'p': 'pv', 'child': {'c': None}}
    comp.process_node(doc, ast_node, parent, None)
    assert doc['p'] == 'pv' and doc['child']['c'] == 'cd'  # 递归补默认值


def test_computes_merge_depends_into_ast():
    schema = {'name': 'T3', 'fields': {},
              'relations': {'child': {'model': 'ChildX', 'type': 'one'}},
              'computes': {'agg': {'type': 'any', 'asyncFn': lambda i, ctx: None,
                                   'depends': ['child{c, d}']}}}
    ast = {'fields': ['a'], 'relations': {}}
    inject = comp._merge_depends_into_ast(ast, schema)
    assert set(ast['relations']['child']['fields']) == {'c', 'd'}  # 依赖注入顺序由 set 决定
    assert inject['relations']['child'] == '__all__'


def test_computes_strip_dep_injected():
    items = [{'child': [{'c': 1, 'd': 2}]}, {'child': {'c': 3, 'd': 4}}, {'child': [{'c': 5}]}]
    comp._strip_dep_injected(items, {'relations': {'child': {'c'}}}, None)
    assert items[0]['child'][0] == {'d': 2}   # 列表子文档，c 被裁
    assert items[1]['child'] == {'d': 4}      # 单文档，c 被裁
    # __all__ 整条关系移除
    comp._strip_dep_injected(items, {'relations': {'extra': '__all__'}}, None)
    assert 'extra' not in items[0]


def test_computes_run_async_fns(monkeypatch):
    import asyncio
    ran = []
    async def af(items, ctx):
        ran.append(items)
        return None
    schema = {'name': 'T_async', 'fields': {},
              'computes': {'agg': {'type': 'any', 'asyncFn': af}}}
    comp._defaults_cache.clear()
    asyncio.run(comp._run_async_fns([{'x': 1}], schema, None))
    assert ran  # 协程 asyncFn 被执行


# ---------- query_executor.run 全链路 mock ----------

import contextlib
from app.services import query_executor as qx


def _inject(monkeypatch):
    from app.db.mongo_store import store as st
    @contextlib.contextmanager
    def _ctx(*a, **k):
        yield
    monkeypatch.setattr(st, 'scoped_roles', _ctx)
    return st


def test_query_executor_run_query_mode(monkeypatch):
    import asyncio
    st = _inject(monkeypatch)
    gqls = []
    async def fake_query(gql, params=None):
        gqls.append(gql)
        return [{'_id': '1', 'unit': 'a', 'income': 100}]
    monkeypatch.setattr(st, 'query', fake_query)
    q = {'model': 'CommercialLedger', 'mode': 'query', 'condition': {},
         'fields': ['unit', 'income'], 'sort': {'income': -1}, 'limit': 50}
    rows, truncated = asyncio.run(qx.run(q))
    assert rows == [{'unit': 'a', 'income': 100}] and truncated is False
    assert 'CommercialLedger' in gqls[0]  # GQL 含业务模型名


def test_query_executor_run_aggregate_truncated(monkeypatch):
    import asyncio
    st = _inject(monkeypatch)
    async def fake_agg(schema_name, pl):
        return [{'unit': 'a', 'sum_income': 100}, {'unit': 'b', 'sum_income': 200}]
    monkeypatch.setattr(st, 'aggregate', fake_agg)
    q = {'model': 'ReportOverall', 'mode': 'aggregate', 'condition': {'year': 2026},
         'groupBy': ['unit'], 'measures': [{'op': 'sum', 'field': 'income'}], 'limit': 1}
    rows, truncated = asyncio.run(qx.run(q))
    assert len(rows) == 1 and truncated is True


def test_query_executor_run_model_not_in_whitelist(monkeypatch):
    import asyncio
    from app.services.query_guard import GuardError
    _inject(monkeypatch)
    with pytest.raises(GuardError):
        asyncio.run(qx.run({'model': 'QaMessage', 'mode': 'query', 'condition': {},
                            'fields': ['role'], 'limit': 5}))


# ---------- query_cache 全链路 mock ----------

from app.services import query_cache as qc


def test_cache_exact_hit_miss(monkeypatch):
    import asyncio
    from app.db.mongo_store import store as st
    async def fake_q1(gql, params=None):
        return None
    monkeypatch.setattr(st, 'query_one', fake_q1)
    assert asyncio.run(qc.exact_hit('问法')) is None


def test_cache_exact_hit_hit(monkeypatch):
    import asyncio
    from app.db.mongo_store import store as st
    calls = []
    async def fake_q1(gql, params=None):
        return {'_id': 'e1', 'template': {'model': 'X'}}
    async def fake_upd(*a, **k):
        calls.append(k or a)
        return None
    async def fake_rai(fn):
        await fn()
    monkeypatch.setattr(st, 'query_one', fake_q1)
    monkeypatch.setattr(st, 'update', fake_upd)
    monkeypatch.setattr(st, 'run_as_internal', fake_rai)
    ex = asyncio.run(qc.exact_hit('同款问法'))
    assert ex['template']['model'] == 'X'
    assert calls  # 命中后 hit 计数已执行


def test_cache_exact_hit_empty_template_no_default(monkeypatch):
    import asyncio
    from app.db.mongo_store import store as st
    async def fake_q1(gql, params=None):
        return {'_id': 'e1', 'template': None}
    async def fake_upd(*a, **k):
        raise AssertionError('不应 hit 计数')
    monkeypatch.setattr(st, 'query_one', fake_q1)
    monkeypatch.setattr(st, 'update', fake_upd)
    assert asyncio.run(qc.exact_hit('问法')) is None  # 查到了但无 template → 视为未命中


def test_cache_exact_hit_empty_question(monkeypatch):
    import asyncio
    from app.db.mongo_store import store as st
    called = []
    async def fake_q1(gql, params=None):
        called.append(True)
        return None
    monkeypatch.setattr(st, 'query_one', fake_q1)
    assert asyncio.run(qc.exact_hit('')) is None   # 空问法 → 不触库
    assert asyncio.run(qc.exact_hit('   ')) is None  # 仅空白 → 归一化后空
    assert called == []


def test_cache_top_k_fuzzy(monkeypatch):
    import asyncio
    from app.db.mongo_store import store as st
    async def fake_q(gql, params=None):
        return [{'question': 'a', 'qnorm': '问题', 'template': {'m': 1}},
                {'question': 'b', 'qnorm': '完全不同', 'template': {'m': 2}}]
    monkeypatch.setattr(st, 'query', fake_q)
    out = asyncio.run(qc.top_k_fuzzy('问题', k=5, min_score=0.0))
    assert isinstance(out, list) and len(out) <= 2  # 仅作 few-shot，按分数截断
    assert asyncio.run(qc.top_k_fuzzy('')) == []  # 空 key → 空


def test_cache_top_k_fuzzy_filter_and_k(monkeypatch):
    import asyncio
    from app.db.mongo_store import store as st
    from app.services import query_cache as _qc
    async def fake_q(gql, params=None):
        # 4 条：精确同词(高分) / 中度相关 / 两条无关低频
        return [
            {'question': 'q0', 'qnorm': '收入排行榜', 'template': {'m': 0}},
            {'question': 'q1', 'qnorm': '收入排行', 'template': {'m': 1}},
            {'question': 'q2', 'qnorm': '合同履约进度', 'template': {'m': 2}},
            {'question': 'q3', 'qnorm': '后勤报销车辆', 'template': {'m': 3}},
        ]
    monkeypatch.setattr(st, 'query', fake_q)
    # k=1 → 只返回最高分一条
    out1 = asyncio.run(_qc.top_k_fuzzy('收入排行榜', k=1, min_score=0.0))
    assert len(out1) == 1 and out1[0]['question'] == 'q0'
    # 高阈值 → 仅精确近义两词保留
    out2 = asyncio.run(_qc.top_k_fuzzy('收入排行榜', k=9, min_score=0.5))
    assert [o['question'] for o in out2] == ['q0', 'q1']
    # 分数单调递减
    scores = [o['score'] for o in out2]
    assert all(scores[i] >= scores[i + 1] for i in range(len(scores) - 1))


def test_cache_upsert_new(monkeypatch):
    import asyncio
    from app.db.mongo_store import store as st
    inserted = []
    async def fake_q1(gql, params=None):
        return None
    async def fake_ins(schema, data):
        inserted.append((schema, data))
        return None
    async def fake_rai(fn):
        await fn()
    monkeypatch.setattr(st, 'query_one', fake_q1)
    monkeypatch.setattr(st, 'insert', fake_ins)
    monkeypatch.setattr(st, 'run_as_internal', fake_rai)
    asyncio.run(qc.upsert('新问法', {'model': 'X'}, True))
    assert inserted[0][0] == 'QueryExample'
    assert inserted[0][1]['favor'] == 1 and inserted[0][1]['qnorm'] == qc.qnorm('新问法')


def test_cache_upsert_existing_update(monkeypatch):
    import asyncio
    from app.db.mongo_store import store as st
    updates = []
    async def fake_q1(gql, params=None):
        return {'_id': 'e1', 'favor': 2, 'hit': 3}
    async def fake_upd(schema, cond, data):
        updates.append((cond, data))
        return None
    async def fake_rai(fn):
        await fn()
    monkeypatch.setattr(st, 'query_one', fake_q1)
    monkeypatch.setattr(st, 'update', fake_upd)
    monkeypatch.setattr(st, 'run_as_internal', fake_rai)
    asyncio.run(qc.upsert('已知问法', {'model': 'Y'}, True))
    assert updates[0][0] == {'_id': 'e1'}
    assert updates[0][1]['$set']['template'] == {'model': 'Y'}  # 升级模板


def test_cache_upsert_fail_downgrade(monkeypatch):
    import asyncio
    from app.db.mongo_store import store as st
    updates = []
    async def fake_q1(gql, params=None):
        return {'_id': 'e1', 'favor': 5}
    async def fake_upd(schema, cond, data):
        updates.append((cond, data))
        return None
    async def fake_rai(fn):
        await fn()
    monkeypatch.setattr(st, 'query_one', fake_q1)
    monkeypatch.setattr(st, 'update', fake_upd)
    monkeypatch.setattr(st, 'run_as_internal', fake_rai)
    asyncio.run(qc.upsert('差评问法', {}, False))
    assert updates[0][1]['favor'] == 3  # 差评降权 favor-2


def test_cache_upsert_empty_key(monkeypatch):
    import asyncio
    asyncio.run(qc.upsert('', {}, True))  # 空 key 直接返回，不触库


def test_cache_upsert_success_without_template_noop(monkeypatch):
    import asyncio
    from app.db.mongo_store import store as st
    touched = []
    async def fake_q1(gql, params=None):
        touched.append('query')
        return None
    async def fake_ins(*a, **k):
        touched.append('insert')
        return None
    async def fake_rai(fn):
        await fn()
    monkeypatch.setattr(st, 'query_one', fake_q1)
    monkeypatch.setattr(st, 'insert', fake_ins)
    monkeypatch.setattr(st, 'run_as_internal', fake_rai)
    # success=True 但无 template → 立即返回，不查询库也不插入
    asyncio.run(qc.upsert('问法', None, True))
    assert touched == []


# ---------- query_candidate 全链路 ----------

from app.services import query_candidate as qcand


def test_pick_checked_guard_error_vs_empty():
    cands = [
        ({'model': 'Evil', 'condition': {'$where': '1'}}, {'idx': 0, 'ok': True}),
        (None, {'idx': 1, 'ok': False, 'error': 'boom'}),
    ]
    checked, statuses = qcand.pick_checked(cands)
    assert checked == [] and statuses[0]['status'] == 'guard_error'  # verify 抛守卫错误
    assert statuses[1]['status'] == 'empty'  # 生成失败


def test_pick_checked_meta_missing_idx():
    # meta 缺 ok/不存在 → empty；缺 idx → status 无 idx 键但不崩溃
    checked, statuses = qcand.pick_checked([(None, {})])
    assert checked == [] and statuses[0]['status'] == 'empty'
    assert statuses[0]['idx'] is None  # meta 缺 idx → 默认 None


def test_pick_checked_cand_none_ok_true():
    # cand=None 即使 ok=True 也判 empty（数据缺失兜底）
    checked, statuses = qcand.pick_checked([(None, {'idx': 0, 'ok': True})])
    assert checked == [] and statuses[0]['status'] == 'empty'


def test_generate_candidates_with_prime(monkeypatch):
    import asyncio
    async def fake_invoke(scenario, vars_, conf):
        return ({'model': 'CommercialLedger'}, {'total_tokens': 5, 'elapsed_s': 0.1,
                'cache_hit_tokens': 0, 'cache_miss_tokens': 0})
    async def fake_chat(msgs, **k):
        return {'elapsed_s': 0.1, 'cache_hit_tokens': 0, 'cache_miss_tokens': 0}
    monkeypatch.setattr(llm_client, 'invoke', fake_invoke)
    monkeypatch.setattr(llm_client, 'chat', fake_chat)
    conf = {'platform': 'deepseek', 'baseUrl': '', 'apiKey': 'k', 'modelName': 'm'}
    cands, prime = asyncio.run(qcand.generate_candidates('问题', [], conf, n=2, concurrency=2,
                                                         preheat=True))
    assert len(cands) == 2 and all(m['ok'] for _, m in cands)
    assert prime and prime['ok'] is True  # 预热随批次并发


def test_generate_candidates_single_failure_isolated(monkeypatch):
    import asyncio
    from app.services import query_candidate as _m

    async def fake_invoke(scenario, vars_, conf):
        idx = vars_.get('question')
        if idx == 'bad':
            raise RuntimeError('boom')
        return ({'model': 'CommercialLedger'}, {'total_tokens': 5, 'elapsed_s': 0.1,
                'cache_hit_tokens': 0, 'cache_miss_tokens': 0})
    monkeypatch.setattr(llm_client, 'invoke', fake_invoke)
    conf = {'platform': 'deepseek', 'baseUrl': '', 'apiKey': 'k', 'modelName': 'm'}
    # 注意 vars 传入的 question 对所有候选是同一个；用 n 大 + 特定问题区分不了。
    # 直接测：invoke 抛错 → 对应候选 meta ok=False，其他候选不受影响（等效多候选独立失败）
    cands, prime = asyncio.run(_m.generate_candidates('q', [], conf, n=1, concurrency=1))
    assert prime is None
    # 命中失败路径：invoke 抛错
    async def fake_fail(scenario, vars_, conf):
        raise RuntimeError('boom')
    monkeypatch.setattr(llm_client, 'invoke', fake_fail)
    cands2, _ = asyncio.run(_m.generate_candidates('q', [], conf, n=1, concurrency=1))
    assert cands2 and cands2[0][0] is None and cands2[0][1]['ok'] is False
    assert 'error' in cands2[0][1]


def test_generate_candidates_preheat_failure_isolated(monkeypatch):
    import asyncio
    from app.services import query_candidate as _m

    async def fake_invoke(scenario, vars_, conf):
        return ({'model': 'CommercialLedger'}, {'total_tokens': 5, 'elapsed_s': 0.1,
                'cache_hit_tokens': 0, 'cache_miss_tokens': 0})
    async def fake_chat_msgs(msgs, **k):
        raise RuntimeError('prime down')
    monkeypatch.setattr(llm_client, 'invoke', fake_invoke)
    monkeypatch.setattr(llm_client, 'chat', fake_chat_msgs)
    conf = {'platform': 'deepseek', 'baseUrl': '', 'apiKey': 'k', 'modelName': 'm'}
    cands, prime = asyncio.run(_m.generate_candidates('q', [], conf, n=1, concurrency=1,
                                                      preheat=True))
    assert len(cands) == 1 and cands[0][1]['ok']  # 预热失败不阻断候选
    assert prime is not None and prime['ok'] is False and 'error' in prime
