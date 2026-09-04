"""场景② 分析结论与追问生成（纯函数）

variables 契约：
- question  必填，用户原始问题
- query     必填，实际执行的查询模板（供 LLM 理解口径）
- rows      必填，真实结果行样本
"""

import json

# 场景特定参数：结论允许适度发挥，失败无重试（守卫链路之外的展示层场景）
PARAMS = {'temperature': 0.3, 'json': True, 'retries': 0}

SYSTEM_TMPL = (
    '你是经营数据分析助手。基于给定的真实查询结果行生成分析结论。'
    '只输出 JSON：{"text": "markdown 结论（2-4 句，引用真实数字）", "follow_ups": ["追问1", "追问2", "追问3"]}。'
    '禁止编造结果中不存在的数字。'
)


def build(variables: dict) -> list[dict]:
    """渲染该场景的消息列表（纯函数，禁 IO）"""
    user = (f'问题：{variables["question"]}\n'
            f'查询：{json.dumps(variables["query"], ensure_ascii=False)}\n'
            f'结果行（共{len(variables["rows"])}条）：{json.dumps(variables["rows"], ensure_ascii=False)}')
    return [
        {'role': 'system', 'content': SYSTEM_TMPL},
        {'role': 'user', 'content': user},
    ]
