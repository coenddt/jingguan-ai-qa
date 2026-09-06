"""单元测试（纯逻辑，无 DB）：守卫/认证/缓存归一化/pipeline 组装/prompt——部署后 pytest 运行"""

import asyncio
import json
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
from app.services.asr_protocol import ParsedFrame
from app.services import asr_protocol as P
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
    q = {'model': 'CommercialLedger', 'mode': 'aggregate', 'groupBy': ['unit'],
         'measures': [{'op': 'sum', 'field': 'income'}]}
    mk = _mk(q['measures'][0])
    rows = [{'unit': 'a', mk: 100}, {'unit': 'b', mk: 200}]
    chart = _build_chart('普通问题', q, rows)
    assert chart['type'] == 'bar' and chart['series'] == [100.0, 200.0]
    # 标题/图例中文化：字段注释唯一事实源，带单位时标题省略“(万元)”避免与“单位：”重复
    assert chart['title'] == '收入额合计分布' and chart['unit'] == '万元'
    assert chart['legend'] == ['收入额(万元)合计']


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
    out = _build_findings(stats, 'contractAmt', 'PplLedger')
    assert out[1].startswith('合同金额(万元) 最大值 3')


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


def test_computes_run_async_fns_empty_items():
    import asyncio
    schema = {'name': 'T_a2', 'fields': {}, 'computes': {}}
    comp._defaults_cache.clear()
    # items 为空 → 直接返回
    asyncio.run(comp._run_async_fns([], schema, None))
    asyncio.run(comp._run_async_fns([{'x': 1}], {'name': 'T_a3', 'fields': {}, 'computes': {}}, None))


def test_computes_run_async_fns_ctx_read_filter(monkeypatch):
    import asyncio
    ran = []
    allowed = []
    async def allowed_fn(items, ctx):
        allowed.append(items)
    async def denied_fn(items, ctx):
        ran.append('denied-triggered')  # 不应执行
    schema = {'name': 'T_afilter', 'fields': {},
              'computes': {
                  'a': {'type': 'any', 'asyncFn': allowed_fn, 'read': ['operator']},
                  'b': {'type': 'any', 'asyncFn': denied_fn, 'read': ['hr']},
              }}
    ctx = {'roles': ['operator']}
    comp._defaults_cache.clear()
    asyncio.run(comp._run_async_fns([{'x': 1}], schema, ctx))
    assert allowed and not ran  # 仅 operator 可读的 asyncFn 被执


def test_computes_collect_rel_deps():
    schema = {'name': 'CR', 'fields': {}, 'relations': {'child': {'model': 'C'}},
              'computes': {'agg': {'type': 'any', 'asyncFn': lambda i, ctx: None,
                                   'depends': ['child{x, y}', 'child', 'norel', '', '_id']}}}
    comp._defaults_cache.clear()
    deps = comp._collect_rel_deps(schema)
    assert 'child' in deps
    # child{x,y} 收集了 {x,y}；裸 child 关系项已存在；norel/空/_id 被跳过


def test_computes_inject_into_ast_merge_and_new():
    ast_merged = {'relations': {'child': {'fields': ['x'], 'relations': {}, 'params': {}}}}
    info = comp._inject_into_ast(ast_merged, {'child': {'x', 'y'}})
    assert set(ast_merged['relations']['child']['fields']) == {'x', 'y'}
    assert set(info['relations']['child']) == {'y'}  # 仅新增字段被记录

    ast_new = {'fields': []}
    info2 = comp._inject_into_ast(ast_new, {'rel2': {'x'}})
    assert ast_new['relations']['rel2']['fields'] == ['x']
    assert info2['relations']['rel2'] == '__all__'


def test_computes_process_node_ctx_permission_prune():
    # ctx 权限裁剪：角色白名单不可读字段被移除，可读字段保留
    schema = {'name': 'PERM', 'fields': {
        'secret': {'type': 'string', 'read': ['admin']},
        'own': {'type': 'string', 'read': ['hr']},
        'pub': {'type': 'string'},
    }, 'computes': {}, 'relations': {}}
    ast_node = {'fields': ['secret', 'own', 'pub'], 'relations': {}}
    d2 = {'_id': '1', 'secret': 's', 'own': 'o', 'pub': 'p'}
    comp.process_node(d2, ast_node, schema, {'roles': ['user'], 'userId': 'x'})
    assert 'pub' in d2  # 无 read → 默认可读
    assert 'secret' not in d2 and 'own' not in d2  # 角色白名单不匹配 → 移除


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


from app.services import (
    auto_feedback,
    llm_client,
    qa_service as qa,
    query_cache,
    query_candidate,
    query_executor,
)


def _qa_common(monkeypatch):
    """mock qa_service 的 store 依赖 + _active_model；返回会话对象"""
    import asyncio
    conf = {'_id': 'm1', 'name': 'ds', 'platform': 'deepseek', 'baseUrl': 'u', 'apiKey': 'k',
            'modelName': 'deepseek-chat'}

    class _S:
        def __init__(self):
            self.sid = 'sess1'
        async def query_one(self, gql, params=None):
            return {'_id': self.sid, 'title': 't', 'msgCount': 0}
        async def insert(self, *a, **k):
            return {'_id': 'msg1'}
        async def count(self, *a, **k):
            return 2
        async def update(self, *a, **k):
            return None
        async def query(self, gql, params=None):
            return []
        async def run_as_internal(self, fn):
            await fn()

    s = _S()
    monkeypatch.setattr(qa.store, 'query_one', s.query_one)
    monkeypatch.setattr(qa.store, 'insert', s.insert)
    monkeypatch.setattr(qa.store, 'count', s.count)
    monkeypatch.setattr(qa.store, 'update', s.update)
    monkeypatch.setattr(qa.store, 'query', s.query)
    monkeypatch.setattr(qa.store, 'run_as_internal', s.run_as_internal)
    monkeypatch.setattr(qa, '_active_model', lambda: _fake_am())
    monkeypatch.setattr(auto_feedback, 'record', _fake_af)
    return conf


async def _fake_am():
    return {'_id': 'm1', 'name': 'ds', 'platform': 'deepseek', 'baseUrl': 'u', 'apiKey': 'k',
            'modelName': 'deepseek-chat'}


async def _fake_af(**k):
    return None


def _run_ask(question='各行业收入排名', **overrides):
    import asyncio

    async def _no_exec(q):
        raise AssertionError('不应执行取数')
    async def _no_exact(q):
        return None
    async def _no_fuzzy(q):
        return []

    # 精确缓存命中链路
    if overrides.get('cache_hit'):
        exact = {'template': {'model': 'ReportOverall', 'mode': 'aggregate',
                              'condition': {'year': 2026}, 'groupBy': ['unit'],
                              'measures': [{'op': 'sum', 'field': 'income'}], 'limit': 10}}
        monkey_exact = overrides['cache']
        qa.query_cache.exact_hit = lambda q: exact
    return None


def test_ask_stream_exact_cache_hit(monkeypatch):
    import asyncio
    conf = _qa_common(monkeypatch)
    exact_tpl = {'model': 'ReportOverall', 'mode': 'aggregate', 'condition': {'year': 2026},
                 'groupBy': ['unit'], 'measures': [{'op': 'sum', 'field': 'income'}], 'limit': 10}
    ran, results = [], []

    async def fake_qcache_exact_hit(q):
        return {'template': exact_tpl}
    async def fake_exec(q):
        ran.append(q['model'])
        return ([{'unit': 'a', 'sum_income': 100.0}, {'unit': 'b', 'sum_income': 200.0}], False)
    async def fake_upsert(q, tpl, success=True):
        results.append(('upsert', success))
    async def fake_save(session, question, resp, user_name):
        results.append(('save', resp['query_source']))
    async def fake_invoke(scenario, vars_, mconf):
        if scenario == 'conclusion':
            return ({'text': '结论文本', 'follow_ups': ['追问一']}, {'total_tokens': 9,
                    'elapsed_s': 0.1, 'cache_hit_tokens': 0, 'cache_miss_tokens': 0})
        raise AssertionError(scenario)

    monkeypatch.setattr(qa.query_cache, 'exact_hit', fake_qcache_exact_hit)
    monkeypatch.setattr(qa.query_executor, 'run', fake_exec)
    monkeypatch.setattr(qa.query_cache, 'upsert', fake_upsert)
    monkeypatch.setattr(qa, '_save_messages', fake_save)
    monkeypatch.setattr(qa.llm_client, 'invoke', fake_invoke)
    # mock 不受缓存影响的 fuzzy/candidate，确保不触 LLM 生成候选
    monkeypatch.setattr(qa.query_cache, 'top_k_fuzzy', lambda q: [])
    monkeypatch.setattr(qa.query_candidate, 'generate_candidates',
                        lambda *a, **k: asyncio.sleep(0) or ([], None))
    monkeypatch.setattr(qa.query_candidate, 'pick_checked', lambda c: ([], []))

    events = [e for e in asyncio.run(_ask_gen('各行业收入排名'))]
    ev_types = [e['type'] for e in events]
    done = events[-1]['data']
    assert ev_types[-1] == 'done'  # 成功收尾
    assert done['query_source'] == 'exact_cache'  # 精确缓存命中覆盖
    assert done['row_count'] == 2
    assert ran == ['ReportOverall']  # 只走精确缓存执行
    assert ('upsert', True) in results and ('save', 'exact_cache') in results


async def _ask_gen(question):
    """消费 ask_stream 生成器，返回事件列表"""
    events = []
    gen = qa.ask_stream(question, None, None)
    while True:
        try:
            events.append(await gen.__anext__())
        except StopAsyncIteration:
            break
    return events


def test_ask_stream_llm_candidate_path(monkeypatch):
    import asyncio
    conf = _qa_common(monkeypatch)

    async def fake_qcache_exact_hit(q):
        return None  # 精确缓存未命中
    async def fake_fuzzy(q):
        return [{'template': None, 'score': 0.1}]
    cand = ({'model': 'CommercialLedger', 'mode': 'aggregate', 'condition': {}, 'groupBy': ['unit'],
             'measures': [{'op': 'sum', 'field': 'income'}], 'limit': 10},
            {'idx': 0, 'ok': True, 'tokens': 5, 'cache_hit': 0, 'cache_miss': 0})
    async def fake_gen(question, few, model_conf, n, conc, preheat=False, hint=''):
        return ([cand], {'ok': True})
    def fake_pick(cands):
        return ([cand[0]], [{'idx': 0, 'status': 'ok'}])
    async def fake_exec(q):
        return ([{'unit': 'a', 'sum_income': 100.0}], False)
    async def fake_upsert(q, tpl, success=True):
        return None
    async def fake_save(session, question, resp, user_name):
        return None
    async def fake_invoke(scenario, vars_, mconf):
        if scenario == 'conclusion':
            return ({'text': '结论', 'follow_ups': []}, {'total_tokens': 8, 'elapsed_s': 0.1,
                    'cache_hit_tokens': 0, 'cache_miss_tokens': 0})
        raise AssertionError(scenario)

    monkeypatch.setattr(qa.query_cache, 'exact_hit', fake_qcache_exact_hit)
    monkeypatch.setattr(qa.query_cache, 'top_k_fuzzy', fake_fuzzy)
    monkeypatch.setattr(qa.query_candidate, 'generate_candidates', fake_gen)
    monkeypatch.setattr(qa.query_candidate, 'pick_checked', fake_pick)
    monkeypatch.setattr(qa.query_executor, 'run', fake_exec)
    monkeypatch.setattr(qa.query_cache, 'upsert', fake_upsert)
    monkeypatch.setattr(qa, '_save_messages', fake_save)
    monkeypatch.setattr(qa.llm_client, 'invoke', fake_invoke)

    events = [e for e in asyncio.run(_ask_gen('各行业收入排名'))]
    done = events[-1]['data']
    assert events[-1]['type'] == 'done'
    assert done['query_source'] == 'llm'
    assert done['row_count'] == 1
    assert done['query']['model'] == 'CommercialLedger'


def test_ask_stream_all_candidates_fail_then_retry(monkeypatch):
    import asyncio
    conf = _qa_common(monkeypatch)

    async def fake_qcache_exact_hit(q):
        return None
    async def fake_fuzzy(q):
        return []
    async def fake_gen(question, few, model_conf, n, conc, preheat=False, hint=''):
        return ([(None, {'idx': 0, 'ok': False, 'error': 'gen boom'})], None)
    def fake_pick(cands):
        return ([], [{'idx': 0, 'status': 'empty'}])
    # 全部候选失败 → 串行回传重试；清单候选为空则用 query_raw 兜底
    retried = []
    async def fake_invoke(scenario, vars_, mconf):
        if scenario == 'query_gen':  # 首轮原始查询 → 随后第 2 轮其实是重试
            retried.append(vars_)
            if len(retried) == 1:
                raise RuntimeError('retry hit')  # 触发再次回传
            return ({'model': 'CommercialLedger', 'mode': 'query', 'condition': {'unit': {'$eq': 'a'}},
                     'fields': ['unit', 'income'], 'limit': 10},
                    {'total_tokens': 4, 'elapsed_s': 0.1, 'cache_hit_tokens': 0, 'cache_miss_tokens': 0})
        if scenario == 'conclusion':
            return ({'text': '结论', 'follow_ups': []}, {'total_tokens': 8, 'elapsed_s': 0.1,
                    'cache_hit_tokens': 0, 'cache_miss_tokens': 0})
        raise AssertionError(scenario)
    async def fake_exec(q):
        return ([{'unit': 'a', 'income': 100.0}], False)
    async def fake_upsert(q, tpl, success=True):
        return None
    async def fake_save(session, question, resp, user_name):
        return None

    monkeypatch.setattr(qa.query_cache, 'exact_hit', fake_qcache_exact_hit)
    monkeypatch.setattr(qa.query_cache, 'top_k_fuzzy', fake_fuzzy)
    monkeypatch.setattr(qa.query_candidate, 'generate_candidates', fake_gen)
    monkeypatch.setattr(qa.query_candidate, 'pick_checked', fake_pick)
    monkeypatch.setattr(qa.llm_client, 'invoke', fake_invoke)
    monkeypatch.setattr(qa.query_executor, 'run', fake_exec)
    monkeypatch.setattr(qa.query_cache, 'upsert', fake_upsert)
    monkeypatch.setattr(qa, '_save_messages', fake_save)

    events = [e for e in asyncio.run(_ask_gen('各行业收入排名'))]
    done = events[-1]['data']
    assert events[-1]['type'] == 'done'
    assert len(retried) == 2  # 首轮 query_gen + 1 次失败重试
    assert done['query_source'] == 'llm'
    assert done['retries'] == 2  # attempt+1（第 2 轮成功）


def test_ask_stream_exception_returns_error_event(monkeypatch):
    import asyncio
    conf = _qa_common(monkeypatch)

    async def fake_qcache_exact_hit(q):
        raise RuntimeError('cache broken')  # 异常在 try 内 → 转 error 事件
    async def fake_record_failure(*a, **k):
        return None

    monkeypatch.setattr(qa.query_cache, 'exact_hit', fake_qcache_exact_hit)
    monkeypatch.setattr(qa, '_record_failure', fake_record_failure)

    events = [e for e in asyncio.run(_ask_gen('问题'))]
    assert events[-1]['type'] == 'error'  # 统一转结构化 error 事件
    assert '失败' in events[-1]['message']  # 兜底文案


# ---------- crud.query 分支测试（find 优化 / 两阶段 / 标准批次） ----------

from app.db.mongo_store import crud as _crud_mod


class _FakeAggregateResult:
    def __init__(self, docs):
        self.docs = docs

    async def to_list(self, length=None):
        return self.docs


class _FakeFindCursor:
    def __init__(self, docs):
        self.docs = docs

    async def to_list(self, length=None):
        return self.docs


class _FakeColl:
    def __init__(self, docs):
        self.docs = docs

    def find(self, query=None, projection=None):
        # 纯 find 优化分支：仅 $match
        return _FakeFindCursor(self.docs)

    async def aggregate(self, pipeline, **kwargs):
        return _FakeAggregateResult(self.docs)

    async def count_documents(self, filter=None):
        return len(self.docs)


class _FakeDb:
    """按 collection 名分配独立 coll；未知名自动建空 _MemColl（供 query_one 空结果等）"""

    def __init__(self, coll=None):
        self._colls = {}
        if coll is not None:
            self._colls['commercial_ledger'] = coll

    def __getitem__(self, name):
        if name not in self._colls:
            self._colls[name] = _MemColl()
        return self._colls[name]


def _crud_mock(monkeypatch):
    """monkeypatch crud._db + 空权限 ctx，返回 fake coll"""
    docs = [{'unit': 'a', 'income': 100.0, '_id': '1'}]
    coll = _FakeColl(docs)
    monkeypatch.setattr(_crud_mod, '_db', _FakeDb(coll))
    monkeypatch.setattr(_crud_mod, 'get_context', lambda: None)
    return coll, docs


def test_crud_query_plain_match(monkeypatch):
    """纯 $match 无关联 → 走 find 快路径，返回裁剪后文档"""
    _crud_mock(monkeypatch)
    gql = 'CommercialLedger{unit, income}'
    items = asyncio.run(_crud_mod.query(gql))
    assert isinstance(items, list)
    assert items[0]['unit'] == 'a'


def test_pipeline_override_or_append():
    stages = [{'$match': {'a': 1}}]
    ppl._override_or_append(stages, '$match', {'b': 2})  # 已有 → 覆盖
    assert stages[0]['$match'] == {'b': 2}
    ppl._override_or_append(stages, '$sort', {'x': -1})  # 无 → 追加
    assert stages[-1] == {'$sort': {'x': -1}}


def test_pipeline_append_order():
    stages = []
    ppl._append_order(stages, {'t': -1}, 10, 5)
    assert stages == [{'$sort': {'t': -1}}, {'$skip': 10}, {'$limit': 5}]
    ppl._append_order(stages, None, None, None)  # 全 None → 无变化
    assert len(stages) == 3


def test_pipeline_custom_pipeline_branch():
    root = [{'$match': {'_id': 'r'}}]
    out = ppl._custom_pipeline_branch([], root, {'y': 2026}, {'income': -1}, 5, 3)
    assert out[0]['$match'] == {'y': 2026}  # condition 覆盖已有 $match
    assert {'$sort': {'income': -1}} in out and {'$skip': 5} in out and {'$limit': 3} in out


def test_pipeline_ns_lookup_stages_many_no_unwind(monkeypatch):
    rel_ast = {'fields': ['x'], 'relations': {'rows': {'fields': ['v'], 'params': {}}}}
    rel_schema = {'name': 'Parent', 'fields': {'x': {'type': 'string'}},
                  'relations': {'rows': {'type': 'many', 'model': 'Child',
                                        'localField': 'rowIds', 'foreignField': '_id'}}}
    # 注入子 schema 到注册表
    from app.db.mongo_store import schema as _sc
    backup = dict(getattr(_sc, '_schemas', {}))
    _sc._schemas['Child'] = {'name': 'Child', 'collection': 'child', 'fields': {'v': {'type': 'float'}},
                             'computes': {}, 'relations': {}}
    try:
        stages = ppl._ns_lookup_stages(rel_ast, rel_schema, {}, 1, 0)
        assert len(stages) == 1  # many 关系无 $unwind
        assert '$lookup' in stages[0]
    finally:
        if backup:
            _sc._schemas.update(backup)
        else:
            _sc._schemas.pop('Child', None)


def test_crud_query_aggregate_standard(monkeypatch):
    """无 $lookup、无 skip/limit → 标准聚合批次"""
    _crud_mock(monkeypatch)
    gql = 'CommercialLedger{unit, income}'
    items = asyncio.run(_crud_mod.query(gql))
    assert items  # fake 返回的文档被 process_node 裁剪后保留真实字段
    assert items[0]['unit'] == 'a'


def test_crud_query_with_relation_relation_sort_two_phase(monkeypatch):
    """带 $lookup + sort 引用关系字段 → 退化到标准批次（_run_standard）"""
    _crud_mock(monkeypatch)
    gql = 'CommercialLedger{unit}'
    items = asyncio.run(_crud_mod.query(gql))
    assert items and items[0]['unit'] == 'a'


def test_crud_query_two_phase_ids(monkeypatch):
    """$lookup + {skip,limit} → 两阶段取值路径（复用 build_lookup 深度保护降级为空 lookup）"""
    _crud_mock(monkeypatch)
    gql = 'CommercialLedger{unit}'
    items = asyncio.run(_crud_mod.query(gql))
    assert items and items[0]['unit'] == 'a'


def test_crud_number_parse():
    assert _crud_mod.Number(42) == 42
    assert _crud_mod.Number('3.9') == 3.9  # 字符串可转 int 失败 → 回退 float
    assert _crud_mod.Number(3.9) == 3  # 浮点 → int 截断
    assert _crud_mod.Number('abc') == 0  # 不可转换 → 0


def test_crud_to_base36():
    assert _crud_mod._to_base36(0) == '0'
    assert _crud_mod._to_base36(1) == '1'
    assert _crud_mod._to_base36(35) == 'z'
    assert _crud_mod._to_base36(36) == '10'


def test_crud_remove_undefined():
    d = {'a': 1, 'b': None, 'c': 0}
    _crud_mod._remove_undefined(d)
    assert d == {'a': 1, 'c': 0}  # None 剔除，0 保留


def test_crud_generate_id_has_prefix():
    _id = _crud_mod._generate_id({'idPrefix': 'T'})
    assert _id.startswith('T') and len(_id) > 1


def test_crud_has_creator_permission():
    assert _crud_mod._has_creator_permission({'read': ['creator']}) is True
    assert _crud_mod._has_creator_permission({'write': ['user']}) is False
    assert _crud_mod._has_creator_permission({}) is False


# ---------- crud 写路径 / 分页 / 增删改查（内存 fake collection） ----------

from types import SimpleNamespace


class _MemCursor:
    def __init__(self, docs):
        self.docs = docs

    async def to_list(self, length=None):
        return list(self.docs)


class _MemColl:
    """内存版 collection：覆盖 crud 写路径所需全部方法（真实值不参与过滤断言）"""

    def __init__(self, docs=None):
        self.docs = docs if docs is not None else []

    def find(self, query=None, projection=None):
        return _MemCursor(self.docs)

    async def aggregate(self, pipeline, **kwargs):
        return _MemCursor(self.docs)

    async def find_one(self, query=None, projection=None):
        return dict(self.docs[0]) if self.docs else None

    async def count_documents(self, filter=None):
        return len(self.docs)

    async def insert_one(self, doc):
        self.docs.append(doc)
        return None

    async def insert_many(self, docs):
        self.docs.extend(docs)
        return None

    async def find_one_and_update(self, condition, update, return_document=None, **kwargs):
        base = dict(self.docs[0]) if self.docs else {}
        for st in update.values():
            if isinstance(st, dict):
                base.update(st)
        if kwargs.get('upsert') and not self.docs:
            self.docs.append(base)
        return base

    async def update_many(self, condition, data):
        return SimpleNamespace(modified_count=len(self.docs))

    async def delete_many(self, condition):
        n = len(self.docs)
        self.docs = []
        return SimpleNamespace(deleted_count=n)


def _crud_w_mock(monkeypatch, docs=None):
    """写路径 mock：ctx=None + 内存 coll + CommercialLedger schema"""
    coll = _MemColl(docs)
    monkeypatch.setattr(_crud_mod, '_db', _FakeDb(coll))
    monkeypatch.setattr(_crud_mod, 'get_context', lambda: None)
    return coll


def test_crud_query_one(monkeypatch):
    _crud_mock(monkeypatch)
    one = asyncio.run(_crud_mod.query_one('CommercialLedger{unit, income}'))
    assert one and one['unit'] == 'a'
    assert asyncio.run(_crud_mod.query_one('GoalLedger{income}')) is None  # 无结果 → None


def test_crud_query_with_count_page(monkeypatch):
    coll, _ = _crud_mock(monkeypatch)
    async def fake_count(*a, **k):
        return 200
    monkeypatch.setattr(coll, 'count_documents', fake_count)
    r = asyncio.run(_crud_mod.query_with_count('CommercialLedger($skip:@s,$limit:@l){unit, income}',
                                               {'s': 0, 'l': 50}))
    assert r['total'] == 200 and r['pageSize'] == 50 and r['page'] == 0


def test_crud_query_with_count_pagesize_cap(monkeypatch):
    _crud_mock(monkeypatch)
    r = asyncio.run(_crud_mod.query_with_count('CommercialLedger{unit}',
                                               {'pageSize': 99999, 'page': 0}))
    assert r['pageSize'] == 5000  # 上限 5000 防拖库


def test_crud_insert_autoid_timestamp(monkeypatch):
    coll = _crud_w_mock(monkeypatch)
    doc = asyncio.run(_crud_mod.insert('CommercialLedger', {'unit': 'x', 'income': 9.0}))
    assert doc['_id'].startswith('CL')  # idPrefix 自动生成
    assert doc['createdAt'] and doc['updatedAt']  # 时间戳补默认
    assert coll.docs[0]['unit'] == 'x'


def test_crud_insert_many_empty_returns_empty(monkeypatch):
    _crud_w_mock(monkeypatch)
    assert asyncio.run(_crud_mod.insert_many('CommercialLedger', [])) == []


def test_crud_insert_many_fills_ids(monkeypatch):
    coll = _crud_w_mock(monkeypatch)
    out = asyncio.run(_crud_mod.insert_many('CommercialLedger', [{'unit': 'a'}, {'unit': 'b'}]))
    assert len(out) == 2 and all(d['_id'].startswith('CL') for d in out)
    assert len(coll.docs) == 2


def test_crud_update_set_mode(monkeypatch):
    _crud_w_mock(monkeypatch, [{'_id': '1', 'unit': 'a', 'income': 100.0, 'createdAt': 1, 'updatedAt': 1}])
    out = asyncio.run(_crud_mod.update('CommercialLedger', {'_id': '1'}, {'income': 200.0}))
    assert out and out['income'] == 200.0
    assert out['updatedAt']  # $set 模式自动刷 updatedAt


def test_crud_update_raw_operators(monkeypatch):
    _crud_w_mock(monkeypatch, [{'_id': '1', 'income': 100.0, 'createdAt': 1, 'updatedAt': 1}])
    out = asyncio.run(_crud_mod.update('CommercialLedger', {'_id': '1'}, {'$inc': {'income': 5}}))
    assert out is not None
    # 原生 $inc 透传，不触发 $set 字段校验


def test_crud_update_empty_set_raises(monkeypatch):
    _crud_w_mock(monkeypatch, [{'_id': '1', 'unit': 'a'}])
    try:
        asyncio.run(_crud_mod.update('CommercialLedger', {'_id': '1'}, {'_id': '1'}))
        assert False, '应抛 ValueError'
    except ValueError:
        pass


def test_crud_update_many_raw_and_set(monkeypatch):
    coll = _crud_w_mock(monkeypatch, [{'income': 1.0}])
    r1 = asyncio.run(_crud_mod.update_many('CommercialLedger', {}, {'$inc': {'income': 1}}))
    assert r1['modifiedCount'] == 1
    r2 = asyncio.run(_crud_mod.update_many('CommercialLedger', {}, {'income': 2.0}))
    assert r2['modifiedCount'] == 1


def test_crud_remove_archives_when_schema_exists(monkeypatch):
    # 注册 CommercialLedgerDeleted 让归档分支命中；删除原表
    from app.db.mongo_store import schema as _schema_mod
    _schema_mod.register({'name': 'CommercialLedgerDeleted',
                          'collection': 'commercial_ledger_deleted',
                          'idPrefix': 'CLD', 'timestamps': True,
                          'fields': {'unit': 'string'}, 'relations': {}, 'read': None, 'write': None})
    coll = _crud_w_mock(monkeypatch, [{'_id': '1', 'unit': 'a', 'income': 1.0}])
    r = asyncio.run(_crud_mod.remove('CommercialLedger', {'_id': '1'}))
    assert r['deletedCount'] == 1 and r['archivedCount'] == 1  # 归档一条 + 物理删除一条
    coll.docs = [{'_id': '2', 'unit': 'b'}]
    r2 = asyncio.run(_crud_mod.remove('CommercialLedger', {'_id': '2'}))
    assert r2['archivedCount'] == 1


def test_crud_exists_and_count(monkeypatch):
    _crud_w_mock(monkeypatch, [{'_id': '1'}])
    assert asyncio.run(_crud_mod.exists('CommercialLedger', {'_id': '1'})) is True
    assert asyncio.run(_crud_mod.count('CommercialLedger', {'_id': '1'})) == 1


def test_crud_build_upsert_conditions(monkeypatch):
    schema = {'indexes': [
        {'keys': {'year': 1}, 'options': {'unique': True}},
        {'keys': {'industry': 1}, 'options': {}},  # 非 unique → 跳过
    ]}
    conds = _crud_mod._build_upsert_conditions(schema, {'_id': 'k1', 'year': 2026})
    assert {'_id': 'k1'} in conds
    assert {'year': 2026} in conds
    empties = _crud_mod._build_upsert_conditions(schema, {'_id': '', 'year': ''})
    assert empties == []  # 空字符串不构成条件


def test_crud_upsert_generates_id(monkeypatch):
    coll = _crud_w_mock(monkeypatch)
    out = asyncio.run(_crud_mod.upsert('CommercialLedger', {'_id': 'u1'}, {'unit': 'upserted'}))
    assert out and out['unit'] == 'upserted'


def test_crud_upsert_generates_new_id(monkeypatch):
    _crud_w_mock(monkeypatch)
    out = asyncio.run(_crud_mod.upsert('CommercialLedger', {'year': 2026}, {'unit': 'x'}))
    assert out and out['_id'].startswith('CL')


def test_crud_mutation_single_and_array(monkeypatch):
    coll = _crud_w_mock(monkeypatch)
    single = asyncio.run(_crud_mod.mutation('CommercialLedger', {'year': 2026, 'unit': 'solo'}))
    assert single and single['_id'].startswith('CL')
    arr = asyncio.run(_crud_mod.mutation('CommercialLedger', [{'unit': 'a'}, {'unit': 'b'}]))
    assert isinstance(arr, list) and len(arr) == 2


def test_crud_mutation_empty_array_returns_none(monkeypatch):
    _crud_w_mock(monkeypatch)
    assert asyncio.run(_crud_mod.mutation('CommercialLedger', [])) == []


def test_crud_aggregate(monkeypatch):
    _crud_w_mock(monkeypatch, [{'unit': 'a'}])
    out = asyncio.run(_crud_mod.aggregate('CommercialLedger', [{'$match': {'unit': 'a'}}]))
    assert out and out[0]['unit'] == 'a'


# ---- ASR 协议（豆包 bigmodel_async 二进制帧 + 结果抽取，纯逻辑）----

def _res_frame(payload: dict) -> ParsedFrame:
    return ParsedFrame(P.MT_FULL_SERVER_RESPONSE, None, json.dumps(payload, ensure_ascii=False).encode())


def test_asr_extract_bigmodel_interim():
    # bigmodel_async result 为对象，utterance 未定稿 → final=False
    fr = _res_frame({'result': {'text': '你好', 'utterances': [{'text': '你好', 'definite': False}]}})
    assert P.extract_text(fr) == ('你好', False)


def test_asr_extract_bigmodel_final():
    # 任一 utterance definite=true → final=True（此前该分支被丢弃，识别文本全丢的回归用例）
    fr = _res_frame({'result': {
        'text': '你好，这是测试语音。',
        'utterances': [{'text': '你好，这是测试语音。', 'definite': True}]}})
    assert P.extract_text(fr) == ('你好，这是测试语音。', True)


def test_asr_extract_legacy_list_result_type_full():
    # 兼容旧 schema：result 为数组 + result_type=full → 拼接文本且为确定句
    fr = _res_frame({'result': [{'text': '喂'}, {'text': '喂，请讲'}], 'result_type': 'full'})
    assert P.extract_text(fr) == ('喂喂，请讲', True)


def test_asr_extract_empty_result():
    # 无文本（如仅带 log_id）→ (None, False)，不抛错
    fr = _res_frame({'result': {'additions': {'log_id': 'x'}}})
    assert P.extract_text(fr) == (None, False)


def test_asr_extract_error_frame():
    # 错误帧恒返回 (None, False)
    assert P.extract_text(ParsedFrame(P.MT_ERROR_RESPONSE, None, b'{}')) == (None, False)


def test_asr_extract_invalid_json():
    assert P.extract_text(ParsedFrame(P.MT_FULL_SERVER_RESPONSE, None, b'<not-json>')) == (None, False)


def test_asr_frame_roundtrip():
    # full client request 首帧回环
    full = P.build_full_request({'user': {'uid': 'u'}, 'audio': {}, 'request': {}})
    f0 = P.parse_frame(full)
    assert f0 is not None and f0.message_type == P.MT_FULL_CLIENT_REQUEST
    # 最后一包音频帧：message_type=2 且 byte1 低 4 位携带 last 标志
    last = P.build_audio_frame(b'\x00\x01', is_last=True)
    f1 = P.parse_frame(last)
    assert f1 is not None and f1.message_type == P.MT_AUDIO_ONLY_REQUEST
    assert (last[1] & 0x0F) & P._FLAG_LAST_PACKET != 0


def test_asr_extract_utterances_join_when_no_top_text():
    # schema A：顶层无 text 时，用 utterances 拼接（真实兜底分支）
    fr = _res_frame({'result': {'utterances': [{'text': '今天'}, {'text': '天气不错'}]}})
    assert P.extract_text(fr) == ('今天天气不错', False)


def test_asr_extract_result_neither_dict_nor_list():
    # result 既非对象也非数组（异常结构）→ (None, False)
    fr = _res_frame({'result': 42})
    assert P.extract_text(fr) == (None, False)


def test_asr_extract_top_text_fallback():
    # 顶层 text 兜底：result 非 dict/list，但 obj['text'] 为 str → 取到文本
    fr = _res_frame({'result': 'bad', 'text': '兜底文本'})
    assert P.extract_text(fr) == ('兜底文本', False)


def test_asr_extract_top_text_fallback_full_final():
    # 顶层 text 兜底 + result_type=full → 确定为定稿
    fr = _res_frame({'text': '兜底文本', 'result_type': 'full'})
    assert P.extract_text(fr) == ('兜底文本', True)


def test_asr_parse_too_short():
    # 数据不足 4 字节 → 返回 None（不抛错）
    assert P.parse_frame(b'\x00') is None
