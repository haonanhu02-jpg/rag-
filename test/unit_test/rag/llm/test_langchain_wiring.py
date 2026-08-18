#
#  Copyright 2026 The InfiniFlow Authors. All Rights Reserved.
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
Wiring contract: the LangChain factory must be reachable through RAGFlow's
provider registration chain.

``conf/llm_factories.json`` feeds ``settings.FACTORY_LLM_INFOS``, which the
model-management API (``provider_api_service``) and model list / instance
lookup (``tenant_llm_service``) consume to decide which providers a user can
select and instantiate. This test pins the two ends of that chain:

* the ``LangChain`` entry exists in the factory file with the expected tags;
* a ``LangChain`` factory resolves to the registered ``LangChainChat`` /
  ``LangChainEmbed`` classes via the same registry the production
  ``TenantLLMService.model_instance`` branch uses, and those classes can be
  instantiated with the production ``(key, model_name, base_url)`` signature.

It reuses the ``test/unit_test/rag/llm`` conftest stub so ``rag.llm`` does not
run its heavy auto-discovery, and builds the registry the same way
``rag/llm/__init__.py`` does (subclasses of ``Base`` carrying
``_FACTORY_NAME``).
"""

import inspect
import json
from pathlib import Path

import pytest

from rag.llm.chat_model import Base as ChatBase
from rag.llm.chat_model import LangChainChat
from rag.llm.embedding_model import Base as EmbedBase
from rag.llm.embedding_model import LangChainEmbed

pytestmark = pytest.mark.p2

_REPO_ROOT = Path(__file__).resolve().parents[4]
_FACTORIES_FILE = _REPO_ROOT / "conf" / "llm_factories.json"


def _load_factories() -> list[dict]:
    return json.loads(_FACTORIES_FILE.read_text(encoding="utf-8"))["factory_llm_infos"]


def _langchain_entry() -> dict:
    for factory in _load_factories():
        if factory["name"] == "LangChain":
            return factory
    raise AssertionError("LangChain factory missing from conf/llm_factories.json")


def _build_registry(base_cls):
    """Replicate rag/llm/__init__.py auto-discovery over one model module."""
    module = inspect.getmodule(base_cls)
    registry = {}
    for _, obj in inspect.getmembers(module):
        if inspect.isclass(obj) and issubclass(obj, base_cls) and obj is not base_cls and hasattr(obj, "_FACTORY_NAME"):
            factory_names = obj._FACTORY_NAME
            for name in factory_names if isinstance(factory_names, list) else [factory_names]:
                registry[name] = obj
    return registry


# --------------------------------------------------------------------------- #
# Factory file registration.
# --------------------------------------------------------------------------- #
def test_langchain_factory_registered_in_conf():
    entry = _langchain_entry()
    # Must expose at least chat + embedding so the two classes we ship are
    # selectable for those model types.
    assert "LLM" in entry["tags"]
    assert "TEXT EMBEDDING" in entry["tags"]
    assert entry["status"] == "1"
    assert isinstance(entry["llm"], list)


def test_factories_file_loads_as_settings_would():
    """The file must stay valid JSON with a non-empty factory list."""
    data = json.loads(_FACTORIES_FILE.read_text(encoding="utf-8"))
    assert len(data["factory_llm_infos"]) > 0


# --------------------------------------------------------------------------- #
# model_instance-style resolution (tenant_llm_service branch for CHAT/EMBEDDING).
# --------------------------------------------------------------------------- #
def test_langchain_chat_resolves_via_model_instance_branch():
    chat_registry = _build_registry(ChatBase)
    assert "LangChain" in chat_registry
    assert chat_registry["LangChain"] is LangChainChat
    inst = chat_registry["LangChain"](
        "sk-test", "gpt-4o", base_url="https://api.openai.com/v1"
    )
    assert inst.model_name == "gpt-4o"


def test_langchain_embedding_resolves_via_model_instance_branch():
    embed_registry = _build_registry(EmbedBase)
    assert "LangChain" in embed_registry
    assert embed_registry["LangChain"] is LangChainEmbed
    inst = embed_registry["LangChain"](
        "sk-test", "text-embedding-3-small", base_url="https://api.openai.com/v1"
    )
    assert inst.model_name == "text-embedding-3-small"
