"""Parsing for the mini markdown-like document language."""

import re

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
