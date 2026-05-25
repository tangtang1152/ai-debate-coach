# 论点攻防 - AI 辩论教练测试文档

## 1. 文档目的

本文档用于说明「论点攻防 - AI 辩论教练」项目的测试方案、测试范围、测试环境、测试用例设计、执行结果与质量结论。文档重点覆盖课堂验收中关注的测试覆盖率、单元测试、集成测试、可靠性、兼容性、代码审查、容错设计、性能测试、验收测试和测试文档准备情况。

## 2. 项目测试对象

本项目是一个前后端分离的 AI 辩论训练系统，当前版本完成 MVP 闭环：

- 用户输入辩题并选择正反方
- 创建辩论会话
- 完成 3 轮用户发言与 AI 反驳
- 基于完整辩论历史生成评分报告
- 保存会话、消息与评分结果
- 前端展示辩论过程、历史会话与评分结果

本轮测试主要覆盖后端 Flask API、业务服务层、数据持久化层、大模型客户端封装、前后端接口契约，以及核心 MVP 验收流程。

## 3. 测试环境

| 项目 | 内容 |
|------|------|
| 操作系统 | macOS，本地开发环境 |
| Python | 3.11+，当前本地测试使用 Python 3.14 |
| 后端框架 | Flask |
| 数据库 | SQLite，测试环境使用 `sqlite:///:memory:` |
| ORM | SQLAlchemy / Flask-SQLAlchemy |
| 测试框架 | pytest |
| 覆盖率工具 | pytest-cov |
| 大模型服务 | OpenRouter，默认测试使用 mock，真实 API 测试单独运行 |
| 前端 | 原生 HTML / CSS / JavaScript |

## 4. 测试工具与命令

常用测试命令如下：

```bash
uv run pytest
uv run pytest -v
uv run pytest --cov=app --cov-report=term-missing
uv run pytest -m performance
uv run pytest -m real_api
uv run pytest -m ""
```

命令说明：

| 命令 | 说明 |
|------|------|
| `uv run pytest` | 运行默认自动化测试，跳过真实 API 测试 |
| `uv run pytest -v` | 输出更详细的测试用例执行信息 |
| `uv run pytest --cov=app --cov-report=term-missing` | 生成后端覆盖率报告 |
| `uv run pytest -m performance` | 单独运行轻量性能基线测试 |
| `uv run pytest -m real_api` | 单独运行真实 OpenRouter API 测试 |
| `uv run pytest -m ""` | 运行所有测试，包括真实 API 测试 |

默认跳过真实 API 测试的原因是：避免日常测试消耗额度、受网络波动影响或触发 OpenRouter 免费模型限流。真实 API 测试在需要验证外部服务兼容性时单独执行。

## 5. 测试策略

项目采用测试金字塔策略：

- 单元测试：覆盖纯逻辑函数、数据校验、错误类、配置解析、Prompt 构造和大模型客户端内部逻辑。
- 集成测试：覆盖 Flask API、Service、Repository、数据库持久化之间的协作。
- 契约测试：验证前端调用的 API 路径、SSE 事件、响应字段和关键 DOM 节点与后端一致。
- 容错测试：验证异常响应、事务回滚、SSE 错误事件、mock 降级和模型 fallback。
- 性能基线测试：验证本地 mock 环境下接口响应没有明显退化。
- 验收测试：覆盖 MVP 主流程，即创建会话、三轮辩论、评分与历史恢复。
- 真实 API 测试：验证 OpenRouter 真实调用、无效模型处理和 fallback 链路。

## 6. 测试范围

### 6.1 已覆盖范围

| 模块 | 覆盖内容 |
|------|----------|
| API 控制层 | `/health`、`/api/debate/start`、`/api/debate/stream`、`/api/debate/evaluate`、会话列表、会话详情 |
| Service 层 | 会话创建、模型校验、三轮辩论、评分生成、评分缓存 |
| Repository 层 | 会话、消息、评分结果的创建、查询与保存 |
| Schema 层 | 请求参数校验、边界值、空值、类型错误 |
| LLMClient | mock 回复、真实 API 路径、SSE 解析、header/payload 构造、fallback 模型链 |
| PromptBuilder | 辩论 prompt 与评分 prompt 构造 |
| EvaluationParser | JSON 评分解析、markdown fence、字段别名、缺省容错、分数钳位 |
| 错误处理 | 400、404、409、500、SSE error 事件 |
| CORS | 指定 Origin、未知 Origin、通配符配置、无 Origin 请求 |
| 前端契约 | API 路径、响应字段、SSE 事件、核心 DOM 节点 |
| 验收流程 | 创建会话、三轮流式辩论、评分、历史详情恢复 |
| 性能基线 | 创建会话接口、流式接口本地 mock 响应时间 |

### 6.2 暂未覆盖或弱覆盖范围

| 范围 | 当前状态 | 说明 |
|------|----------|------|
| 浏览器端 E2E 测试 | 暂未正式加入自动化测试 | 当前通过前后端契约测试保证接口一致性，后续可加入 Playwright |
| 高并发压力测试 | 暂未覆盖 | 当前只有轻量本地性能基线，不包含大规模并发压测 |
| 长时间稳定性测试 | 暂未覆盖 | 暂无 24 小时运行、内存增长、连接泄漏等测试 |
| 正式代码审查记录 | 需在过程文档中补充 | 自动化测试已作为质量门禁，但还可补充人工审查表 |

## 7. 测试用例分类

| 测试类型 | 测试文件 | 说明 |
|----------|----------|------|
| 单元测试 | `tests/test_prompt_builder.py` | Prompt 模板构造 |
| 单元测试 | `tests/test_evaluation_parser.py` | 评分 JSON 解析与容错 |
| 单元测试 | `tests/test_evaluation_result.py` | 评分结果数据结构 |
| 单元测试 | `tests/test_schemas.py` | 请求参数校验 |
| 单元测试 | `tests/test_errors.py` | 自定义异常类 |
| 单元测试 | `tests/test_config.py` | 配置加载与环境变量解析 |
| 单元测试 | `tests/test_llm_client.py` | LLMClient 内部逻辑 |
| 单元测试 | `tests/test_llm_client_extra.py` | LLMClient 非 mock 分支与异常路径 |
| 集成测试 | `tests/test_start_api.py` | 创建会话、模型选择、历史查询 |
| 集成测试 | `tests/test_stream_api.py` | 流式辩论、消息持久化、回合推进 |
| 集成测试 | `tests/test_evaluate_api.py` | 三轮评分、评分持久化、模型一致性 |
| 集成测试 | `tests/test_session_service.py` | 会话服务与模型白名单 |
| 集成测试 | `tests/test_api_endpoints.py` | 健康检查、CORS、错误响应 |
| 集成测试 | `tests/test_debate_service_extra.py` | 流式异常、空回复、超回合、回滚 |
| 集成测试 | `tests/test_evaluation_service_extra.py` | 评分缓存、空历史报错 |
| 边界测试 | `tests/test_edge_cases.py` | 边界路径、状态属性、Repository save |
| 契约测试 | `tests/test_frontend_contract.py` | 前后端接口契约 |
| 验收测试 | `tests/test_acceptance_flow.py` | 完整 MVP 主流程 |
| 性能测试 | `tests/test_performance_baseline.py` | 本地轻量性能基线 |
| 真实 API 测试 | `tests/test_real_api.py` | OpenRouter 真实调用与 fallback |

## 8. 关键测试用例说明

### 8.1 单元测试示例

以 `tests/test_evaluation_parser.py` 为例，测试目标是保证大模型返回评分文本后，系统能够稳定解析出结构化评分结果。覆盖场景包括：

- 标准 JSON 解析
- markdown code fence 中的 JSON 解析
- 字段别名兼容
- 缺失字段时使用 fallback
- 分数超出范围时进行钳位
- 非法 JSON 时返回可用的默认结果

该测试保证即使大模型返回格式不完全稳定，系统仍能给用户生成可用评分结果。

### 8.2 集成测试示例

以 `tests/test_stream_api.py` 为例，测试目标是验证流式辩论接口的完整后端协作：

- 调用 `/api/debate/start` 创建会话
- 调用 `/api/debate/stream` 发起一轮辩论
- 验证响应类型为 `text/event-stream`
- 验证返回 `chunk` 与 `done` SSE 事件
- 验证用户消息和 AI 消息被持久化
- 验证当前回合数正确推进
- 验证会话使用的模型保持一致

该测试证明 API 层、Service 层、LLMClient、Repository 和数据库之间能够正确协作。

### 8.3 验收测试示例

`tests/test_acceptance_flow.py` 覆盖完整 MVP 验收路径：

1. 创建辩论会话。
2. 连续完成 3 轮用户发言和 AI 流式反驳。
3. 第三轮结束后调用评分接口。
4. 验证评分结果包含逻辑、论据、表达三个维度。
5. 查询会话详情，验证 6 条消息和评分结果已持久化。
6. 验证三轮辩论和评分均使用同一个模型。

该测试可作为项目验收测试的核心自动化用例。

### 8.4 容错测试示例

容错测试覆盖以下场景：

- 大模型返回空内容时生成 SSE error 事件。
- 流式生成中发生异常时执行数据库回滚。
- 超过最大回合数时返回 409 conflict。
- 评分历史不足时拒绝评分。
- 未知会话返回 404 not_found。
- 非法输入返回 400 validation_error。
- 未捕获异常返回统一 500 internal_server_error。
- 大模型调用失败时进入 fallback 模型链。
- 未配置 API Key 时使用 mock 模式，保证本地开发可用。

这些测试证明系统在异常情况下不会产生脏数据，也能向前端返回稳定错误格式。

### 8.5 性能测试示例

`tests/test_performance_baseline.py` 提供轻量性能基线：

- 连续创建 30 个会话，总耗时小于 5 秒，平均每次小于 0.2 秒。
- 连续执行 12 次本地 mock 流式接口，总耗时小于 5 秒，平均每次小于 0.3 秒。

该性能测试不包含真实大模型延迟，只用于验证本地业务路径和数据库路径没有明显性能退化。

### 8.6 兼容性测试示例

兼容性测试包括：

- CORS Origin 匹配测试。
- CORS 通配符测试。
- 前端使用的 API 路径与后端接口一致性测试。
- 前端对 `chunk`、`done`、`error` 三类 SSE 事件的处理契约测试。
- OpenRouter 真实 API 调用测试。
- 无效模型时的错误处理与 fallback 链测试。

## 9. 测试数据设计

测试数据主要采用小规模、可重复、无外部依赖的数据：

| 数据类型 | 示例 |
|----------|------|
| 辩题 | `人工智能是否会提升大学生学习效率` |
| 持方 | `正方`、`反方` |
| 模型 | `qwen/qwen3-next-80b-a3b-instruct:free`、`qwen/qwen3-coder:free` |
| 用户发言 | `AI 可以提升反馈效率。` |
| AI mock 回复 | `反驳要点：请补充事实依据。` |
| 评分结果 | `logic_score=8`、`evidence_score=7`、`fluency_score=9` |

测试环境使用内存数据库，每个测试用例独立创建和销毁数据库结构，避免测试间互相污染。

## 10. 测试执行结果

### 10.1 默认测试结果

最近一次执行命令：

```bash
uv run pytest --cov=app --cov-report=term-missing
```

执行结果：

```text
168 passed, 4 deselected
app/ 覆盖率 100%
```

说明：

- 168 个默认测试全部通过。
- 4 个 `real_api` 测试被默认跳过。
- 后端 `app/` 目录 711 条语句全部覆盖。

### 10.2 真实 API 测试结果

最近一次执行命令：

```bash
uv run pytest -m real_api
```

执行结果：

```text
4 passed, 168 deselected
```

说明：

- 当前 `.env` 已配置 `LLM_API_KEY`。
- 真实 API 测试可以运行。
- 执行过程中 OpenRouter 可能触发免费模型限流，测试代码会将限流作为可接受的外部服务状态处理，并验证相关代码路径。

### 10.3 当前统计

| 指标 | 数值 |
|------|------|
| 测试文件数 | 20 |
| 默认测试用例数 | 168 |
| 真实 API 测试用例数 | 4 |
| 总测试用例数 | 172 |
| 默认测试通过率 | 100% |
| 真实 API 测试通过率 | 100% |
| 后端代码覆盖率 | 100% |

## 11. 可靠性保障

项目通过以下方式提升可靠性：

- 使用单元测试保证基础逻辑稳定。
- 使用集成测试验证 API、Service、Repository、数据库之间的协作。
- 使用内存数据库隔离测试数据。
- 使用 mock LLM 避免日常测试依赖外部网络。
- 使用真实 API 测试验证外部服务兼容性。
- 使用统一错误响应格式，方便前端稳定处理异常。
- 对流式接口使用 SSE `error` 事件返回异常。
- 对流式生成中的异常执行数据库事务回滚，避免半成功数据。
- 对大模型调用设置 fallback 模型链，降低单个模型失败的影响。
- 对评分接口实现缓存，避免重复评分导致结果不一致或浪费额度。

## 12. 容错设计验证

| 容错场景 | 验证方式 |
|----------|----------|
| 未配置 API Key | LLMClient 自动进入 mock 模式 |
| 模型调用失败 | fallback 模型链测试 |
| 流式接口返回空内容 | SSE error 事件测试 |
| 流式生成中异常 | 数据库回滚测试 |
| 超过三轮继续发言 | 返回 409 conflict |
| 提前评分 | 返回 409 conflict |
| 会话不存在 | 返回 404 not_found |
| 请求参数非法 | 返回 400 validation_error |
| 未预期异常 | 返回统一 500 internal_server_error |
| 评分 JSON 格式异常 | EvaluationParser fallback |

## 13. 兼容性验证

项目当前没有传统意义上的遗留系统交互，但存在以下兼容性要求：

- 前端与后端 API 契约兼容。
- 前端与后端 SSE 事件格式兼容。
- 后端与 OpenRouter Chat Completions API 兼容。
- 支持多个可选模型和 fallback 模型。
- CORS 支持本地前端开发地址。
- 测试环境与开发环境配置隔离。

相关测试已经覆盖前后端契约、CORS、OpenRouter 真实调用和模型 fallback。

## 14. 代码审查说明

当前项目主要依靠自动化测试、覆盖率报告和模块化结构作为质量门禁。代码结构按 Controller、Service、Repository、Schema、Client、Utils 分层，便于审查。

建议正式验收时补充人工代码审查记录，审查重点包括：

- 接口参数校验是否完整。
- 错误响应是否统一。
- 数据库事务是否正确提交或回滚。
- 大模型调用失败时是否有降级策略。
- 前后端字段命名是否一致。
- 是否存在硬编码密钥或敏感信息泄漏。
- 测试是否覆盖主流程、异常流程和边界条件。

## 15. 课堂十问对照

| 问题 | 回答口径 | 对应证据 |
|------|----------|----------|
| Q1 到目前为止测试覆盖率是多少 | 后端 `app/` 目录覆盖率 100% | `uv run pytest --cov=app --cov-report=term-missing` |
| Q2 能举一个单元测试例子吗 | 可以，例如评分 JSON 解析、Schema 参数校验、Prompt 构造 | `tests/test_evaluation_parser.py`、`tests/test_schemas.py`、`tests/test_prompt_builder.py` |
| Q3 如何进行集成测试 | 使用 Flask test client + 内存 SQLite，覆盖 API、Service、Repository、DB 协作 | `tests/test_start_api.py`、`tests/test_stream_api.py`、`tests/test_evaluate_api.py` |
| Q4 有没有可靠性指标，如何保证可靠性 | 有通过率、覆盖率、异常路径、事务回滚、fallback、性能基线 | 覆盖率报告、容错测试、性能基线测试 |
| Q5 是否需要与遗留系统交互，有无兼容性计划 | 无传统遗留系统；重点验证前后端契约、CORS、OpenRouter 兼容 | `tests/test_frontend_contract.py`、`tests/test_real_api.py` |
| Q6 怎么做代码审查 | 目前以自动化测试和覆盖率作为质量门禁，建议补充人工审查记录 | 本文档第 14 节 |
| Q7 项目中是否有容错设计 | 有 mock 降级、模型 fallback、统一错误响应、SSE error、事务回滚 | `tests/test_debate_service_extra.py`、`tests/test_llm_client.py` |
| Q8 如何进行性能测试 | 已加入本地 mock 轻量性能基线，验证接口没有明显退化 | `tests/test_performance_baseline.py` |
| Q9 如何进行验收测试 | 使用完整 MVP 主流程自动化验收测试 | `tests/test_acceptance_flow.py` |
| Q10 如何准备测试文档 | 已准备完整测试文档，包含范围、策略、用例、结果和风险 | `TEST_DOCUMENT.md` |

## 16. 风险与改进计划

| 风险 | 当前处理 | 后续改进 |
|------|----------|----------|
| 外部大模型限流 | 默认测试使用 mock，真实 API 单独运行 | 增加更稳定的测试模型或专用测试额度 |
| 浏览器真实交互未自动化 | 当前使用前后端契约测试 | 后续加入 Playwright E2E 测试 |
| 压测不足 | 当前只有轻量性能基线 | 后续使用 Locust、k6 或 JMeter 做并发压测 |
| 人工代码审查记录不足 | 当前依赖自动化测试门禁 | 补充代码审查表和审查记录 |
| 长时间运行稳定性未知 | 当前未做长稳测试 | 增加长时间运行和资源占用监控 |

## 17. 测试结论

当前项目已经建立了较完整的自动化测试体系，覆盖单元测试、集成测试、容错测试、契约测试、验收测试、性能基线测试和真实 API 测试。默认测试 168 个用例全部通过，真实 API 测试 4 个用例全部通过，后端 `app/` 目录代码覆盖率达到 100%。

从课程验收角度看，当前测试方案已经能够支撑核心功能可靠性说明，并能针对课堂提出的 10 个测试相关问题给出明确证据。后续可进一步补充浏览器端 E2E 测试、并发压测和正式代码审查记录，以提升工程完整度。
