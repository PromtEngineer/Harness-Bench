from megamodule import parse_document, validate_document


def _codes(errors):
    return [e.split(":", 1)[0] for e in errors]


def test_valid_document_has_no_errors():
    doc = parse_document("# Title\n\nSome perfectly normal text.")
    assert validate_document(doc) == []


def test_missing_h1_reported():
    doc = parse_document("## Only a subheading")
    assert _codes(validate_document(doc)) == ["E100"]


def test_heading_level_jump():
    doc = parse_document("# A\n\n### B")
    assert _codes(validate_document(doc)) == ["E103"]


def test_code_language_whitelist():
    doc = parse_document("# T\n\n```ruby\nputs 1\n```")
    errors = validate_document(doc)
    assert _codes(errors) == ["E105"] and "ruby" in errors[0]


def test_link_scheme_rules():
    bad = parse_document("# T\n\nClick [here](javascript:void0).")
    assert _codes(validate_document(bad)) == ["E107"]
    ok = parse_document("# T\n\nSee [rel](docs/a.md) and [abs](https://x.io).")
    assert validate_document(ok) == []


def test_duplicate_slug_and_schema_override():
    doc = parse_document("# Intro\n\n## Intro")
    assert _codes(validate_document(doc)) == ["E104"]
    strict = validate_document(doc, {"max_heading_level": 1})
    assert sorted(_codes(strict)) == ["E102", "E104"]
