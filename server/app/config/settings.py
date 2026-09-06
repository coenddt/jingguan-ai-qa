"""运行环境配置（pydantic-settings 读 .env）：密钥 / 数据库 / LLM 连接 / 语音凭据"""

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """环境级配置：真实值仅存服务器侧 .env，不入 git；密钥缺失/泄露默认值 → 启动即拒"""

    # 密钥/凭据一律无默认值（空串）：迫使 .env 显式配置，防默认密钥带病上线
    APP_SECRET_KEY: str = ''
    ADMIN_USER: str = 'admin'
    ADMIN_PASS: str = ''

    MONGO_URI: str = 'mongodb://127.0.0.1:27018'
    MONGO_DB: str = 'jingguan'

    # 火山 TTS（新版控制台 API Key，仅 Key 参与鉴权；应用名仅控制台标识不入程序）
    VOICE_API_KEY: str = ''

    # 火山豆包语音识别 2.0（新版控制台 API Key，与 TTS 用途分开，仅服务器 .env 配置）
    ASR_API_KEY: str = ''

    LLM_PLATFORM: str = 'deepseek'
    LLM_BASE_URL: str = 'https://api.deepseek.com/v1'
    LLM_API_KEY: str = ''
    LLM_MODEL: str = 'deepseek-v4-flash'

    # HTTPS 部署后置 true：登录 Cookie 加 Secure 标志（HTTP 期间保持 false）
    COOKIE_SECURE: bool = False

    model_config = SettingsConfigDict(env_file='.env', extra='ignore')


cfg = Settings()

# 历史泄露黑名单（值曾入 git 历史，视为公开）：命中即拒启动，强制轮换
_BURNED_SECRET = 'dev-secret-change-me'
_BURNED_PASS = '***REMOVED***'


def validate_security() -> None:
    """安全基线自检（main.lifespan 首步调用）：密钥/管理员密码缺失或仍为已知泄露值 → 拒绝启动"""
    if not cfg.APP_SECRET_KEY or cfg.APP_SECRET_KEY == _BURNED_SECRET:
        raise RuntimeError('APP_SECRET_KEY 未配置或仍为默认值：请在 .env 配置随机 64 位 hex（拒绝带默认密钥启动）')
    if not cfg.ADMIN_PASS or cfg.ADMIN_PASS == _BURNED_PASS:
        raise RuntimeError('ADMIN_PASS 未配置或仍为历史泄露默认值：请在 .env 轮换管理员密码（拒绝带泄露密码启动）')
