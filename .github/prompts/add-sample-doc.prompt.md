---
description: "Add a new fake knowledge-base document for RAG and verify it is retrievable."
name: "Add Knowledge Doc"
argument-hint: "e.g. 'insurance.md — coverage and claims FAQ'"
agent: "agent"
---

Add a new document to the local RAG knowledge base.

Rules:
- Create a `.md` file under [data/sample_docs/](../../data/sample_docs/).
- Use only **fake, non-medical, non-PII** content, consistent with the existing
  "BrightSmile Dental Clinic" sample docs.
- Use `##` headings per topic — the loader chunks by heading, so keep one idea per
  section for good keyword retrieval.
- Do not include diagnosis/treatment advice; add the standard "this assistant
  cannot provide medical advice" note where relevant.

Then verify:
1. `GET /api/documents` lists the new file with a chunk count ≥ 1.
2. A representative question retrieves it via `POST /api/documents/search`.
3. Optionally extend [tests/test_rag_service.py](../../tests/test_rag_service.py).

Document to add: $ARGUMENTS
