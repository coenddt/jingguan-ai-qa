"""唯一 LLM IO 出口：平台预设 × 模型配置 × 场景参数（OpenAI 兼容 chat/completions，httpx）

三层架构：
- 平台层  PLATFORM_PRESETS  平台预设（base_url 等），新增平台只加一条
- 模型层  model_conf        AiModel 记录（platform/baseUrl/apiKey/modelName，管理端配置）
- 场景层  agent/prompts     提示词组装 + 场景参数（temperature/json/retries）
"""

import json
import re
import time
from urllib.parse import urlparse

import httpx

from app.agent.prompts import build_messages, scenario_params
from app.config import LLM_TEMPERATURE, LLM_TIMEOUT, cfg
from app.log import log
from app.services import json_schema_shell

PLATFORM_PRESETS = {
    'deepseek': {'name': 'DeepSeek', 'base_url': 'https://api.deepseek.com/v1'},
    'volcengine': {'name': '火山引擎方舟', 'base_url': 'https://ark.cn-beijing.volces.com/api/v3'},
}

# 平台层：reasoning 语义 → 各平台请求体翻译（新增/变更平台只改这里，场景层不感知）。
# reasoning 取值范围见场景参数（当前仅 'disabled'：不需模型思考，纯可见输出）。
_REASONING_PAYLOADS = {
    'disabled': {'deepseek': {'type': 'disabled'}, 'volcengine': {'type': 'disabled'}},
}


def _resolve_reasoning(platform: str, flag: str | None) -> dict | None:
    """把场景语义 flag 翻译成 platform 的请求体；无 flag 或平台未定义该姿势 → None（不注入）。

    未知平台/未知语义不静默注入奇怪字段导致上抛 400，但也不该无声回头踏默认行为，
    故落一条 warn 告警（堡垒思想：宁可误告警，不可漏告警）。
    """
    if not flag:
        return None
    payload = _REASONING_PAYLOADS.get(flag, {}).get(platform)
    if payload is None:
        log('warn', 'llm_reasoning_unmapped', flag=flag, platform=platform)
    return payload

# 共享连接池：复用一个 keep-alive 客户端，避免每次调用新建 TCP+TLS 连接
# （预热/候选并发/结论每次调用都受益；httpx.AsyncClient 天然支持并发复用）
_client: httpx.AsyncClient | None = None


def _get_client() -> httpx.AsyncClient:
    global _client
    if _client is None:
        _client = httpx.AsyncClient(timeout=LLM_TIMEOUT)
    return _client


async def aclose() -> None:
    """应用退出时关闭共享客户端（由 main lifespan 钩子调用）"""
    global _client
    if _client is not None:
        await _client.aclose()
        _client = None


def resolve_base_url(platform: str, base_url: str | None = None) -> str:
    """平台 baseUrl 解析：显式 baseUrl 优先，空则取平台预设；未知平台抛错（禁静默兜底）。
    自定义 baseUrl 仅允许与平台预设同 host（防 SSRF 探测内网）。"""
    preset = PLATFORM_PRESETS.get(platform)
    if not preset:
        raise ValueError(f'不支持的大模型平台：{platform}')
    if not base_url:
        return preset['base_url'].rstrip('/')
    preset_host = urlparse(preset['base_url']).netloc
    parsed = urlparse(base_url)
    if parsed.scheme not in ('http', 'https') or parsed.netloc != preset_host:
        raise ValueError(f'baseUrl 域名不合法：仅允许平台预设域名 {preset_host}')
    return base_url.rstrip('/')


async def chat(messages: list[dict], base_url: str | None = None,
               api_key: str | None = None, model: str | None = None,
               temperature: float = LLM_TEMPERATURE, max_tokens: int | None = None,
               thinking: dict | None = None) -> dict:
    url = (base_url or cfg.LLM_BASE_URL).rstrip('/') + '/chat/completions'
    headers = {'Authorization': f'Bearer {api_key or cfg.LLM_API_KEY}'}
    body = {
        'model': model or cfg.LLM_MODEL,
        'messages': messages,
        'temperature': temperature,
    }
    if max_tokens is not None:
        body['max_tokens'] = max_tokens  # 预热等极短输出场景限制生成长度，少烧 token
    if thinking is not None:
        body['thinking'] = thinking  # 显式关思考：思考 token 计入 max_tokens，不关则封顶必截断（实测 ~500 token 思考）
    t0 = time.monotonic()
    resp = await _get_client().post(url, json=body, headers=headers)
    if resp.status_code != 200:
        raise RuntimeError(f'LLM 请求失败 {resp.status_code}: {resp.text[:200]}')
    data = resp.json()
    content = data['choices'][0]['message']['content']
    usage = data.get('usage', {}) or {}
    # 前缀缓存命中/token（DeepSeek 与 火山方舟均返回；支持不了的平台为 0，不影响主流程）
    cache_hit = usage.get('prompt_cache_hit_tokens') or 0
    cache_miss = usage.get('prompt_cache_miss_tokens') or 0
    prompt_tokens = usage.get('prompt_tokens', 0) or (cache_hit + cache_miss or 0)
    return {
        'content': content,
        'prompt_tokens': prompt_tokens,
        'completion_tokens': usage.get('completion_tokens', 0),
        'total_tokens': usage.get('total_tokens', 0) or (prompt_tokens + usage.get('completion_tokens', 0) or 0),
        'elapsed_s': round(time.monotonic() - t0, 2),
        'cache_hit_tokens': cache_hit,
        'cache_miss_tokens': cache_miss,
    }


def extract_json(text: str) -> dict:
    """从 LLM 输出中提取 JSON（容忍 ```json 围栏）"""
    m = re.search(r'```(?:json)?\s*(.*?)```', text, re.DOTALL)
    raw = m.group(1) if m else text
    start = raw.find('{')
    if start < 0:
        raise ValueError('LLM 输出不含 JSON')
    obj, _ = json.JSONDecoder().raw_decode(raw[start:])
    return obj


async def invoke(scenario_id: str, variables: dict, model_conf: dict) -> tuple[dict | str, dict]:
    """场景化通用调用（平台 → 模型 → 场景）：
    提示词与参数来自 agent/prompts 注册表，平台/模型来自 AiModel 配置。
    JSON Schema 壳在唯一 LLM 出口做浅层挂载：入口注入 schema、出口结构校验（失败抛 ShellError）。
    返回 (json 场景为解析后的对象，否则为原文, meta)。"""
    params = scenario_params(scenario_id)
    messages = json_schema_shell.attach_schema(build_messages(scenario_id, variables), scenario_id)
    ret = await chat(
        messages,
        base_url=resolve_base_url(model_conf['platform'], model_conf.get('baseUrl')),
        api_key=model_conf.get('apiKey'),
        model=model_conf.get('modelName'),
        temperature=params['temperature'],
        max_tokens=params.get('max_tokens'),
        thinking=_resolve_reasoning(model_conf['platform'], params.get('reasoning')),
    )
    if params['json']:
        return json_schema_shell.validate(extract_json(ret['content']), scenario_id), ret
    return ret['content'], ret
