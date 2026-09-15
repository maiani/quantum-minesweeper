"""Load trusted user-facing HTML fragments from package content."""

from pathlib import Path

PAGE_CONTENT = ("simple_setup", "advanced_setup", "about")


def load_html_fragment(path: Path) -> str:
    """Return one trusted package-owned HTML fragment."""
    if not path.exists():
        return "<p>Not found.</p>"
    return path.read_text(encoding="utf-8")


def load_page_content(content_dir: Path) -> dict[str, str]:
    """Load the English page fragments used by setup and About templates."""
    english_dir = content_dir / "en"
    return {
        name: load_html_fragment(english_dir / f"{name}.html")
        for name in PAGE_CONTENT
    }
