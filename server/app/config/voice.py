"""语音服务配置（火山 TTS v3 大模型语音合成，X-Api-Key 鉴权）"""

# TTS 合成端点（v3 HTTP 单向流式）
TTS_API_URL = 'https://openspeech.bytedance.com/api/v3/tts/unidirectional'

# 资源版本（决定计费与可用音色：seed-tts-2.0 仅支持 2.0 音色）
TTS_RESOURCE_ID = 'seed-tts-2.0'

# 音色 / 音频参数
TTS_VOICE_TYPE = 'zh_female_vv_uranus_bigtts'
TTS_AUDIO_FORMAT = 'mp3'
TTS_SAMPLE_RATE = 24000

# 请求超时（秒）/ 单次合成文本最大长度
TTS_TIMEOUT = 30
TTS_MAX_CHARS = 1000

# 用户标识
TTS_USER_UID = 'jingguan'
