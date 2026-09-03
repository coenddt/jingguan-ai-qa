> 适用场景：执行部署/上线/SCP 上传/SSH 服务器操作/SFTP 传输，或询问部署路径、服务器账号时必读

# 服务器信息（AI 创新中心项目）

- 服务器：`<SERVER_IP>`（Ubuntu），与个人绘画集、生活助手项目共用一台机器
- **本项目专用账号：`<user>`**（uid 1004，sudo 组，家目录/远程根 `/home/<user>`，2026-09-03 创建）
  - **本项目一切部署只在该账号下进行**；sudo 可用（密码见 [.agents/skills/ssh-server-task/.env](../skills/ssh-server-task/.env)，严禁写入文档/代码）
- 同机现有账号（其他项目，**严禁误碰**）：
  - `coen-user` → 个人绘画集项目（gallery-server PM2、nginx 域名证书、/home/coen-user）
  - `ecs-user` → 生活助手项目（life-companion / finance-* 等 PM2、mongod 127.0.0.1:27017）
  - `sattc` → 本项目旧账号（2026-09-02~09-03），**已停用**，残留旧项目文件仅作回滚备份，严禁在其中部署或启动服务
- 认证：本机 `~/.ssh/id_rsa` 公钥已装入 <user> 的 `authorized_keys`，SSH/SCP 免密可用；密码兜底见 [.agents/skills/ssh-server-task/.env](../skills/ssh-server-task/.env)，严禁写入文档/代码

# 部署布局（<user> 账号）

- 远程根目录：`/home/<user>`（本地项目文件按项目根映射，如 `server-py/db/store.py` → `/home/<user>/server-py/db/store.py`）
- 进程管理：pm2 在 `/home/<user>/.local/bin`，常驻服务一律 pm2 管理（服务名以服务器 `pm2 list` 实际为准）；`pm2 startup systemd`（unit `pm2-<user>.service`）已注册并已 `pm2 save`
- 端口分配避开同机已占用的 3000/3100/3200，新服务端口先在服务器确认空闲再用

# 服务端部署后校验（强制）

- 部署重启后至少验证：curl 对应服务端口返回 200；启动日志无报错
- 本地与服务器代码可能漂移；大改动部署前先 `ssh <user>@<SERVER_IP> "grep -n <关键标识> <远程文件>"` 比对版本

# 服务器操作工具

- SSH 执行命令/排查：`ssh-server-task` skill（本地临时脚本，执行完即删）
- 文件上传：SSH/SCP 免密，直接 `scp` 上传到 `/home/<user>` 对应路径

# 配置一致性铁律（本地=服务器，唯一事实源）

- **铁律**：关键配置以本地代码为准，必须与服务器逐字完全一致
- 改配置一律先改**本地**，再同步部署到服务器；杜绝「只在服务器改、本地落后」
- 例外（必须显式注明在本地注释里）：允许的环境差异项要在对应行注明差异原因；无注释说明的差异一律视为 BUG
- API Key/密码等属环境差异项：只存在于服务器侧 .env/服务配置，本地以占位符标注并注明来源
