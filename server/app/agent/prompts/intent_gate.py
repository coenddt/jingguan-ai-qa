"""场景③ 生成前意图门：判断问题条件是否充分（A 兜底；纯函数）"""

PARAMS = {'temperature': 0.1, 'json': True, 'retries': 0}

SYSTEM_TMPL = """你是问数意图校验器。判断用户问题是否给出了足够明确的查询条件
（切片维度如年份/经营单元/行业/产品线/阶段/风险等级，以及度量）。
条件充分则只输出 JSON：{"need_more_info": false, "question": "", "dimensions": []}；
条件不足或过于模糊，则输出 {"need_more_info": true, "question": "一句针对性追问", "dimensions": [...]}。
dimensions 只能从 ["year","unit","industry","productLine","stage","riskLevel"] 中选取你认为缺失的维度键；
若拿不准，就将全部维度键列出。追问需具体、可答，给出可选值。只输出 JSON，不要多余文字。"""


def build(variables: dict) -> list[dict]:
    question = variables['question']
    return [
        {'role': 'system', 'content': SYSTEM_TMPL},
        {'role': 'user', 'content': f'可用切片维度：年份(2025/2026)、经营单元、行业、产品线、阶段、风险等级\n问题：{question}'},
    ]