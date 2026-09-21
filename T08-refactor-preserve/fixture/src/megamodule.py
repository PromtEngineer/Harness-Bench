"""megamodule - parse, validate and render a mini markdown-like language.

This module has grown organically and now mixes three separate concerns in a
single file:

  1. PARSING    - turning source text into a document tree of plain dicts.
  2. VALIDATION - checking a parsed tree against a configurable schema.
  3. RENDERING  - turning a parsed tree into HTML.

Document model
--------------
parse_document() returns:

    {"type": "document", "blocks": [block, ...]}

Block shapes:

    {"type": "heading", "level": int, "text": str, "inline": [...], "slug": str}
    {"type": "paragraph", "inline": [inline, ...]}
    {"type": "list", "items": [[inline, ...], ...]}
    {"type": "code", "language": str, "lines": [str, ...]}

Inline shapes:

    {"type": "text", "value": str}      {"type": "em", "value": str}
    {"type": "strong", "value": str}    {"type": "code", "value": str}
    {"type": "link", "text": str, "url": str}

Public API (used by external callers - keep it stable):
    parse_document, parse_inline, iter_blocks, heading_outline, slugify,
    strip_markup, count_words, validate_document, is_valid, summarize_errors,
    DEFAULT_SCHEMA, render_document, render_block, render_inline, render_toc,
    escape_html, html_from_text.
"""

import re


# ---------------------------------------------------------------------------
# SECTION: parsing
# ---------------------------------------------------------------------------
_SLUG_STRIP = re.compile(r"[^a-z0-9\s-]")
_SLUG_DASH = re.compile(r"[\s-]+")
_INLINE_TOKEN = re.compile(
    r"(\*\*[^*]+\*\*|\*[^*]+\*|`[^`]+`|\[[^\]]*\]\([^)]*\))"
)
_HEADING = re.compile(r"^(#{1,6})\s+(.*)$")
_BULLET = re.compile(r"^[-*]\s+(.*)$")
_FENCE = re.compile(r"^```\s*([A-Za-z0-9_+-]*)\s*$")


def slugify(text):
    """Turn heading text into an anchor slug.

    Lowercases, drops everything but letters/digits/spaces/dashes, then
    collapses runs of spaces and dashes into single dashes.
    """
    t = _SLUG_STRIP.sub("", text.lower())
    t = _SLUG_DASH.sub("-", t.strip())
    return t or "section"


def parse_inline(text):
    """Parse inline markup into a flat list of inline nodes."""
    nodes = []
    pos = 0
    for match in _INLINE_TOKEN.finditer(text):
        if match.start() > pos:
            nodes.append({"type": "text", "value": text[pos:match.start()]})
        token = match.group(0)
        if token.startswith("**"):
            nodes.append({"type": "strong", "value": token[2:-2]})
        elif token.startswith("*"):
            nodes.append({"type": "em", "value": token[1:-1]})
        elif token.startswith("`"):
            nodes.append({"type": "code", "value": token[1:-1]})
        else:
            label, _, url = token[1:-1].partition("](")
            nodes.append({"type": "link", "text": label, "url": url})
        pos = match.end()
    if pos < len(text):
        nodes.append({"type": "text", "value": text[pos:]})
    return nodes


def _heading_block(hashes, title):
    return {
        "type": "heading",
        "level": len(hashes),
        "text": title,
        "inline": parse_inline(title),
        "slug": slugify(title),
    }


def parse_document(text):
    """Parse a whole document string into a document dict."""
    blocks = []
    lines = text.split("\n")
    para = []
    i = 0

    def flush_paragraph():
        if para:
            blocks.append(
                {"type": "paragraph", "inline": parse_inline(" ".join(para))}
            )
            para.clear()

    while i < len(lines):
        stripped = lines[i].strip()
        fence = _FENCE.match(stripped)
        if fence:
            flush_paragraph()
            language = fence.group(1) or "text"
            body = []
            i += 1
            while i < len(lines) and lines[i].strip() != "```":
                body.append(lines[i])
                i += 1
            i += 1  # skip the closing fence (or run past EOF)
            blocks.append({"type": "code", "language": language, "lines": body})
            continue
        heading = _HEADING.match(stripped)
        if heading:
            flush_paragraph()
            blocks.append(_heading_block(heading.group(1), heading.group(2).strip()))
            i += 1
            continue
        if _BULLET.match(stripped):
            flush_paragraph()
            items = []
            while i < len(lines):
                bullet = _BULLET.match(lines[i].strip())
                if not bullet:
                    break
                items.append(parse_inline(bullet.group(1).strip()))
                i += 1
            blocks.append({"type": "list", "items": items})
            continue
        if not stripped:
            flush_paragraph()
            i += 1
            continue
        para.append(stripped)
        i += 1
    flush_paragraph()
    return {"type": "document", "blocks": blocks}


def iter_blocks(doc):
    """Yield every top-level block of a parsed document."""
    for block in doc.get("blocks", []):
        yield block


def heading_outline(doc):
    """Return (level, slug) pairs for every heading, in document order."""
    return [
        (b["level"], b["slug"]) for b in iter_blocks(doc) if b["type"] == "heading"
    ]


def strip_markup(nodes):
    """Plain text of a list of inline nodes (labels for links)."""
    parts = []
    for node in nodes:
        if node["type"] == "link":
            parts.append(node["text"])
        else:
            parts.append(node["value"])
    return "".join(parts)


def count_words(doc):
    """Rough word count over paragraphs, headings and list items."""
    total = 0
    for block in iter_blocks(doc):
        if block["type"] in ("paragraph", "heading"):
            total += len(strip_markup(block["inline"]).split())
        elif block["type"] == "list":
            for item in block["items"]:
                total += len(strip_markup(item).split())
    return total


# ---------------------------------------------------------------------------
# SECTION: validation
# ---------------------------------------------------------------------------
DEFAULT_SCHEMA = {
    "require_h1_first": True,
    "max_heading_level": 4,
    "allowed_languages": {"text", "python", "json", "bash", "html"},
    "max_paragraph_chars": 600,
    "allowed_link_schemes": {"http", "https"},
}


def _merged_schema(schema):
    merged = dict(DEFAULT_SCHEMA)
    if schema:
        merged.update(schema)
    return merged


def _inline_nodes(block):
    if block["type"] in ("paragraph", "heading"):
        yield from block["inline"]
    elif block["type"] == "list":
        for item in block["items"]:
            yield from item


def _link_ok(url, schemes):
    if not url:
        return False
    head, sep, _rest = url.partition(":")
    if sep and "/" not in head:
        return head.lower() in schemes
    return True  # relative URL


def validate_document(doc, schema=None):
    """Return a list of "Exxx: message" strings; empty means valid."""
    rules = _merged_schema(schema)
    errors = []
    seen_slugs = set()
    prev_level = 0
    blocks = list(iter_blocks(doc))
    if rules["require_h1_first"]:
        if not blocks or blocks[0]["type"] != "heading" or blocks[0]["level"] != 1:
            errors.append("E100: document must start with a level-1 heading")
    for idx, block in enumerate(blocks):
        kind = block["type"]
        if kind == "heading":
            if not block["text"]:
                errors.append(f"E101: empty heading at block {idx}")
            if block["level"] > rules["max_heading_level"]:
                errors.append(
                    f"E102: heading level {block['level']} exceeds max "
                    f"{rules['max_heading_level']} at block {idx}"
                )
            if prev_level and block["level"] > prev_level + 1:
                errors.append(
                    f"E103: heading level jumps from {prev_level} to "
                    f"{block['level']} at block {idx}"
                )
            prev_level = block["level"]
            if block["slug"] in seen_slugs:
                errors.append(
                    f"E104: duplicate heading slug '{block['slug']}' at block {idx}"
                )
            seen_slugs.add(block["slug"])
        elif kind == "code":
            if block["language"] not in rules["allowed_languages"]:
                errors.append(
                    f"E105: code language '{block['language']}' not allowed "
                    f"at block {idx}"
                )
        elif kind == "paragraph":
            length = len(strip_markup(block["inline"]))
            if length > rules["max_paragraph_chars"]:
                errors.append(
                    f"E106: paragraph too long ({length} chars) at block {idx}"
                )
        for node in _inline_nodes(block):
            if node["type"] == "link" and not _link_ok(
                node["url"], rules["allowed_link_schemes"]
            ):
                errors.append(
                    f"E107: disallowed link url '{node['url']}' at block {idx}"
                )
    return errors


def is_valid(doc, schema=None):
    """True when validate_document reports no errors."""
    return not validate_document(doc, schema)


def summarize_errors(errors):
    """Map error code (e.g. 'E104') to the number of occurrences."""
    counts = {}
    for err in errors:
        code = err.split(":", 1)[0]
        counts[code] = counts.get(code, 0) + 1
    return counts


# ---------------------------------------------------------------------------
# SECTION: rendering
# ---------------------------------------------------------------------------
_ESCAPES = (("&", "&amp;"), ("<", "&lt;"), (">", "&gt;"), ('"', "&quot;"))


def escape_html(text):
    """Escape &, <, > and double quotes for safe HTML embedding."""
    for raw, safe in _ESCAPES:
        text = text.replace(raw, safe)
    return text


def render_inline(nodes):
    """Render a list of inline nodes to an HTML fragment."""
    parts = []
    for node in nodes:
        kind = node["type"]
        if kind == "text":
            parts.append(escape_html(node["value"]))
        elif kind == "em":
            parts.append("<em>%s</em>" % escape_html(node["value"]))
        elif kind == "strong":
            parts.append("<strong>%s</strong>" % escape_html(node["value"]))
        elif kind == "code":
            parts.append("<code>%s</code>" % escape_html(node["value"]))
        elif kind == "link":
            parts.append(
                '<a href="%s">%s</a>'
                % (escape_html(node["url"]), escape_html(node["text"]))
            )
        else:
            raise ValueError("unknown inline node type: %r" % kind)
    return "".join(parts)


def render_block(block):
    """Render one block dict to an HTML string."""
    kind = block["type"]
    if kind == "heading":
        level = block["level"]
        return '<h%d id="%s">%s</h%d>' % (
            level, block["slug"], render_inline(block["inline"]), level,
        )
    if kind == "paragraph":
        return "<p>%s</p>" % render_inline(block["inline"])
    if kind == "list":
        items = "".join(
            "<li>%s</li>" % render_inline(item) for item in block["items"]
        )
        return "<ul>%s</ul>" % items
    if kind == "code":
        body = escape_html("\n".join(block["lines"]))
        return '<pre><code class="language-%s">%s</code></pre>' % (
            block["language"], body,
        )
    raise ValueError("unknown block type: %r" % kind)


def render_toc(doc):
    """Render a flat table of contents linking to heading slugs."""
    entries = "".join(
        '<li class="level-%d"><a href="#%s">%s</a></li>' % (level, slug, slug)
        for level, slug in heading_outline(doc)
    )
    return '<nav class="toc"><ol>%s</ol></nav>' % entries


def render_document(doc, title=None, strict=False):
    """Render a document to an <article> HTML string.

    With strict=True the document is validated first and ValueError is
    raised on the first validation error.
    """
    if strict:
        errors = validate_document(doc)
        if errors:
            raise ValueError(errors[0])
    body = "\n".join(render_block(b) for b in doc.get("blocks", []))
    if title is None:
        return "<article>\n%s\n</article>" % body
    return '<article aria-label="%s">\n%s\n</article>' % (escape_html(title), body)


def html_from_text(text, schema=None, title=None):
    """One-shot pipeline: parse, validate, then render.

    Raises ValueError with all validation messages joined by '; '.
    """
    doc = parse_document(text)
    errors = validate_document(doc, schema)
    if errors:
        raise ValueError("; ".join(errors))
    return render_document(doc, title=title)
