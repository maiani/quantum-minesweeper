"""Shared Markdown rendering for user-facing documentation snippets."""

from __future__ import annotations

from pathlib import Path

import markdown
from markdown.extensions.toc import TocExtension


def render_markdown(path: Path, strip_title: bool = False) -> tuple[str, str]:
    """Render a Markdown file to ``(title, html)``."""
    if not path.exists():
        return path.stem, "<p>Not found.</p>"

    text = path.read_text(encoding="utf-8")
    title = path.stem

    if strip_title:
        lines = text.splitlines()
        for i, line in enumerate(lines):
            if line.strip().startswith("#"):
                title = line.lstrip("# ").strip()
                lines = lines[i + 1 :]
                break
        text = "\n".join(lines).strip()

    html = markdown.markdown(
        text,
        extensions=[
            "fenced_code",
            "tables",
            TocExtension(),
            "pymdownx.arithmatex",
        ],
        extension_configs={"pymdownx.arithmatex": {"generic": True}},
    )
    return title, html


def load_docs(docs_dir: Path) -> dict[str, str]:
    """Load the documentation snippets used by setup/about templates."""
    return {
        "simple_setup": render_markdown(docs_dir / "simple_setup.md")[1],
        "advanced_setup": render_markdown(docs_dir / "advanced_setup.md")[1],
        "about": render_markdown(docs_dir / "about.md")[1],
    }
