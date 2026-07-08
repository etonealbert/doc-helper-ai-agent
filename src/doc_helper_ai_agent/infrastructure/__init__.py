"""Infrastructure adapters: mock CRM, mock schedule, and the local vector store.

These stand in for external systems so the project runs fully offline. Each
adapter is exposed as a lazily-created process singleton via a ``get_*`` helper.
"""
