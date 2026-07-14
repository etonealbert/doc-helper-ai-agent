"""Load and chunk markdown/text documents from the sample docs directory."""

from __future__ import annotations

from pathlib import Path

from doc_helper_ai_agent.core.logging import get_logger

logger = get_logger(__name__)

_MAX_CHUNK_CHARS = 900


def _split_into_sections(text: str) -> list[str]:
    """Split markdown by top-level-ish headings, keeping the heading with its body."""
    sections: list[str] = []
    current: list[str] = []
    for line in text.splitlines():
        if line.startswith("#") and current:
            sections.append("\n".join(current).strip())
            current = [line]
        else:
            current.append(line)
    if current:
        sections.append("\n".join(current).strip())
    sections = [section for section in sections if section]
    if not sections:
        return []

    document_heading = sections[0].splitlines()[0]
    if not document_heading.startswith("# "):
        return sections
    return [
        section
        if index == 0 or section.startswith(document_heading)
        else f"{document_heading}\n\n{section}"
        for index, section in enumerate(sections)
    ]


def _chunk_section(section: str) -> list[str]:
    """Further split a large section into paragraph-aligned chunks."""
    if len(section) <= _MAX_CHUNK_CHARS:
        return [section]
    chunks: list[str] = []
    buffer: list[str] = []
    size = 0
    for para in section.split("\n\n"):
        para = para.strip()
        if not para:
            continue
        if size + len(para) > _MAX_CHUNK_CHARS and buffer:
            chunks.append("\n\n".join(buffer))
            buffer, size = [], 0
        buffer.append(para)
        size += len(para)
    if buffer:
        chunks.append("\n\n".join(buffer))
    return chunks


def load_documents(docs_dir: Path) -> list[dict[str, str]]:
    """Load ``*.md`` / ``*.txt`` files and return a flat list of chunks.

    Each chunk is ``{"id", "text", "source", "locale"}``. Files directly in
    ``docs_dir`` are English; files under an ``en`` or ``es`` directory use that
    locale. ``source`` remains the filename so citations are language-neutral.
    """
    if not docs_dir.exists():
        logger.warning("Sample docs directory does not exist: %s", docs_dir)
        return []

    chunks: list[dict[str, str]] = []
    for path in sorted(docs_dir.glob("**/*")):
        if path.suffix.lower() not in {".md", ".txt"}:
            continue
        try:
            text = path.read_text(encoding="utf-8")
        except OSError as exc:
            logger.warning("Could not read %s: %s", path, exc)
            continue
        relative_parts = path.relative_to(docs_dir).parts
        locale = relative_parts[0] if relative_parts[0] in {"en", "es"} else "en"
        source = path.name
        for section in _split_into_sections(text):
            for piece in _chunk_section(section):
                chunks.append(
                    {
                        "id": f"{locale}:{source}::{len(chunks)}",
                        "text": piece,
                        "source": source,
                        "locale": locale,
                    }
                )
    logger.info("Loaded %d chunk(s) from %s", len(chunks), docs_dir)
    return chunks
