# 经管之星·AI问数助手 部署与 nginx 登录 执行文档

> 日期：2026-09-03
> 设计依据：`doc/solution/2026/09/已完成-经管之星AI问数助手需求文档.md`（§3.7 nginx 登录、§4.1 架构、§4.5 权衡）
> 接口依据：`doc/execution/2026/09/未处理-后端FastAPI分层执行文档.md`（§4.5 认证契约）
> 性质：代码执行文档（AI 照此执行部署落地）
> 服务器：`<user>@<SERVER_IP>`（sudo 组）；新增 pm2 服务 `jingguan-api`；MongoDB 常驻本服务器

## 1. 目标（验收标准）

1. MongoDB 在本服务器常驻，弱机最低配可运行（ipv4 回环认证启用），库 `jingguan` 就绪
2. FastAPI 以 `jingguan-api` 跑在 pm2 上，`curl http://127.0.0.1:8000/api/auth/check` 返回按预期
3. nginx 托管前端静态资源 + 反代 `/api` + `auth_request` 登录校验；未登录访问任意路径 → 跳登录页
4. 登录成功签发 24h Cookie，期内免重复登录；过期重新登录；登出主动失效
5. 首次启动自动建 schema + 灌种子；`.env` 敏感值只存服务器侧，不入 git
6. 线上端口 curl 走通：登录 → 问数（7 个示例之一）→ 越界查询被拒

## 2. 涉及端 × 角色

| 端 | 是否涉及 | 角色 | 说明 |
|---|---|---|---|
| server（FastAPI） | 是 | 被部署对象 | 本端负责其进程/pm2/迁移 |
| MongoDB | 是 | 数据底座 | 本端负责安装/常驻/认证 |
| nginx | 是 | 网关 | 静态+反代+auth_request+24h Cookie |
| web-front（React） | 是 | 部署产物 | 构建 `dist/` 由 nginx 托管 |
| 本机（开发） | 否（本地仅静态自检） | - | 常驻/演示实例不上本机（testing-rules） |

## 3. 迁移与移除清单

### 3.1 新增清单

| 新增项 | 服务器路径 | 说明 |
|---|---|---|
| 后端代码 | `~/jingguan/api/` | 上传 `server/`（含 `app/db/mongo_store`），见 §4.1 目录 |
| `.env` | `~/jingguan/api/.env` | 真实机密，不入库 |
| 依赖锁 | `~/jingguan/api/requirements.txt` | pip install 用 |
| 前端产物 | `~/jingguan/web/` | `npm run build` 的 `dist/` 上传；nginx root 指此 |
| pm2 应用 | pm2 name=`jingguan-api` | 指向 `~/jingguan/api`，`uvicorn app.main:app` |
| MongoDB 服务 | 系统服务（systemd，名 `mongod-jingguan`） | 常驻，回环 + 认证，**端口 27018**（27017 已被同机生活助手项目占用） |
| nginx vhost | `/etc/nginx/conf.d/jingguan.conf` | 详见 §4.3；nginx 为同机共享服务（coen-user 域名证书等共存），改前备份 |

### 3.2 修改清单

| 修改项 | 文件 | 由 → 到 |
|---|---|---|
| nginx 主配置 | `/etc/nginx/nginx.conf` | 若 vhost 用 `conf.d` 需确认 `include conf.d/*.conf` 存在；否则改用 `sites-enabled`。**nginx 为同机共享服务**：改前备份、`nginx -t` 通过后 reload、验证其他站点不受影响 |

### 3.3 删除清单

| 删除项 | 位置 | 原因 | 替代 |
|---|---|---|---|
| 无 | - | 新部署 | - |

## 4. 详细执行契约

### 4.1 上传目录与依赖

```bash
# 本机 SCP 上传（路径按实际）
scp -r server/ <user>@<SERVER_IP>:~/jingguan/api/
scp -r web-front/dist/ <user>@<SERVER_IP>:~/jingguan/web/

# 服务器装依赖（明确版本，勿整棵升级）
cd ~/jingguan/api
python3.11 -m venv .venv && . .venv/bin/activate   # 后端固定 Python 3.11（与 requirements.txt 口径一致）
pip install -r requirements.txt    # fastapi uvicorn[standard] pymongo[async] pydantic-settings openpyxl httpx
```

### 4.2 MongoDB 常驻（弱机最低配，固定 7.0 稳定版，**端口 27018**）

```yaml
# mongod.conf（回环 + 轻量认证；单机入库演示无需副本集；systemd 前台运行，不开 fork。
# 服务名 mongod-jingguan，与同机生活助手项目的 mongod(27017) 共存，严禁动它）
net:
  bindIp: 127.0.0.1
  port: 27018
security:
  authorization: enabled
storage:
  dbPath: /data/mongo
systemLog:
  destination: file
  path: /data/mongo/mongod.log
  logAppend: true
```

```bash
# 建库用户
mongosh --port 27018 jingguan --eval '
  db.createUser({user:"jingguan", pwd:"<用随机强密码>", roles:[{role:"readWrite",db:"jingguan"}]})'
# 常驻：systemd 单元（Type=simple，前台运行）；`systemctl enable --now mongod`；验证
ss -tlnp | grep 27018                                   # 仅 127.0.0.1:27018（说明 bind 生效；27017 属生活助手项目，勿动）
mongosh --quiet --eval "db.runCommand({ping:1})"        # 无凭据应报认证错误（说明 authorization 生效）
```

`.env` 对应：`MONGO_URI=mongodb://jingguan:<密码>@127.0.0.1:27018/?authSource=jingguan`（弱机无外网暴露，回环+账号即可；**authSource 必须带上**，否则 pymongo 默认对 admin 库认证会失败）。

### 4.3 nginx vhost（静态 + 反代 + auth_request + 24h Cookie）

```nginx
# /etc/nginx/conf.d/jingguan.conf
server {
  listen 80;
  server_name jingguan.example.com;   # 按实际域名/IP

  root /home/<user>/jingguan/web;
  index index.html;

  # 登录相关接口直接放行
  location = /api/auth/login   { proxy_pass http://127.0.0.1:8000; }
  location = /api/auth/check   { proxy_pass http://127.0.0.1:8000; }
  location = /api/auth/logout  { proxy_pass http://127.0.0.1:8000; }

  # 其余 /api → auth_request 拦截后反代
  location /api/ {
    auth_request /__auth;
    proxy_pass http://127.0.0.1:8000;
    proxy_set_header Host $host;
    proxy_set_header X-Real-IP $remote_addr;
  }

  location = /__auth {
    internal;
    proxy_pass http://127.0.0.1:8000/api/auth/check;
    proxy_pass_request_body off;
    proxy_set_header Content-Length "";
    proxy_set_header X-Original-URI $request_uri;
  }

  # 前端 SPA + 未登录兜底跳登录
  location / {
    try_files $uri $uri/ /index.html;
  }
}
```

**认证语义**（与前端执行文档 §4.3 一致）：
- 后端 `check` 校验签名 Cookie（HMAC，24h 过期）；有效返回 200，无效返回 401
- 401 → nginx `auth_request` 失败 → 前端 axios 捕获 401 → 跳 `/login`
- 登录/登出/过期均由后端 Cookie（`HttpOnly`）控制；前端不存 token
- 登出接口清 Cookie 并返回，nginx 放行

> 说明：采用 `auth_request` 方案（保留原").actid)` 即可实现时效，替代 v1.0 讨论的 auth_basic（无法时效）。前端 SPA 自身路由不做鉴权，以接口 401 驱动跳转。

### 4.4 pm2 起 FastAPI

```bash
cd ~/jingguan/api && . .venv/bin/activate
# process.json
# { "apps": [{ "name":"jingguan-api","script":"uvicorn","args":"app.main:app --host 127.0.0.1 --port 8000","interpreter":".venv/bin/python","cwd":"/home/<user>/jingguan/api" }] }
pm2 start process.json
pm2 save && pm2 startup            # 开机自启
pm2 restart jingguan-api
curl http://127.0.0.1:8000/api/auth/check   # 未带 cookie → 401；带有效 cookie → 200
```

> 弱机提示：uvicorn worker=1 即可；MongoDB 与 API 同机回环，无网络放大。pm2 日志路径 `~/.pm2/logs/jingguan-api-*`，排障用。

### 4.5 首次启动与种子

- 后端启动事件：`init(db)` 注册 14 核心模型（P1 问法缓存步骤启用后再加 QueryExample，共 15）+ 建索引 + 若库空则执行种子（固定种子，见后端执行文档 §4.9）
- `.env` 需先写好（`SECRET_KEY/ADMIN_*/MONGO_URI/VOICE_*`）；密码只存服务器侧 `.env`

### 4.6 安全加固清单

| 项 | 动作 |
|---|---|
| Mongo 暴露 | 仅 `bindIp:127.0.0.1`，不对外 |
| `.env` | `chmod 600`，不入 git/备份 |
| 登录 | 固定账号密码 + 24h Cookie + 登录接口可做简单失败限速（可选） |
| API Key | 只存后端 `.env`/`AiModel` 库，前端不可见 |

## 5. 执行步骤

| 步骤 | 状态 | 详细说明 |
|---|---|---|
| 1. 本地自检 | [ ] 待处理 | **做什么**：`python -m py_compile server/app/**/*.py`；`node/npx tsc --noEmit`（前端）；确认 `server/app/db/mongo_store` 已导入。<br>**验证**：各文件零语法错 |
| 2. MongoDB 安装 | [ ] 待处理 | ssh 服务器先做端口预检：`ss -tlnp | grep -E ':(8000|27018)'`（8000 给 API、27018 给 Mongo，被占则换空闲端口并同步 `.env`/nginx；**27017 属生活助手项目严禁占用**）→ 安装 MongoDB + `mongod.conf` + 建库用户 + `mongod-jingguan` 开机自启（§4.2）。<br>**验证**：`mongosh --port 27018 -u jingguan -p --authenticationDatabase jingguan` 可登；回环 bind 生效 |
| 3. 上传后端 | [ ] 待处理 | SCP `server/` → `~/jingguan/api/`；python venv + pip install；写 `.env`。<br>**验证**：`python -c "import app.main"` 无错 |
| 4. 构建上传前端 | [ ] 待处理 | `web-front` `npm run build` → 上传 `dist/` → `~/jingguan/web/`。<br>**验证**：`ls ~/jingguan/web` 见 `index.html` |
| 5. nginx 登录 | [ ] 待处理 | 写 `jingguan.conf` + `nginx -t` + reload（§4.3）。<br>**验证**：未登录访问 → 被拦/前端跳登录 |
| 6. pm2 起服务 | [ ] 待处理 | `process.json` + `pm2 start|save|startup`（§4.4）。<br>**验证**：`curl 127.0.0.1:8000/api/auth/check` 401（验证逻辑而非填错）；看 `pm2 logs` |
| 7. 首启种子 | [ ] 待处理 | 触发后端启动事件建 schema+种子。<br>**验证**：`mongosh` 查 `jingguan` 各集合有数据、索引存在 |
| 8. 端到端验证 | [ ] 待处理 | 浏览器登录 → 问"2026年各经营单元收入排名柱状图" → 表格+图表；再问越界（如 `$where` 注入样例）→ 被拒。<br>**验证**：登录/问数/越界拒绝 3 项全过 |
| 9. 收尾检查 | [ ] 待处理 | 确认无线索文件残留；`.env` 不入 git；临时 SSH 脚本用完即删。<br>**验证**：`git status` 干净；敏感值仅服务器侧 |

## 6. 实施顺序

| 阶段 | 内容 | 依赖 |
|---|---|---|
| A 数据底座 | 步骤 1-2（自检/MongoDB） | 无 |
| B 服务部署 | 步骤 3-6（上传/前端/nginx/pm2） | A |
| C 数据初始化 | 步骤 7（种子） | B |
| D 验收收尾 | 步骤 8-9（端到端/收尾） | C |

## 7. 禁止事项

❌ 不在本机启动 MongoDB/FastAPI 常驻实例（遵循 testing-rules，常驻/演示只在服务器）
❌ 不把 `.env`（SECRET_KEY/管理员密码/Mongo 凭据/火山KEY/API Key）提交入库或写进示例文件
❌ 不对外暴露 MongoDB 端口（仅回环）
❌ 不用 `auth_basic` 替代（无法 24h 时效）；登录必须走后端 Cookie 时效
❌ 不把 Mongo 连接串/API Key 写进前端或 nginx 公开配置
❌ 不保留临时 SSH/含密码脚本（执行完立即删除）

## 8. 注意事项

1. 服务器为 `<user>` 账号（sudo 组），依赖安装/nginx/systemd 操作需 sudo；命令防挂起（长命令后台化或加超时）
2. MongoDB 弱机最低配：单实例回环即可，勿开副本集/外网绑定；**端口 27018**（27017 已被同机生活助手项目占用，systemd 服务名 `mongod-jingguan` 与现有实例区分）；磁盘与日志收敛（定期 rotate 或 `logRotate`）
3. nginx `auth_request` 校验走 `/api/auth/check`，登录/登出/check 三个 location 必须放行，否则登录死循环
4. Cookie 需 `HttpOnly` + `SameSite=Lax`（跨前置避免)；前端 axios `withCredentials: true`
5. 过期演示：可在配置调短时效展示跳登录，演示后再还原 24h
6. pm2 是 Supervisor：改动代码后 `pm2 restart jingguan-api`；部署走 server-deploy/ssh-server-task 流程
7. 验证若 401 应定位是"未登录"还是"接口错误"：`curl` 直接带/不带 Cookie 对比；看 `pm2 logs` 与 `nginx error.log`
8. 同机多账号共存（deploy-rules）：coen-user/ecs-user 为其他项目、sattc 为本项目已停用旧账号（残留仅作回滚备份）——一切操作仅限 <user> 账号，严禁误碰其他账号目录/服务
9. nginx 为共享服务：`server_name` 按实际定；若直接用 IP 访问需确认 default_server 不与其他站点冲突（必要时用独立端口监听）

