"""问数业务配置：数据源清单 / 预置热问 / 结果加工口径"""

# 前端可选数据源（key 对应模型白名单；selected 为前端默认勾选）
QA_SOURCES = [
    {'group': '台账', 'items': [
        {'key': 'commercial', 'name': '商业签约台账', 'label': '签约明细与产品线收入', 'group': '台账', 'selected': True},
        {'key': 'ppl', 'name': '项目储备台账', 'label': '在途项目阶段与风险', 'group': '台账', 'selected': True},
        {'key': 'goal', 'name': '经营目标台账', 'label': '各单元年度目标', 'group': '台账', 'selected': True},
    ]},
    {'group': '统计报表', 'items': [
        {'key': 'overall', 'name': '整体达成', 'label': '中国区整体及各经营单元达成', 'group': '统计报表', 'selected': True},
        {'key': 'product', 'name': '产品线达成', 'label': '各产品线收入与同比', 'group': '统计报表', 'selected': True},
        {'key': 'solution', 'name': '商解达成', 'label': '商解收入与目标', 'group': '统计报表', 'selected': True},
        {'key': 'industry', 'name': '行业达成', 'label': '各行业收入与拆分', 'group': '统计报表', 'selected': True},
        {'key': 'keyunit', 'name': '重点单元', 'label': '订单/未收款/高风险', 'group': '统计报表', 'selected': True},
    ]},
]

# 无热度数据时的预置快捷提问
QA_PRESET_HOT = ['政企行业收入3000万-5000万数据', '北京代表处今年达成情况']

# 快捷提问（热问推荐）最多返回条数
QA_HOT_LIMIT = 10

# 会话标题最大长度
QA_TITLE_MAX = 20

# 明细字段中优先作为统计口径的数值字段（按序匹配）
QA_NUMERIC_FIELDS = ('income', 'contractAmt', 'orderAmt', 'solutionIncome', 'yoy')

# 时间维度字段（图表折线判定）
QA_TIME_DIMS = ('year', 'month', 'quarter', 'signDate')

# 图表口径：饼图关键词与最大行数 / 金额度量标记与单位
QA_CHART = {
    'pie_keywords': ('占比', '构成', '分布比例', '结构'),
    'pie_max_rows': 8,
    'amount_markers': ('Amt', 'income', 'Goal'),
    'amount_unit': '万元',
}

# 结论生成引用的结果行采样上限
QA_CONCLUSION_ROWS = 20

# 追问建议条数
QA_FOLLOW_UPS = 3
