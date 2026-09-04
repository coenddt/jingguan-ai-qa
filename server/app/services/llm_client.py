"""唯一 LLM IO 出口：平台预设 × 模型配置 × 场景参数（OpenAI 兼容 chat/completions，httpx）

三层架构：
- 平台层  PLATFORM_PRESETS  平台预设（base_url 等），新增平台只加一条
- 模型层  model_conf        AiModel 记录（platform/baseUrl/apiKey/modelName，管理端配置）
- 场景层  agent/prompts     提示词组装 + 场景参数（temperature/json/retries）
"""

import json
import re
import time

import httpx

from app.agent.prompts import build_messages, scenario_params
from app.config import LLM_TEMPERATURE, LLM_TIMEOUT, cfg

PLATFORM_PRESETS = {
    'deepseek': {'name': 'DeepSeek', 'base_url': 'https://api.deepseek.com/v1'},
    'volcengine': {'name': '火山引擎方舟', 'base_url': 'https://ark.cn-beijing.volces.com/api/v3'},
}


def resolve_base_url(platform: str, base_url: str | None = None) -> str:
    """平台 baseUrl 解析：显式 baseUrl 优先，空则取平台预设；未知平台抛错（禁静默兜底）"""
    preset = PLATFORM_PRESETS.get(platform)
    if not preset:
        raise ValueError(f'不支持的大模型平台：{platform}')
    return (base_url or preset['base_url']).rstrip('/')


async def chat(messages: list[dict], base_url: str | None = None,
               api_key: str | None = None, model: str | None = None,
               temperature: float = LLM_TEMPERATURE) -> dict:
    url = (base_url or cfg.LLM_BASE_URL).rstrip('/') + '/chat/completions'
    headers = {'Authorization': f'Bearer {api_key or cfg.LLM_API_KEY}'}
    body = {
        'model': model or cfg.LLM_MODEL,
        'messages': messages,
        'temperature': temperature,
    }
    t0 = time.monotonic()
    async with httpx.AsyncClient(timeout=LLM_TIMEOUT) as client:
        resp = await client.post(url, json=body, headers=headers)
        if resp.status_code != 200:
            raise RuntimeError(f'LLM 请求失败 {resp.status_code}: {resp.text[:200]}')
        data = resp.json()
    content = data['choices'][0]['message']['content']
    usage = data.get('usage', {}) or {}
    return {
        'content': content,
        'prompt_tokens': usage.get('prompt_tokens', 0),
        'completion_tokens': usage.get('completion_tokens', 0),
        'total_tokens': usage.get('total_tokens', 0),
        'elapsed_s': round(time.monotonic() - t0, 2),
    }


def extract_json(text: str) -> dict:
    """从 LLM 输出中提取 JSON（容忍 ```json 围栏）"""
    m = re.search(r'```(?:json)?\s*(.*?)```', text, re.S)
    raw = m.group(1) if m else text
    start = raw.find('{')
    if start < 0:
        raise ValueError('LLM 输出不含 JSON')
    obj, _ = json.JSONDecoder().raw_decode(raw[start:])
    return obj


async def invoke(scenario_id: str, variables: dict, model_conf: dict) -> tuple[dict | str, dict]:
    """场景化通用调用（平台 → 模型 → 场景）：
    提示词与参数来自 agent/prompts 注册表，平台/模型来自 AiModel 配置。
    返回 (json 场景为解析后的对象，否则为原文, meta)。"""
    params = scenario_params(scenario_id)
    messages = build_messages(scenario_id, variables)
    ret = await chat(
        messages,
        base_url=resolve_base_url(model_conf['platform'], model_conf.get('baseUrl')),
        api_key=model_conf.get('apiKey'),
        model=model_conf.get('modelName'),
        temperature=params['temperature'],
    )
    return (extract_json(ret['content']) if params['json'] else ret['content']), ret
