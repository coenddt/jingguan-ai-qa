"""唯一 LLM IO 出口：OpenAI 兼容 chat/completions（httpx），采集 usage 与耗时"""

import json
import re
import time

import httpx

from app.config import cfg

LLM_TIMEOUT = 120


async def chat(messages: list[dict], base_url: str | None = None,
               api_key: str | None = None, model: str | None = None,
               temperature: float = 0.1) -> dict:
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


async def chat_json(messages: list[dict], **kw) -> tuple[dict, dict]:
    ret = await chat(messages, **kw)
    return extract_json(ret['content']), ret
