"""全工程配置中心（唯一配置出口）：外部模块一律 from app.config import ...

目录即配置索引：
- settings.py      运行环境配置（pydantic-settings 读 .env，密钥/数据库/LLM 连接/语音凭据）
- server.py        服务元信息与 CORS
- auth.py          认证策略
- qa.py            问数业务（数据源/预置热问/结果加工口径）
- query_policy.py  查询安全与执行策略（守卫白名单/行数上限/执行超时）
- cache.py         问法缓存参数（相似度权重/阈值/条数）
- llm.py           LLM 通用调用参数（超时/默认温度；场景参数见 agent/prompts）
- voice.py         语音 TTS
- voice_asr.py     豆包语音识别 2.0（ASR）
- app_defaults.py  前台应用默认配置（AppConfig）
"""

from .app_defaults import APP_CONFIG_DEFAULTS
from .auth import TOKEN_TTL
from .cache import FUZZY_MIN_SCORE, FUZZY_TOP_K, SIM_JACCARD_W, SIM_LEV_W
from .llm import LLM_TEMPERATURE, LLM_TIMEOUT
from .qa import (
    QA_CHART,
    QA_CONCLUSION_ROWS,
    QA_FOLLOW_UPS,
    QA_HOT_FUZZY_SCORE,
    QA_HOT_LIMIT,
    QA_NUMERIC_FIELDS,
    QA_PREHEAT_ENABLED,
    QA_PRESET_HOT,
    QA_QUERY_CANDIDATE_CONCURRENCY,
    QA_QUERY_CANDIDATES,
    QA_SOURCES,
    QA_TIER,
    QA_TIME_DIMS,
    QA_TITLE_MAX,
)
from .query_policy import (
    ALLOWED_MEASURES,
    ALLOWED_OPS,
    DENIED_OPS,
    EXEC_TIMEOUT,
    MAX_LIMIT,
    NUMERIC_TYPES,
)
from .server import APP_TITLE, CORS_ORIGINS
from .settings import cfg, validate_security
from .voice import (
    TTS_API_URL,
    TTS_AUDIO_FORMAT,
    TTS_MAX_CHARS,
    TTS_RESOURCE_ID,
    TTS_SAMPLE_RATE,
    TTS_TIMEOUT,
    TTS_USER_UID,
    TTS_VOICE_TYPE,
)
from .voice_asr import (
    ASR_AUDIO,
    ASR_PACKET_SEC,
    ASR_REQUEST,
    ASR_RESOURCE_ID,
    ASR_WS_URL,
)

__all__ = [
    'ALLOWED_MEASURES',
    'ALLOWED_OPS',
    'APP_CONFIG_DEFAULTS',
    'APP_TITLE',
    'ASR_AUDIO',
    'ASR_PACKET_SEC',
    'ASR_REQUEST',
    'ASR_RESOURCE_ID',
    'ASR_WS_URL',
    'CORS_ORIGINS',
    'DENIED_OPS',
    'EXEC_TIMEOUT',
    'FUZZY_MIN_SCORE',
    'FUZZY_TOP_K',
    'LLM_TEMPERATURE',
    'LLM_TIMEOUT',
    'MAX_LIMIT',
    'NUMERIC_TYPES',
    'QA_CHART',
    'QA_CONCLUSION_ROWS',
    'QA_FOLLOW_UPS',
    'QA_HOT_FUZZY_SCORE',
    'QA_HOT_LIMIT',
    'QA_NUMERIC_FIELDS',
    'QA_PREHEAT_ENABLED',
    'QA_PRESET_HOT',
    'QA_QUERY_CANDIDATES',
    'QA_QUERY_CANDIDATE_CONCURRENCY',
    'QA_SOURCES',
    'QA_TIER',
    'QA_TIME_DIMS',
    'QA_TITLE_MAX',
    'SIM_JACCARD_W',
    'SIM_LEV_W',
    'TOKEN_TTL',
    'TTS_API_URL',
    'TTS_AUDIO_FORMAT',
    'TTS_MAX_CHARS',
    'TTS_RESOURCE_ID',
    'TTS_SAMPLE_RATE',
    'TTS_TIMEOUT',
    'TTS_USER_UID',
    'TTS_VOICE_TYPE',
    'cfg',
    'validate_security',
]
