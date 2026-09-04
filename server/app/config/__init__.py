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
- app_defaults.py  前台应用默认配置（AppConfig）
"""

from .app_defaults import APP_CONFIG_DEFAULTS
from .auth import TOKEN_TTL
from .cache import FUZZY_MIN_SCORE, FUZZY_TOP_K, SIM_JACCARD_W, SIM_LEV_W
from .llm import LLM_TEMPERATURE, LLM_TIMEOUT
from .qa import (
    QA_CHART, QA_CONCLUSION_ROWS, QA_FOLLOW_UPS, QA_HOT_LIMIT, QA_NUMERIC_FIELDS,
    QA_PRESET_HOT, QA_SOURCES, QA_TIME_DIMS, QA_TITLE_MAX,
)
from .query_policy import ALLOWED_MEASURES, ALLOWED_OPS, EXEC_TIMEOUT, MAX_LIMIT, NUMERIC_TYPES
from .server import APP_TITLE, CORS_ORIGINS
from .settings import cfg
from .voice import TTS_API_URL, TTS_CLUSTER, TTS_ENCODING, TTS_MAX_CHARS, TTS_TIMEOUT, TTS_USER_UID, TTS_VOICE_TYPE

__all__ = [
    'cfg',
    'APP_TITLE', 'CORS_ORIGINS',
    'TOKEN_TTL',
    'QA_SOURCES', 'QA_PRESET_HOT', 'QA_HOT_LIMIT', 'QA_TITLE_MAX', 'QA_NUMERIC_FIELDS',
    'QA_TIME_DIMS', 'QA_CHART', 'QA_CONCLUSION_ROWS', 'QA_FOLLOW_UPS',
    'ALLOWED_OPS', 'ALLOWED_MEASURES', 'NUMERIC_TYPES', 'MAX_LIMIT', 'EXEC_TIMEOUT',
    'SIM_JACCARD_W', 'SIM_LEV_W', 'FUZZY_MIN_SCORE', 'FUZZY_TOP_K',
    'LLM_TIMEOUT', 'LLM_TEMPERATURE',
    'TTS_API_URL', 'TTS_CLUSTER', 'TTS_VOICE_TYPE', 'TTS_ENCODING', 'TTS_TIMEOUT',
    'TTS_MAX_CHARS', 'TTS_USER_UID',
    'APP_CONFIG_DEFAULTS',
]
