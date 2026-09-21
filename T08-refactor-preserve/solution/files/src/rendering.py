"""HTML rendering of parsed documents."""

from parsing import heading_outline, parse_document
from validation import validate_document

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
