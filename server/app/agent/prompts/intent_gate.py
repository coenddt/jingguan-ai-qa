"""场景③ 生成前意图门：判断问题条件是否充分（A 兜底；纯函数）"""

PARAMS = {'temperature': 0.1, 'json': True, 'retries': 0}

SYSTEM_TMPL = """你是问数意图校验器。判断用户问题是否给出了足够明确的查询条件
（切片维度如年份/经营单元/行业/产品线/阶段/风险等级，以及度量）。
条件充分则只输出 JSON：{"need_more_info": false, "question": "", "dimensions": []}；
条件不足或过于模糊，则输出 {"need_more_info": true, "question": "一句针对性追问", "dimensions": [...]}。
dimensions 只能从 ["year","unit","industry","productLine","stage","riskLevel"] 中选取你认为缺失的维度键。
**问题中已明确给出的维度不得再次列入 dimensions**：如"2025年/2026年"表示 year 已给出，
"经营单元为…"表示 unit 已给出、"行业为…"表示 industry 已给出等——已给出的维度请勿重复追问。
只列出真正缺失、需要用户补充的维度；确实拿不准时可多列，但优先少列。
追问需具体、可答，给出可选值。只输出 JSON，不要多余文字。"""

# 已给出维度的文本特征（纯字符串匹配，防重复追问）：A 门只看到当前问题字符串，须从中识别已确认参数
_GIVEN_PATTERNS = (
    ('year', ('2025年', '2026年', '年份为')),
    ('unit', ('经营单元为',)),
    ('industry', ('行业为',)),
    ('productLine', ('产品线为',)),
    ('stage', ('阶段为',)),
    ('riskLevel', ('风险等级为',)),
)


def given_dims(question: str) -> list[str]:
    """识别问题字符串中已明确给出的维度键（纯函数，供意图门 prompt 注入与兜底排除复用）"""
    out = []
    for key, pats in _GIVEN_PATTERNS:
        if any(p in question for p in pats):
            out.append(key)
    return out


def build(variables: dict) -> list[dict]:
    question = variables['question']
    given = given_dims(question)
    given_hint = f'（已在问题中给出：{"/".join(given)}，请勿重复追问）' if given else ''
    return [
        {'role': 'system', 'content': SYSTEM_TMPL},
        {'role': 'user', 'content': f'可用切片维度：年份(2025/2026)、经营单元、行业、产品线、阶段、风险等级\n问题：{question}{given_hint}'},
    ]