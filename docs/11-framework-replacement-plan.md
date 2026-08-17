---
document_id: FRAMEWORK-REPLACEMENT-PLAN
document_role: RAGFlow 三桶拆解与 LangChain/LangGraph 框架替代实施计划（下一轮路线图提议）
status: proposed
document_version: "0.1.0"
created_at: "2026-08-17"
last_updated_at: "2026-08-17"
project_root: "D:/download/ragflow-agent"
ragflow_reference_commit: "cd846cc9d4e32a19e684c59a1f302601027ef976"
---

# RAGFlow 功能拆解与框架替代实施计划

## 文档导航

[项目总纲](./00-project-master.md) · [开发路线图](./05-development-roadmap.md) · [决策与风险](./07-decisions-and-risks.md) · [能力矩阵](./02-ragflow-capability-matrix.md) · [代码复用策略](./04-code-reuse-strategy.md) · [目标架构](./03-target-architecture.md) · [阶段状态索引](./phases/README.md)

## 0. 文档定位与状态

- **[规划]** 本文档是"下一轮路线图"的提议输入，**不是 Phase 11**；文档编号 `11` 是文档编号，不是阶段编号。路线图仍按 [AGENTS.md](./AGENTS.md) 第 1 条维持"没有 Phase 11"。
- **[规划]** 按 [AGENTS.md](./AGENTS.md) 实施规则，任何落地实现前必须先形成 ADR，并经用户确认进入下一轮路线图。
- **[事实]** 本文拆解基于 RAGFlow Python 路径的**模块级职责**；结论在 [ADR-005](./07-decisions-and-risks.md) 冻结基线 `cd846cc9d4e32a19e684c59a1f302601027ef976` 的 Python 路径同样成立（`api/`、`rag/`、`agent/`、`deepdoc/`、`common/` 的模块与职责在冻结基线与当前 `main` 一致）。Go 路径不分析、不复现、不作为参考（[ADR-004](./07-decisions-and-risks.md)）。
- **[事实]** 本项目已按 [ADR-002](./07-decisions-and-risks.md)、[ADR-017](./07-decisions-and-risks.md) 落地混合架构：Agent 编排用 LangGraph，模型/Embedding/Tool/结构化输出用 LangChain，领域/检索/解析/生命周期/权限/Trace/评测为自研。本文档的 Part B 是对这一现状的**复核**，不是从零规划。
- 状态标签沿用 [项目总纲 0.1](./00-project-master.md)：事实 / 决策 / 规划 / 待确认 / 范围外 / 风险。

---

## Part A. RAGFlow 功能拆解（三桶）

把 RAGFlow Python 功能按"能否被 LangChain/LangGraph 替代"拆成三类。这里"替代"的定义是：**框架替代编排骨架与标准能力，自研保留产品语义与专有能力**——不是"全用框架"也不是"全自研"。

### A.1 能被框架完全替代的（直接换，无需自研核心）

| 功能 | RAGFlow 位置 | 框架替代物 | 注意 |
|---|---|---|---|
| LLM 对话/生成（含流式） | `rag/llm` 生成部分（`LLMBundle`） | LangChain `ChatModel` + `stream()` | 流式要映射回前端 SSE 契约 |
| Embedding | `rag/llm` | LangChain `Embeddings` | 核对各 provider 覆盖；小众模型写适配类 |
| 带工具 Agent 的循环骨架 | `agent/component/agent_with_tools.py` | LangGraph `create_react_agent` / `StateGraph` | 循环骨架给框架；工具是自研（见 A.2） |
| 纯文本切块（按分隔符/长度） | chunking | LangChain `TextSplitter` | 仅纯文本；版面切块不能换（见 A.3-B） |
| 会话级记忆持久化 | `memory/` 基础 | LangGraph `Checkpointer` | 自定义记忆语义要保留（见 A.2） |
| 简单向量检索（无自定义过滤） | 部分 `common/doc_store` | LangChain `VectorStore` + `Retriever` | 只覆盖最基础场景 |
| RAG 链的"串联调度管道" | `rag/app/*`、`rag/flow` | LCEL `RunnableSequence` | 管道给框架，节点自研 |

> 这类是"轮子"：RAGFlow 只是薄封装。用框架换掉后代码变短、功能不丢。

### A.2 部分能实现：拆到功能边界（框架接管标准段，自研保留专有段）

| 功能 | RAGFlow 位置 | 框架接管 | 保留自研（包成节点/组件） |
|---|---|---|---|
| 通用 RAG 问答 | `rag/app/naive.py` | 管道串联、重试、流式（LCEL） | 混合检索、`kb_prompt`、引用生成、多轮改写 |
| Agent 带工具 | `agent/component/agent_with_tools.py` | 循环骨架、状态、检查点（LangGraph） | 组件→工具适配、MCP 工具、结构化输出强制、SSE 事件映射 |
| 向量检索整体 | `common/doc_store` | 连接、基础查询（vectorstore） | 混合检索、metadata 过滤 DSL、文档状态过滤 |
| 重排 Rerank | `rag/advanced_rag`、`rag/llm` | Reranker 标准接口 | 多 provider + 本地 bge-rerank 实现 |
| 记忆 | `memory/` | 持久化、会话存储（checkpointer） | 自定义记忆语义（长期记忆、摘要） |
| 外部数据源 | `common/data_source` | 通用 loader（wiki/jira/slack/github） | 专有源（akshare/SharePoint/钉钉等） |
| 文档型应用 | `rag/app/paper,book,table,laws,resume,manual,qa` | 问答链管道（LCEL） | 专属解析器 + 专属提示词/检索逻辑 |
| GraphRAG | `rag/graphrag` | 图存储访问基础 | 实体抽取、图谱构建、图检索管线、提示词 |
| 多轮对话优化 | `rag/flow` | 对话链编排 | 问题改写、上下文压缩、引用提示词 |
| 画布执行引擎 | `agent/canvas.py` | 图执行（LangGraph 节点/边/状态） | 画布 UI、DSL、组件库（见 A.3-C） |

> 两端都保留 → 功能不丢；手写调度被框架删掉 → 变简单。这是改造主力。

### A.3 替代不了的，三类处理

#### A.3-A 包成扩展点插进框架（重写不了，但能变成节点/工具/检索器）

| 能力 | RAGFlow 位置 | 包装成 |
|---|---|---|
| 混合检索 + 过滤 DSL | `common/metadata_es_filter.py`、`metadata_infinity_filter.py` | 自定义 `BaseRetriever` |
| 引用生成 | `rag/prompts/generator.py`（citation_plus） | `RunnableLambda` / 节点 |
| 知识检索组件 | `agent/component/` | 节点 / `BaseRetriever` |
| RAGFlow 组件作为工具 | `agent/component/*` | `@tool` / `BaseTool` |
| 提示词模板 | `rag/prompts/`（kb_prompt 等） | `PromptTemplate` |
| 结构化输出强制 | `json_repair` 相关 | 节点 |

#### A.3-B 留在框架外做"数据准备"（产出 Document/切块，框架只管消费）

| 功能 | RAGFlow 位置 |
|---|---|
| 深度解析与 OCR | `deepdoc/`（pdf/docx/excel/ppt/html、布局分析、OCR、云解析器） |
| 版面感知切块（表格/图表/版面） | chunking 专有部分 |
| 视觉/版面模型 | `deepdoc/vision` |

#### A.3-C 完全不动（产品壳，框架不涉及）

| 功能 | RAGFlow 位置 |
|---|---|
| 多租户 API 服务、认证、知识库/文档/会话管理 | `api/` |
| 元数据存储 | `api/db`（Peewee 模型、MySQL） |
| 多渠道接入 | `api/channels`（飞书/钉钉/Slack/微信/Telegram/Line） |
| 异步入库任务流水线 | `rag/svr/task_executor.py`（队列、状态机、checkpoint） |
| 数据源同步 | `rag/svr/sync_data_source.py` |
| 画布产品层（UI + DSL + 组件库 + 插件 + 沙箱） | `web/` 画布页、`agent/canvas.py`、`agent/plugin`、`agent/sandbox` |
| 前端全部、SDK、部署 | `web/`、`sdk/python`、`conf/`、`docker/`、`helm/` |

---

## Part B. 映射到本项目代码（现状复核）

把 Part A 的每个桶映射到 `src/ragflow_agent` 的真实模块，并给出当前状态。状态分三种：

- ✅ **已用框架**：已由 LangChain/LangGraph 接管（符合 A.1/A.2 的"框架段"）。
- ✅ **正确自研**：属于 A.3 的能力/产品壳，自研是正确选择，不应替换。
- ⚠️ **候选差距**：可能还能进一步交给框架，需要证据复核（见 Part C）。

| RAGFlow 三桶项 | 本项目模块 | 现状 | 证据 |
|---|---|---|---|
| A.1 LLM 调用/生成 | `knowledge/infrastructure/models/langchain_openai.py::LangChainChatProvider` | ✅ 已用 LangChain（`ChatOpenAI.ainvoke`） | 代码可见 |
| A.1 Embedding | 同文件 `LangChainEmbeddingAdapter` | ✅ 已用 LangChain（`OpenAIEmbeddings.aembed_documents`） | 代码可见 |
| A.1 结构化输出 | `agent/infrastructure/langchain/model.py::LangChainStructuredModelAdapter` | ✅ 已用 LangChain（`with_structured_output`） | 代码可见 |
| A.1 Agent 循环骨架 | `agent/graphs/minimal_agent.py`、`agent/graphs/agentic_rag.py` | ✅ 已用 LangGraph `StateGraph`；自定义节点是**治理设计**（预算/证据/HITL 在应用层环绕节点），非缺口 | 代码可见 |
| A.1 Checkpoint | `agent/infrastructure/checkpoint/postgres.py`、`scoped.py` | ✅ 已用官方 `AsyncPostgresSaver` + 租户作用域 | ADR-017 |
| A.1 纯文本切块 | `knowledge/infrastructure/chunking/general.py` | ⚠️ 自研；可评估是否换 LangChain `TextSplitter`（须保持 `sha256-v1` 稳定 ID 与黄金输出一致） | 候选 G-3 |
| A.2 固定 RAG 链 | `knowledge/application/fixed_rag.py` | ✅ 检索/上下文预算自研（正确）；模型调用走 `ChatProviderPort`（LangChain）；**提示词是硬编码字符串** | 候选 G-1 |
| A.2 检索管道 | `knowledge/application/query/retrieve.py`（+ fusion/rerank/fallback/clean/filters） | ✅ 正确自研：全文/向量双路、RRF、Rerank 回退、阈值清理、降级、权限 push-down、Trace。LangChain retriever 无法承载权限与 Trace 契约 | 代码可见 |
| A.2 查询改写/翻译/关键词 | `knowledge/application/query/transforms.py`、`preprocess.py` | ✅ 编排自研（正确）；模型调用走 `QueryTransformProviderPort` | 代码可见 |
| A.2 Reranker | `knowledge/infrastructure/models/bge_reranker.py` | ✅ 端口隔离自研（正确）；LangChain 无更优的本地 BGE 集成 | 代码可见 |
| A.2 Agentic RAG 编排 | `agent/graphs/agentic_rag.py` + `agent/application/agentic_runtime.py` | ✅ LangGraph + 自研治理（Evidence/Budget/HITL/Memory） | ADR-023 |
| A.2 记忆 | `agent/application/memory.py` | ✅ LangGraph checkpoint + 自研治理（consent/TTL/隔离） | ADR-023 |
| A.3-A 知识检索能力 | `agent/tools/knowledge_base.py`（KnowledgeBaseTool） | ✅ 正确自研，走共享 `KnowledgeQueryService` | ADR-009 |
| A.3-B 解析/OCR | `knowledge/infrastructure/parsers/*`、`ocr/tesseract.py` | ✅ 正确自研（八格式 + Tesseract + 资源门禁） | ADR-020 |
| A.3-C 生命周期/权限/Trace/评测/API/Worker | `knowledge/application/lifecycle/*`、`permission_service.py`、`api/`、`worker/`、`knowledge/evaluation/` | ✅ 正确自研（产品壳与领域治理） | ADR-022/018/021 |

**复核结论（事实级）**：项目已按本拆解落地，`✅` 项合计覆盖全部 RAGFlow 功能面。真正剩余的是 4 个**低风险候选差距**，且都有明确的不换理由或需验证前提：

| 候选 | 内容 | 初步判断 |
|---|---|---|
| G-1 | `fixed_rag.py` 提示词迁移到 `ChatPromptTemplate` | 低收益；仅一致性收益；需黄金测试证明输出不变 |
| G-2 | 固定 RAG 流式生成（LangChain `astream`） | 取决于产品是否需要流式；当前无流式是范围决定，非缺口 |
| G-3 | 纯文本切块换 LangChain `TextSplitter` | 低收益；须保持 `sha256-v1` 稳定 ID 与黄金输出一致，建议不换 |
| G-4 | Agent 图迁移到 `create_react_agent` | **预计丢失治理**（预算/证据/HITL/确定性决策），建议不换；仅当评测证明收益才做 |

---

## Part C. 实施计划（下一轮路线图提议）

### C.0 总体判断

- **[事实]** 本项目已是"LangGraph 编排 + LangChain 模型/工具 + 自研领域/检索/解析/治理"的混合架构，Part A 的拆解已 90% 落地。
- **[决策]** 本计划的目标不是"最大化用框架"，而是：**复核现状 → 消除残留的自研轮子（若有）→ 守住"无功能损失"契约 → 保持纪律**。禁止为了"用框架"而放宽权限、Trace、确定性评测或 ADR-021/022/023 契约。
- **[范围外]** 不重写 `parsers`、`lifecycle`、`permission`、`trace`、`evaluation`；不引入 Phase 11；不拆微服务；不引入 UI。

### C.1 阶段提案 1：框架替代度复核与登记（0 代码）

把 Part B 的映射逐项用真实代码与测试验证，为 G-1 至 G-4 各形成一条"换 / 不换 / 需实验"结论，并回填 [能力矩阵](./02-ragflow-capability-matrix.md)。

任务（示例编号 `FR-T01` 起，按 AGENTS.md 规则不擅自归入既有阶段）：

| 任务 | 内容 | 验收 |
|---|---|---|
| FR-T01 | 逐项核对 Part B 表格与真实代码/测试一致；修正本文档漂移 | 每条有模块路径 + 关键符号 + 测试证据 |
| FR-T02 | 对 G-1 至 G-4 各写一条决策说明（引用代码、黄金测试、评测） | 4 条结论明确；不换的给出不换理由 |
| FR-T03 | 结论回填能力矩阵与本文档；列出是否需要 ADR | 文档一致；需要时形成 ADR 草案 |

验收：`uv run ruff check .`、`uv run mypy src/ragflow_agent tests`、`uv run pytest` 全绿（本阶段 0 代码变更）。

### C.2 阶段提案 2：微整合（可选、低风险、每项独立可回退）

仅当 C.1 确认存在真正差距时执行；每项独立提交、独立黄金/契约测试、独立回退。

| 任务 | 内容 | 无功能损失证明 |
|---|---|---|
| FR-T10 | 如采纳 G-1：`fixed_rag.py` 提示词迁移 `ChatPromptTemplate` | 固定问答黄金输出与迁移前一致；`input/output_tokens`、Citation、Trace 不变 |
| FR-T11 | 如采纳 G-2：固定 RAG 流式（`astream`），SSE 契约自研 | 流式分片与既有无流式回答在内容上一致；确定性评测不触发 |
| FR-T12 | 如审计发现重复的 provider 构造代码，统一到 LangChain 适配层 | 契约测试通过；无行为变化 |

验收：每个任务有迁移前后对比的黄金/契约测试；确定性评测 no-go 门禁不触发；关键安全违规 0。

### C.3 阶段提案 3：候选实验（仅当 C.1 证据支持）

| 任务 | 内容 | 门禁 |
|---|---|---|
| FR-T20 | 如采纳 G-4：评估 Agent 图迁移 `create_react_agent` 的收益/损失 | 用现有确定性评测对比工具选择合法率、预算执行、证据判定、恢复成功率；无收益则按 Phase 09 惯例记录 no-go 并保持现状 |

### C.4 依赖与顺序

```
C.1 复核（0 代码，必做） → C.2 微整合（可选） → C.3 候选实验（由 C.1 证据门禁）
```

- C.1 是唯一"必做"；C.2/C.3 都由 C.1 的证据决定是否立项。
- 任何进入实现的任务，必须先形成 ADR 并经用户确认（AGENTS.md 第 5、6 条）。

---

## Part D. 验收与门禁

1. 每阶段照 [AGENTS.md](./AGENTS.md) 任务完成规则执行 `uv run ruff check .`、`uv run mypy src/ragflow_agent tests`、`uv run pytest`；迁移/API/Worker/容器变更另加专项命令。
2. "无功能损失"的最硬证明 = 迁移前后同一黄金输入/输出 + 确定性评测（`datasets/`）不降级 + 关键安全违规 0 + 权限/Trace/Citation 契约测试全绿。
3. 状态标签：未实现一律标 `[规划]`；批准用 `[决策]`；范围外用 `[范围外]`。
4. 本计划被采纳或拒绝都要更新 [项目总纲](./00-project-master.md)、[路线图](./05-development-roadmap.md)、[能力矩阵](./02-ragflow-capability-matrix.md) 与本文档。

---

## Part E. 风险与开放问题

| 编号 | 风险/问题 | 控制措施 | 状态 |
|---|---|---|---|
| FR-R-01 | 拆解基于当前 `main` 的 Python 路径，与冻结基线有漂移 | 按 ADR-005 只引用冻结基线 `cd846cc`；本文 Part A 为模块级职责，两处一致 | Monitoring |
| FR-R-02 | 微整合引入回归 | 黄金测试 + 确定性评测 + 独立回退 | Open |
| FR-R-03 | `create_react_agent` 或框架组件丢失治理（预算/证据/HITL） | C.3 用确定性评测对比；无收益即 no-go 并保持现状 | Open |
| FR-R-04 | 真实 Provider 效果未验证，Fake 结论被误当真实 | 沿用 ADR-019/021 的 Fake/真实分离报告 | Monitoring |
| FR-O-01 | 是否需要流式固定 RAG（G-2） | 由产品需求决定；当前无流式是范围决定 | 待确认 |

---

## 维护记录

| 日期 | 版本 | 变更 |
|---|---|---|
| 2026-08-17 | 0.1.0 | 创建：RAGFlow 三桶拆解、映射到本项目代码的现状复核、下一轮路线图实施计划提议 |
