"""模型清单 + 字段注释 + 维度枚举（text-to-query 注入源；纯函数，禁 IO）"""

from app.models.registry import BUSINESS_MODELS, MODEL_TABLE
from app.seed.dim_defs import INDUSTRIES, PRODUCT_LINES, RISK_LEVELS, STAGES, UNITS

FIELD_COMMENTS: dict[str, dict[str, str]] = {
    'CommercialLedger': {
        'signDate': '签约日期 YYYY-MM-DD', 'year': '年份', 'quarter': '季度1-4', 'month': '月份1-12',
        'unit': '经营单元', 'industry': '行业', 'productLine': '产品线',
        'productModel': '产品型号', 'contractAmt': '合同金额(万元)', 'income': '收入额(万元)',
        'customer': '客户',
    },
    'PplLedger': {
        'year': '年份', 'projectName': '项目名称', 'unit': '经营单元', 'industry': '行业',
        'contractAmt': '合同金额(万元)', 'stage': '项目阶段', 'riskLevel': '风险等级',
    },
    'GoalLedger': {
        'year': '年份', 'unit': '经营单元',
        'commercialGoal': '商业目标(万元)', 'solutionGoal': '商解目标(万元)',
    },
    'ReportOverall': {
        'year': '年份', 'unit': '经营单元', 'income': '收入额(万元)',
        'gcIncome': '商业收入(万元)', 'znIncome': '智能收入(万元)', 'bsIncome': '商解收入(万元)',
    },
    'ReportProduct': {
        'year': '年份', 'productLine': '产品线', 'income': '收入额(万元)', 'yoy': '同比(%)',
    },
    'ReportSolution': {
        'year': '年份', 'unit': '经营单元',
        'solutionIncome': '商解收入(万元)', 'solutionGoal': '商解目标(万元)',
    },
    'ReportIndustry': {
        'year': '年份', 'industry': '行业', 'income': '收入额(万元)',
        'gcIncome': '商业收入(万元)', 'znIncome': '智能收入(万元)', 'bsIncome': '商解收入(万元)',
    },
    'ReportKeyUnit': {
        'year': '年份', 'unit': '经营单元', 'orderAmt': '订单金额(万元)',
        'notRecvAmt': '未收款项(万元)', 'riskCount': '高风险项目数',
    },
}

DIM_ENUMS: dict[str, list] = {
    'unit': UNITS, 'industry': INDUSTRIES, 'productLine': PRODUCT_LINES,
    'stage': STAGES, 'riskLevel': RISK_LEVELS, 'year': [2025, 2026],
}

_MODEL_HINTS = {
    'CommercialLedger': '商业签约台账（签约明细，含产品线/客户）',
    'PplLedger': '项目储备台账（在途项目、阶段与风险）',
    'GoalLedger': '经营目标台账（各单元年度目标）',
    'ReportOverall': '整体达成统计（各单元收入与拆分）',
    'ReportProduct': '产品线统计（收入与同比）',
    'ReportSolution': '商解统计（各单元商解收入与目标）',
    'ReportIndustry': '行业统计（各行业收入）',
    'ReportKeyUnit': '重点单元统计（订单/未收款/高风险数）',
}


def describe_models() -> list[dict]:
    """输出 text-to-query 用的模型描述（纯函数）"""
    out = []
    for name in BUSINESS_MODELS:
        s = MODEL_TABLE[name]
        fields = []
        for f, spec in s['fields'].items():
            ftype = spec['type'] if isinstance(spec, dict) else spec
            fields.append({
                'name': f, 'type': ftype,
                'comment': FIELD_COMMENTS.get(name, {}).get(f, ''),
                'enum': DIM_ENUMS.get(f),
            })
        out.append({'model': name, 'hint': _MODEL_HINTS.get(name, ''), 'fields': fields})
    return out
