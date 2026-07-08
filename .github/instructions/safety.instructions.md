---
description: "Use when touching safety, escalation, RAG answers, or any user-facing clinical wording. Guards against medical advice and ensures human escalation."
name: "Safety Guardrails"
---

# Safety Guardrails (non-negotiable)

This project is a **demo assistant, not a medical tool**. Whenever you edit
[safety_service.py](../../src/doc_helper_ai_agent/services/safety_service.py),
escalation logic, RAG answer wording, or any user-facing text, uphold these rules:

- **Never** produce a diagnosis, prescription, dosage, or treatment recommendation.
- Detect and escalate these risk signals: severe pain, bleeding, swelling, fever,
  trauma, diagnosis requests, medication/prescription questions, emergencies.
- On any risk signal the response must:
  1. avoid clinical advice,
  2. recommend contacting a professional/clinic (and emergency services if
     life-threatening),
  3. create a callback/escalation and set `requires_human=true`.
- If you **add** a risk term, add a matching case to
  [tests/test_safety_service.py](../../tests/test_safety_service.py).
- If you **relax** detection, stop and confirm with a human first — err on the
  side of over-escalation.
- Use only fake sample data. Never add real patient data or PII.
- RAG answers must stay grounded in the provided documents; if unsure, say so and
  suggest contacting the clinic.
