"""提示词工程统一出口：场景注册表 + 消息渲染 + 场景参数（纯函数；LLM IO 只在 services/llm_client）"""

from app.agent.prompts.registry import SCENARIOS, build_messages, scenario_params

__all__ = ['SCENARIOS', 'build_messages', 'scenario_params']
