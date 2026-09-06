"""条件完整度校验（B，纯函数，禁 IO）：基于 schema 判定 LLM 产出查询是否缺必要条件，
   产出结构化澄清表单（缺哪些维度字段 + 中文标签 + 控件类型 + 枚举选项）。"""
from app.agent.schema_registry import DIM_ENUMS, FIELD_COMMENTS

# 统计/目标类模型必须显式指定年份口径，否则结果口径不明
_REQUIRED_YEAR_MODELS = {
    'ReportOverall', 'ReportProduct', 'ReportSolution',
    'ReportIndustry', 'ReportKeyUnit', 'GoalLedger',
}

# 通用中文标签：A门无 model 时兜底（客户不在 DIM_ENUMS，仅台账模型手填）
DIM_LABELS = {
    'year': '年份', 'unit': '经营单元', 'industry': '行业',
    'productLine': '产品线', 'stage': '阶段', 'riskLevel': '风险等级',
    'customer': '客户',
}

# 选项数超过该值 → 用下拉多选(select)，否则平铺复选(checkbox)，避免卡片过长
MULTI_SELECT_THRESHOLD = 12


def _model_keys(model: str | None) -> set[str]:
    """该模型真实存在的字段键（来自 FIELD_COMMENTS 静态中文注释表，键名为驼峰业务名）。"""
    return set((FIELD_COMMENTS.get(model) or {}).keys()) if model else set()


def missing_dims(query: dict) -> list[str]:
    """判缺失字段集（收紧版）：仅当统计/目标类模型未显式指定年份（口径不明）时拦截追问；
    其余一律放行执行（先查再说——空结果/全量汇总由结论层与追问建议承接）。"""
    model = query.get('model')
    cond = query.get('condition') or {}
    topic_keys = {k for k in cond if not k.startswith('$')}
    if model in _REQUIRED_YEAR_MODELS and 'year' not in topic_keys:
        return ['year']
    return []


def _field_type(key: str, options: list | None) -> str:
    """控件类型映射：year→radio 单选；customer→input 自由输入；其余按选项数分 checkbox/select。"""
    if key == 'year':
        return 'radio'
    if key == 'customer':
        return 'input'
    if options and len(options) > MULTI_SELECT_THRESHOLD:
        return 'select'
    return 'checkbox'


def build_clarify_fields(available_dims: list[str], model: str | None = None) -> list[dict]:
    """由维度键集合生成字段+标签+选项+控件类型（纯函数，禁 IO）。
    model 给定时：只保留该模型真实存在的字段（FIELD_COMMENTS 静态键），label 优先其中文注释。"""
    model_fields = _model_keys(model)
    fields = []
    for key in available_dims:
        if key not in DIM_ENUMS and key != 'customer':
            continue
        if model_fields and key not in model_fields:
            continue
        opts = list(DIM_ENUMS[key]) if key in DIM_ENUMS else None
        label = (model and FIELD_COMMENTS.get(model, {}).get(key)) or DIM_LABELS.get(key) or key
        fields.append({
            'key': key,
            'label': label,
            'type': _field_type(key, opts),
            'required': key == 'year',
            'options': opts,
            'placeholder': '请输入客户名称' if key == 'customer' else None,
        })
    return fields


def completeness_issues(query: dict) -> dict | None:
    """返回 {'text','fields'} 澄清表单；条件充足返回 None。query 须为已过守卫的 checked 模板。"""
    dims = missing_dims(query)
    if not dims:
        return None
    text = '请补充查询年份（可选 2025、2026）'
    return {'text': text, 'fields': build_clarify_fields(dims, query.get('model'))}


def build_query_hint(dims: list[str]) -> str:
    """意图门软提示：把判定的缺失维度转成 query_gen 的 hint（纯函数，禁 IO）。
    策略先行不追问：year→缺省 2026，其余维度→全量汇总，直接生成最合理查询。"""
    labels = '、'.join(DIM_LABELS.get(d, d) for d in dims) or '部分条件'
    return (f'意图门提示：问题可能未明确{labels}，无需追问用户——'
            '年份缺省取 2026，未指明维度按全量汇总（不加过滤）处理，直接生成最合理的查询。')