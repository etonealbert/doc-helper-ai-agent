"""LangGraph-based agentic workflow.

The graph classifies a message, runs a safety check, routes to the appropriate
capability (RAG, appointment intake, complaint intake, or human escalation), and
composes a final structured response.
"""
