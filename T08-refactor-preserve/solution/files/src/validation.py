"""Validation of parsed documents against a configurable schema."""

from parsing import iter_blocks, strip_markup

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
