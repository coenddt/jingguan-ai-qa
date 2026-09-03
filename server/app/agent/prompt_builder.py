"""system prompt 组装（纯函数）：模型描述 + 输出契约 + 示例 + 可选 few-shot"""

import json

from app.agent.schema_registry import describe_models

SYSTEM_TMPL = """你是数据查询生成器。根据用户问题，从给定模型清单中选择合适的模型，产出一个结构化查询 JSON（对 mongo-store 模型的查询，非 SQL）。

可用模型：
{models}

输出要求（只输出 JSON，不要多余文字）：
- 简单明细/排名 → {{"mode":"query","model":"...","condition":{{}},"fields":[...],"sort":{{}},"limit":50}}
- 汇总统计 → {{"mode":"aggregate","model":"...","condition":{{}},"groupBy":["..."],"measures":[{{"op":"sum","field":"..."}}],"sort":{{}},"limit":50}}
- condition 支持 $eq/$gt/$gte/$lt/$lte/$in/$ne/$regex/$exists；sort 的键必须是该模型字段（aggregate 时 sort 键为 groupBy 字段或聚合键 op_field）；limit ≤ 200
- 涉及收入/金额汇总优先 aggregate；涉及目标/完成率用 ReportOverall(收入) 与 GoalLedger(目标) 分别查询（只选一个主模型）
- 年份缺省取 2026；条件值必须来自维度枚举，禁止编造
{few_shot}"""

MODEL_JSON_EXAMPLES = [
    '问"2026年各经营单元收入排名" → {"mode":"aggregate","model":"ReportOverall","condition":{"year":{"$eq":2026}},"groupBy":["unit"],"measures":[{"op":"sum","field":"income"}],"sort":{"sum_income":-1},"limit":21}',
    '问"政企行业收入3000万-5000万数据" → {"mode":"query","model":"CommercialLedger","condition":{"year":{"$eq":2026},"industry":{"$eq":"政企"},"income":{"$gte":3000,"$lte":5000}},"fields":["signDate","unit","productLine","income","customer"],"sort":{"income":-1},"limit":100}',
    '问"各产品线销售情况" → {"mode":"aggregate","model":"ReportProduct","condition":{"year":{"$eq":2026}},"groupBy":["productLine"],"measures":[{"op":"sum","field":"income"}],"sort":{"sum_income":-1},"limit":10}',
]


def build_system_prompt(few_shots: list[dict] | None = None) -> str:
    models = json.dumps(describe_models(), ensure_ascii=False)
    few = ''
    if few_shots:
        lines = [f'- "{e["question"]}" → {json.dumps(e["template"], ensure_ascii=False)}' for e in few_shots[:3]]
        few = '\n参考以下历史成功问法（仅作参考，仍需按当前问题生成）：\n' + '\n'.join(lines)
    return SYSTEM_TMPL.format(models=models, few_shot=few) + '\n输出示例：\n' + '\n'.join(MODEL_JSON_EXAMPLES)


def build_retry_prompt(question: str, bad_query: dict, error: str) -> str:
    return (
        f'用户问题：{question}\n上次生成的查询：{json.dumps(bad_query, ensure_ascii=False)}\n'
        f'错误：{error}\n请修正后重新只输出查询 JSON。'
    )
