from megamodule import escape_html, parse_document, render_document, slugify


def test_render_heading_and_paragraph():
    html = render_document(parse_document("# Hi\n\nHello *world*."))
    assert html.startswith("<article>")
    assert '<h1 id="hi">Hi</h1>' in html
    assert "<p>Hello <em>world</em>.</p>" in html


def test_escape_html_and_render_escaping():
    assert escape_html('<b> & "x"') == '&lt;b&gt; &amp; &quot;x&quot;'
    html = render_document(parse_document("# T\n\nA <script> tag & stuff."))
    assert "&lt;script&gt;" in html and "&amp;" in html
    assert "<script>" not in html


def test_render_list_code_and_slugify():
    assert slugify("Hello, World!") == "hello-world"
    text = "# Demo\n\n- alpha\n- beta\n\n```python\nprint(1)\n```"
    html = render_document(parse_document(text))
    assert "<ul><li>alpha</li><li>beta</li></ul>" in html
    assert '<pre><code class="language-python">print(1)</code></pre>' in html
