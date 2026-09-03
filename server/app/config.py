from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """全工程唯一配置入口（pydantic-settings 读 .env）"""

    APP_SECRET_KEY: str = 'dev-secret-change-me'
    ADMIN_USER: str = 'admin'
    ADMIN_PASS: str = '***REMOVED***'

    MONGO_URI: str = 'mongodb://127.0.0.1:27018'
    MONGO_DB: str = 'jingguan'

    VOICE_APP_ID: str = ''
    VOICE_ACCESS_TOKEN: str = ''
    SYS_HOT_THRESHOLD: int = 3

    LLM_BASE_URL: str = 'https://api.deepseek.com/v1'
    LLM_API_KEY: str = ''
    LLM_MODEL: str = 'deepseek-v4-flash'

    model_config = SettingsConfigDict(env_file='.env', extra='ignore')


cfg = Settings()
