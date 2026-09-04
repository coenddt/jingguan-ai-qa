"""system prompt 组装（纯函数）：模型描述 + 输出契约 + 示例 + 可选 few-shot（文案配置见 config/prompts.py）"""

import json

from app.agent.schema_registry import describe_models
from app.config import FEW_SHOT_MAX, MODEL_JSON_EXAMPLES, RETRY_TMPL, SYSTEM_TMPL


def build_system_prompt(few_shots: list[dict] | None = None) -> str:
    models = json.dumps(describe_models(), ensure_ascii=False)
    few = ''
    if few_shots:
        lines = [f'- "{e["question"]}" → {json.dumps(e["template"], ensure_ascii=False)}' for e in few_shots[:FEW_SHOT_MAX]]
        few = '\n参考以下历史成功问法（仅作参考，仍需按当前问题生成）：\n' + '\n'.join(lines)
    return SYSTEM_TMPL.format(models=models, few_shot=few) + '\n输出示例：\n' + '\n'.join(MODEL_JSON_EXAMPLES)


def build_retry_prompt(question: str, bad_query: dict, error: str) -> str:
    return RETRY_TMPL.format(
        question=question,
        bad_query=json.dumps(bad_query, ensure_ascii=False),
        error=error,
    )
