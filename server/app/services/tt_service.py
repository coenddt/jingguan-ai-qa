"""火山 TTS 代理（HTTP 合成，返回音频 bytes）"""

import base64
import uuid

import httpx

from app.config import cfg
from app.errors import BusinessError

TTS_URL = 'https://openspeech.bytedance.com/api/v1/tts'


async def synthesize(text: str) -> bytes:
    if not cfg.VOICE_APP_ID or not cfg.VOICE_ACCESS_TOKEN:
        raise BusinessError('TTS 未配置（VOICE_APP_ID/VOICE_ACCESS_TOKEN 缺失）', 400)
    reqid = uuid.uuid4().hex
    body = {
        'app': {'appid': cfg.VOICE_APP_ID, 'token': 'access_token', 'cluster': ' volcano_tts'},
        'user': {'uid': 'jingguan'},
        'audio': {'voice_type': 'zh_female_cancan', 'encoding': 'mp3'},
        'request': {'reqid': reqid, 'text': text[:1000], 'operation': 'query'},
    }
    headers = {'Authorization': f'Bearer; {cfg.VOICE_ACCESS_TOKEN}'}
    async with httpx.AsyncClient(timeout=15) as client:
        resp = await client.post(TTS_URL, json=body, headers=headers)
        if resp.status_code != 200:
            raise BusinessError(f'TTS 服务错误 {resp.status_code}', 502)
        data = resp.json()
    if data.get('code') != 3000 or not data.get('data'):
        raise BusinessError(f'TTS 合成失败: {data.get("message", "unknown")}', 502)
    return base64.b64decode(data['data'])
