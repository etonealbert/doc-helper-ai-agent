"""RAG service tests (deterministic mock retrieval)."""

from __future__ import annotations

import pytest

from doc_helper_ai_agent.dependencies import get_container
from doc_helper_ai_agent.domain.enums import Locale
from doc_helper_ai_agent.tools.knowledge_tools import answer_question


def test_pricing_question_retrieves_pricing_doc():
    rag = get_container().rag
    result = rag.answer("How much does teeth whitening cost?", locale=Locale.EN)
    assert result.sources
    assert any("pricing" in source for source in result.sources)
    assert "whitening" in result.answer.lower()


def test_opening_hours_retrieves_faq():
    rag = get_container().rag
    result = rag.answer("What are your opening hours?", locale=Locale.EN)
    assert any("clinic_faq" in source for source in result.sources)


def test_unknown_question_returns_graceful_answer():
    rag = get_container().rag
    result = rag.answer("zzzz qqqq xxxx no matching keywords here", locale=Locale.EN)
    # No overlap -> no sources, but a safe fallback message.
    assert result.sources == []
    assert "contact the clinic" in result.answer.lower()


def test_spanish_pricing_question_retrieves_spanish_content_only():
    rag = get_container().rag
    result = rag.answer("¿Cuánto cuesta el blanqueamiento dental?", locale=Locale.ES)

    assert result.sources[0] == "pricing.md"
    assert result.chunks
    assert all(chunk.locale == Locale.ES for chunk in result.chunks)
    assert "Según nuestros documentos" in result.answer
    assert "blanqueamiento" in result.answer.lower()


def test_spanish_unknown_question_returns_spanish_fallback():
    rag = get_container().rag
    result = rag.answer("zzzz qqqq xxxx sin coincidencias", locale=Locale.ES)

    assert result.sources == []
    assert "contacta con la clínica" in result.answer.lower()


@pytest.mark.parametrize(
    "question,expected_source",
    [
        ("¿A qué hora cierran?", "clinic_faq.md"),
        ("¿Dónde queda la clínica?", "clinic_faq.md"),
        ("¿Cuánto cuestan los implantes?", "pricing.md"),
    ],
)
def test_common_spanish_paraphrases_retrieve_the_expected_document(
    question, expected_source
):
    rag = get_container().rag
    result = rag.answer(question, locale=Locale.ES)

    assert result.sources
    assert result.sources[0] == expected_source


def test_english_question_can_request_a_spanish_answer():
    rag = get_container().rag
    result = rag.answer("What are your opening hours?", locale=Locale.ES)

    assert result.sources[0] == "clinic_faq.md"
    assert result.answer.startswith("Según nuestros documentos")


def test_spanish_question_can_request_an_english_answer():
    rag = get_container().rag
    result = rag.answer("¿Cuánto cuesta el blanqueamiento?", locale=Locale.EN)

    assert result.sources[0] == "pricing.md"
    assert result.answer.startswith("Based on our documents")


def test_knowledge_tool_keeps_top_k_as_the_second_positional_argument():
    action = answer_question(
        "How much does teeth whitening cost?", 1, locale=Locale.EN
    )

    assert action.result["num_chunks"] == 1


def test_document_summary_lists_all_sample_docs():
    rag = get_container().rag
    summary = dict(rag.document_summary())
    for expected in ("clinic_faq.md", "pricing.md", "patient_policy.md", "services.md"):
        assert expected in summary
        assert summary[expected] >= 1
