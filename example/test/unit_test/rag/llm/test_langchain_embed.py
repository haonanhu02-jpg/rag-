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
Offline unit tests for the LangChain-backed embedding provider.

These tests exercise the :class:`LangChainEmbed` contract with a fake
langchain ``OpenAIEmbeddings``-shaped object (no network), matching the
existing ``test/unit_test/rag/llm`` offline pattern. They pin:

* the ``_FACTORY_NAME`` registration predicate used by ``rag.llm.__init__``;
* the numpy array return type that callers rely on (``embedding_service.py``,
  ``search.py``);
* batch handling via ``Base._batched_encode`` (deterministic per-text vectors);
* the ``encode_queries`` single-vector shape.
"""

import inspect
from unittest.mock import MagicMock

import numpy as np
import pytest

if isinstance(__import__("sys").modules.get("rag.llm.embedding_model"), MagicMock):
    del __import__("sys").modules["rag.llm.embedding_model"]

from rag.llm.embedding_model import Base, LangChainEmbed


class _FakeOpenAIEmbeddings:
    """OpenAIEmbeddings-shaped fake: deterministic per-text vectors."""

    def __init__(self):
        self.embed_documents_calls: list = []

    def embed_documents(self, texts):
        self.embed_documents_calls.append(texts)
        return [[float(len(text)), float(1)] for text in texts]

    def embed_query(self, text):
        return [float(len(text)), float(1)]


def _make_embed() -> LangChainEmbed:
    inst = LangChainEmbed.__new__(LangChainEmbed)
    inst.model_name = "text-embedding-3-small"
    inst.base_url = "https://api.openai.com/v1"
    inst.client = _FakeOpenAIEmbeddings()
    return inst


# --------------------------------------------------------------------------- #
# Factory registration predicate (what rag.llm.__init__ checks).
# --------------------------------------------------------------------------- #
def test_langchain_embed_is_registered_factory_class():
    assert issubclass(LangChainEmbed, Base)
    assert hasattr(LangChainEmbed, "_FACTORY_NAME")
    assert LangChainEmbed._FACTORY_NAME == "LangChain"


def test_langchain_embed_would_be_discovered_by_init():
    """Replicate the rag.llm.__init__ discovery predicate over the module."""
    from rag.llm import embedding_model

    discovered = [
        obj._FACTORY_NAME
        for _, obj in inspect.getmembers(embedding_model)
        if inspect.isclass(obj) and issubclass(obj, Base) and obj is not Base and hasattr(obj, "_FACTORY_NAME")
    ]
    assert "LangChain" in discovered


# --------------------------------------------------------------------------- #
# encode contract.
# --------------------------------------------------------------------------- #
def test_encode_returns_numpy_matrix_and_vectors():
    embed = _make_embed()
    vectors, tokens = embed.encode(["设备复位", "检查电源"])

    assert isinstance(vectors, np.ndarray)
    assert vectors.shape == (2, 2)
    # Deterministic fake vectors: [len(text), 1].
    assert float(vectors[0][0]) == len("设备复位")
    assert float(vectors[1][0]) == len("检查电源")
    assert embed.client.embed_documents_calls == [["设备复位", "检查电源"]]


def test_encode_batches_when_above_batch_size():
    embed = _make_embed()
    texts = [f"文本{i}" for i in range(20)]
    vectors, _ = embed.encode(texts)

    # _batched_encode issues ceil(20 / 16) = 2 provider calls.
    assert len(embed.client.embed_documents_calls) == 2
    assert sum(len(batch) for batch in embed.client.embed_documents_calls) == 20
    assert vectors.shape == (20, 2)


# --------------------------------------------------------------------------- #
# encode_queries contract.
# --------------------------------------------------------------------------- #
def test_encode_queries_returns_single_vector():
    embed = _make_embed()
    vector, tokens = embed.encode_queries("复位后检查")

    assert isinstance(vector, np.ndarray)
    assert vector.shape == (2,)
    assert float(vector[0]) == len("复位后检查")
