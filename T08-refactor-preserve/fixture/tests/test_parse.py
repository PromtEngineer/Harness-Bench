from megamodule import iter_blocks, parse_document


def test_parse_heading():
    doc = parse_document("# Hello World")
    blocks = doc["blocks"]
    assert doc["type"] == "document" and len(blocks) == 1
    h = blocks[0]
    assert h["type"] == "heading" and h["level"] == 1
    assert h["text"] == "Hello World" and h["slug"] == "hello-world"
    assert h["inline"] == [{"type": "text", "value": "Hello World"}]


def test_parse_paragraph_inline():
    doc = parse_document("This is *fine* and **bold** with `code`.")
    (p,) = doc["blocks"]
    assert p["type"] == "paragraph"
    kinds = [n["type"] for n in p["inline"]]
    assert kinds == ["text", "em", "text", "strong", "text", "code", "text"]
    assert p["inline"][1] == {"type": "em", "value": "fine"}
    assert p["inline"][3] == {"type": "strong", "value": "bold"}
    assert p["inline"][5] == {"type": "code", "value": "code"}


def test_parse_list():
    doc = parse_document("- one\n- two\n- three")
    (lst,) = doc["blocks"]
    assert lst["type"] == "list" and len(lst["items"]) == 3
    assert lst["items"][1] == [{"type": "text", "value": "two"}]


def test_parse_code_fence():
    doc = parse_document("```python\nx = 1\n\ny = 2\n```")
    (code,) = doc["blocks"]
    assert code["type"] == "code"
    assert code["language"] == "python"
    assert code["lines"] == ["x = 1", "", "y = 2"]


def test_iter_blocks_and_links():
    text = "# Title\n\nSee [docs](https://example.com/d).\n\n- item"
    doc = parse_document(text)
    blocks = list(iter_blocks(doc))
    assert [b["type"] for b in blocks] == ["heading", "paragraph", "list"]
    link = blocks[1]["inline"][1]
    assert link == {"type": "link", "text": "docs", "url": "https://example.com/d"}
