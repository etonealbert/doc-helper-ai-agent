"""RAG service tests (deterministic mock retrieval)."""

from __future__ import annotations

from doc_helper_ai_agent.dependencies import get_container


def test_pricing_question_retrieves_pricing_doc():
    rag = get_container().rag
    result = rag.answer("How much does teeth whitening cost?")
    assert result.sources
    assert any("pricing" in source for source in result.sources)
    assert "whitening" in result.answer.lower()


def test_opening_hours_retrieves_faq():
    rag = get_container().rag
    result = rag.answer("What are your opening hours?")
    assert any("clinic_faq" in source for source in result.sources)


def test_unknown_question_returns_graceful_answer():
    rag = get_container().rag
    result = rag.answer("zzzz qqqq xxxx no matching keywords here")
    # No overlap -> no sources, but a safe fallback message.
    assert result.sources == []
    assert "contact the clinic" in result.answer.lower()


def test_document_summary_lists_all_sample_docs():
    rag = get_container().rag
    summary = dict(rag.document_summary())
    for expected in ("clinic_faq.md", "pricing.md", "patient_policy.md", "services.md"):
        assert expected in summary
        assert summary[expected] >= 1
