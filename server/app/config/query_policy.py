"""查询安全与执行策略：守卫白名单 / 行数上限 / 执行超时"""

# 条件操作符白名单
ALLOWED_OPS = {'$eq', '$gt', '$gte', '$lt', '$lte', '$in', '$nin', '$ne', '$exists', '$regex'}

# 聚合算子白名单
ALLOWED_MEASURES = {'sum', 'avg', 'count', 'min', 'max'}

# 数值型 schema 类型（聚合目标字段必须为数值）
NUMERIC_TYPES = ('int', 'long', 'float', 'double')

# 单查询最大返回行数（守卫强制截断）
MAX_LIMIT = 200

# 受限查询执行超时（秒）
EXEC_TIMEOUT = 10
