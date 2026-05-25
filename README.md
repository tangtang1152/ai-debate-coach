# 论点攻防 - AI 辩论教练

「论点攻防」是一套前后端分离的 AI 辩论训练系统。当前版本面向个人用户，完成“设置辩题 -> 进行 3 回合辩论 -> 生成评分报告”的 MVP 闭环。

## 功能

- 辩题输入与正反方选择
- 默认使用 Qwen 模型，并支持开始训练前切换可选模型
- 固定 3 回合 AI 辩论流程
- SSE 流式 AI 反驳展示
- 会话、消息与评分结果持久化
- 三维评分报告：逻辑严密性、论据充实度、表达流畅性
- 雷达图与文字改进建议
- OpenRouter 兼容模型调用
- 主模型限流时自动尝试备用免费模型

## 项目结构

```text
ai-debate-coach
├── app/                    # Flask 后端应用
│   ├── clients/            # 大模型 API 客户端
│   ├── controllers/        # API 路由控制层
│   ├── models/             # SQLAlchemy 数据模型
│   ├── repositories/       # 数据访问层
│   ├── schemas/            # 请求/响应数据校验
│   ├── services/           # 业务服务层
│   └── utils/              # Prompt、SSE、异常等工具
├── frontend/               # 原生 HTML/CSS/JS 前端
├── migrations/             # Alembic 数据库迁移
├── tests/                  # Pytest 测试
├── examples/frontend/      # 前端 API 调用示例
├── .env.example            # 环境变量模板
├── pyproject.toml          # Python 依赖配置
├── uv.lock                 # uv 锁文件
└── run.py                  # 后端启动入口
```

## 后端启动

推荐使用 `uv`：

```bash
uv sync
cp .env.example .env
uv run alembic -c alembic.ini upgrade head
uv run python run.py
```

后端默认运行在：

```text
http://127.0.0.1:8000
```

## 前端启动

另开一个终端，在仓库根目录运行：

```bash
python3 -m http.server 5173 --directory frontend
```

然后访问：

```text
http://127.0.0.1:5173
```

前端只保留正式后端模式，默认调用：

```text
http://127.0.0.1:8000
```

## 大模型配置

在 `.env` 中填写 OpenRouter API Key：

```env
LLM_PROVIDER=openrouter
LLM_API_BASE_URL=https://openrouter.ai/api/v1
LLM_API_KEY=你的_OpenRouter_Key
LLM_MODEL=qwen/qwen3-next-80b-a3b-instruct:free
LLM_FALLBACK_MODELS=tencent/hy3-preview:free,google/gemma-4-31b-it:free
LLM_SELECTABLE_MODELS=qwen/qwen3-next-80b-a3b-instruct:free,tencent/hy3-preview:free,google/gemma-4-31b-it:free,qwen/qwen3-coder:free
```

前端默认选择 `qwen/qwen3-next-80b-a3b-instruct:free`。用户可以在开始训练前切换模型，后端会把本场会话使用的模型保存到 `sessions.model_name`，后续三轮辩论和评分都会沿用该模型。`LLM_SELECTABLE_MODELS` 用作后端白名单，避免前端传入任意模型名。

如果 `LLM_API_KEY` 为空，后端会回退到 mock 回复，方便本地流程测试。正式演示时请填写有效 key。

## 核心接口

```text
GET  /health
POST /api/debate/start
POST /api/debate/stream
POST /api/debate/evaluate
```

其中 `/api/debate/stream` 返回 `text/event-stream`，前端会逐块渲染 AI 回复。

## 测试

### 运行测试

```bash
uv run pytest                # 运行全部测试（跳过真实 API 测试）
uv run pytest -v             # 详细输出
uv run pytest --cov=app --cov-report=term-missing   # 覆盖率报告
uv run pytest -m performance # 单独运行轻量性能基线测试
uv run pytest -m real_api    # 运行真实 API 集成测试（需 API Key）
uv run pytest -m ""          # 运行所有测试（含真实 API）
```

### 测试策略

项目采用**测试金字塔**分层策略：

| 层级 | 类型 | 测试文件 | 说明 |
|------|------|---------|------|
| 单元测试 | 纯逻辑 | `test_prompt_builder.py` | Prompt 模板构造，无外部依赖 |
| 单元测试 | 纯逻辑 | `test_evaluation_parser.py` | 评分 JSON 解析，含容错 fallback |
| 单元测试 | 纯逻辑 | `test_evaluation_result.py` | EvaluationResult 数据类 |
| 单元测试 | 纯逻辑 | `test_schemas.py` | 请求参数校验，边界值与异常路径 |
| 单元测试 | 纯逻辑 | `test_errors.py` | 自定义异常类属性验证 |
| 单元测试 | 纯逻辑 | `test_config.py` | 配置加载、环境变量解析 |
| 单元测试 | 纯逻辑 | `test_llm_client.py` | LLMClient 内部方法：SSE 解析、header/payload 构建、模型链、mock 降级、容错 fallback |
| 单元测试 | Mock | `test_llm_client_extra.py` | LLMClient 非 mock 公共方法、无模型报错、流式成功/异常路径 |
| 集成测试 | DB + API | `test_start_api.py` | 会话创建 → 持久化 → 列表/详情查询 |
| 集成测试 | DB + API | `test_stream_api.py` | SSE 流式辩论 → 消息持久化 → 回合管理 |
| 集成测试 | DB + API | `test_evaluate_api.py` | 3 回合评分 → 结果持久化 → 模型一致性 |
| 集成测试 | DB + API | `test_session_service.py` | Service 层模型校验与会话查找 |
| 集成测试 | DB + API | `test_api_endpoints.py` | /health 端点、CORS 头、错误响应格式、会话详情无评分 |
| 集成测试 | DB + API | `test_debate_service_extra.py` | 流式辩论异常路径：空 chunk、空回复、非 AppError、超回合、回滚 |
| 集成测试 | DB + API | `test_evaluation_service_extra.py` | 评分缓存命中、空历史报错 |
| 集成测试 | DB + API | `test_edge_cases.py` | isoformat(None)、Session 状态、CORS 通配符、DB 路径、类型校验、Repository save |
| 契约测试 | 前后端 | `test_frontend_contract.py` | 前端调用的 API 路径、SSE 事件、响应字段与 DOM 节点契约 |
| 验收测试 | MVP 流程 | `test_acceptance_flow.py` | 创建会话 → 3 回合流式辩论 → 评分 → 历史恢复 |
| 性能基线 | 本地 Mock | `test_performance_baseline.py` | 创建会话与流式接口的轻量本地响应时间基线 |
| 集成测试 | 真实 API | `test_real_api.py` | 真实 OpenRouter API 调用、模型 fallback 链（需 Key，默认跳过） |

### 测试基础设施

- **框架**: pytest 8.x + pytest-cov 6.x
- **数据库**: 每个测试使用 `sqlite:///:memory:` 内存数据库，测试间完全隔离
- **LLM Mock**: 测试环境设置 `LLM_PROVIDER=mock`，不调用外部 API；必要时通过 `monkeypatch` 替换 LLMClient 方法
- **性能基线**: 使用 `performance` marker，仅验证本地 Mock 路径没有明显退化，不把外部大模型延迟纳入指标
- **覆盖率**: 当前 100%。所有 app/ 模块的 711 条语句全部覆盖。
- **真实 API 测试**: `uv run pytest -m real_api` 会调用 OpenRouter 真实 API（需在 `.env` 中配置 `LLM_API_KEY`）；默认 `uv run pytest` 跳过此类测试以避免消耗配额

### 当前测试统计

| 指标 | 数值 |
|------|------|
| 测试文件数 | 20 |
| 测试用例数 | 168（不含 real_api）/ 172（全部） |
| 通过率 | 100% |
| 代码覆盖率 | 100% |

### 覆盖详情

- 创建会话接口（含模型选择与校验、会话列表/详情查询）
- 流式辩论接口（含消息持久化、回合推进、超回合拦截、异常回滚）
- 评分接口（含缓存命中、空历史拦截、容错 fallback、模型一致性）
- Prompt 构造（辩论 prompt + 评分 prompt）
- 评分 JSON 解析（含 markdown fence、字段别名、缺省容错、分数钳位）
- 请求参数校验（含边界值、非法输入、空值、类型错误）
- 自定义异常（AppError / ValidationError / NotFoundError / ConflictError / LLMClientError）
- 配置加载（默认值、环境变量覆盖、类型转换、DB 路径解析）
- LLMClient 内部方法（SSE 解析、header/payload 构建、模型链、mock 降级、JSON 解析异常）
- LLMClient 公共方法（非 mock 分支、无模型报错、流式成功/异常数据/空内容路径）
- SessionService（模型白名单校验、会话查找）
- Session 模型（status 属性：created/debating/ready_for_evaluation）
- CORS 策略（Origin 匹配、通配符、无 Origin 头）
- Repository 层（含 EvaluationRepository.save）
- HTTP 错误响应格式（400/404/409/500、SSE 错误事件）
- 完整 MVP 验收流程（创建会话、三轮辩论、评分、历史恢复）
- 前后端接口契约（API 路径、SSE 事件、响应字段、关键 DOM 节点）
- 轻量性能基线（本地 mock 下的创建会话和流式接口响应时间）
- 所有模块覆盖率达到 100%

### 课堂提问对照

| 问题 | 当前证据 |
|------|----------|
| Q1 测试覆盖率 | `uv run pytest --cov=app --cov-report=term-missing`，当前 app/ 覆盖率 100% |
| Q2 单元测试例子 | Prompt 构造、评分解析、Schema 校验、错误类、配置加载、LLMClient 内部逻辑 |
| Q3 集成测试 | `test_start_api.py`、`test_stream_api.py`、`test_evaluate_api.py` 覆盖 DB + API |
| Q4 可靠性指标 | 通过率、覆盖率、异常路径、回滚、fallback、缓存命中和性能基线 |
| Q5 兼容性交互 | 前后端契约测试、CORS 测试、OpenRouter 兼容调用和真实 API 可选测试 |
| Q6 代码审查 | 通过自动化测试与覆盖率作为基础质量门禁；正式审查记录需在提交或验收文档中补充 |
| Q7 容错设计 | Mock 降级、模型 fallback、SSE error 事件、统一错误响应、事务回滚 |
| Q8 性能测试 | `test_performance_baseline.py` 提供本地轻量性能基线 |
| Q9 验收测试 | `test_acceptance_flow.py` 覆盖 MVP 主流程验收 |
| Q10 测试文档 | README 测试章节记录运行命令、测试策略、统计、覆盖范围和课堂提问对照 |

## 注意

- `.env`、数据库文件、虚拟环境不会提交到 Git。
- `qwen/qwen3-next-80b-a3b-instruct:free` 是首选模型，但免费模型可能被 OpenRouter 上游临时限流；系统会按配置自动尝试备用模型。
- 当前版本不包含用户注册、登录、历史会话列表和多人对战，符合 MVP 范围。
