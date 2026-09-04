"""提示词配置：system 模板 / few-shot 示例 / 重试与结论指令（纯文本，组装在 agent/）"""

# 查询生成 system prompt（{models}/{few_shot} 由 prompt_builder 注入）
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

# few-shot 输出示例
MODEL_JSON_EXAMPLES = [
    '问"2026年各经营单元收入排名" → {"mode":"aggregate","model":"ReportOverall","condition":{"year":{"$eq":2026}},"groupBy":["unit"],"measures":[{"op":"sum","field":"income"}],"sort":{"sum_income":-1},"limit":21}',
    '问"政企行业收入3000万-5000万数据" → {"mode":"query","model":"CommercialLedger","condition":{"year":{"$eq":2026},"industry":{"$eq":"政企"},"income":{"$gte":3000,"$lte":5000}},"fields":["signDate","unit","productLine","income","customer"],"sort":{"income":-1},"limit":100}',
    '问"各产品线销售情况" → {"mode":"aggregate","model":"ReportProduct","condition":{"year":{"$eq":2026}},"groupBy":["productLine"],"measures":[{"op":"sum","field":"income"}],"sort":{"sum_income":-1},"limit":10}',
]

# few-shot 历史问法最多注入条数
FEW_SHOT_MAX = 3

# 校验失败重试 prompt（{question}/{bad_query}/{error} 由 prompt_builder 注入）
RETRY_TMPL = '用户问题：{question}\n上次生成的查询：{bad_query}\n错误：{error}\n请修正后重新只输出查询 JSON。'

# 结论生成 system prompt
CONCLUSION_TMPL = (
    '你是经营数据分析助手。基于给定的真实查询结果行生成分析结论。'
    '只输出 JSON：{"text": "markdown 结论（2-4 句，引用真实数字）", "follow_ups": ["追问1", "追问2", "追问3"]}。'
    '禁止编造结果中不存在的数字。'
)
