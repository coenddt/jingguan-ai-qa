"""提示词场景注册表：新增场景 = 新建场景模块（PARAMS + build）+ 此处注册一行"""

from app.agent.prompts import conclusion, intent_gate, query_gen

SCENARIOS = {'query_gen': query_gen, 'conclusion': conclusion, 'intent_gate': intent_gate}


def build_messages(scenario_id: str, variables: dict) -> list[dict]:
    """渲染场景消息（纯函数，禁 IO）；未注册场景直接抛错，禁静默兜底"""
    scenario = SCENARIOS.get(scenario_id)
    if not scenario:
        raise ValueError(f'未注册的提示词场景：{scenario_id}')
    return scenario.build(variables)


def scenario_params(scenario_id: str) -> dict:
    """取场景参数（temperature/json/retries 等）；未注册场景直接抛错"""
    scenario = SCENARIOS.get(scenario_id)
    if not scenario:
        raise ValueError(f'未注册的提示词场景：{scenario_id}')
    return dict(scenario.PARAMS)
