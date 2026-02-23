# Project Overview

## Name
stealth-fetch-mcp

## Purpose
`stealth-fetch-mcp` is a local MCP (Model Context Protocol) server that fetches and parses web content using browser-grade TLS fingerprint impersonation via `curl_cffi`. It solves the problem of MCP clients (Claude Code/Desktop, Codex, and similar AI tools) being blocked by websites that detect and reject default Python HTTP client signatures.

## Problem It Solves
Many websites employ bot-detection mechanisms that fingerprint TLS handshakes, HTTP/2 settings, and header patterns. Standard Python HTTP libraries (`requests`, `httpx`, `aiohttp`) produce machine-identifiable signatures that trigger blocking. This server wraps `curl_cffi` — which can impersonate real browser TLS/JA3/HTTP2 fingerprints — behind a set of structured MCP tools, giving AI agents resilient web access without requiring a headless browser.

## Target Audience
- AI agent developers who need reliable web fetching from MCP-compatible clients
- Claude Code, Claude Desktop, and Codex CLI users who want a drop-in stealth fetch tool
- Developers building workflows that require scraping or API access through bot-protected endpoints

## Key Capabilities
- 9 read-only, idempotent MCP tools covering raw HTML, readable text, JSON APIs, link extraction, HTTP headers, structured metadata, HTML tables, RSS/Atom feeds, and concurrent bulk fetching
- Browser impersonation profiles (default: Chrome) with full `curl_cffi` session/request option passthrough
- Output truncation, actionable error messages, and strict Pydantic input validation
- Context-engineered `SERVER_INSTRUCTIONS` that guide consuming models on tool selection and compliance

## Constraints
- Not a CAPTCHA solver — improves transport-level compatibility only
- No streaming or multipart upload support (by design)
- Requires Python 3.12+ and `uv`/`uvx` for package management
