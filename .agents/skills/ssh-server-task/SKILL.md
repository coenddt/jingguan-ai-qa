---
name: "ssh-server-task"
description: "SSH 登录远程服务器执行任务（免密优先，密码兜底）。当需要 SSH 到服务器执行命令、排查问题、sudo 操作时调用。本项目服务器：<SERVER_IP>，专用账号 <user>（sudo 组）。"
---

# SSH Server Task（航空卫星项目）

## 核心概念

先生成本地脚本（Python/Node.js）→ 执行 → 执行完毕即删除脚本（清除密码）。

## 服务器信息

| 项 | 值 |
|----|-----|
| IP | `<SERVER_IP>` |
| 端口 | `22` |
| **本项目账号** | `<user>`（专用，uid 1004，sudo 组，家目录 `/home/<user>`，2026-09-03 创建） |
| 同机其他账号 | `coen-user`（绘画集项目）、`ecs-user`（生活助手项目）——**严禁误碰**；`sattc` 为本项目旧账号（已停用，仅紧急兜底） |
| 免密 | 本机 `~/.ssh/id_rsa` 公钥已装入 <user> 的 `authorized_keys`，可 `ssh <user>@<SERVER_IP>` 直接免密 |
| 密码兜底 | <user> 密码存于本目录 [.env](.env)（`AICC_PASSWORD`），**严禁写入文档/代码/提交入库** |

> **优先用免密**：密码认证仅作兜底（公钥失效时）或 `sudo -S` 输密码用。

## 执行流程

### 1. 解析输入

从用户消息/任务描述提取：`host`（默认 <SERVER_IP>）、`user`（默认 <user>）、`password`（默认取 .env）、`task`。

### 2. 选择脚本语言

| 语言 | 库 | 安装 |
|------|-----|------|
| **Python**（首选，本机已装 3.14 + paramiko 5.0） | `paramiko` | `pip install paramiko` |
| **Node.js**（备选） | `ssh2` | `npm install -g ssh2` |

### 3. 生成本地脚本

脚本统一写到项目根 `tmp/`（已 gitignore），命名如 `tmp/ssh_task_xxx.py`：

```python
#!/usr/bin/env python3
import paramiko, sys

HOST = "<SERVER_IP>"
USER = "<user>"
PASSWORD = "<免密可用时省略；需要时从 .agents/skills/ssh-server-task/.env 读取>"
PORT = 22

def run(client, cmd, label=None, input_text=None):
    if label: print(f"\n===== {label} =====")
    stdin, stdout, stderr = client.exec_command(cmd, timeout=30)
    if input_text is not None:              # sudo -S 场景：密码走 stdin
        stdin.write(input_text + "\n")
        stdin.channel.shutdown_write()
    out, err = stdout.read().decode(), stderr.read().decode()
    if out: print(out.strip())
    if err: print(f"[STDERR] {err.strip()}", file=sys.stderr)

def main():
    client = paramiko.SSHClient()
    client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
    client.connect(HOST, port=PORT, username=USER, password=PASSWORD, timeout=10)
    run(client, 'df -h', '磁盘使用情况')
    client.close()

if __name__ == '__main__':
    main()
```

### 4. 执行并清理

```bash
python tmp/<脚本>.py
# 执行完毕后必须立即删除脚本文件（清除密码）
```

## sudo 使用

- <user> 在 sudo 组（`(ALL:ALL) ALL`），sudo 需输密码：`echo '<AICC_PASSWORD>' | sudo -S <cmd>`
- 或脚本内 `run(client, f"echo '{PASSWORD}' | sudo -S bash -c '...'", label, input_text=PASSWORD)`
- 家目录为 0700，其他账号（含 sattc）无法直读 <user> 文件；读 <user> 自有文件需 `sudo -iu <user>` 或 sudo bash
- **部署相关 sudo 操作限于 <user> 自身环境**（如 pm2 startup、安装依赖），严禁改动其他账号的服务/数据

## 禁止事项

❌ 执行完毕后不删除含密码的脚本文件
❌ 将脚本上传到服务器而非本地执行
❌ 把密码写进 skills/rules 的文档里（密码只允许出现在临时脚本与本目录 .env）
❌ 误操作同机其他项目账号（coen-user / ecs-user）下的任何服务、进程、文件
❌ 在已停用的旧账号 sattc 下部署或启动任何服务

## 注意事项

1. SSH 连接设置 10 秒超时，避免长时间挂起
2. `AutoAddPolicy` 自动接受主机密钥
3. 每条命令的输入输出用标签清晰标记，便于查看结果
4. 服务器环境与部署布局见 `deploy-rules` 规则文件
