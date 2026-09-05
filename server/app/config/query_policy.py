"""查询安全与执行策略：守卫白名单 / 行数上限 / 执行超时"""

# 条件操作符白名单（默认拒绝，仅此集内放行）——$regex 已移除（ReDoS 面，改用 $eq/$in 精确匹配）
ALLOWED_OPS = {'$eq', '$gt', '$gte', '$lt', '$lte', '$in', '$nin', '$ne', '$exists'}

# 显式声明被拒绝的危险/扩展操作符（文档化 + 守卫命中时给出明确信息，防 LLM 猜测）
# 涵盖：JS 执行($where)、跨集合/跨库($lookup/$unionWith/$merge/$out)、表达式注入($expr/$function)、
# 逻辑组合($and/$or/$nor/$not)、数组操作($elemMatch/$all/$size)、子串截断($text)、
# 正则灾难回溯($regex，ReDoS 面) 等
DENIED_OPS = {
    '$where', '$lookup', '$unionWith', '$merge', '$out', '$facet', '$graphLookup', '$match',
    '$expr', '$function', '$accumulator', '$map', '$reduce', '$filter',
    '$and', '$or', '$nor', '$not', '$elemMatch', '$all', '$size', '$text', '$regex',
}

# 聚合算子白名单
ALLOWED_MEASURES = {'sum', 'avg', 'count', 'min', 'max'}

# 数值型 schema 类型（聚合目标字段必须为数值）
NUMERIC_TYPES = ('int', 'long', 'float', 'double')

# 单查询最大返回行数（守卫强制截断）
MAX_LIMIT = 200

# 受限查询执行超时（秒）
EXEC_TIMEOUT = 10
