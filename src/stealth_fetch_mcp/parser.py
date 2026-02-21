from __future__ import annotations

import json
import re
import xml.etree.ElementTree as ET
from typing import Any
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


# --- Metadata extraction ---

def extract_metadata(html: str) -> str:
    """Extract JSON-LD, Open Graph, Twitter Card, and standard meta tags as structured JSON."""
    soup = BeautifulSoup(html, "lxml")

    json_ld: list[Any] = []
    for tag in soup.find_all("script", type="application/ld+json"):
        raw = tag.string or ""
        try:
            json_ld.append(json.loads(raw))
        except (json.JSONDecodeError, ValueError):
            pass

    opengraph: dict[str, str] = {}
    for tag in soup.find_all("meta", attrs={"property": True}):
        prop = str(tag.get("property", ""))
        if prop.startswith("og:"):
            opengraph[prop[3:]] = str(tag.get("content", ""))

    twitter: dict[str, str] = {}
    for tag in soup.find_all("meta", attrs={"name": True}):
        name = str(tag.get("name", ""))
        if name.startswith("twitter:"):
            twitter[name[8:]] = str(tag.get("content", ""))

    meta: dict[str, str] = {}
    for tag in soup.find_all("meta"):
        raw_name = tag.get("name") or tag.get("http-equiv")
        content = tag.get("content")
        if not raw_name or not content:
            continue
        name_str = str(raw_name)
        if name_str.startswith(("og:", "twitter:")):
            continue
        meta[name_str] = str(content)

    return json.dumps(
        {"json_ld": json_ld, "opengraph": opengraph, "twitter": twitter, "meta": meta},
        indent=2,
    )


# --- Table extraction ---

def extract_tables(html: str, selector: str | None = None) -> str:
    """Extract <table> elements from HTML as a list of {headers, rows} objects."""
    soup = BeautifulSoup(html, "lxml")
    root: Tag | BeautifulSoup = soup
    if selector:
        found = soup.select_one(selector)
        if found is not None:
            root = found

    table_els: list[Any]
    if isinstance(root, Tag) and root.name == "table":
        table_els = [root]
    else:
        table_els = root.find_all("table")

    results: list[dict[str, Any]] = []
    for table in table_els:
        if not isinstance(table, Tag):
            continue
        headers: list[str] = []

        thead = table.find("thead")
        if isinstance(thead, Tag):
            header_tr = thead.find("tr")
            if isinstance(header_tr, Tag):
                headers = [
                    _normalize_whitespace(cell.get_text())
                    for cell in header_tr.find_all(["th", "td"])
                ]

        if not headers:
            first_tr = table.find("tr")
            if isinstance(first_tr, Tag) and first_tr.find("th"):
                headers = [
                    _normalize_whitespace(cell.get_text())
                    for cell in first_tr.find_all(["th", "td"])
                ]

        tbody = table.find("tbody")
        row_source: Tag = tbody if isinstance(tbody, Tag) else table
        rows: list[list[str]] = []
        for tr in row_source.find_all("tr"):
            if not isinstance(tr, Tag):
                continue
            cells = [_normalize_whitespace(td.get_text()) for td in tr.find_all(["td", "th"])]
            if any(cells):
                rows.append(cells)

        if headers and rows and rows[0] == headers:
            rows = rows[1:]

        results.append({"headers": headers, "rows": rows})

    return json.dumps(results, indent=2)


# --- Feed parsing (RSS 2.0 / Atom) ---

_ATOM_NS = "http://www.w3.org/2005/Atom"


def _xml_text(el: ET.Element | None) -> str:
    if el is None:
        return ""
    return (el.text or "").strip()


def parse_feed(xml_text: str, max_items: int = 50) -> str:
    """Parse an RSS 2.0 or Atom feed into structured JSON."""
    try:
        root = ET.fromstring(xml_text.strip())
    except ET.ParseError as exc:
        raise ValueError(f"Invalid XML feed: {exc}") from exc

    feed_title = ""
    feed_link = ""
    items: list[dict[str, str]] = []

    tag = root.tag
    if tag == "rss" or tag.endswith("}rss"):
        channel = root.find("channel")
        if channel is not None:
            feed_title = _xml_text(channel.find("title"))
            feed_link = _xml_text(channel.find("link"))
            for item_el in channel.findall("item")[:max_items]:
                items.append({
                    "title": _xml_text(item_el.find("title")),
                    "link": _xml_text(item_el.find("link")),
                    "published": _xml_text(item_el.find("pubDate")),
                    "summary": _xml_text(item_el.find("description")),
                })
    elif tag == f"{{{_ATOM_NS}}}feed" or tag == "feed":
        pfx = f"{{{_ATOM_NS}}}" if tag.startswith("{") else ""
        feed_title = _xml_text(root.find(f"{pfx}title"))
        link_el = root.find(f"{pfx}link")
        feed_link = (link_el.get("href") or "") if link_el is not None else ""
        for entry in root.findall(f"{pfx}entry")[:max_items]:
            link_entry = entry.find(f"{pfx}link")
            link_href = (link_entry.get("href") or "") if link_entry is not None else ""
            summary_el = entry.find(f"{pfx}summary")
            if summary_el is None:
                summary_el = entry.find(f"{pfx}content")
            pub_el = entry.find(f"{pfx}updated")
            if pub_el is None:
                pub_el = entry.find(f"{pfx}published")
            items.append({
                "title": _xml_text(entry.find(f"{pfx}title")),
                "link": link_href,
                "published": _xml_text(pub_el),
                "summary": _xml_text(summary_el),
            })
    else:
        raise ValueError(f"Unrecognized feed format: root tag '{tag}'")

    return json.dumps({"feed_title": feed_title, "feed_link": feed_link, "items": items}, indent=2)


# --- Robots.txt parsing ---

def parse_robots_txt(text: str) -> dict[str, Any]:
    """Parse robots.txt content into {user_agents, sitemaps} structure."""
    user_agents: dict[str, dict[str, Any]] = {}
    sitemaps: list[str] = []
    current_agents: list[str] = []

    for raw_line in text.splitlines():
        line = raw_line.split("#")[0].strip()
        if not line:
            current_agents = []
            continue
        if ":" not in line:
            continue
        key, _, value = line.partition(":")
        key = key.strip().lower()
        value = value.strip()

        if key == "user-agent":
            if value not in user_agents:
                user_agents[value] = {"allow": [], "disallow": [], "crawl_delay": None}
            current_agents.append(value)
        elif key == "disallow":
            for agent in current_agents:
                if agent in user_agents:
                    user_agents[agent]["disallow"].append(value)
        elif key == "allow":
            for agent in current_agents:
                if agent in user_agents:
                    user_agents[agent]["allow"].append(value)
        elif key == "crawl-delay":
            try:
                delay = float(value)
            except ValueError:
                pass
            else:
                for agent in current_agents:
                    if agent in user_agents:
                        user_agents[agent]["crawl_delay"] = delay
        elif key == "sitemap":
            if value not in sitemaps:
                sitemaps.append(value)

    return {"user_agents": user_agents, "sitemaps": sitemaps}
