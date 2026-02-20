from __future__ import annotations

import json

import pytest

from stealth_fetch_mcp.parser import _clean_html, _resolve_url, extract_links


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
