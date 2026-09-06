"""豆包语音识别 2.0 配置（双向流式优化版 bigmodel_async，X-Api-Key 鉴权）"""

# 双向流式·优化版端点（大模型流式语音识别）
ASR_WS_URL = 'wss://openspeech.bytedance.com/api/v3/sauc/bigmodel_async'

# 资源版本：豆包流式语音识别模型 2.0 · 小时版（计费与能力随版本而定）
ASR_RESOURCE_ID = 'volc.seedasr.sauc.duration'

# 音频输入：PCM 原始采样，16000Hz / 16bit / 单声道
ASR_AUDIO = {
    'format': 'pcm',
    'codec': 'raw',
    'rate': 16000,
    'bits': 16,
    'channel': 1,
}

# 识别请求参数：书面化 / 加标点 / 语义顺滑
ASR_REQUEST = {
    'model_name': 'bigmodel',
    'enable_itn': True,
    'enable_punc': True,
    'enable_ddc': True,
}

# 分包间隔（秒）：期望上行音频分包约 100~200ms，PCM 16k/16bit/mono ≈ 3200B/100ms
ASR_PACKET_SEC = 0.1