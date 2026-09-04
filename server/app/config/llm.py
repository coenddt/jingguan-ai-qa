"""LLM 通用调用参数（场景特定参数见 agent/prompts/ 各场景的 PARAMS）"""

# 请求超时（秒）
LLM_TIMEOUT = 120

# 低层 chat 默认采样温度（场景化调用会以场景 PARAMS 覆盖）
LLM_TEMPERATURE = 0.1
