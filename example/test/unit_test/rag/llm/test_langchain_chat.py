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
* the explicit no-tools scope boundary.
"""

import inspect
from unittest.mock import AsyncMock, MagicMock

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
# Tool scope boundary.
# --------------------------------------------------------------------------- #
@pytest.mark.asyncio
async def test_tool_paths_raise_not_implemented():
    chat = _make_chat()
    with pytest.raises(NotImplementedError):
        await chat.async_chat_with_tools("system", [{"role": "user", "content": "x"}])
    with pytest.raises(NotImplementedError):
        async for _ in chat.async_chat_streamly_with_tools("system", [{"role": "user", "content": "x"}]):
            pass
