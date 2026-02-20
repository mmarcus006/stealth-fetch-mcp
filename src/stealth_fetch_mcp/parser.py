from __future__ import annotations

import json
import re
from urllib.parse import urljoin

from bs4 import BeautifulSoup, NavigableString, Tag
from bs4.element import AttributeValueList, PageElement

NOISE_TAGS = {"script", "style", "noscript", "nav", "footer", "aside", "form", "svg", "iframe"}


def _normalize_whitespace(value: str) -> str:
    return re.sub(r"\s+", " ", value).strip()


def _truncate(value: str, max_chars: int) -> str:
    if max_chars <= 0:
        return "[truncated at 0 chars]"
    if len(value) <= max_chars:
        return value
    truncated = value[:max_chars].rstrip()
    return f"{truncated}\n[truncated at {max_chars} chars]"


def _href_to_str(value: str | AttributeValueList | None) -> str:
    if value is None:
        return ""
    if isinstance(value, list):
        return " ".join(str(item) for item in value)
    return str(value)


def _inline_text(node: PageElement) -> str:
    if isinstance(node, NavigableString):
        return _normalize_whitespace(str(node))
    if not isinstance(node, Tag):
        return ""
    if node.name in NOISE_TAGS:
        return ""
    if node.name == "a":
        href = _href_to_str(node.get("href")).strip()
        text = _normalize_whitespace(" ".join(_inline_text(c) for c in node.children))
        if not text:
            text = href
        if href:
            return f"[{text}]({href})"
        return text
    parts = [_inline_text(child) for child in node.children]
    return _normalize_whitespace(" ".join(part for part in parts if part))


def _clean_html(html: str, selector: str | None = None, max_chars: int = 50_000) -> str:
    soup = BeautifulSoup(html, "lxml")
    for tag in soup.find_all(NOISE_TAGS):
        tag.decompose()

    target: Tag | BeautifulSoup | None = soup.body or soup
    prefix = ""
    if selector:
        selected = soup.select_one(selector)
        if selected is None:
            prefix = f"[selector not found: {selector}]\n\n"
        else:
            target = selected

    lines: list[str] = []
    if target is None:
        return _truncate(prefix.strip(), max_chars=max_chars)

    tracked_tags = ["h1", "h2", "h3", "h4", "h5", "h6", "p", "li", "div"]
    tracked_tag_set = set(tracked_tags)
    for tag in target.find_all(tracked_tags, recursive=True):
        if not isinstance(tag, Tag):
            continue
        if tag.name == "div":
            has_nested_blocks = any(
                isinstance(child, Tag) and child.name in tracked_tag_set
                for child in tag.children
            )
            if has_nested_blocks:
                continue
        text = _normalize_whitespace(_inline_text(tag))
        if not text:
            continue
        if tag.name in {"h1", "h2", "h3", "h4", "h5", "h6"}:
            level = int(tag.name[1])
            lines.append(f"{'#' * level} {text}")
        elif tag.name == "li":
            lines.append(f"- {text}")
        else:
            lines.append(text)

    rendered = prefix + "\n".join(lines)
    return _truncate(rendered.strip(), max_chars=max_chars)


def _resolve_url(base: str, href: str) -> str:
    return urljoin(base, href)


def extract_links(
    html: str,
    base_url: str,
    selector: str = "a[href]",
    pattern: str | None = None,
    max_results: int = 100,
) -> str:
    regex: re.Pattern[str] | None = None
    if pattern:
        try:
            regex = re.compile(pattern)
        except re.error as exc:
            raise ValueError(f"Invalid regex pattern: {exc}") from exc

    soup = BeautifulSoup(html, "lxml")
    results: list[dict[str, str]] = []
    for tag in soup.select(selector):
        if not isinstance(tag, Tag):
            continue
        href = _href_to_str(tag.get("href")).strip()
        if not href:
            continue
        if regex and regex.search(href) is None:
            continue
        text = _normalize_whitespace(tag.get_text(" ", strip=True))
        results.append(
            {
                "text": text,
                "href": href,
                "absolute_url": _resolve_url(base_url, href),
            }
        )
        if len(results) >= max_results:
            break

    return json.dumps(results, indent=2)
