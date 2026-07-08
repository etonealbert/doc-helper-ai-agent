"""A small local vector store for RAG.

Design goals:
- **Deterministic mock mode** (default): keyword/overlap scoring with no network
  and no heavy dependencies, so retrieval is reproducible in tests.
- **Optional embeddings mode**: when real embeddings are enabled, chunks and
  queries are embedded with OpenAI and ranked by cosine similarity.

The public API is intentionally tiny (``add`` / ``query``) so it can later be
swapped for Chroma or a managed vector DB without touching callers.
"""

from __future__ import annotations

import math
import re
from dataclasses import dataclass, field

from doc_helper_ai_agent.core.config import Settings
from doc_helper_ai_agent.core.logging import get_logger
from doc_helper_ai_agent.domain.models import RetrievedChunk

logger = get_logger(__name__)

_TOKEN_RE = re.compile(r"[a-z0-9]+")
_STOPWORDS = {
    "the", "a", "an", "and", "or", "of", "to", "in", "on", "for", "is", "are",
    "do", "does", "how", "what", "when", "where", "can", "i", "my", "me", "you",
    "your", "we", "with", "at", "it", "this", "that", "be", "will", "would",
}


def _tokenize(text: str) -> list[str]:
    return [t for t in _TOKEN_RE.findall(text.lower()) if t not in _STOPWORDS]


@dataclass
class _Entry:
    id: str
    text: str
    source: str
    tokens: list[str]
    embedding: list[float] | None = field(default=None)


def _cosine(a: list[float], b: list[float]) -> float:
    dot = sum(x * y for x, y in zip(a, b, strict=False))
    na = math.sqrt(sum(x * x for x in a))
    nb = math.sqrt(sum(y * y for y in b))
    if na == 0 or nb == 0:
        return 0.0
    return dot / (na * nb)


class LocalVectorStore:
    """In-memory vector store with keyword and optional embedding retrieval."""

    def __init__(self, settings: Settings) -> None:
        self._settings = settings
        self._entries: list[_Entry] = []
        self._embed_enabled = settings.use_embeddings

    @property
    def size(self) -> int:
        return len(self._entries)

    def clear(self) -> None:
        self._entries.clear()

    def add(self, chunks: list[dict[str, str]]) -> None:
        """Add chunks. Each chunk is ``{"id", "text", "source"}``."""
        texts = [c["text"] for c in chunks]
        embeddings = self._embed(texts) if self._embed_enabled else [None] * len(texts)
        for chunk, embedding in zip(chunks, embeddings, strict=False):
            self._entries.append(
                _Entry(
                    id=chunk["id"],
                    text=chunk["text"],
                    source=chunk["source"],
                    tokens=_tokenize(chunk["text"]),
                    embedding=embedding,
                )
            )
        logger.info("Vector store indexed %d chunk(s) (total=%d)", len(chunks), self.size)

    def query(self, text: str, top_k: int = 3) -> list[RetrievedChunk]:
        if not self._entries:
            return []
        if self._embed_enabled:
            ranked = self._query_embeddings(text)
        else:
            ranked = self._query_keywords(text)
        results = [
            RetrievedChunk(id=e.id, text=e.text, source=e.source, score=round(score, 4))
            for score, e in ranked
            if score > 0
        ]
        return results[:top_k]

    # --- keyword path -----------------------------------------------------
    def _query_keywords(self, text: str) -> list[tuple[float, _Entry]]:
        query_tokens = _tokenize(text)
        if not query_tokens:
            return []
        query_set = set(query_tokens)
        scored: list[tuple[float, _Entry]] = []
        for entry in self._entries:
            if not entry.tokens:
                continue
            overlap = sum(1 for t in entry.tokens if t in query_set)
            if overlap == 0:
                continue
            # Normalise by chunk length to avoid favouring long chunks.
            score = overlap / math.sqrt(len(entry.tokens))
            scored.append((score, entry))
        scored.sort(key=lambda pair: pair[0], reverse=True)
        return scored

    # --- embedding path ---------------------------------------------------
    def _query_embeddings(self, text: str) -> list[tuple[float, _Entry]]:
        query_vec = self._embed([text])[0]
        if query_vec is None:
            return self._query_keywords(text)
        scored: list[tuple[float, _Entry]] = []
        for entry in self._entries:
            if entry.embedding is None:
                continue
            scored.append((_cosine(query_vec, entry.embedding), entry))
        scored.sort(key=lambda pair: pair[0], reverse=True)
        return scored

    def _embed(self, texts: list[str]) -> list[list[float] | None]:
        """Embed texts with OpenAI; fall back to ``None`` on any failure."""
        try:
            from openai import OpenAI

            client = OpenAI(api_key=self._settings.openai_api_key)
            response = client.embeddings.create(
                model=self._settings.embedding_model,
                input=texts,
            )
            return [item.embedding for item in response.data]
        except Exception as exc:  # pragma: no cover - network/credential dependent
            logger.warning("Embedding failed, falling back to keyword mode: %s", exc)
            self._embed_enabled = False
            return [None] * len(texts)


_store: LocalVectorStore | None = None


def get_vector_store(settings: Settings) -> LocalVectorStore:
    """Return the process-wide :class:`LocalVectorStore` singleton."""
    global _store
    if _store is None:
        _store = LocalVectorStore(settings)
    return _store


def reset_vector_store() -> None:
    """Drop the singleton (used by tests)."""
    global _store
    _store = None
