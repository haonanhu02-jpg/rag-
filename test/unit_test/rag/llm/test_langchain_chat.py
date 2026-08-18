#
#  Copyright 2025 The InfiniFlow Authors. All Rights Reserved.
#
#  Licensed under the Apache License, Version 2.0 (the "License");
#  you may not use this file except in compliance with the License.
#  You may obtain a copy of the License at
#
#      http://www.apache.org/licenses/LICENSE-2.0
#
#  Unless required by applicable law or agreed to in writing, software
#  distributed under the License is distributed on an "AS IS" BASIS,
#  WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
#  See the License for the specific language governing permissions and
#  limitations under the License.
#
"""
Offline unit tests for the LangChain-backed chat provider.

These tests exercise the :class:`LangChainChat` contract with a fake
langchain ``ChatOpenAI``-shaped object (no network), following the existing
``test/unit_test/rag/llm`` pattern of building instances via ``__new__`` +
attribute injection to avoid real client construction. They pin:

* the ``_FACTORY_NAME`` registration predicate used by ``rag.llm.__init__``;
* the ``async_chat`` return contract (answer string, token count);
* the ``async_chat_streamly`` generator contract (text chunks then a final
  ``int`` token count);
* the ``last_usage`` split mapping (langchain ``input/output_tokens`` ->
  RAGFlow ``prompt/completion_tokens``);
* the tool-bound paths (``async_chat_with_tools`` / ``async_chat_streamly_with_tools``)
  via the OpenAI-style tool-call adapter.
"""

import inspect
import json
from unittest.mock import MagicMock

import pytest
from langchain_core.messages import AIMessage, AIMessageChunk

if isinstance(__import__("sys").modules.get("rag.llm.chat_model"), MagicMock):
    del __import__("sys").modules["rag.llm.chat_model"]

from rag.llm.chat_model import Base, LangChainChat


class _FakeChatLLM:
    """ChatOpenAI-shaped fake: records calls, returns deterministic messages."""

    def __init__(self, *, empty: bool = False):
        self.empty = empty
        self.ainvoke_calls: list = []
        self.astream_calls: list = []

    async def ainvoke(self, messages, **kwargs):
        self.ainvoke_calls.append((messages, kwargs))
        if self.empty:
            return AIMessage(content="", usage_metadata={"input_tokens": 7, "output_tokens": 0, "total_tokens": 7})
        return AIMessage(
            content="  RAGFlow 复位前需要检查电源。  ",
            usage_metadata={"input_tokens": 7, "output_tokens": 3, "total_tokens": 10},
        )

    async def astream(self, messages, **kwargs):
        self.astream_calls.append((messages, kwargs))
        yield AIMessageChunk(content="设备")
        yield AIMessageChunk(content="复位")
        yield AIMessageChunk(
            content="完成。",
            usage_metadata={"input_tokens": 7, "output_tokens": 3, "total_tokens": 10},
        )


def _make_chat(empty: bool = False) -> LangChainChat:
    inst = LangChainChat.__new__(LangChainChat)
    inst.model_name = "gpt-4o"
    inst.base_url = "https://api.openai.com/v1"
    inst.llm = _FakeChatLLM(empty=empty)
    inst.max_retries = 1
    inst.base_delay = 0.01
    inst.max_rounds = 3
    inst.is_tools = False
    inst.tools = []
    inst.toolcall_sessions = {}
    inst.last_usage = {"prompt_tokens": 0, "completion_tokens": 0, "total_tokens": 0}
    return inst


# --------------------------------------------------------------------------- #
# Factory registration predicate (what rag.llm.__init__ checks).
# --------------------------------------------------------------------------- #
def test_langchain_chat_is_registered_factory_class():
    assert issubclass(LangChainChat, Base)
    assert hasattr(LangChainChat, "_FACTORY_NAME")
    assert LangChainChat._FACTORY_NAME == "LangChain"


def test_langchain_chat_would_be_discovered_by_init():
    """Replicate the rag.llm.__init__ discovery predicate over the module."""
    from rag.llm import chat_model

    discovered = [
        obj._FACTORY_NAME
        for _, obj in inspect.getmembers(chat_model)
        if inspect.isclass(obj) and issubclass(obj, Base) and obj is not Base and hasattr(obj, "_FACTORY_NAME")
    ]
    assert "LangChain" in discovered


# --------------------------------------------------------------------------- #
# async_chat contract.
# --------------------------------------------------------------------------- #
@pytest.mark.asyncio
async def test_async_chat_returns_content_and_usage():
    chat = _make_chat()
    history = [{"role": "user", "content": "设备复位前检查步骤？"}]
    answer, tokens = await chat.async_chat("你是设备维护助手。", history, {"temperature": 0.5})

    assert answer == "RAGFlow 复位前需要检查电源。"
    assert tokens == 10
    # System prompt is prepended when missing.
    assert history[0] == {"role": "system", "content": "你是设备维护助手。"}
    # Usage split mapped from langchain input/output_tokens.
    assert chat.last_usage == {"prompt_tokens": 7, "completion_tokens": 3, "total_tokens": 10}


@pytest.mark.asyncio
async def test_async_chat_empty_content_returns_empty():
    chat = _make_chat(empty=True)
    answer, tokens = await chat.async_chat("system", [{"role": "user", "content": "x"}])
    assert answer == ""
    # Base contract: empty content -> ("", 0), matching the OpenAI provider path.
    assert tokens == 0


# --------------------------------------------------------------------------- #
# async_chat_streamly contract.
# --------------------------------------------------------------------------- #
@pytest.mark.asyncio
async def test_async_chat_streamly_yields_chunks_then_int():
    chat = _make_chat()
    history = [{"role": "user", "content": "复位后应该做什么？"}]
    out = [item async for item in chat.async_chat_streamly("助手", history, {"temperature": 0.5})]

    # Text chunks followed by a final int token count (generator contract).
    assert out[:-1] == ["设备", "复位", "完成。"]
    assert out[-1] == 10
    assert isinstance(out[-1], int)
    # System prompt prepended for streaming too.
    assert history[0] == {"role": "system", "content": "助手"}
    assert chat.last_usage["total_tokens"] == 10


# --------------------------------------------------------------------------- #
# Tool paths.
# --------------------------------------------------------------------------- #
class _FakeToolLLM:
    """ChatOpenAI-shaped fake for the tool loop: one tool call per invoke."""

    def __init__(self, *, tool_calls: int = 1):
        self.tool_calls = tool_calls
        self.tools = []
        self.ainvoke_calls: list = []
        self.astream_calls: list = []

    def bind_tools(self, tools):
        self.tools = tools
        return self

    async def ainvoke(self, messages, **kwargs):
        self.ainvoke_calls.append((messages, kwargs))
        if self.tool_calls:
            self.tool_calls -= 1
            return AIMessage(
                content="",
                tool_calls=[
                    {"name": "get_weather", "args": {"city": "Beijing"}, "id": "call_1", "type": "tool_call"}
                ],
                usage_metadata={"input_tokens": 8, "output_tokens": 2, "total_tokens": 10},
            )
        return AIMessage(content="Beijing: 21C sunny.", usage_metadata={"input_tokens": 8, "output_tokens": 2, "total_tokens": 10})

    async def astream(self, messages, **kwargs):
        self.astream_calls.append((messages, kwargs))
        if self.tool_calls:
            self.tool_calls -= 1
            yield AIMessageChunk(
                content="",
                tool_call_chunks=[
                    {"name": "get_weather", "args": '{"city": "Beijing"}', "id": "call_1", "index": 0}
                ],
                usage_metadata={"input_tokens": 8, "output_tokens": 2, "total_tokens": 10},
            )
        else:
            yield AIMessageChunk(content="Beijing: 21C sunny.", usage_metadata={"input_tokens": 8, "output_tokens": 2, "total_tokens": 10})


class _FakeToolSession:
    def __init__(self):
        self.calls: list = []

    async def tool_call_async(self, name, arguments):
        self.calls.append((name, arguments))
        return f"{arguments['city']}: 21C sunny"


def _make_tool_chat(tool_calls: int = 1):
    inst = LangChainChat.__new__(LangChainChat)
    inst.model_name = "gpt-4o"
    inst.base_url = "https://api.openai.com/v1"
    inst.llm = _FakeToolLLM(tool_calls=tool_calls)
    inst.max_retries = 1
    inst.base_delay = 0.01
    inst.max_rounds = 3
    inst.is_tools = True
    inst.tools = [
        {
            "type": "function",
            "function": {
                "name": "get_weather",
                "description": "Get weather for a city",
                "parameters": {
                    "type": "object",
                    "properties": {"city": {"type": "string"}},
                    "required": ["city"],
                },
            },
        }
    ]
    inst.toolcall_session = _FakeToolSession()
    inst.last_usage = {"prompt_tokens": 0, "completion_tokens": 0, "total_tokens": 0}
    return inst


def test_tool_call_adapter_produces_openai_style_object():
    from rag.llm.chat_model import _langchain_tool_call_to_openai

    tc = _langchain_tool_call_to_openai(
        {"name": "get_weather", "args": {"city": "Beijing"}, "id": "call_1", "type": "tool_call"},
        index=2,
    )
    assert tc.id == "call_1"
    assert tc.index == 2
    assert tc.function.name == "get_weather"
    # RAGFlow's tool loop parses .function.arguments as JSON.
    assert json.loads(tc.function.arguments) == {"city": "Beijing"}


@pytest.mark.asyncio
async def test_async_chat_with_tools_runs_tool_then_answers():
    chat = _make_tool_chat()
    answer, tokens = await chat.async_chat_with_tools("sys", [{"role": "user", "content": "weather?"}])

    assert chat.toolcall_session.calls == [("get_weather", {"city": "Beijing"})]
    assert "Beijing: 21C sunny." in answer
    assert "get_weather" in answer  # verbose tool-use marker in the answer
    assert tokens == 20  # two rounds: tool call (10) + final answer (10)
    assert chat.last_usage == {"prompt_tokens": 16, "completion_tokens": 4, "total_tokens": 20}


@pytest.mark.asyncio
async def test_async_chat_with_tools_answers_directly_when_no_tool_needed():
    chat = _make_tool_chat(tool_calls=0)
    answer, tokens = await chat.async_chat_with_tools("sys", [{"role": "user", "content": "hi"}])

    assert chat.toolcall_session.calls == []
    assert answer == "Beijing: 21C sunny."
    assert tokens == 10


@pytest.mark.asyncio
async def test_async_chat_streamly_with_tools_yields_tool_run_then_answer():
    chat = _make_tool_chat()
    out = [item async for item in chat.async_chat_streamly_with_tools("sys", [{"role": "user", "content": "weather?"}])]

    assert chat.toolcall_session.calls == [("get_weather", {"city": "Beijing"})]
    # Streaming contract: <think>Running...> marker, verbose tool use, final int.
    assert "<think>Running the get_weather tool...</think>" in out
    assert any("Beijing: 21C sunny." in str(item) for item in out)
    assert out[-1] == 20
    assert isinstance(out[-1], int)


@pytest.mark.asyncio
async def test_tool_loop_keeps_history_between_rounds():
    chat = _make_tool_chat()
    await chat.async_chat_with_tools("sys", [{"role": "user", "content": "weather?"}])

    # First round sent the user message; second round also carried the tool result.
    messages = chat.llm.ainvoke_calls
    assert len(messages) == 2
    assert messages[0][0][0]["role"] == "system"
    assert messages[1][0][0]["role"] == "system"
    # Tool result appended between rounds (OpenAI tool protocol messages).
    roles = [m["role"] for m in messages[1][0]]
    assert "tool" in roles
    assert "assistant" in roles
