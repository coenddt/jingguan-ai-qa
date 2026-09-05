# LLM 壳（JSON Schema 结构校验）落地执行文档

> 日期: 2026-09-05
> 设计依据: doc/solution/2026/09/已完成-LLM外置JSONSchema壳-方案.md
> 性质: 代码执行文档（AI 照此执行；含代码自检 / 部署 / 测试 / 测试报告）

## 1. 目标（验收标准）

1. 新增独立壳模块 `json_schema_shell`，仅做**结构**校验（必填/类型/枚举/未定义键），不入业务语义（语义仍归 query_guard）。
2. `llm_client.invoke()` 完成浅层挂载：入口 `attach_schema`、出口 `validate`；`chat()` 零改动。结构越界抛 `ShellError`，**不允许**穿透到 query_guard。
3. query_gen 场景结构越界时：候选管道丢弃该候选（`empty`），串行重试能捕获 `ShellError` 并自动反馈、回传 LLM 重试，**不产生 500**。
4. 前缀缓存不失效：改造后生产实测 query_gen 候选 `cache_hit_tokens > 0`（与改造前量级相当）。
5. **代码自检全绿**：改动三文件 py_compile + 模块加载零错误；壳 `validate` 本地正反例全过。
6. **云端链路测试通过**：问数自然语言提问正常出结构化卡片；结构拦截不 500、有自动反馈。
7. **产出测试报告**：测试用例/结果沉淀至 `doc/test-report/2026/09/`，每例标注通过/失败及证据。

## 2. 涉及端 × 角色

| 端 | 是否涉及 | 角色 | 说明 |
|---|---|---|---|
| server/app（FastAPI 服务端·经管之星） | 是 | admin | 壳模块 + invoke 挂载 + qa_service 捕获/反馈 |
| miniapp / web-saas 前端 | 否 | - | 错误语义不变，前端无改动 |

## 3. 迁移与移除清单（动手清单）

### 3.1 新增清单

| 新增项 | 所在文件 | 说明 |
|---|---|---|
| json_schema_shell 模块 | server/app/services/json_schema_shell.py | 壳：OUTPUT_SCHEMAS 注册表 + attach_schema + validate + ShellError |

### 3.2 修改清单

| 修改项 | 文件 | 由 → 到 |
|---|---|---|
| invoke() 浅层挂载 | server/app/services/llm_client.py | 不挂载 → 入口 attach_schema、出口 validate |
| 导入 ShellError | server/app/services/qa_service.py | 顶部 import 增加 |
| 重试 except 元组 | server/app/services/qa_service.py | `(GuardError, BusinessError, RuntimeError, TimeoutError)` → 加入 `ShellError` |
| 串行重试 ShellError 自动反馈 | server/app/services/qa_service.py | 无 → except 内 ShellError 分支调 auto_feedback.record |

### 3.3 删除清单

无。

## 4. 详细执行契约（代码优先）

### 4.1 新增 `server/app/services/json_schema_shell.py`

```python
"""JSON Schema 壳（结构校验前置层，纯函数，无 IO）

在唯一 LLM 出口（llm_client.invoke）做浅层挂载：
- 入口 attach_schema()：把场景输出 json schema 固化为一条恒定 system，追加到消息末尾
- 出口 validate()：对 LLM 产出的结构化对象做结构硬校验，失败抛 ShellError

与 query_guard 分层：本壳只管"结构"（必填 / 类型 / 枚举 / 未定义键），
不管"语义"（模型/字段/操作符白名单、limit 上限）——语义权威仍是 query_guard。

前缀缓存注意：schema 消息追加在庞大 system 模板之后，各调用共享该公共前缀，
不破坏 query_candidate 的前缀预热 / 前缀缓存（配置文件勿改 schema 加进可变文案）。
"""

import json
from typing import Any


class ShellError(Exception):
    """结构校验拒绝（结构层守卫）；路由层/调用方按需捕获并自动反馈"""


# 场景输出 schema（仅结构约束）。key = scenario_id；值 = 极简 JSON Schema 子集。
# 注意：变更 schema 会影响恒定前缀的缓存重建成本，需评估后再改。
OUTPUT_SCHEMAS: dict[str, dict] = {
    'query_gen': {
        'type': 'object',
        'required': ['mode', 'model'],
        'properties': {
            'mode': {'type': 'string', 'enum': ['query', 'aggregate']},
            'model': {'type': 'string'},
            'condition': {'type': 'object'},
            'fields': {'type': 'array', 'items': {'type': 'string'}},
            'sort': {'type': 'object'},
            'limit': {'type': 'integer'},
            'groupBy': {'type': 'array', 'items': {'type': 'string'}},
            'measures': {
                'type': 'array',
                'items': {
                    'type': 'object',
                    'required': ['op', 'field'],
                    'properties': {
                        'op': {'type': 'string'},
                        'field': {'type': 'string'},
                    },
                    'additionalProperties': False,
                },
            },
        },
        'additionalProperties': False,
    },
}

# 模块加载期把 schema 固化为恒定文本，保证前缀缓存稳定
_SCHEMA_MESSAGES: dict[str, str] = {
    sid: json.dumps(schema, ensure_ascii=False) for sid, schema in OUTPUT_SCHEMAS.items()
}

# JSON Schema 子集 → Python 类型
_TYPE_MAP = {'object': dict, 'array': list, 'string': str, 'integer': int}


def attach_schema(messages: list[dict], scenario_id: str) -> list[dict]:
    """入口挂载：有注册 schema 则追加一条恒定 system；无则原样返回（浅层挂载，不进 user 文案）"""
    text = _SCHEMA_MESSAGES.get(scenario_id)
    if text is None:
        return messages
    return [*messages, {'role': 'system', 'content': text}]


def _fail(path: str, reason: str) -> None:
    raise ShellError(f'查询结构校验失败 @ {path or "root"}：{reason}')


def _check(value: Any, spec: dict, path: str) -> None:
    """按 spec 递归校验单节点结构；任何不符抛 ShellError（结构层，非语义）"""
    want = _TYPE_MAP.get(spec.get('type'))
    enum = spec.get('enum')

    if want is not None:
        # integer 排除 bool（Python 中 bool 是 int 子类，需单独排除）
        if not isinstance(value, want) or (spec.get('type') == 'integer' and isinstance(value, bool)):
            _fail(path, f'应为 {spec.get("type")}，实为 {type(value).__name__}')
    if enum is not None and value not in enum:
        _fail(path, f'不在枚举内: {value!r}，可选 {enum}')

    if spec.get('type') == 'object':
        props = spec.get('properties') or {}
        required = spec.get('required') or []
        if spec.get('additionalProperties') is False:
            unknown = [k for k in value if k not in props]
            if unknown:
                _fail(path, f'含未定义键: {unknown}（仅允许 {",".join(props)}）')
        for k in required:
            if k not in value or value[k] is None:
                _fail(f'{path}.{k}', '缺失必填字段')
        for k, v in value.items():
            if k in props:
                _check(v, props[k], f'{path}.{k}')
    elif spec.get('type') == 'array':
        items = spec.get('items') or {}
        for i, item in enumerate(value):
            _check(item, items, f'{path}[{i}]')


def validate(parsed: Any, scenario_id: str) -> Any:
    """出口硬校验：未注册场景直通；注册场景递归结构校验，失败抛 ShellError（允许被拦、禁止静默）"""
    schema = OUTPUT_SCHEMAS.get(scenario_id)
    if schema is None:
        return parsed
    if not isinstance(parsed, dict):
        raise ShellError(f'查询结构校验失败：应为 JSON 对象，实为 {type(parsed).__name__}')
    _check(parsed, schema, 'query')
    return parsed
```

### 4.2 修改 `server/app/services/llm_client.py` invoke()

当前位置（L99-114）整体替换为：

```python
async def invoke(scenario_id: str, variables: dict, model_conf: dict) -> tuple[dict | str, dict]:
    """场景化通用调用（平台 → 模型 → 场景）：
    提示词与参数来自 agent/prompts 注册表，平台/模型来自 AiModel 配置。
    JSON Schema 壳在唯一 LLM 出口做浅层挂载：入口注入 schema、出口结构校验（失败抛 ShellError）。
    返回 (json 场景为解析后的对象，否则为原文, meta)。"""
    params = scenario_params(scenario_id)
    messages = json_schema_shell.attach_schema(build_messages(scenario_id, variables), scenario_id)
    ret = await chat(
        messages,
        base_url=resolve_base_url(model_conf['platform'], model_conf.get('baseUrl')),
        api_key=model_conf.get('apiKey'),
        model=model_conf.get('modelName'),
        temperature=params['temperature'],
        max_tokens=params.get('max_tokens'),
        thinking=params.get('thinking'),
    )
    if params['json']:
        return json_schema_shell.validate(extract_json(ret['content']), scenario_id), ret
    return ret['content'], ret
```

文件顶部（L15 附近）import 增加一行：

```python
from app.services import json_schema_shell
```

顺序不变：`extract_json` 先解析（非 JSON 抛 ValueError），`json_schema_shell.validate` 再做结构校验（越界抛 ShellError）。错误信息为可喂回式（缺失/枚举/类型），供重试自纠。

### 4.3 修改 `server/app/services/qa_service.py`

(a) import（L22 附近 `from app.services import auto_feedback, llm_client, query_cache, query_candidate, query_executor`）后追加：

```python
from app.services.json_schema_shell import ShellError
```

(b) 串行回传重试 except 元组（L252）与 ShellError 自动反馈。原：

```python
                    except (GuardError, BusinessError, RuntimeError, TimeoutError) as e:
                        last_err = str(e)
                        if attempt == q_params['retries'] - 1:
                            raise BusinessError(f'查询生成失败：{last_err}', 422)
```

改为：

```python
                    except (GuardError, ShellError, BusinessError, RuntimeError, TimeoutError) as e:
                        last_err = str(e)
                        if isinstance(e, ShellError):
                            # 结构层拦截被反复触发 → 自动反馈（允许被拦，禁止静默）
                            await auto_feedback.record(
                                category='shell',
                                trigger_point='query_gen_shell_validation',
                                reason=last_err,
                                layer='外置JSONSchema壳-结构校验拦截',
                                upstream='LLM 产出结构越界，未达 query_guard',
                                fix_hint='按 reason 定位结构偏差并回传重试；必要时评估修正 OUTPUT_SCHEMAS 后回放验证',
                                question=question, query_raw=base_bad)
                        if attempt == q_params['retries'] - 1:
                            raise BusinessError(f'查询生成失败：{last_err}', 422)
```

`base_bad` 在 L230 已定义于该循环前，作用域可用。候选管道 `query_candidate._one` 用宽 except，`ShellError` 自动把该候选置为 `empty`，无需改 query_candidate.py。

## 5. 代码自检规范（改完代码必做）

> 依据 testing-rules：本地仅静态自检 + 纯函数验证；完整链路验证一律走云端。

| # | 检查项 | 命令/验证 | 预期 |
|---|---|---|---|
| A1 | 壳模块语法 | `python -m py_compile server/app/services/json_schema_shell.py` | 0 退出 |
| A2 | llm_client 语法 | `python -m py_compile server/app/services/llm_client.py` | 0 退出 |
| A3 | qa_service 语法 | `python -m py_compile server/app/services/qa_service.py` | 0 退出 |
| A4 | 模块加载无环/无误 | `python -c "import app.services.json_schema_shell; import app.services.llm_client; import app.services.qa_service"` | 无 ImportError |
| A5 | validate 正例（本地纯函数） | `python -c "from app.services.json_schema_shell import validate; from app.services.query_guard import verify; q={'mode':'aggregate','model':'ReportOverall','condition':{'year':{'$eq':2026}},'groupBy':['unit'],'measures':[{'op':'sum','field':'income'}],'sort':{'sum_income':-1},'limit':10}; assert validate(q,'query_gen')==q; assert verify(q)['mode']=='aggregate'"` | 通过且不抛 | 
| A6 | validate 反例串（本地纯函数逐条断言抛 ShellError） | 见下方反例脚本，覆盖：缺 mode / 缺 model / 多未定义键 / mode 枚举外 / limit 类型错(bool) / measures 缺 field / measures[0].op 枚举外 / 非对象 | 每条均抛 ShellError，error 信息含路径+原因 |
| A7 | attach_schema 恒定性 | `python -c "from app.services.json_schema_shell import attach_schema; m1=attach_schema([{'role':'system','content':'S'}],'query_gen'); m2=attach_schema([{'role':'system','content':'S'}],'query_gen'); assert m1==m2; assert m1[-1]['content']==m2[-1]['content']"` | 等值（前缀稳定） |
| A8 | 未注册场景直通 | `python -c "from app.services.json_schema_shell import attach_schema, validate; ms=[{'role':'system','content':'S'}]; assert attach_schema(ms,'conclusion')==ms; assert validate({'text':'t','follow_ups':['a']},'conclusion')=={'text':'t','follow_ups':['a']}"` | 原样返回 |

**A6 反例脚本**（存入 `tmp/` 运行，用后即删）：

```python
from app.services.json_schema_shell import validate, ShellError

valid = {'mode':'aggregate','model':'ReportOverall','condition':{'year':{'$eq':2026}},
         'groupBy':['unit'],'measures':[{'op':'sum','field':'income'}],'sort':{'sum_income':-1},'limit':10}
cases = {
    '缺mode':    {**valid, 'mode': None},
    '缺model':   {**valid, 'model': None},
    '多未定义键': {**valid, 'xx': 1},
    'mode枚举外': {**valid, 'mode': 'select'},
    'limit类型错':{**valid, 'limit': '50'},
    'bool算integer': {**valid, 'limit': True},
    'measures缺field': {**valid, 'measures': [{'op':'sum'}]},
    'measures缺op':    {**valid, 'measures': [{'field':'income'}]},
    'measures未知键':  {**valid, 'measures': [{'op':'sum','field':'income','zz':1}]},
    '非对象':  'not a dict',
}
ok = 0
for name, obj in cases.items():
    try:
        validate(obj, 'query_gen')
        print(f'FAIL {name}: 未抛 ShellError')
    except ShellError as e:
        ok += 1
        print(f'PASS {name}: {e}')
assert ok == len(cases), f'仅 {ok}/{len(cases)} 通过'
print(f'反例全部拦截 OK {ok}/{len(cases)}')
```

## 6. 部署（仅云端 <user> 账号）

> 依据 deploy-rules / ssh-server-task：常驻演示实例只在服务器 `<user>` 账号 pm2 管理，**严禁本地起常驻**。服务器 `<user>@<SERVER_IP>`，部署路径 `/home/<user>/jingguan/api`。

| # | 操作 | 命令/说明 | 验证 |
|---|---|---|---|
| D1 | 上传改动文件 | `scp server/app/services/json_schema_shell.py server/app/services/llm_client.py server/app/services/qa_service.py <user>@<SERVER_IP>:/home/<user>/jingguan/api/server/app/services/`（qa_service 到 services 目录，注意路径与远程仓库结构一致） | scp 成功 |
| D2 | SCP 前先核对远程目录结构 | `ssh <user>@<SERVER_IP> "ls /home/<user>/jingguan/api"` 确认 services 模块实际挂载路径，必要时再上传到 `api/app/` | 路径匹配 |
| D3 | 重启对应 pm2 服务 | `ssh <user>@<SERVER_IP> "cd /home/<user>/jingguan/api && pm2 restart <服务名>"`（服务名以远程 pm2 list 为准） | pm2 重启成功、无退出 |
| D4 | 看启动日志 | `ssh <user>@<SERVER_IP> "pm2 logs <服务名> --lines 80"` | 无 ImportError / ShellError 启动报错 |
| D5 | curl 线上端口 | `curl http://<SERVER_IP>:<端口>/health` 或对应健康端点 | 200 |
| D6 | 收尾 | `git status` 确认无临时文件残留；`tmp/` 含密码的 SSH 脚本用完即删 | 干净 |

## 7. 测试（云端走问数链路）

> 依据 testing-rules / server-testing：完整功能验证在云端；测试数据用完即删。

| # | 用例 | 操作/观察 | 预期 |
|---|---|---|---|
| T1 | 结构合法 query_gen（冷问） | 线上自然语言提问（如"2026年各经营单元收入排名"） | 正常出结构化卡片（分析过程+表格+图表+结论），不 500 |
| T2 | 重复问（tier=exact） | 紧接 T1 再问同一句 | 命中缓存、复用模板，耗时显著缩短 |
| T3 | 前缀缓存红线 | T1/T2 日志看 `ask_candidates` 的 cache_hit | `cache_hit > 0`（证明 schema 追加未破坏前缀缓存） |
| T4 | aggregate 问法 | 问汇总/收入类 | 出聚合卡片，mode=aggregate 正常 |
| T5 | 结构拦截不 500（可选一次） | 触发一次结构越界（见步骤 S7） | 候选 empty + 串行重试入 ShellError 分支 + 出 `shell` 自动反馈，最终 422 而非 500 |
| T6 | conclusion 直通回归 | 结论卡片正常展示 text + follow_ups | conclusion 未被壳误伤（未注册直通） |
| T7 | 测试数据清理 | 临时会话/临时记录用后即删 | 无残留 |

## 8. 测试报告（产出）

执行完成后，把代码自检 + 部署 + 测试结果沉淀为报告，存入 `doc/test-report/2026/09/`，文件名 `已完成-LLM外置JSONSchema壳-测试报告.md`。报告模板：

```markdown
# LLM 外置 JSON Schema 壳 测试报告

> 日期: <YYYY-MM-DD>
> 依据: doc/execution/2026/09/已完成-LLM外置JSONSchema壳落地-执行.md

## 1. 测试环境
- 服务器: <user>@<SERVER_IP>（<IP>）
- 服务名 / 部署路径: <服务名> / /home/<user>/jingguan/api
- 涉及代码版本: json_schema_shell.py / llm_client.py / qa_service.py 改动内容哈希或 diff 摘要

## 2. 代码自检结果（引用 execution 第5章 A1-A8）
| 项 | 结果 | 证据 |
|----|------|------|
| A1-A4 语法/模块加载 | ✅ / ❌ | 命令输出摘要 |
| A5 正例 | ✅ / ❌ | 通过/抛出内容 |
| A6 反例(10类) | ✅ xx/10 | 各自 PASS/FAIL 输出 |
| A7 恒定性 | ✅ / ❌ | - |
| A8 未注册直通 | ✅ / ❌ | - |

## 3. 部署结果（引用 execution 第6章 D1-D6）
| 项 | 结果 | 证据 |
|----|------|------|
| D1-D2 上传 | ✅ / ❌ | 路径 |
| D3-D4 pm2 重启/日志 | ✅ / ❌ | 启动日志摘录 |
| D5 curl 线上 | ✅ / ❌ | HTTP 状态码 |

## 4. 测试结果（引用 execution 第7章 T1-T7）
| # | 用例 | 结果 | 关键日志/证据 | 备注 |
|---|------|------|---------------|------|
| T1 | 冷问结构合法 | | | |
| T2 | 重复问 exact | | | |
| T3 | 前缀缓存 cache_hit | | | 红线 |
| T4 | aggregate 问法 | | | |
| T5 | 结构拦截不500 | | | 触发方式记录 |
| T6 | conclusion 直通 | | | |
| T7 | 测试数据清理 | | | |

## 5. 结论与遗留
- 是否达成 execution 第1章全部 7 项目标（逐条 ✅/❌）
- 遗留问题 / 待观察项（如一轮通过率、拦截率）
- 中止/继续建议
```

## 9. 执行步骤（逐步骤状态，可中断续做）

| 步骤 | 状态 | 详细说明 | 关联节 |
|---|---|---|---|
| 1. 新增壳模块 | [ ] 待处理 | 按 4.1 新建 `server/app/services/json_schema_shell.py`（完整代码）。 | 4.1 |
| 2. 修改 llm_client | [ ] 待处理 | 按 4.2 加 import + invoke 入口 attach_schema + 出口 validate；chat() 不改。 | 4.2 |
| 3. 修改 qa_service | [ ] 待处理 | 按 4.3(a) import ShellError；4.3(b) 改 except 元组 + ShellError 自动反馈分支。 | 4.3 |
| 4. 代码自检（本地） | [ ] 待处理 | 跑第 5 章 A1-A8；A6 反例脚本写入 `tmp/` 运行后即删。 | 5 |
| 5. 云端部署 | [ ] 待处理 | 按第 6 章 D1-D6 scp + pm2 重启 + curl + 日志确认。 | 6 |
| 6. 云端链路测试 | [ ] 待处理 | 按第 7 章 T1-T7 逐条过，采集日志证据。 | 7 |
| 7. 结构拦截专项 | [ ] 待处理 | （T5）构造一次结构越界，验证 empty + ShellError 分支 + 自动反馈 + 非500。 | 7 |
| 8. 出测试报告 | [ ] 待处理 | 按第 8 章模板产出 `doc/test-report/2026/09/已完成-LLM外置JSONSchema壳-测试报告.md`。 | 8 |

状态迁移：开始执行 → 重命名 `处理中-`；每完成一步勾 `[x]`；全部（含报告）完成 → 重命名 `已完成-`。

## 10. 实施顺序（阶段依赖）

| 阶段 | 内容 | 依赖 |
|---|---|---|
| 1（步骤1） | 壳模块 | 无 |
| 2（步骤2-3） | 挂载 + 捕获 | 步骤1 |
| 3（步骤4） | 代码自检 | 步骤2-3 |
| 4（步骤5） | 云端部署 | 步骤4 |
| 5（步骤6-8） | 云测 + 拦截专项 + 报告 | 步骤5 |

## 11. 禁止事项

❌ 禁止改 `chat()`（LLM 调用核心必须零感知）
❌ 禁止在壳里做语义白名单校验（模型/字段/算子/limit 上限归 query_guard）
❌ 禁止把 schema 写进 user 消息或可变文案（破坏前缀缓存红线）
❌ 禁止漏改 qa_service 的 except 元组（漏则结构越界 500）
❌ 禁止为 conclusion 等未注册场景强开壳（未注册必须直通）
❌ 禁止引第三方 jsonschema 依赖（轻量自写校验，保持零依赖）
❌ 禁止本地启动常驻服务（一律云端 <user> + pm2）
❌ 禁止漏跑代码自检 A1-A8 就上云；禁止不产测试报告就收尾
❌ 禁止把 `.env`（密钥/连接串）提交入库；临时含密码 SSH 脚本用完即删

## 12. 注意事项

1. `OUTPUT_SCHEMAS` 的恒定前缀影响缓存，改 schema 需评估重建成本并在服务器验证 cache_hit。
2. mode 枚举收紧为 `{query, aggregate}`：model 示例均用这两值，通过率风险低；若上线后 query_gen 一轮通过率下降，优先查壳拦截信息可读性，再考虑放宽。
3. 未注册场景直通，diff 行为为 0，灰度为低。
4. 测试用例数据（临时会话/记录）用完即删；测试报告保留入库。
5. 自动反馈遵循"允许被拦、禁止静默"——结构拦截必须能查到 reason 与 trigger_point。
6. 上传前先核对远程仓库真实模块路径（`ls /home/<user>/jingguan/api`），避免 scp 落错目录导致 ImportError。