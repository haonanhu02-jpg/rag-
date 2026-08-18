---
document_id: REAL-CODE-LANGCHAIN-EXECUTION
document_role: 在真实 RAGFlow 代码上执行 LangChain 框架替换的记录（rag- 仓库）
status: active
document_version: "1.0.0"
created_at: "2026-08-18"
last_updated_at: "2026-08-18"
project_root: "D:/download/rag-"
ragflow_branch: "ragflow-langchain"
ragflow_reference_commit: "cd846cc9d4e32a19e684c59a1f302601027ef976"
ragflow_version: "0.26.4"
---

# 在真实 RAGFlow 代码上执行 LangChain 框架替换

## 文档导航

[框架替代拆解与实施计划](./11-framework-replacement-plan.md) · [能力矩阵](./02-ragflow-capability-matrix.md)

## 0. 文档定位与状态

- **[事实]** 本仓库 `ragflow-langchain` 分支基于 RAGFlow v0.26.4（冻结基线 `cd846cc`）的 Python 源码（已排除 `go/`、`internal/`、`cmd/`、`ragflow_deps/`）。
- **[事实]** 本记录描述在**真实 RAGFlow 代码**上落地的 LangChain 替换，对应 [11 计划](./11-framework-replacement-plan.md) 中 A.1 表"完全可替代"的模型层项（LLM 对话/生成 与 Embedding）。
- **[决策]** 替换采用**新增可选 provider** 的方式：在现有 `rag/llm` 工厂注册 `LangChain` 路由，默认 provider 完全不动，因此**功能无损失**由"默认路径不变 + 接口契约测试"证明。
- **[范围外]** 未做真实模型 API 验证（需外部 key，本次不执行）；未替换 Agent 图循环（A.1 表第 3 项，[G-4 决策](./11-framework-replacement-plan.md) 不推荐）；未替换纯文本切块（G-3 不推荐）。

## 1. 本次改动清单

### 1.1 新增 LangChain-backed 工厂类（核心）

| 文件 | 改动 | 对应 A.1 项 |
|---|---|---|
| `rag/llm/chat_model.py` | 新增 `LangChainChat(Base)`，`_FACTORY_NAME = "LangChain"`；`async_chat` / `async_chat_streamly` 走 `langchain_openai.ChatOpenAI`；复用 `Base` 的重试、错误分类、`_length_stop` | A.1 LLM 对话/生成 |
| `rag/llm/embedding_model.py` | 新增 `LangChainEmbed(Base)`，`_FACTORY_NAME = "LangChain"`；`encode` / `encode_queries` 走 `langchain_openai.OpenAIEmbeddings`，返回 numpy 数组（调用方契约不变） | A.1 Embedding |

### 1.2 工具路径（Agent 循环的支持面）

`LangChainChat` 实现 `async_chat_with_tools` / `async_chat_streamly_with_tools`：
- 用 `ChatOpenAI.bind_tools()` 绑定 RAGFlow 的 OpenAI-format 工具 schema（已实测兼容）。
- 新增 `_langchain_tool_call_to_openai` 适配器，把 langchain 的 `tool_call` dict 映射回 RAGFlow 工具循环期望的 OpenAI 风格对象（`tc.function.name/.arguments/.id/.index`），从而复用 `Base._append_history_batch`、`_verbose_tool_use`、`_exceptions_async`。
- 用法统计在多个工具调用轮次间累加（`last_usage`），与 Base 一致。

### 1.3 依赖与测试

| 文件 | 改动 |
|---|---|
| `pyproject.toml` | 增加 `langchain-openai>=0.3.0,<1.0.0`；`uv.lock` 重新生成（加入 langchain-openai v0.3.34） |
| `test/unit_test/rag/llm/test_langchain_chat.py` | 新增：非工具契约（async_chat / streamly / 空内容）+ 工具往返、流式工具、无需工具直接回答、跨轮历史、适配器 |
| `test/unit_test/rag/llm/test_langchain_embed.py` | 新增：encode / encode_queries 返回 numpy、批处理、工厂注册谓词 |
| `test/unit_test/rag/llm/conftest.py` | 增加受保护的 `common.settings` stub（仅当真实 settings 无法导入时生效）+ 完整 `SupportedLiteLLMProvider` 枚举，使 llm 单测可在无存储 SDK 的离线环境运行 |

## 2. 功能无损失证明

1. **默认路径不变**：未修改任何现有 provider（OpenAI / DeepSeek / Ollama / LiteLLM 等全部原样）；`LangChain` 只是工厂里多出的一个可选项。
2. **接口契约一致**：新类继承同一 `Base`，构造签名 `(key, model_name, base_url, **kwargs)`、`async_chat` 返回 `(answer, tokens)`、`async_chat_streamly` 先 yield 文本再 yield `int` token——均由离线测试锁定。
3. **调用方契约**：Embedding 返回 numpy 数组，与 `embedding_service.py` / `search.py` 的消费方式一致。
4. **工厂注册**：按 `rag/llm/__init__.py` 的自动发现谓词复核，`LangChain` 进入 `ChatModel`（25 个 provider）与 `EmbeddingModel`（43 个 provider）。

## 3. 验证记录

| 门禁 | 结果 |
|---|---|
| `pytest test/unit_test/rag/llm/` | **153 passed**（含新增的 chat/embed 工具路径测试；11 个基础 + 4 个工具 = 15 个新测试） |
| 离线 | 全部使用 fake client / MagicMock，不联网 |
| 环境 | Windows / CPython 3.13；离线 venv（`infinity-sdk` 因 `datrie` 在 Windows 构建失败，用 conftest stub 绕开存储栈，属测试基建，不影响产品代码） |

## 4. 提交历史（rag- 分支 `ragflow-langchain`）

| 提交 | 内容 |
|---|---|
| `44af292` | 基座：导入 RAGFlow 0.26.4 源码树（Python 栈，排除 go/internal/cmd/ragflow_deps） |
| `3465419` | LangChain-backed chat / embedding provider（A.1 模型层） |
| `c4991a4` | 工具路径：`async_chat_with_tools` / `async_chat_streamly_with_tools` + 适配器 + 测试 |

## 5. 与 11 计划的关系

- **已执行**：A.1 表第 1、2 行（LLM 生成、Embedding）落到真实代码。
- **工具路径**：覆盖了 Agent 带工具循环对模型层的要求（A.2 中"Agent 带工具"的模型调用段），使 agentic 流程切到 LangChain 路由无缺口。
- **未执行 / 决策维持**：
  - 真实模型 API 验证（FR-R-04：Fake 结论未被当真实验证，本记录明确标注）——本次按用户决定不执行。
  - Agent 图换 `create_react_agent`（G-4 不推荐）、纯文本切块换 `TextSplitter`（G-3 不推荐）、提示词迁移 `ChatPromptTemplate`（G-1 低收益，未立项）。

## 维护记录

| 日期 | 版本 | 变更 |
|---|---|---|
| 2026-08-18 | 1.0.0 | 记录 rag- `ragflow-langchain` 分支上真实 RAGFlow 代码的 LangChain 替换执行（chat/embed 工厂类 + 工具路径 + 测试 153 过） |
