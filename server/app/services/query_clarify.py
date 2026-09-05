"""条件完整度校验（B，纯函数，禁 IO）：基于 schema 判定 LLM 产出查询是否缺必要条件"""
from app.models.registry import MODEL_TABLE

# 统计/目标类模型必须显式指定年份口径，否则结果口径不明
_REQUIRED_YEAR_MODELS = {
    'ReportOverall', 'ReportProduct', 'ReportSolution',
    'ReportIndustry', 'ReportKeyUnit', 'GoalLedger',
}


def completeness_issues(query: dict) -> str | None:
    """返回需澄清的追问文案；条件充足返回 None。query 须为已过守卫的 checked 模板。"""
    model = query.get('model')
    cond = query.get('condition') or {}
    # 顶层字段条件是 topic 键（非 $ 前缀）
    topic_keys = set(k for k in cond if not k.startswith('$'))
    if model in _REQUIRED_YEAR_MODELS and 'year' not in topic_keys:
        return '请补充查询年份（可选 2025、2026），例如「2026年各经营单元达成情况」。'
    if not topic_keys:
        return '问题条件不足：请补充查询维度或范围（如年份、经营单元、行业、产品线）。'
    return None