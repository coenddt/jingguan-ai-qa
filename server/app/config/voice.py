"""语音服务配置（火山 TTS）"""

# TTS 合成端点
TTS_API_URL = 'https://openspeech.bytedance.com/api/v1/tts'

# 集群 / 音色 / 编码
TTS_CLUSTER = ' volcano_tts'
TTS_VOICE_TYPE = 'zh_female_cancan'
TTS_ENCODING = 'mp3'

# 请求超时（秒）/ 单次合成文本最大长度
TTS_TIMEOUT = 15
TTS_MAX_CHARS = 1000

# 用户标识
TTS_USER_UID = 'jingguan'
