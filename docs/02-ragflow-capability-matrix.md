---
document_id: RAGFLOW-CAPABILITY-MATRIX
status: active
last_updated_at: "2026-08-17"
ragflow_frozen_baseline_commit: "cd846cc9d4e32a19e684c59a1f302601027ef976"
---

# RAGFlow 能力与目标采用矩阵

## 文档导航

[项目总纲](./00-project-master.md) · [RAGFlow 架构](./01-ragflow-architecture.md) · [目标架构](./03-target-architecture.md) · [代码复用策略](./04-code-reuse-strategy.md) · [开发路线图](./05-development-roadmap.md) · [工程标准](./06-engineering-standards.md) · [决策与风险](./07-decisions-and-risks.md) · [领域契约](./08-domain-model-and-contracts.md) · [Agentic RAG](./10-agentic-rag.md)

## 1. 使用规则

本文件是能力名称、责任归属、采用分类、实施阶段和当前状态的规范来源。其他文档引用能力时必须使用本文件的 `CAP-*` 编号和完整名称。Phase 00 原始基线形成 `CAP-01` 至 `CAP-42`；2026-07-30 用户恢复时序 RAG 范围后新增 `CAP-43`。

- RAGFlow 代码位置均相对于冻结 commit `cd846cc9d4e32a19e684c59a1f302601027ef976`。
- “LangChain 能否承担”和“LangGraph 能否承担”描述框架原生或合理扩展能力，不代表项目已经实现。
- 采用分类只能使用：`直接复用`、`改造复用`、`参考重写`、`自行开发`、`暂缓`。
- 当前状态必须按已验证的阶段事实记录：Phase 00 至 Phase 09 已完成；所有高级能力因缺少真实 Provider 增益证据继续默认关闭。
- 复用的具体源文件、依赖和改造办法见[代码复用策略](./04-code-reuse-strategy.md)。
- 已实际核验的类、函数和调用关系集中登记在[源码证据地图](./research/ragflow-source-map.md)；矩阵中的路径不能脱离该冻结 commit 解释。

## 2. 能力矩阵

| ID | 能力名称 | RAGFlow 是否具备 | RAGFlow 代码位置 | LangChain 能否承担 | LangGraph 能否承担 | 采用方式 | 复用分类 | 实施阶段 | 验收方法 | 当前状态 |
|---|---|---|---|---|---|---|---|---|---|---|
| CAP-01 | 多格式文档解析 | 是 | `deepdoc/parser/{pdf,docx,excel,ppt}_parser.py`；`rag/app/naive.py::chunk`；`chunk_builder.py::get_parser` | 部分：标准 Loader | 否 | 统一 ParserPort；八类 Parser 均独立实现，不复制 RAGFlow | 自行开发 | Phase 04 最小路径；Phase 05 完整 | PDF、DOCX、PPTX、XLSX、TXT、MD、HTML、图片黄金样本 | 已实现并验收八类格式、确定性 MIME/扩展路由、结构黄金、资源门禁、内存与真实后端 E2E |
| CAP-02 | OCR 与版面分析 | 是 | `deepdoc/vision/`；`deepdoc/parser/pdf_parser.py::RAGFlowPdfParser` | 否 | 否 | 自定义 OCR Port + 外部 Tesseract；格式原生/PDF/OCR bbox；不采用 RAGFlow Vision 模型 | 自行开发 | Phase 05 基线；复杂模型版面后续再决策 | 扫描 PDF、图片 OCR、坐标、语言包和资源上限测试 | 已实现 Tesseract CPU OCR、扫描页 fallback、word/line bbox、置信度与稳定错误；复杂多栏语义版面和模型表格识别未实现 |
| CAP-03 | 统一文档结构 | 部分 | DeepDOC sections、positions、tables、images 字段 | 部分：Document 类型不足 | 否 | 自定义 ParsedDocument/ParsedBlock，适配各 Parser 输出 | 自行开发 | Phase 03 契约；Phase 05 全 Parser 落地 | 所有 Parser 通过同一契约测试，保留页码、bbox、层级和来源顺序 | schema v2 已在八类 Parser 落地：六类 Block、page/bbox/heading/table/image/source order/parser/source/warning；Elasticsearch/Citation 保留 bbox |
| CAP-04 | 场景化 Chunk Method | 是 | `rag/svr/task_executor_refactor/chunk_builder.py::get_parser/run_chunking`；`rag/app/{naive,paper,book,manual,laws,qa,table,resume,picture,audio,email}.py::chunk` | 部分：Text Splitter | 否 | 建立 ChunkerPort/Registry 并独立实现九种策略 | 自行开发 | Phase 04 General；Phase 05 完整 | 每种策略固定输入、黄金 Chunk、稳定 ID、Token 上限和重叠测试 | General、Paper、Book、Manual、Laws、QA、Table、Resume、Picture 已逐项通过确定性、来源、稳定 ID、table/QA 边界验收；Audio/Email 不在 Phase 05 |
| CAP-05 | Chunk 自动关键词 | 是 | `rag/svr/task_executor_refactor/chunk_service.py::build_chunks` → `chunk_post_processor.py::extract_keywords`；`rag/prompts/generator.py::keyword_extraction` | 是：模型、Prompt、结构化输出 | 否 | 独立实现，公开行为只作依据 | 参考重写 | Phase 09 | 关键词数量、格式、可重复性、失败降级、成本和检索增益测试 | 已实现确定性基线；experimental/off，真实 Provider 增益未验证 |
| CAP-06 | Chunk 自动问题 | 是 | `rag/svr/task_executor_refactor/chunk_service.py::build_chunks` → `chunk_post_processor.py::generate_questions`；`rag/prompts/generator.py::question_proposal` | 是 | 否 | 独立实现，公开行为只作依据 | 参考重写 | Phase 09 | 问题格式、覆盖度、去重、失败降级、成本和检索增益测试 | 已实现确定性基线；experimental/off，真实 Provider 增益未验证 |
| CAP-07 | 摘要、标题与 TOC | 部分 | `ChunkService.insert_chunks/_create_mother_chunks`；`TaskHandler._build_toc`；`PostProcessor.insert_toc_chunk`；RAPTOR summary | 是 | 部分：可编排 | Phase 05 保留结构字段；Phase 09 独立实现三层摘要、确定性 TOC、父子扩展与 RAPTOR | 参考重写 | Phase 05 结构契约；Phase 09 自动生成/父子/RAPTOR | 层级、页码、来源映射、忠实度、Token 预算、父子关系和重建测试 | 已实现并通过来源/预算/收敛测试；默认关闭，真实生成质量未验证 |
| CAP-08 | Embedding 与索引写入 | 是 | `rag/svr/task_executor_refactor/embedding_service.py::EmbeddingService.embed_chunks`；`chunk_service.py::ChunkService.insert_chunks` | 是：Embeddings | 否 | LangChain Embeddings + 自研版本和 SearchIndexPort；参考字段构造 | 参考重写 | Phase 04 | 批处理、维度、模型版本、失败重试、索引可检索和重建测试 | Phase 04 已实现 BGE-M3 OpenAI-compatible Adapter、维度/模型/input 校验和 Elasticsearch bulk/版本激活；真实 BGE 服务未作为 CI 前置 |
| CAP-09 | 全文检索 | 是 | `rag/nlp/query.py::FulltextQueryer.question`；`rag/nlp/search.py::Dealer.search` | 部分 | 否 | SearchPort 实现 BM25；参考 query/tokenizer | 参考重写 | Phase 04 基线；Phase 06 完整 | 关键词、短语、过滤、排名和真实后端评测 | Phase 06 已完成独立全文通道、短语 boost、硬过滤 push-down、原始分数/排名与真实 Elasticsearch 验证；复杂中文 analyzer 未实现 |
| CAP-10 | 向量检索 | 是 | `Dealer.get_vector/search/_knn_scores`；`MatchDenseExpr`；各 DocStore | 是：Retriever/VectorStore | 否 | LangChain Embeddings + SearchPort KNN | 参考重写 | Phase 04 基线；Phase 06 完整 | Recall@K、维度/版本、阈值、过滤和真实后端测试 | Phase 06 已完成独立 KNN 通道、同一硬过滤、原始分数/排名与真实 Elasticsearch 验证；真实 BGE-M3 质量/性能未验证 |
| CAP-11 | 混合检索 | 是 | `Dealer.search/retrieval/rerank_with_knn`；`FusionExpr` | 部分 | 否 | 全文和向量候选统一到 RetrievalCandidate 后融合 | 自行开发 | Phase 04 基线；Phase 06 完整 | 相对全文/向量基线提升；融合排序和后端集成测试 | 已完成：真实 Elasticsearch BM25+KNN 双路召回、按 chunk_id 去重、RRF k=60；小型夹具 Recall@3 从单路 0.5 提升到 1.0 |
| CAP-12 | 查询改写与独立问题生成 | 是 | `generator.py::full_question` | 是 | 是：决定是否改写和重试 | 内部结构化 QueryTransform Provider；Phase 08 才由 LangGraph 决定多步重试 | 参考重写 | Phase 06 | 多轮历史、无需改写、非法输出和失败回退 | 已完成 Provider 隔离、可关闭开关和 canonical query 回退；真实 DeepSeek 未验证 |
| CAP-13 | 跨语言查询 | 是 | `generator.py::cross_languages`；Dialog/Tool 调用 | 是 | 部分：路由 | 内部结构化 QueryTransform Provider，保留 canonical 与翻译变体 | 参考重写 | Phase 06 | 中英目标语言、去重、限额和失败降级测试 | 已完成协议、Provider Adapter 和 Fake/Stub 测试；真实 DeepSeek 跨语言质量未验证 |
| CAP-14 | 关键词扩展 | 是 | `generator.py::keyword_extraction`；`FulltextQueryer` synonym/term weight | 是 | 部分 | 确定性词法关键词 + 可选结构化 Provider，统一变体上限 | 参考重写 | Phase 06 | 扩展、去重、噪声上限、关闭和 Trace 测试 | 已完成独立实现；没有复制算法，也没有同义词词典服务或真实模型质量结论 |
| CAP-15 | 元数据过滤 | 是 | `common/metadata_utils.py::apply_meta_data_filter/meta_filter`；`generator.py::gen_meta_filter`；`DocMetadataService` push-down | 部分：SelfQuery 可参考 | 否 | 递归 AND/OR/NOT Filter AST，在 Search Adapter 编译并与硬过滤合并 | 参考重写 | Phase 06 | 操作符、类型、组合逻辑、非法字段、注入和真实后端测试 | 已完成：用户/推断过滤分离、递归 AST 和 Elasticsearch push-down；未知字段/操作符拒绝 |
| CAP-16 | 权限过滤 | 部分 | `Knowledgebase.permission`；`KnowledgebaseService._visibility_and_status_filter/accessible`；`check_team_permission.py`；`Dealer.retrieval` tenant index | 否 | 否 | `AuthorizationContext` + `PermissionChecker`；Search 强制 tenant/ACL/KB/index/文档状态，复杂 ACL 后置 | 自行开发 | Phase 03 契约；Phase 04 最小；Phase 06 完整；Phase 10 生产门禁 | 跨租户、owner/visibility/roles、文档状态和全部降级负向测试 | Phase 06 已完成 owner/tenant/actor/roles 与状态过滤及真实 ES 负向验证；复杂 RBAC/部门/动态规则仍后置 |
| CAP-17 | 空结果降级 | 部分 | `Dealer.search` 二次重查；`apply_meta_data_filter` 的 `None/[-999]`；`Dialog.prompt_config.empty_response`；Agentic abstain | 部分 | 是：降级路由和重试 | ADR-021 有限策略，最终结构化 `no_evidence`，系统错误单独失败 | 自行开发 | Phase 06 | 真空、阈值、推断过滤、单通道、依赖故障和硬过滤不变 | 已完成：最多四步可配置降级，永不放宽硬过滤；依赖错误不伪装空结果，全部步骤进入 Trace |
| CAP-18 | 候选清理与去重 | 是 | `Dealer._prune_deleted_chunks`；检索合并和 Chunk ID 去重 | 部分 | 否 | 自研 CandidateCleaner；后端先排除禁用/删除，应用层按 ID/阈值/每文档限额清理 | 参考重写 | Phase 06；Phase 07 权威状态防御 | 状态、重复、阈值、每文档限额、最终截断和删除竞态测试 | Phase 06 候选清理与 Phase 07 PostgreSQL 最终权威状态检查均已完成；删除/旧版本候选不能穿透最终结果 |
| CAP-19 | Reranker | 是 | `Dealer.rerank_by_model`；`LLMBundle.similarity` | 是：Reranker 适配 | 否 | 内部 RerankerPort + BGE HTTP Adapter；失败回 RRF | 参考重写 | Phase 06 | 排序、分数、候选身份、超时、异常和无模型降级 | Provider/Adapter、Fake 确定性测试和 RRF 回退已完成；真实 BGE Reranker/GPU 未验证 |
| CAP-20 | 分数融合、阈值与 TopK/TopN | 是 | `Dealer._rerank_window/retrieval/rerank_by_model/rerank_with_knn`；Dialog 字段 | 部分 | 否 | ScoreBreakdown 保存各阶段原始分数/排名；RRF→Rerank→阈值/TopN | 参考重写 | Phase 06 | RRF、tie、阈值、候选窗口、TopN 和回退稳定性 | 已完成独立实现并在 Trace 持久化全文/向量/融合/Rerank/最终排名；未实现多融合算法选择 |
| CAP-21 | 引用与来源定位 | 是 | `generator.py::kb_prompt/citation_prompt`；`Dealer.fetch_chunk_vectors/insert_citations`；`dialog_service.py::repair_bad_citation_formats` | 部分：Prompt | 否 | 沿用自研 Citation，统一在线检索只输出同授权/版本来源 | 参考重写 | Phase 04 基础；Phase 05 bbox；Phase 06 完整；Phase 07 删除防御 | 引用存在性、页码/bbox/quote/版本/权限、删除后不可见和回答公开字段 | 在线 Citation/source/trace_id 与删除后权威状态过滤已完成；准确率大数据集仍留 Phase 10 |
| CAP-22 | Retrieval Trace | 部分 | `Dealer.retrieval(trace_id)` 权重日志；`DialogService.async_chat` Langfuse LLM observation/耗时；无统一持久候选事件模型 | 部分：Callback | 部分：图 Trace | 自研内容最小化事件/候选模型、PostgreSQL Store、角色读取和 TTL 清理 | 自行开发 | Phase 04 基础；Phase 06 完整 | 阶段/候选/分数/模型/配置/降级可审计，tenant/权限/脱敏/TTL/失败测试 | 已完成 v2 持久 Trace、30 天 TTL、真实 PG 租户隔离与清理、写失败非阻断计数；未建设 180 天聚合指标仓库 |
| CAP-23 | 文档上传与解析任务 | 是 | `document_api.py::upload_document/parse_documents` → `FileService.upload_document` → `DocumentService.run` → `TaskService.queue_tasks` | 否 | 部分：可编排 | FastAPI 持久化 tenant-scoped IngestionJob 后投递；独立 Worker 按 tenant_id + job_id 加载并执行 | 参考重写 | Phase 04 基础；Phase 07 可靠化 | 上传、哈希、tenant 隔离、任务、进度、取消、失败和对象存储集成测试 | Phase 04 上传/队列/Worker 与 Phase 07 生命周期操作、Outbox、取消/进度和批量聚合均已实现；生产跨租户调度告警留 R-033 |
| CAP-24 | 文档更新与重新解析 | 是 | `document_api.py::update_document/parse_documents`；`DocumentService.clear_chunk_num_when_rerun/run`；旧 Task/Nav/DocStore delete | 否 | 部分 | 自研 DocumentVersion、候选索引验证、alias 切换和 PostgreSQL CAS 激活 | 自行开发 | Phase 07 | 旧版本持续可查、新版本原子切换、回滚、失败保留旧版 | 已完成：不可变版本、update/reparse、候选发布、旧版退休和回滚通过内存/真实四后端验证 |
| CAP-25 | 文档删除与索引同步 | 是 | `document_api.py::delete_documents` → `FileService.delete_docs` → `DocumentService.delete_document_and_update_kb_counts/remove_document/delete_chunk_images` → DocStore/ObjectStore | 否 | 部分 | 自研 tombstone、权威状态过滤、保留期回收和跨 PostgreSQL/ObjectStore/Search reconciliation | 自行开发 | Phase 07 | 正常删除、恢复、部分失败、重试、幂等、回收和引用不可见性 | 已完成：删除立即不可检索、恢复、幂等 purge、残留检测/安全修复和 tenant 隔离通过；生产定时调度留 R-033 |
| CAP-26 | 任务重试、取消与幂等 | 部分 | `TaskService.get_task` 领取计数/3 次放弃；`cancel_all_task_of/has_canceled`；Redis pending/requeue；`task_executor.handle_task` 异常后 ACK | 否 | 是：只编排 Agent 重试和恢复 | TaskQueuePort + IngestionJob/LifecycleOperation + Outbox；显式 transient/permanent/cancelled、有限退避、dead-letter 和 CAS/fencing | 自行开发 | Phase 04 最小；Phase 07 完整 | 重复投递、故障分类、死信、取消竞态、恢复、CAS 和无重复 Chunk | Phase 07 已完成错误分类、有限重试/死信、协作取消、Outbox、确定性 ID 和并发 CAS；ARQ 独立 ACK lease 与长时混沌未冒充验证 |
| CAP-27 | 固定 RAG 问答 | 是 | `chat_api.py::session_completion` → `dialog_service.py::rag_agent`（reasoning off）→ `async_chat` → `Dealer.retrieval` → `kb_prompt` → `LLMBundle` → Citation | 是 | 否 | 自研 FixedRAGService，使用统一 KnowledgeQueryService | 参考重写 | Phase 04 | 端到端答案、空结果、引用、流式输出和 Trace | Phase 04 固定 RAG 与 Citation/Trace E2E 已通过；FR-T11 新增流式 SSE 端点 `/v1/rag/query/stream`（LangChain `astream`，delta/done 事件）并经单元测试；真实外部模型未验证 |
| CAP-28 | KnowledgeBaseTool | 是 | `agent/tools/retrieval.py::Retrieval._retrieve_kb` → `settings.retriever.retrieval` → TOC/children/KG → `Canvas.add_reference`/`kb_prompt` | 是：Tool | 是：Tool 节点 | LangChain Tool 包装 KnowledgeQueryService；参考参数与引用输出 | 参考重写 | Phase 08 | 与固定 RAG 检索结果一致；结构化错误和引用测试 | 已完成：`KnowledgeBaseTool` 与直接 RAG 共享 `KnowledgeQueryService`，服务端注入权限，返回候选/Citation/Trace 引用；契约和两路径 E2E 通过 |
| CAP-29 | LangGraph 状态、路由与循环 | 部分 | `agentic_rag_graph.py::AgenticState/build_agentic_graph/run_agentic_rag`；主 Canvas 是自定义运行时 | 部分 | 是 | 自研 AgentState 和业务图，参考 Agentic RAG 节点 | 自行开发 | Phase 02 基础；Phase 08 知识检索循环 | 路由、循环上限、超时、取消、错误路径和状态序列 | 已完成：Phase 02 基础上增加直接/Tool RAG 路由、结构化规划、最多三轮检索、证据/Tool/HITL/终止图和服务端多维预算 |
| CAP-30 | Checkpoint 与运行恢复 | 否：Agentic 图未配置 Checkpointer | `agentic_rag_graph.py::build_agentic_graph` 以无参数 `g.compile()` 结束；`ainvoke` 无 thread_id | 否 | 是 | 使用 LangGraph Checkpointer，持久化 thread/run | 自行开发 | Phase 02 | 进程重启、节点失败、重复恢复和版本兼容测试 | 已实现并验收：官方异步 PostgreSQL Saver、租户作用域、版本迁移/拒绝、失败节点恢复、重复 resume 和跨租户失败关闭 |
| CAP-31 | Human-in-the-loop | 部分：Canvas 有 `userfillup/user_inputs`，非目标运行时 | `agent/canvas.py::Canvas._run_impl`；Agentic `StateGraph` 无 interrupt | 部分：Tool | 是 | LangGraph interrupt/resume + 审批数据模型；复用 Phase 02 Checkpoint/恢复协议 | 自行开发 | Phase 08 | 中断、审批、拒绝、超时、重复提交、权限重验和审计测试 | 已完成：八态审批、30 分钟 TTL、角色/tenant/Tool/version/参数摘要绑定、CAS、持久 Checkpoint 和幂等恢复通过 Fake 高风险 Tool 与真实 PostgreSQL 测试 |
| CAP-32 | 多 Agent 协作 | 部分 | Canvas Agent Invoke/组件与 Agentic orchestrator；无 LangGraph supervisor/worker 治理和持久共享状态 | 是：Tool/Agent 封装 | 是 | 在单 Agent 成熟后设计 supervisor/worker 图 | 暂缓 | Phase 08 评估；后续按收益重开 | 子 Agent 边界、共享状态、失败隔离、终止和成本测试 | 暂缓：Phase 08 单 Agent 的 28 场景确定性基线全部通过，暂无量化收益支撑 supervisor/worker 复杂度；出现单 Agent 无法满足的质量、隔离或吞吐需求时重评 |
| CAP-33 | GraphRAG | 是 | `TaskHandler._run_graphrag`；`general/index.py::run_graphrag_for_kb/generate_subgraph/resolve_entities/extract_community`；`checkpoints.py`；`phase_markers.py`；`search.py::KGSearch` | 部分 | 部分：构建/检索编排 | 独立实现实体/边/社区、幂等/取消/恢复和 provenance；不复制源码 | 参考重写 | Phase 09 | 图构建正确性、实体/关系质量、查询增益、版本绑定、重建、取消和 checkpoint 恢复 | 已实现协议与确定性算法；experimental/off、no-go，真实增益未验证 |
| CAP-34 | RAPTOR | 是 | `knowlege_compile/raptor.py::RecursiveAbstractiveProcessing4TreeOrganizedRetrieval`；`TaskHandler._run_raptor`；`RaptorService._generate_raptor` | 部分 | 部分：任务编排 | 独立实现严格收敛树、叶来源和版本绑定；不复制源码 | 参考重写 | Phase 09 | 层级树、叶 Chunk 来源、检索增益、成本、收敛和取消测试 | 已实现最多 4 层确定性基线；experimental/off、no-go |
| CAP-35 | 多模态 RAG | 是 | `rag/app/picture.py::chunk/vision_llm_chunk`、`audio.py::chunk`、`deepdoc/parser/figure_parser.py::VisionFigureParser`、LLMBundle Vision/ASR | 部分：模型接口 | 部分：流程编排 | 独立 Vision/ASR Port + 图片/图表/音频派生物与媒体 Citation；不复制源码 | 参考重写 | Phase 05 解析基础；Phase 09 跨模态检索 | 图片/音频解析、媒体来源映射、跨模态检索和引用测试 | 图片/图表/音频协议与 Fake 通过；视频未实现，真实模型未验证，off/no-go |
| CAP-36 | 模型注册与调用 | 是 | `LLMBundle`；`tenant_model_service.py`；`rag/llm/` | 是 | 否 | LangChain 模型接口；自研注册、密钥、配额、降级和审计 | 自行开发 | Phase 01 基础；Phase 04 最小可用；后续扩展 | 多供应商契约、流式、Token、超时、降级和密钥保护 | Phase 08 已将模型输入/输出 Token 与超时纳入 Agent budget，继续使用 DeepSeek OpenAI-compatible Provider 与 Fake CI；流式已实现（`LangChainChatProvider.stream` 经 LangChain `astream`，FR-T11）；真实调用、注册、配额和真实流式仍未验证 |
| CAP-37 | FastAPI 服务接口 | 否：RAGFlow 使用 Quart | `api/apps/` 仅作接口用例参考；`launch_backend_service.sh` 证明 API/Worker 可分进程 | 否 | 否 | 自研 FastAPI API 入口；与 Worker 同仓库共享应用/领域代码，不经内部 HTTP 调用 Worker | 自行开发 | Phase 01 基础；各阶段扩展 | OpenAPI、校验、错误、`AuthorizationContext`、流式、API/Worker 进程边界和集成测试 | Phase 04 已增加 KB 创建、文档上传、Job 查询和固定 RAG API；FR-T11 新增固定 RAG 流式 SSE 端点 `/v1/rag/query/stream`；开发身份仅限非生产，生产 IdP 未实现 |
| CAP-38 | 后台任务与 Ingestion 执行 | 是 | `TaskService.queue_tasks/get_task`；`RedisDB.queue_product/queue_consumer/get_unacked_iterator`；`task_executor.py::collect/handle_task`；`TaskManager.run_refactored_task`；`TaskHandler.handle_task`；`launch_backend_service.sh` | 否 | 部分：不承担数据面 Worker | 模块化单体 + 独立 Ingestion Worker；Redis/ARQ 隔离在 Queue Adapter，PostgreSQL Outbox 提供业务可靠边界 | 参考重写 | Phase 04 基础；Phase 07 可靠化 | 独立启动、tenant-scoped 消息、有限重试、取消、死信、幂等、进度、批量和恢复 | Phase 07 已完成 Outbox dispatcher、tenant envelope、进度/取消、错误分类/死信、批量聚合和 stale 对账；生产跨租户调度/告警留 R-033，长时 kill/网络分区留 R-034 |
| CAP-39 | 评测与回归门禁 | 部分：主要是性能 benchmark | `test/benchmark/dataset.py`；`metrics.py::summarize`；`report.py::{chat_report,retrieval_report}` | 部分：可接评测库 | 部分：图执行评测 | 自研检索、答案、引用、Agent、性能和回归体系 | 自行开发 | Phase 04 起建基线；Phase 10 完整门禁 | 固定数据集、Recall/MRR/NDCG、忠实度、引用正确率、Agent 成功率、性能阈值、基线对比和 CI 门禁 | Phase 10 已实现版本化 CC0 数据、检索/答案/Citation/Agent/九项高级能力评测、故意退化和 CI 门禁；Fake/隔离报告通过，真实模型与业务数据效果未验证 |
| CAP-40 | 日志、指标与链路追踪 | 部分 | logging；`common/token_utils.py::token_usage_sink`；LLMBundle/Langfuse；Dealer `trace_id` 日志；Docker OTEL/Jaeger 配置 | 部分：Callbacks | 部分：LangGraph events | 自研统一 Trace/metric schema，接入标准观测后端 | 自行开发 | Phase 01 基础；Phase 10 完整 | 请求到任务、检索、模型、Agent 的关联；trace 传播、采样和敏感信息检查 | Phase 10 已实现 JSON 日志、最小化 Trace、OTLP、Prometheus、十类低基数组件指标、Dashboard/告警并启动本地观测栈；30/90 天真实保留和通知通道未运营验证 |
| CAP-41 | 权限与安全 | 部分 | `Tenant`、`UserTenant`、KB permission、`add_tenant_id_to_kwargs`、`check_team_permission.py`、API token、认证配置、Sandbox | 否 | 部分：Tool 审批 | 第一版自研 tenant 强隔离、owner/visibility、AuthorizationContext、PermissionChecker；复杂 RBAC、部门和动态规则后置 | 自行开发 | Phase 03 第一版边界；Phase 06 检索；Phase 10 生产门禁 | 跨租户/owner/visibility/roles/状态/降级负向测试、密钥扫描、Tool 审批和审计 | Phase 10 全仓权限/Tool/SQL/API/SSRF/密钥/供应链负向门禁通过并提供 TLS/限流/默认拒绝网络配置；企业 IdP、复杂 RBAC 和企业系统接入为可选扩展 |
| CAP-42 | 生产部署、备份与恢复 | 是：RAGFlow 有 Docker/Helm | `docker/launch_backend_service.sh`；`docker/docker-compose{,-base}.yml`；`helm/templates/ragflow.yaml`；`helm/values.yaml` | 否 | 否 | 第一版同一制品启动 FastAPI 与独立 Worker；自研配置、迁移、备份和恢复手册，不拆微服务 | 参考重写 | Phase 10 | API/Worker 独立健康检查和扩缩容、全新部署、升级、回滚、备份恢复和容量测试 | Phase 10 已构建 Linux/amd64 non-root 镜像并启动隔离 Compose、一次性迁移、API/Worker/四后端/观测栈，完成 hash 恢复与故障演练；已达到本地或自有云运行条件，长期 RPO/RTO/SLO 属运行期验证 |
| CAP-43 | 时序 RAG | 部分：有 timeline 知识编译，不是完整时序 RAG | `api/db/init_data/compilation_templates/timeline.yaml`；`runner.py::run_structure_compile_over_batches/_compile_batch/_flush` → `structure.py::compile_structure_from_text/merge_compiled_structures/cleanup_timeline_isolated_entities` | 部分：模型/Prompt/Tool 适配 | 部分：查询与工具路由 | 自研事件时间线、UTC 数值窗口/聚合/趋势/相似历史、文本融合和时间 Citation；不引入时序数据库 | 自行开发 | Phase 09 | 时间过滤、乱序/缺失/时区、窗口聚合、事件/文本对齐、tenant/版本/删除、普通检索对照增益 | 已实现实验基线并通过确定性测试；experimental/off、no-go，真实数据规模未验证 |

## 3. 分类汇总

### 3.1 改造复用

`CAP-33`、`CAP-34`、`CAP-35`。

### 3.2 参考重写

`CAP-05`、`CAP-06`、`CAP-07`、`CAP-08`、`CAP-09`、`CAP-10`、`CAP-12`、`CAP-13`、`CAP-14`、`CAP-15`、`CAP-18`、`CAP-19`、`CAP-20`、`CAP-21`、`CAP-23`、`CAP-27`、`CAP-28`、`CAP-38`、`CAP-42`。

### 3.3 自行开发

`CAP-01`、`CAP-02`、`CAP-03`、`CAP-04`、`CAP-11`、`CAP-16`、`CAP-17`、`CAP-22`、`CAP-24`、`CAP-25`、`CAP-26`、`CAP-29`、`CAP-30`、`CAP-31`、`CAP-32`、`CAP-36`、`CAP-37`、`CAP-39`、`CAP-40`、`CAP-41`、`CAP-43`。

### 3.4 直接复用与暂缓

- 当前没有能力获批“直接复用”；源文件必须先经过[代码复用策略](./04-code-reuse-strategy.md)规定的依赖、许可证和测试审计。
- 当前没有目标能力标记为“暂缓”。GraphRAG、RAPTOR、多模态 RAG 和时序 RAG 安排在 Phase 09，均默认关闭并要求独立验收。

## 4. 维护约束

1. 增删能力必须同步更新[项目总纲](./00-project-master.md)、[目标架构](./03-target-architecture.md)和[开发路线图](./05-development-roadmap.md)。
2. 修改采用分类必须同步更新[代码复用策略](./04-code-reuse-strategy.md)。
3. 修改阶段必须同步更新[开发路线图](./05-development-roadmap.md)和未生成的对应阶段文档。
4. 当前状态只有在代码、迁移和验收测试存在后才能改为“已实现”。
