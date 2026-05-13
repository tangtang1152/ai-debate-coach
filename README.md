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

```bash
uv run pytest
```

当前测试覆盖：

- 创建会话接口
- 流式辩论接口
- 评分接口
- Prompt 构造逻辑

## 注意

- `.env`、数据库文件、虚拟环境不会提交到 Git。
- `qwen/qwen3-next-80b-a3b-instruct:free` 是首选模型，但免费模型可能被 OpenRouter 上游临时限流；系统会按配置自动尝试备用模型。
- 当前版本不包含用户注册、登录、历史会话列表和多人对战，符合 MVP 范围。
