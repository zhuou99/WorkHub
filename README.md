# WorkHub（Python）

个人工作空间：工作台、笔记文章、收藏与 RSS、代码片段、客户项目、发票收支和万能工具台。
用 FastAPI + Pydantic + SQLAlchemy + SQLite 重写自 C# 版（`../01_WorkHub_C`），
前端用 Vue 3 + Vite 重建（`frontend/`）。

业务数据落在本机 SQLite；外部同步与翻译只在用到时访问对应服务。

## 快速开始

后端需要 Python 3.12+，前端需要 Node 20+。

```bash
# 1. 后端
pip install -r requirements.txt -r requirements-dev.txt
python -m uvicorn app.main:app --host 127.0.0.1 --port 5277

# 2. 前端（另开一个终端）
cd frontend
npm install
npm run dev          # 打开 http://127.0.0.1:5173

# 3. 测试与冒烟
python -m pytest -q
python scripts/smoke.py
```

- 页面：**http://127.0.0.1:5173**
- 接口文档：http://127.0.0.1:5277/docs

首次登录用 `admin / admin123`，登录后请立刻在「偏好设置」修改口令。

### 配置

全部通过环境变量，复制 `.env.example` 为 `.env` 即可；不配也能跑。

| 变量 | 默认 | 说明 |
|---|---|---|
| `WORKHUB_DB_PATH` | `<项目根>/WorkHub.db` | SQLite 主库路径 |
| `WORKHUB_HOST` / `WORKHUB_PORT` | `127.0.0.1` / `5277` | 监听地址与端口 |
| `WORKHUB_COOKIE_NAME` | `workhub_session` | 会话 Cookie 名 |
| `WORKHUB_COOKIE_MAX_AGE` | `43200` | 会话有效期（秒） |
| `WORKHUB_SESSION_KEY` | 空 | 会话密钥；留空则自动生成并存进 `SysConfig` |
| `WORKHUB_COOKIE_SECURE` | `0` | 走 HTTPS / TLS 反代时置 `1` |
| `WORKHUB_ALLOW_INSECURE_REMOTE` | `0` | 允许绑定到非回环地址（明文 HTTP） |
| `WORKHUB_BEHIND_TLS_PROXY` | `0` | 前置反代已终结 TLS |
| `WORKHUB_ALLOWED_NETWORKS` | 空 | 访问白名单：IP 或 IPv4 CIDR，逗号/分号分隔 |

**安全边界**：默认只监听回环。绑到非回环地址且仍是明文 HTTP 时，服务**拒绝启动**，
除非满足其一：存在 `https://` 端点、`BehindTlsProxy` 为真、`AllowInsecureRemote` 为真。

## 接口一览

统一信封：`{"code": 200, "message": "", "data": ...}`。
HTTP 状态码用真实状态码——业务校验失败 400、未登录 401、角色不足 403、不存在 404。

| 分组 | 前缀 | 说明 |
|---|---|---|
| 认证 | `/api/auth` | 登录、登出、当前用户、登录保护状态 |
| 账号 | `/api/users` | 账号增删改查、重置口令（Owner 专属） |
| 客户 | `/api/clients` | 客户档案、沟通记录、删除影响预览 |
| 项目 | `/api/projects` | 项目台账、里程碑、删除影响预览 |
| 任务 | `/api/tasks` | 看板换列 |
| 财务 | `/api/finance` | 发票、回款、支出、回款计划、收支统计 |
| 工具台 | `/api/tools` | 28 个工具的目录与执行、历史 |
| 笔记 | `/api/notes` | 笔记增删改查、分页、关键字搜索 |
| 文章 | `/api/articles` | 文章增删改查、分页、发布状态 |
| 片段 | `/api/snippets` | 代码片段增删改查 |
| 收藏 | `/api/bookmarks` | 收藏、网页快照（`/clip`） |
| 检索 | `/api/search` | 全文检索（FTS5）、索引状态与重建 |
| RSS | `/api/rss` | 订阅、同步、条目操作 |
| 开源 | `/api/repos` | 仓库镜像、GitHub 同步、发布计划 |
| 翻译 | `/api/translate` | 百度翻译、术语表 |
| 发布 | `/api/publish` | 博客园 Markdown、公众号 HTML、发布日志 |
| 周报 | `/api/report` | 近 N 天小结，存文章/笔记 |
| 备份 | `/api/backup` | 一键备份、恢复、轮转 |
| 调度 | `/api/scheduler` | 定时同步与自动备份 |
| 密钥 | `/api/secrets` | 外部服务密钥（加密存本机，不回显明文） |
| 附件 | `/api/files` | 上传（`/uploads/yyyyMM/…`） |
| 设置 | `/api/settings` | 账号资料、修改口令 |
| 日志 | `/api/audit`、`/api/errors` | 审计日志、运行错误 |
| 元信息 | `/api/meta/labels`、`/api/meta/menus` | 状态字典、可见菜单 |
| 健康 | `/health` | 匿名可访问 |

**角色**：Owner 全部；Editor 全部业务目录的读写；Viewer 只读。
角色闸门在路由层（C# 那边靠页面层拦，API 没有页面）。

请求与响应的 JSON 字段走 camelCase（`userName`、`createTime`）；也接受 PascalCase 原样传入。

## 目录结构

```
app/
├── main.py          应用工厂：中间件、CORS、异常处理、路由注册、启动期建表+迁移+种子
├── config.py        配置（环境变量 / .env）
├── db.py            engine / session / PRAGMA
├── deps.py          依赖注入与角色闸门
├── core/            信封、异常处理、分页夹取、会话
├── models/          SQLAlchemy 模型（PascalCase 列名，与旧库逐字一致）
├── schemas/         Pydantic 模型（camelCase 线格式）
├── services/        用例层，一服务一文件
├── routers/         HTTP 路由
├── common/          ← C# 的 WorkHub/Common：纯函数（财务口径、状态字典、权限、ULID…）
├── platforms/       宿主适配（文件存储、密钥保护、SQLite 在线备份）
└── toolbox/         ← C# 的 ToolCatalog + Transforms：28 个工具
frontend/            Vue 3 + Vite 前端
├── src/views/       页面（17 个页面全部铺开）
├── src/components/  导航壳、顶栏、图标
├── src/api.ts       API 客户端（带 Cookie 会话、CORS 凭证）
└── src/styles.css   设计令牌与样式（沿用 C# 版 app.css 的口径）
tests/               pytest（含从 C# 移植过来的行为契约）
scripts/smoke.py     全链路冒烟
```

## 数据落点

| 内容 | 说明 |
|---|---|
| `WorkHub.db` | SQLite 主库，业务表都在这一文件里（默认在项目根） |
| `SysConfig` | 配置 KV：口令散列、失败计数、结构版本、会话密钥 |
| `backups/` | 备份 zip（一键与自动备份落这里） |
| `uploads/` | 附件与网页快照（`/uploads/yyyyMM/…`） |

**列名保持 PascalCase**（`IssueDate`、`CreateTime`、`ProjectId`…），**金额列存 REAL**——
与 C# 版逐字一致，所以 `../01_WorkHub_C/WorkHub.db` 可以直接被本项目打开：
旧 admin 账号的 PBKDF2 散列原样可用，24 张表的行数完全一致。

```bash
# 想直接读 C# 版的老库（建议先复制一份）
WORKHUB_DB_PATH=../01_WorkHub_C/WorkHub.db python -m uvicorn app.main:app
```

注意：打开老库会在 `SysConfig` 里写两条配置——`workhub.session.key`（会话密钥）与
`workhub.secret.key`（外部服务密钥的加密密钥），它们都没有别的来源。

**精度**：库里存 REAL，Python 侧一律用 `decimal.Decimal`，银行家舍入
（`Math.Round(decimal)` 的口径：2.125 → 2.12，不是 2.13）。
线上金额是 JSON 数字，尾零会丢（`56.60` → `56.6`），计算过程一步不丢。

## 测试

```bash
python -m pytest -q          # 全部
python -m pytest -q -k lock  # 单个主题
```

C# 那边的 15 个 xUnit 文件全部移植成 pytest，行为契约一一对应：

| C# 测试 | pytest | 阶段 1 内容 |
|---|---|---|
| `TransformsTests.cs` | `test_transforms.py` | 全部 14 个方法 |
| `YamlTransformsTests.cs` | `test_yaml_transforms.py` | 全部 6 个方法 |
| `FinanceCalcTests.cs` | `test_finance_calc.py` | 全部 8 个方法 |
| `LabelsTests.cs` | `test_labels.py` | 全部 11 个方法 |
| `UserRulesTests.cs` | `test_user_rules.py` | 全部 8 个方法 |
| `UlidTests.cs` | `test_ulid.py` | 全部 4 个方法 |
| `PermissionPolicyTests.cs` | `test_permission_policy.py` | 17 个方法（授权目录改为静态清单） |
| `SchemaMigrationTests.cs` | `test_schema_migration.py` | 全部 7 个方法 |
| `ErrorLogRulesTests.cs` | `test_error_log_rules.py` | 全部 9 个方法 |
| `IpAllowListTests.cs` | `test_ip_allow_list.py` | 全部 7 个方法 |
| `SecurityOptionsTests.cs` | `test_security_options.py` | 全部 6 个方法 |
| `SchedulerOptionsTests.cs` | `test_scheduler_options.py` | 全部 6 个方法（纯逻辑） |
| `UnitCatalogTests.cs` | `test_unit_catalog.py` | 全部 6 个方法 |
| `BackupServiceTests.cs` | `test_backup_rotate.py` | 只移植 `Rotate` 纯函数 |
| `WritingQueryTests.cs` | `test_paging.py` | 只移植分页夹取；文章/笔记的 SQL 形状断言已随阶段 2 落地 |

另有 14 个新增的接口测试文件：认证、账号、客户、项目、任务、财务、工具台、
内容（笔记/文章/片段/收藏）、检索、RSS 解析、周报、发布、备份、宿主适配、调度。

测试库用 `tmp_path` 临时文件而不是 `:memory:`：真实文件能覆盖与生产一致的 WAL/pragma 行为。

## 与 C# 版的差异

| # | 差异 | 原因 |
|---|---|---|
| 1 | 浏览器界面是 Vue 3 + Vite 重建，17 个页面全部铺开 | C# 的 Blazor 界面在本机编不起来（缺 .NET 10 SDK 与 Known 框架）；Vue 版按同样视觉重建 |
| 2 | `json` 工具的「压缩」选项真正压缩 | C# 的目录注册的是 `"min"`，实现只认 `"minify"`，按了「压缩」其实输出格式化结果（bug）。Python 版两个值都映射到压缩 |
| 3 | HTTP 用真实状态码（400/401/403/404），信封形状不变 | C# 一律 200；API 后端用真实状态码更利于客户端判断 |
| 4 | 角色闸门下沉到路由 | C# 靠页面层拦；API 没有页面，必须在路由层拦 |
| 5 | 金额 JSON 输出为数字且尾零丢失（`56.60` → `56.6`） | 与 C# 的 `decimal` 序列化一致；计算过程不丢精度 |
| 6 | 失败计数的全局键会被写入 | C# 只写按账号的键，匿名接口读旧的全局键 → 登录页的「还剩几次」永远是 5。Python 版把全局键当镜像写，锁定判定仍以按账号的键为准 |
| 7 | QR 工具服务端可出 SVG（可选 `segno`） | C# 的像素是 Blazor 组件画的，服务端只有校验逻辑；本项目没有界面，服务端得直接给得出图。条码仍只校验不生成图像 |
| 8 | `translate` 工具已接入百度翻译与术语表 | 阶段 2 完成；未配密钥时明确降级 |
| 9 | 授权目录是写死的 17 个菜单名 | C# 靠反射扫 `[Menu]`/`[Action]`；Python 没有这回事，行为一致、收集方式换了 |
| 10 | 异常类名沿用 .NET 的 `FormatException` / `InvalidOperationException` | 异常类型名会直接进入 `wh_error.Message` 与界面提示，改名会让文案与旧库对不上 |
| 11 | 结构化日志用 `logging` 写文件 | C# 那边是 Known 的文件日志器 |
| 12 | 外部服务密钥用 Fernet（对称加密）而非 DPAPI | 密钥存 `SysConfig[workhub.secret.key]`，换机器自然解不开，语义与 DPAPI 对齐 |
| 13 | 公众号 HTML 用 `markdown` 库渲染 | C# 用 Known 的 MarkdownRenderer，渲染结果可能有细微差异（内联样式注入规则一致） |
| 14 | 备份包里没有 `appsettings.json` | Python 版用环境变量配置，不落配置文件 |

## 阶段 2 已交付

- 笔记 / 文章 / 收藏 / 代码片段（`wh_note`、`wh_article`、`wh_bookmark`、`wh_snippet`）
- 全文检索（SQLite FTS5，trigram → fts5 → LIKE 三级降级，增量索引 + 全量重建）
- RSS 订阅与抓取（站点首页自动发现 feed、ETag 条件请求、按 guid/链接判重）
- 开源仓库同步（GitHub API，星标曲线快照，Token 加密保存）
- 附件上传与网页快照（`/uploads/yyyyMM/…`、HTML → Markdown 正文抽取）
- 备份与恢复（zip + SQLite 在线快照 + 附件 + 反悔备份）、定时任务调度
- 翻译（百度 API 签名 + 术语表，密钥加密保存，术语表可离线查）
- 周报生成、发布记录（博客园 Markdown / 公众号内联样式 HTML）

## 依赖

| 包 | 用途 |
|---|---|
| `fastapi` / `uvicorn` | HTTP 框架与服务器 |
| `pydantic` | 请求 / 响应模型 |
| `SQLAlchemy` | ORM |
| `itsdangerous` | 会话 Cookie 签名 |
| `PyYAML` | YAML 解析（工具台） |
| `segno` | 可选：二维码 SVG |
| `lxml` | HTML 解析（网页快照、RSS 摘要去标签） |
| `markdown` | Markdown → HTML（公众号导出） |
| `cryptography` | 外部服务密钥加密（Fernet） |
| `httpx` | RSS / GitHub / 百度翻译 / 网页抓取 |

前端（`frontend/`，`npm install` 后 `npm run dev`）：

| 包 | 用途 |
|---|---|
| `vue` / `vue-router` | 界面框架与路由 |
| `vite` / `@vitejs/plugin-vue` | 构建与热更新 |
| `marked` | Markdown → HTML（收藏正文预览） |
| `playwright` | 可选：截图核对视觉效果（用本机 Edge 跑） |

## 页面清单（17 个，全部铺开）

| 分组 | 页面 | 路由 |
|---|---|---|
| — | 工作台 | `/` |
| — | 登录 | `/login` |
| 工具箱 | 万能工具台（28 个工具） | `/toolbox` |
| 资料库 | 全文检索 / 我的收藏 / RSS 订阅 | `/search` `/bookmarks` `/rss` |
| 创作 | 笔记 / 代码片段 / 文章 / 发布记录 | `/notes` `/snippets` `/articles` `/publish` |
| 客户 | 客户（含档案弹窗、沟通留痕） | `/clients` |
| 项目 | 项目列表 / 任务看板 / 开源项目 | `/projects` `/tasks` `/repos` |
| 财务 | 发票台账 / 收支统计 / 回款计划 | `/invoices` `/stats` `/plans` |
| 设置 | 偏好设置（账号/密钥/备份/调度/日志 五个页签） | `/settings` |
