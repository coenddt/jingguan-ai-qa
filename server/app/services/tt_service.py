"""火山 TTS 代理（v3 HTTP 单向流式合成，聚合 base64 音频分片为 bytes）"""

import base64
import json

import httpx

from app.config import (
    TTS_API_URL, TTS_AUDIO_FORMAT, TTS_MAX_CHARS, TTS_RESOURCE_ID, TTS_SAMPLE_RATE, TTS_TIMEOUT,
    TTS_USER_UID, TTS_VOICE_TYPE,
)
from app.config import cfg
from app.errors import BusinessError

# 官方约定：流式响应 code=0 携带 base64 音频分片，20000000 表示合成完成
_DONE_CODE = 20000000


async def synthesize(text: str) -> bytes:
    if not cfg.VOICE_API_KEY:
        raise BusinessError('TTS 未配置（VOICE_API_KEY 缺失）', 400)
    payload = {
        'user': {'uid': TTS_USER_UID},
        'req_params': {
            'text': text[:TTS_MAX_CHARS],
            'speaker': TTS_VOICE_TYPE,
            'audio_params': {'format': TTS_AUDIO_FORMAT, 'sample_rate': TTS_SAMPLE_RATE},
        },
    }
    headers = {
        'Content-Type': 'application/json',
        'X-Api-Key': cfg.VOICE_API_KEY,
        'X-Api-Resource-Id': TTS_RESOURCE_ID,
    }
    chunks: list[bytes] = []
    async with httpx.AsyncClient(timeout=TTS_TIMEOUT) as client:
        async with client.stream('POST', TTS_API_URL, json=payload, headers=headers) as resp:
            if resp.status_code != 200:
                detail = (await resp.aread())[:200].decode('utf-8', 'ignore')
                raise BusinessError(f'TTS 服务错误 {resp.status_code}: {detail}', 502)
            async for line in resp.aiter_lines():
                if not line:
                    continue
                data = json.loads(line)
                code = data.get('code')
                if code == _DONE_CODE:
                    break
                if code != 0:
                    raise BusinessError(f'TTS 合成失败: {data.get("message", "unknown")}', 502)
                audio = data.get('data')
                if audio:
                    chunks.append(base64.b64decode(audio))
    if not chunks:
        raise BusinessError('TTS 合成失败: 未返回音频', 502)
    return b''.join(chunks)
