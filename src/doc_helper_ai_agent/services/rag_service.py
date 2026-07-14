"""Retrieval-Augmented Generation service.

Indexes the sample documents into the vector store and answers questions with
provenance. In mock mode the answer is composed deterministically from the most
relevant retrieved chunk; with a real LLM configured it synthesises an answer
grounded in the retrieved context.
"""

from __future__ import annotations

import threading

from doc_helper_ai_agent.core.config import Settings
from doc_helper_ai_agent.core.logging import get_logger
from doc_helper_ai_agent.domain.enums import Locale
from doc_helper_ai_agent.domain.models import RagResult, RetrievedChunk
from doc_helper_ai_agent.infrastructure.vector_store import LocalVectorStore
from doc_helper_ai_agent.services.document_loader import load_documents

logger = get_logger(__name__)

_SYSTEM_PROMPTS = {
    Locale.EN: (
        "You are a helpful clinic front-desk assistant. Answer in English using ONLY "
        "the provided context. If the answer is not in the context, say you are not "
        "sure and suggest contacting the clinic. Never provide medical diagnosis or "
        "treatment advice."
    ),
    Locale.ES: (
        "Eres un asistente de recepción de una clínica. Responde en español usando "
        "ÚNICAMENTE el contexto proporcionado. Si la respuesta no está en el contexto, "
        "indica que no tienes certeza y sugiere contactar con la clínica. Nunca des "
        "diagnósticos ni consejos de tratamiento médico."
    ),
}

_NO_RESULT_MESSAGES = {
    Locale.EN: (
        "I couldn't find that in our documents. Please contact the clinic and our team "
        "will be happy to help."
    ),
    Locale.ES: (
        "No pude encontrar esa información en nuestros documentos. Contacta con la "
        "clínica y nuestro equipo estará encantado de ayudarte."
    ),
}


class RagService:
    """Index documents and answer questions with citations."""

    def __init__(self, settings: Settings, store: LocalVectorStore) -> None:
        self._settings = settings
        self._store = store
        self._indexed = False
        self._lock = threading.Lock()

    def ensure_indexed(self) -> None:
        """Index the sample documents exactly once (thread-safe)."""
        if self._indexed:
            return
        with self._lock:
            if self._indexed:
                return
            chunks = load_documents(self._settings.sample_docs_path)
            if chunks:
                self._store.add(chunks)
            self._indexed = True

    def document_summary(self) -> list[tuple[str, int]]:
        """Return ``(source, chunk_count)`` pairs for indexed documents."""
        self.ensure_indexed()
        counts: dict[str, int] = {}
        # Re-load lightweight metadata without embeddings for an accurate count.
        for chunk in load_documents(self._settings.sample_docs_path):
            counts[chunk["source"]] = counts.get(chunk["source"], 0) + 1
        return sorted(counts.items())

    def answer(
        self,
        question: str,
        top_k: int | None = None,
        locale: Locale = Locale.ES,
    ) -> RagResult:
        """Answer ``question`` using retrieved context."""
        self.ensure_indexed()
        k = top_k or self._settings.rag_top_k
        chunks = self._store.query(question, locale=locale, top_k=k)

        if not chunks:
            return RagResult(
                answer=_NO_RESULT_MESSAGES[locale],
                sources=[],
                chunks=[],
            )

        sources = _unique_preserving_order(c.source for c in chunks)
        if self._settings.use_real_llm:
            answer = self._synthesize_with_llm(question, chunks, locale)
        else:
            answer = self._compose_mock_answer(chunks, locale)
        return RagResult(answer=answer, sources=sources, chunks=chunks)

    # --- answer composition ----------------------------------------------
    def _compose_mock_answer(self, chunks: list[RetrievedChunk], locale: Locale) -> str:
        top = chunks[0]
        snippet = top.text.strip()
        if len(snippet) > 600:
            snippet = snippet[:600].rstrip() + "…"
        if locale == Locale.ES:
            return (
                f"Según nuestros documentos ({top.source}):\n\n{snippet}\n\n"
                "Si necesitas algo más, nuestro equipo estará encantado de ayudarte."
            )
        return (
            f"Based on our documents ({top.source}):\n\n{snippet}\n\n"
            "If you need anything else, our team is happy to help."
        )

    def _synthesize_with_llm(
        self, question: str, chunks: list[RetrievedChunk], locale: Locale
    ) -> str:  # pragma: no cover - network dependent
        try:
            from openai import OpenAI

            context = "\n\n---\n\n".join(f"[{c.source}]\n{c.text}" for c in chunks)
            client = OpenAI(api_key=self._settings.openai_api_key)
            response = client.chat.completions.create(
                model=self._settings.llm_model,
                temperature=0,
                messages=[
                    {"role": "system", "content": _SYSTEM_PROMPTS[locale]},
                    {
                        "role": "user",
                        "content": f"Context:\n{context}\n\nQuestion / Pregunta: {question}",
                    },
                ],
            )
            return (response.choices[0].message.content or "").strip()
        except Exception as exc:
            logger.warning("LLM synthesis failed, using mock composition: %s", exc)
            return self._compose_mock_answer(chunks, locale)


def _unique_preserving_order(items) -> list[str]:
    seen: set[str] = set()
    result: list[str] = []
    for item in items:
        if item not in seen:
            seen.add(item)
            result.append(item)
    return result


_service: RagService | None = None


def get_rag_service(settings: Settings, store: LocalVectorStore) -> RagService:
    """Return the process-wide :class:`RagService` singleton."""
    global _service
    if _service is None:
        _service = RagService(settings, store)
    return _service


def reset_rag_service() -> None:
    """Drop the singleton (used by tests)."""
    global _service
    _service = None
