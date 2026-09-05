"""场景① text-to-query 查询生成：system 模板 + 输出示例 + few-shot + 重试修正（纯函数）

variables 契约：
- question        必填，用户自然语言问题
- few_shots       可选，历史成功问法 [{question, template}]（首次生成时注入）
- bad_query/error 可选，同时提供时进入重试修正形态
"""

import json

from app.agent.schema_registry import describe_models

# 场景特定参数：查询生成要求高确定性，且守卫失败需回传重试
# reasoning=disabled 语义：不需要模型思考。实测 4 类问法守卫通过率 4/4、语义 3/4 完全一致 1/4 等价，
# 耗时从 2.5~21.9s 降至 0.54~0.68s；守卫链路（白名单+择优+重试）不变，越界仍被拦并自动反馈。
# 具体请求体由 llm_client 平台层翻译（场景层不耦合平台姿势）。
PARAMS = {'temperature': 0.1, 'json': True, 'retries': 3, 'few_shot_max': 3,
          'reasoning': 'disabled'}

SYSTEM_TMPL = """你是数据查询生成器。根据用户问题，从给定模型清单中选择合适的模型，产出一个结构化查询 JSON（对 mongo-store 模型的查询，非 SQL）。

可用模型：
{models}

输出要求（只输出 JSON，不要多余文字）：
- 简单明细/排名 → {{"mode":"query","model":"...","condition":{{}},"fields":[...],"sort":{{}},"limit":50}}
- 汇总统计 → {{"mode":"aggregate","model":"...","condition":{{}},"groupBy":["..."],"measures":[{{"op":"sum","field":"..."}}],"sort":{{}},"limit":50}}
- condition 支持 $eq/$gt/$gte/$lt/$lte/$in/$ne/$exists；sort 的键必须是该模型字段（aggregate 时 sort 键为 groupBy 字段或聚合键 op_field）；limit ≤ 200
- 涉及收入/金额汇总优先 aggregate；涉及目标/完成率用 ReportOverall(收入) 与 GoalLedger(目标) 分别查询（只选一个主模型）
- 求整体汇总指标（总金额/总收入/平均值/共多少单等，无分组维度）时 groupBy 固定取 ["year"]（返回单行）；计数类用 {{"op":"count","field":""}}
- 按维度求"平均/最高/最低"（问题含"各/每个/按某维度"分组词，如"各产品线的平均/单笔最高/单笔最低签约额"）→ groupBy 该维度 + measures 用 avg/max/min；切勿降级成整体排序明细
- 无分组词的整体求平均/最高/最低（如"重点单元平均订单金额"）→ groupBy 固定取 ["year"]（单行），勿按隐含维度分组
- 年份缺省取 2026；条件值必须来自维度枚举，禁止编造
{few_shot}"""

MODEL_JSON_EXAMPLES = [
    '问"2026年各经营单元收入排名" → {"mode":"aggregate","model":"ReportOverall","condition":{"year":{"$eq":2026}},"groupBy":["unit"],"measures":[{"op":"sum","field":"income"}],"sort":{"sum_income":-1},"limit":21}',
    '问"政企行业收入3000万-5000万数据" → {"mode":"query","model":"CommercialLedger","condition":{"year":{"$eq":2026},"industry":{"$eq":"政企"},"income":{"$gte":3000,"$lte":5000}},"fields":["signDate","unit","productLine","income","customer"],"sort":{"income":-1},"limit":100}',
    '问"各产品线销售情况" → {"mode":"aggregate","model":"ReportProduct","condition":{"year":{"$eq":2026}},"groupBy":["productLine"],"measures":[{"op":"sum","field":"income"}],"sort":{"sum_income":-1},"limit":10}',
    '问"2026年签约总金额是多少" → {"mode":"aggregate","model":"CommercialLedger","condition":{"year":{"$eq":2026}},"groupBy":["year"],"measures":[{"op":"sum","field":"contractAmt"}],"sort":{},"limit":10}',
    '问"2026年共签了多少单" → {"mode":"aggregate","model":"CommercialLedger","condition":{"year":{"$eq":2026}},"groupBy":["year"],"measures":[{"op":"count","field":""}],"sort":{},"limit":10}',
    '问"2026年各产品线单笔最高的签约金额" → {"mode":"aggregate","model":"CommercialLedger","condition":{"year":{"$eq":2026}},"groupBy":["productLine"],"measures":[{"op":"max","field":"contractAmt"}],"sort":{"max_contractAmt":-1},"limit":50}',
    '问"2026年各产品线单笔最低的签约金额" → {"mode":"aggregate","model":"CommercialLedger","condition":{"year":{"$eq":2026}},"groupBy":["productLine"],"measures":[{"op":"min","field":"contractAmt"}],"sort":{"min_contractAmt":-1},"limit":50}',
]

RETRY_TMPL = '用户问题：{question}\n上次生成的查询：{bad_query}\n错误：{error}\n请修正后重新只输出查询 JSON。'


def _system_prompt(few_shots: list[dict] | None) -> str:
    models = json.dumps(describe_models(), ensure_ascii=False)
    few = ''
    if few_shots:
        lines = [f'- "{e["question"]}" → {json.dumps(e["template"], ensure_ascii=False)}'
                 for e in few_shots[:int(PARAMS['few_shot_max'])]]
        few = '\n参考以下历史成功问法（仅作参考，仍需按当前问题生成）：\n' + '\n'.join(lines)
    return SYSTEM_TMPL.format(models=models, few_shot=few) + '\n输出示例：\n' + '\n'.join(MODEL_JSON_EXAMPLES)


def build(variables: dict) -> list[dict]:
    """渲染该场景的消息列表（纯函数，禁 IO）"""
    question = variables['question']
    if 'bad_query' in variables and 'error' in variables:
        return [
            {'role': 'system', 'content': _system_prompt(None)},
            {'role': 'user', 'content': RETRY_TMPL.format(
                question=question,
                bad_query=json.dumps(variables['bad_query'], ensure_ascii=False),
                error=variables['error'],
            )},
        ]
    return [
        {'role': 'system', 'content': _system_prompt(variables.get('few_shots'))},
        {'role': 'user', 'content': question},
    ]
