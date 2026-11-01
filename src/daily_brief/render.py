"""Render an edition's content JSON to print-ready HTML and PDF."""

import os
import sys
from datetime import date, timedelta
from pathlib import Path

from jinja2 import Environment, FileSystemLoader, select_autoescape

from daily_brief import puzzles

TEMPLATES = Path(__file__).parent / "templates"


def _weasyprint():
    try:
        import weasyprint
    except OSError:
        # Homebrew's pango/cairo live outside the default macOS search path, and
        # DYLD_* must be set before the process starts, so re-exec once with it.
        if sys.platform == "darwin" and "DYLD_FALLBACK_LIBRARY_PATH" not in os.environ:
            env = {**os.environ, "DYLD_FALLBACK_LIBRARY_PATH": "/opt/homebrew/lib:/usr/local/lib"}
            os.execve(sys.executable, [sys.executable, *sys.argv], env)
        raise
    return weasyprint


# "full": two pages, for duplex printing. "compact": one page, small PDF for email.
LAYOUTS = {"full": "brief", "compact": "compact"}


def _fill_puzzles(content: dict, day: date) -> None:
    """Generate the grids for sudoku blocks, plus yesterday's solution."""
    for page in content["pages"]:
        for b in (page.get("left") or []) + (page.get("right") or []):
            if b.get("kind") == "sudoku":
                level = b.get("level", "easy")
                b["grid"], _ = puzzles.sudoku(day, level)
                _, b["prev_solution"] = puzzles.sudoku(day - timedelta(days=1), level)


def to_html(content: dict, config: dict, layout: str = "full") -> str:
    env = Environment(loader=FileSystemLoader(TEMPLATES), autoescape=select_autoescape())
    name = LAYOUTS[layout]
    day = date.fromisoformat(content["date"])
    _fill_puzzles(content, day)
    return env.get_template(f"{name}.html.j2").render(
        c=content,
        cfg=config,
        title=content.get("title") or (config.get("paper") or {}).get("title") or "The Daily Brief",
        css=(TEMPLATES / f"{name}.css").read_text(),
        long_date=day.strftime("%A, %-d %B %Y"),
    )


def to_pdf(content: dict, config: dict, out: Path, layout: str = "full") -> int:
    """Write the PDF (and the HTML next to it); return the page count."""
    html = to_html(content, config, layout)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.with_suffix(".html").write_text(html)
    doc = _weasyprint().HTML(string=html, base_url=str(TEMPLATES)).render()
    doc.write_pdf(out)
    return len(doc.pages)
