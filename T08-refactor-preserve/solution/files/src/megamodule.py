"""megamodule - thin facade over parsing.py, validation.py, rendering.py.

The original single-file implementation was split by concern; this module
re-exports the public API so existing imports keep working unchanged.
"""

from parsing import (
    count_words,
    heading_outline,
    iter_blocks,
    parse_document,
    parse_inline,
    slugify,
    strip_markup,
)
from rendering import (
    escape_html,
    html_from_text,
    render_block,
    render_document,
    render_inline,
    render_toc,
)
from validation import (
    DEFAULT_SCHEMA,
    is_valid,
    summarize_errors,
    validate_document,
)

__all__ = [
    "DEFAULT_SCHEMA",
    "count_words",
    "escape_html",
    "heading_outline",
    "html_from_text",
    "is_valid",
    "iter_blocks",
    "parse_document",
    "parse_inline",
    "render_block",
    "render_document",
    "render_inline",
    "render_toc",
    "slugify",
    "strip_markup",
    "summarize_errors",
    "validate_document",
]
