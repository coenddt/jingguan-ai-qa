"""固定种子灌库（random.seed(42) 可复现）：明细汇总≈统计表、完成率=income/goal"""

import random

from app.config import cfg
from app.db.mongo_store import store
from app.seed.dim_defs import (
    INDUSTRIES, INCOME_SUBS, PRODUCT_LINES, PRODUCT_MODELS, RISK_LEVELS,
    STAGES, UNITS, YEARS,
)

_CUSTOMERS = ['华信集团', '中科曙光', '国泰银行', '南方电网', '交通投资集团', '第一医院',
              '明日科技', '智造股份', '移动省公司', '城建集团', '证券交易所', '能源研究院']


def _r1(x: float) -> float:
    return round(x, 1)


async def seed_if_empty() -> bool:
    """库空则灌种子；已启动过则跳过（幂等）"""
    n = await store.count('CommercialLedger')
    if n > 0:
        return False
    await store.run_as_internal(_seed_all)
    return True


async def _seed_all() -> None:
    random.seed(42)
    await _seed_commercial()
    await _seed_ppl()
    await _seed_reports()
    await _seed_app_defaults()


async def _seed_commercial() -> None:
    rows: list[dict] = []
    for year in YEARS:
        for i in range(210):
            month = random.randint(1, 12)
            unit = random.choice(UNITS)
            industry = random.choice(INDUSTRIES)
            line = random.choice(PRODUCT_LINES)
            contract = random.uniform(500, 8000)
            rows.append({
                'signDate': f'{year}-{month:02d}-{random.randint(1, 28):02d}',
                'year': year, 'quarter': (month - 1) // 3 + 1, 'month': month,
                'unit': unit, 'industry': industry,
                'productLine': line, 'productModel': random.choice(PRODUCT_MODELS[line]),
                'contractAmt': _r1(contract), 'income': _r1(contract * random.uniform(0.6, 0.95)),
                'customer': random.choice(_CUSTOMERS),
            })
    await store.insert_many('CommercialLedger', rows)


async def _seed_ppl() -> None:
    rows: list[dict] = []
    for year in YEARS:
        for i in range(55):
            risk = random.choice(RISK_LEVELS)
            if len(rows) < 8:
                risk = '高'  # 保证 ≥7 条高风险
            rows.append({
                'year': year,
                'projectName': f'{random.choice(UNITS)[:2]}{random.choice(PRODUCT_LINES)}项目{i + 1}',
                'unit': random.choice(UNITS), 'industry': random.choice(INDUSTRIES),
                'contractAmt': _r1(random.uniform(100, 3000)),
                'stage': random.choice(STAGES), 'riskLevel': risk,
            })
    await store.insert_many('PplLedger', rows)


async def _seed_reports() -> None:
    items = await store.query(
        'CommercialLedger($condition:@c0) { year, unit, industry, productLine, contractAmt, income }',
        {'c0': {}},
    )
    ppl = await store.query('PplLedger($condition:@c0) { year, unit, riskLevel, contractAmt }', {'c0': {}})

    inc_unit: dict[tuple, float] = {}
    inc_ind: dict[tuple, float] = {}
    inc_line: dict[tuple, float] = {}
    subs: dict[tuple, dict] = {}
    ct_amt: dict[tuple, float] = {}
    ct_inc: dict[tuple, float] = {}
    for it in items:
        y = it['year']
        inc_unit[(y, it['unit'])] = inc_unit.get((y, it['unit']), 0) + it['income']
        inc_ind[(y, it['industry'])] = inc_ind.get((y, it['industry']), 0) + it['income']
        inc_line[(y, it['productLine'])] = inc_line.get((y, it['productLine']), 0) + it['income']
        ct_amt[(y, it['unit'])] = ct_amt.get((y, it['unit']), 0) + it['contractAmt']
        ct_inc[(y, it['unit'])] = ct_inc.get((y, it['unit']), 0) + it['income']
        s = subs.setdefault((y, it['unit']), {'gcIncome': 0.0, 'znIncome': 0.0, 'bsIncome': 0.0})
        k = INCOME_SUBS[random.randint(0, 2)]
        s[k] = _r1(s[k] + it['income'])

    goal_rows = []
    for (y, unit), inc in inc_unit.items():
        goal_rows.append({
            'year': y, 'unit': unit,
            'commercialGoal': _r1(inc * random.uniform(0.92, 1.18)),
            'solutionGoal': _r1(inc * random.uniform(0.25, 0.45)),
        })
    await store.insert_many('GoalLedger', goal_rows)
    goal_map = {(g['year'], g['unit']): g for g in goal_rows}

    overall = []
    for (y, unit), inc in inc_unit.items():
        s = subs.get((y, unit), {'gcIncome': 0, 'znIncome': 0, 'bsIncome': 0})
        overall.append({'year': y, 'unit': unit, 'income': _r1(inc),
                        'gcIncome': _r1(s['gcIncome']), 'znIncome': _r1(s['znIncome']),
                        'bsIncome': _r1(s['bsIncome'])})
    await store.insert_many('ReportOverall', overall)

    product = []
    for (y, line), inc in inc_line.items():
        product.append({'year': y, 'productLine': line, 'income': _r1(inc), 'yoy': 0.0})
    line_2025 = {p['productLine']: p['income'] for p in product if p['year'] == 2025}
    for p in product:
        if p['year'] == 2026 and line_2025.get(p['productLine']):
            p['yoy'] = _r1((p['income'] / line_2025[p['productLine']] - 1) * 100)
    await store.insert_many('ReportProduct', product)

    solution = []
    for (y, unit), inc in inc_unit.items():
        g = goal_map.get((y, unit), {})
        solution.append({'year': y, 'unit': unit, 'solutionIncome': _r1(inc * 0.35),
                         'solutionGoal': g.get('solutionGoal', 0.0)})
    await store.insert_many('ReportSolution', solution)

    industry = []
    for (y, ind), inc in inc_ind.items():
        industry.append({'year': y, 'industry': ind, 'income': _r1(inc),
                         'gcIncome': _r1(inc * 0.4), 'znIncome': _r1(inc * 0.35),
                         'bsIncome': _r1(inc * 0.25)})
    await store.insert_many('ReportIndustry', industry)

    key_unit = []
    for (y, unit), amt in ct_amt.items():
        risk_n = len([p for p in ppl if p['year'] == y and p['unit'] == unit and p['riskLevel'] == '高'])
        key_unit.append({'year': y, 'unit': unit, 'orderAmt': _r1(amt),
                         'notRecvAmt': _r1(max(0.0, amt - ct_inc.get((y, unit), 0))),
                         'riskCount': risk_n})
    await store.insert_many('ReportKeyUnit', key_unit)


async def _seed_app_defaults() -> None:
    await store.insert('AiModel', {
        'name': cfg.LLM_MODEL, 'baseUrl': cfg.LLM_BASE_URL,
        'apiKey': cfg.LLM_API_KEY, 'modelName': cfg.LLM_MODEL, 'enabled': True,
    })
    defaults = {
        'greeting': {'text': '你好，我是经管之星·AI问数助手，可以就经营台账与统计报表向你提供数据问答服务。',
                     'questions': ['各产品线销售情况', '北京的产品线收入情况', '深圳的产品销售情况']},
        'suggestions': True,
        'tts': False,
        'stt': False,
        'modelConfig': True,
        'hotRecommend': {'enabled': True, 'threshold': cfg.SYS_HOT_THRESHOLD},
    }
    for k, v in defaults.items():
        await store.upsert('AppConfig', {'key': k}, {'value': v})
