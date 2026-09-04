"""火山 TTS 代理（HTTP 合成，返回音频 bytes）"""

import base64
import uuid

import httpx

from app.config import (
    TTS_API_URL, TTS_CLUSTER, TTS_ENCODING, TTS_MAX_CHARS, TTS_TIMEOUT, TTS_USER_UID, TTS_VOICE_TYPE,
)
from app.config import cfg
from app.errors import BusinessError


async def synthesize(text: str) -> bytes:
    if not cfg.VOICE_APP_ID or not cfg.VOICE_ACCESS_TOKEN:
        raise BusinessError('TTS 未配置（VOICE_APP_ID/VOICE_ACCESS_TOKEN 缺失）', 400)
    reqid = uuid.uuid4().hex
    body = {
        'app': {'appid': cfg.VOICE_APP_ID, 'token': 'access_token', 'cluster': TTS_CLUSTER},
        'user': {'uid': TTS_USER_UID},
        'audio': {'voice_type': TTS_VOICE_TYPE, 'encoding': TTS_ENCODING},
        'request': {'reqid': reqid, 'text': text[:TTS_MAX_CHARS], 'operation': 'query'},
    }
    headers = {'Authorization': f'Bearer; {cfg.VOICE_ACCESS_TOKEN}'}
    async with httpx.AsyncClient(timeout=TTS_TIMEOUT) as client:
        resp = await client.post(TTS_API_URL, json=body, headers=headers)
        if resp.status_code != 200:
            raise BusinessError(f'TTS 服务错误 {resp.status_code}', 502)
        data = resp.json()
    if data.get('code') != 3000 or not data.get('data'):
        raise BusinessError(f'TTS 合成失败: {data.get("message", "unknown")}', 502)
    return base64.b64decode(data['data'])
