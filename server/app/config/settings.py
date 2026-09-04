"""运行环境配置（pydantic-settings 读 .env）：密钥 / 数据库 / LLM 连接 / 语音凭据"""

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """环境级配置：真实值仅存服务器侧 .env，不入 git"""

    APP_SECRET_KEY: str = 'dev-secret-change-me'
    ADMIN_USER: str = 'admin'
    ADMIN_PASS: str = '***REMOVED***'

    MONGO_URI: str = 'mongodb://127.0.0.1:27018'
    MONGO_DB: str = 'jingguan'

    VOICE_APP_ID: str = ''
    VOICE_ACCESS_TOKEN: str = ''

    LLM_PLATFORM: str = 'deepseek'
    LLM_BASE_URL: str = 'https://api.deepseek.com/v1'
    LLM_API_KEY: str = ''
    LLM_MODEL: str = 'deepseek-v4-flash'

    model_config = SettingsConfigDict(env_file='.env', extra='ignore')


cfg = Settings()
