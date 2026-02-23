from __future__ import annotations

import json

import pytest

from stealth_fetch_mcp.parser import (
    _clean_html,
    _resolve_url,
    extract_links,
    extract_metadata,
    extract_tables,
    parse_feed,
)


def test_resolve_url_with_relative_href() -> None:
    assert (
        _resolve_url("https://example.com/docs/page.html", "../about")
        == "https://example.com/about"
    )


def test_clean_html_removes_noise_and_preserves_structure() -> None:
    html = """
    <html>
      <body>
        <nav>menu</nav>
        <h1>Heading</h1>
        <p>Paragraph <a href="/a">Link</a></p>
        <ul><li>First</li><li>Second</li></ul>
        <script>alert("x")</script>
      </body>
    </html>
    """

    text = _clean_html(html)

    assert "menu" not in text
    assert 'alert("x")' not in text
    assert "# Heading" in text
    assert "[Link](/a)" in text
    assert "- First" in text
    assert "- Second" in text


def test_clean_html_scoped_selector_and_fallback() -> None:
    html = """
    <html>
      <body>
        <div class="main">
          <h2>Main Section</h2>
        </div>
        <div class="other">Other Section</div>
      </body>
    </html>
    """

    scoped = _clean_html(html, selector=".main")
    fallback = _clean_html(html, selector=".missing")

    assert "Main Section" in scoped
    assert "Other Section" not in scoped
    assert "[selector not found: .missing]" in fallback
    assert "Other Section" in fallback


def test_clean_html_truncates_with_marker() -> None:
    html = "<html><body><p>" + ("x" * 50) + "</p></body></html>"
    text = _clean_html(html, max_chars=20)
    assert text.endswith("[truncated at 20 chars]")


def test_extract_links_with_pattern_and_max_results() -> None:
    html = """
    <html>
      <body>
        <a href="/news/1">One</a>
        <a href="/blog/2">Two</a>
        <a href="/news/3">Three</a>
      </body>
    </html>
    """

    payload = extract_links(
        html=html,
        base_url="https://example.com/root",
        selector="a[href]",
        pattern=r"/news/",
        max_results=1,
    )
    data = json.loads(payload)

    assert len(data) == 1
    assert data[0]["text"] == "One"
    assert data[0]["href"] == "/news/1"
    assert data[0]["absolute_url"] == "https://example.com/news/1"


def test_extract_links_invalid_regex_raises_value_error() -> None:
    with pytest.raises(ValueError, match="Invalid regex pattern"):
        extract_links(
            html="<a href='/x'>x</a>",
            base_url="https://example.com",
            selector="a[href]",
            pattern="(",
            max_results=10,
        )


# --- extract_metadata ---

def test_extract_metadata_json_ld_and_og_and_twitter_and_meta() -> None:
    html = """
    <html>
      <head>
        <script type="application/ld+json">{"@type": "Article", "name": "Test"}</script>
        <meta property="og:title" content="OG Title" />
        <meta property="og:url" content="https://example.com" />
        <meta name="twitter:card" content="summary" />
        <meta name="description" content="Page desc" />
        <meta name="viewport" content="width=device-width" />
      </head>
      <body></body>
    </html>
    """
    data = json.loads(extract_metadata(html))

    assert data["json_ld"] == [{"@type": "Article", "name": "Test"}]
    assert data["opengraph"]["title"] == "OG Title"
    assert data["opengraph"]["url"] == "https://example.com"
    assert data["twitter"]["card"] == "summary"
    assert data["meta"]["description"] == "Page desc"
    assert data["meta"]["viewport"] == "width=device-width"
    assert "title" not in data["meta"]
    assert "card" not in data["meta"]


def test_extract_metadata_invalid_json_ld_skipped() -> None:
    html = '<html><head><script type="application/ld+json">not json</script></head></html>'
    data = json.loads(extract_metadata(html))
    assert data["json_ld"] == []


def test_extract_metadata_empty_page() -> None:
    data = json.loads(extract_metadata("<html></html>"))
    assert data == {"json_ld": [], "opengraph": {}, "twitter": {}, "meta": {}}


# --- extract_tables ---

def test_extract_tables_with_thead_and_tbody() -> None:
    html = """
    <html><body>
      <table>
        <thead><tr><th>Name</th><th>Age</th></tr></thead>
        <tbody>
          <tr><td>Alice</td><td>30</td></tr>
          <tr><td>Bob</td><td>25</td></tr>
        </tbody>
      </table>
    </body></html>
    """
    data = json.loads(extract_tables(html))

    assert len(data) == 1
    assert data[0]["headers"] == ["Name", "Age"]
    assert data[0]["rows"] == [["Alice", "30"], ["Bob", "25"]]


def test_extract_tables_th_in_first_row_as_headers() -> None:
    html = """
    <html><body>
      <table>
        <tr><th>Col1</th><th>Col2</th></tr>
        <tr><td>val1</td><td>val2</td></tr>
      </table>
    </body></html>
    """
    data = json.loads(extract_tables(html))
    assert data[0]["headers"] == ["Col1", "Col2"]
    assert data[0]["rows"] == [["val1", "val2"]]


def test_extract_tables_headerless() -> None:
    html = "<html><body><table><tr><td>A</td><td>B</td></tr></table></body></html>"
    data = json.loads(extract_tables(html))
    assert data[0]["headers"] == []
    assert data[0]["rows"] == [["A", "B"]]


def test_extract_tables_multiple_tables() -> None:
    html = """
    <html><body>
      <table><tr><th>X</th></tr><tr><td>1</td></tr></table>
      <table><tr><th>Y</th></tr><tr><td>2</td></tr></table>
    </body></html>
    """
    data = json.loads(extract_tables(html))
    assert len(data) == 2
    assert data[0]["headers"] == ["X"]
    assert data[1]["headers"] == ["Y"]


def test_extract_tables_empty_page() -> None:
    data = json.loads(extract_tables("<html><body></body></html>"))
    assert data == []


# --- parse_feed ---

_RSS_SAMPLE = """<?xml version="1.0"?>
<rss version="2.0">
  <channel>
    <title>My Blog</title>
    <link>https://blog.example.com</link>
    <item>
      <title>First Post</title>
      <link>https://blog.example.com/1</link>
      <pubDate>Mon, 01 Jan 2024 00:00:00 GMT</pubDate>
      <description>Hello world</description>
    </item>
    <item>
      <title>Second Post</title>
      <link>https://blog.example.com/2</link>
      <pubDate>Tue, 02 Jan 2024 00:00:00 GMT</pubDate>
      <description>Follow-up</description>
    </item>
  </channel>
</rss>"""

_ATOM_SAMPLE = """<?xml version="1.0"?>
<feed xmlns="http://www.w3.org/2005/Atom">
  <title>Atom Feed</title>
  <link href="https://atom.example.com" />
  <entry>
    <title>Entry One</title>
    <link href="https://atom.example.com/1" />
    <updated>2024-01-01T00:00:00Z</updated>
    <summary>Atom summary</summary>
  </entry>
</feed>"""


def test_parse_feed_rss() -> None:
    data = json.loads(parse_feed(_RSS_SAMPLE))
    assert data["feed_title"] == "My Blog"
    assert data["feed_link"] == "https://blog.example.com"
    assert len(data["items"]) == 2
    assert data["items"][0]["title"] == "First Post"
    assert data["items"][0]["summary"] == "Hello world"
    assert data["items"][1]["title"] == "Second Post"


def test_parse_feed_rss_max_items() -> None:
    data = json.loads(parse_feed(_RSS_SAMPLE, max_items=1))
    assert len(data["items"]) == 1


def test_parse_feed_atom() -> None:
    data = json.loads(parse_feed(_ATOM_SAMPLE))
    assert data["feed_title"] == "Atom Feed"
    assert data["feed_link"] == "https://atom.example.com"
    assert len(data["items"]) == 1
    assert data["items"][0]["title"] == "Entry One"
    assert data["items"][0]["link"] == "https://atom.example.com/1"
    assert data["items"][0]["summary"] == "Atom summary"
    assert data["items"][0]["published"] == "2024-01-01T00:00:00Z"


def test_parse_feed_invalid_xml_raises() -> None:
    with pytest.raises(ValueError, match="Invalid XML feed"):
        parse_feed("this is not xml")


def test_parse_feed_unknown_root_raises() -> None:
    with pytest.raises(ValueError, match="Unrecognized feed format"):
        parse_feed("<html><body>not a feed</body></html>")
