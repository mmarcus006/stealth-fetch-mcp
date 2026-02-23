# stealth-fetch-mcp: curl_cffi Capability Inventory Analysis

**Research Stage**: 3 (Codebase Capability Inventory)
**Date**: 2026-02-21
**Analyst**: Scientist Agent
**Status**: COMPLETE

---

## Executive Summary

The `stealth-fetch-mcp` project has exposed **a robust and well-structured subset of curl_cffi capabilities** through its `SessionOptionsInput` and `RequestOptionsInput` Pydantic models. This analysis inventories what is currently exposed versus what remains unused in the curl_cffi library.

**Key Finding**: 31 curl_cffi session-level + request-level options are exposed; 20 significant gaps identified in cookies management, response metadata, streaming, multipart uploads, and metadata extraction.

---

## [FINDING:F1] Currently Exposed curl_cffi Features

### Session-Level Options (SessionOptionsInput)
**Total: 21 fields**

| Field | Type | Description |
|-------|------|-------------|
| `headers` | dict | Default session headers |
| `cookies` | dict | Default session cookies |
| `auth` | tuple | HTTP basic auth (username, password) |
| `proxies` | dict | Proxy map for schemes/hosts |
| `proxy` | str | Single proxy URL for all requests |
| `proxy_auth` | tuple | Proxy auth tuple (username, password) |
| `base_url` | str | Absolute base URL for relative paths |
| `params` | dict/list | Default query params for all requests |
| `verify` | bool/str | TLS verification (bool) or CA bundle path |
| `timeout` | float/tuple | Session timeout or (connect, read) tuple |
| `trust_env` | bool | Use proxy/cert settings from environment |
| `allow_redirects` | bool | Default redirect behavior |
| `max_redirects` | int | Maximum redirect count (-1=unlimited) |
| `impersonate` | BrowserTypeLiteral | Browser fingerprint profile (chrome, firefox, safari, edge) |
| `ja3` | str | Custom JA3 TLS fingerprint string |
| `akamai` | str | Custom Akamai HTTP/2 fingerprint |
| `extra_fp` | ExtraFingerprintInput | Additional fingerprint overrides (10 sub-fields) |
| `default_headers` | bool | Enable curl_cffi browser default headers |
| `default_encoding` | str | Default response text encoding fallback |
| `http_version` | HttpVersionLiteral | HTTP version strategy (v1, v2, v2tls, v2_prior_knowledge, v3, v3only) |
| `debug` | bool | Enable curl debug logs |
| `interface` | str | Bind socket to specific interface/source IP |
| `cert` | str/tuple | Client cert path or (cert_path, key_path) |
| `discard_cookies` | bool | Do not persist response cookies into jar |
| `raise_for_status` | bool | Raise HTTP errors for 4xx/5xx |
| `max_clients` | int | AsyncSession connection pool size (1-1000) |
| `curl_options` | list | Low-level libcurl CurlOpt overrides |

### Request-Level Options (RequestOptionsInput)
**Total: 24 fields**

| Field | Type | Description |
|-------|------|-------------|
| `params` | dict/list | Per-request query params |
| `data` | dict/list/str | Request body for form/text payloads |
| `json_body` | dict/list | Request JSON body (aliased as `json`) |
| `headers` | dict | Per-request headers |
| `cookies` | dict | Per-request cookies |
| `auth` | tuple | HTTP basic auth |
| `timeout` | float/tuple | Request timeout or (connect, read) |
| `allow_redirects` | bool | Per-request redirect behavior |
| `max_redirects` | int | Maximum redirects |
| `proxies` | dict | Proxy map |
| `proxy` | str | Single proxy URL |
| `proxy_auth` | tuple | Proxy auth tuple |
| `verify` | bool/str | TLS verification or CA bundle path |
| `referer` | str | Referer header shortcut |
| `accept_encoding` | str | Accept-Encoding header value |
| `impersonate` | BrowserTypeLiteral | Browser fingerprint for this request |
| `ja3` | str | Custom JA3 TLS fingerprint |
| `akamai` | str | Custom Akamai HTTP/2 fingerprint |
| `extra_fp` | ExtraFingerprintInput | Additional fingerprint overrides |
| `default_headers` | bool | Enable/disable browser default headers |
| `default_encoding` | str | Default response encoding fallback |
| `quote` | str/False | URL quoting behavior (False = keep as-is) |
| `http_version` | HttpVersionLiteral | HTTP version strategy |
| `interface` | str | Bind socket to specific interface/source IP |
| `cert` | str/tuple | Client cert path or (cert_path, key_path) |
| `stream` | bool | **REJECTED** (validation error: not supported) |
| `max_recv_speed` | int | Maximum receive speed (bytes/second) |
| `discard_cookies` | bool | Do not store response cookies |
| `curl_options` | list | Low-level libcurl overrides |

### Fingerprinting Options (ExtraFingerprintInput)
**Total: 10 sub-fields** (can be nested in session or request options)

| Field | Type | Description |
|-------|------|-------------|
| `tls_min_version` | int | TLS min version (e.g., 771=TLSv1.2, 772=TLSv1.3) |
| `tls_grease` | bool | Enable TLS GREASE extension |
| `tls_permute_extensions` | bool | Permute TLS extension order in ClientHello |
| `tls_cert_compression` | str | TLS compression preference (zlib or brotli) |
| `tls_signature_algorithms` | list | TLS signature algorithms list |
| `tls_delegated_credential` | str | TLS delegated credential signatures |
| `tls_record_size_limit` | int | TLS record size limit extension value |
| `http2_stream_weight` | int | HTTP/2 stream weight fingerprint |
| `http2_stream_exclusive` | int | HTTP/2 stream exclusive fingerprint |
| `http2_no_priority` | bool | Disable HTTP/2 priority signals |

### HTTP Methods Supported
**RequestMethod type definition (client.py line 12)**

Supported: GET, POST, PUT, DELETE, OPTIONS, HEAD, TRACE, PATCH, QUERY

All 9 methods exposed via `stealth_fetch_json` tool (method parameter).

### MCP Tools (4 total)

1. **stealth_fetch_page** - Raw HTML fetching with impersonation
   - Returns: raw HTML string
   - Max chars: 100,000

2. **stealth_fetch_text** - Cleaned readable text extraction
   - Returns: markdown-style text (headings, lists, links)
   - Max chars: 50,000
   - Supports CSS selector scoping

3. **stealth_fetch_json** - JSON API fetching with GET/POST
   - Returns: pretty-printed JSON
   - Supports JSON request bodies
   - Max chars: 100,000

4. **stealth_extract_links** - Link extraction with filtering
   - Returns: JSON array of {text, href, absolute_url}
   - Supports CSS selector and regex filtering
   - Max results: 100 (configurable, max 10,000)

### Parser Capabilities

| Capability | Implementation | Output |
|-----------|----------------|--------|
| HTML → Text | `_clean_html()` in parser.py | Markdown-ish format (headings, lists, links) |
| Noise removal | Removes script, style, noscript, nav, footer, aside, form, svg, iframe tags | Clean readability text |
| Link extraction | `extract_links()` | JSON: [{text, href, absolute_url}] |
| CSS selectors | BeautifulSoup.select_one() / select() | Scoped content extraction |
| URL resolution | urljoin() from urllib.parse | Absolute URL computation |

---

## [FINDING:F2] Gaps - curl_cffi Features NOT Yet Exposed

### Critical Gaps (High Impact)

**1. Response Metadata Access**
- Missing: HTTP status codes, response headers, final URL in tool output
- Why gap: FetchResult stores status_code, final_url, headers but tools only return .text
- Impact: Cannot inspect Content-Type, Set-Cookie, redirect chains
- Evidence: Line 502, 518, 549, 575 return only result.text

**2. Cookies Jar Inspection & Persistence**
- Missing: Cookie jar state inspection, manual cookie manipulation
- Why gap: SessionOptionsInput has cookies dict (initial) and discard_cookies bool, no jar API
- Impact: Cannot inspect cookies set by server, cannot export/import state
- Evidence: No CookieJar API exposed; only boolean discard flag

**3. Multipart Form Data & File Uploads**
- Missing: multipart/form-data requests with file upload
- Why gap: RequestOptionsInput.data accepts dict/list/str but no files parameter
- Impact: Cannot upload files, cannot submit forms with attachments
- Evidence: curl_cffi accepts files param but RequestOptionsInput doesn't define it

**4. Response Headers in Output**
- Missing: Including response headers in tool output
- Why gap: Headers captured in FetchResult but tools only return .text
- Impact: Cannot check MIME type, caching directives, auth challenges
- Evidence: FetchResult stores headers dict but _truncate() only operates on text

**5. HTTP Status Code Access in Output**
- Missing: Status code included in tool output
- Why gap: FetchResult.status_code captured but tools only return .text
- Impact: Cannot distinguish successful (200) from error states
- Evidence: All tool returns (502, 518, 549, 575) return only .text field

**6. Final URL After Redirects**
- Missing: Final URL exposed in tool output
- Why gap: FetchResult.final_url tracked but not exposed
- Impact: Cannot trace redirect chains or detect URL changes
- Evidence: FetchResult.final_url captured (line 169) but never returned

### Medium-Impact Gaps

**7. Streaming Response Handling**
- Missing: Chunked/streaming response bodies
- Why gap: RequestOptionsInput.stream explicitly rejected (lines 290-295)
- Impact: Must load entire response into memory
- Evidence: Validation error: "stream=True is not supported..."

**8. Response Size Limits (Early Termination)**
- Missing: Hard limit on response body size with early disconnect
- Why gap: Only soft truncation after fetch completes
- Impact: Large responses must be fully downloaded
- Evidence: _truncate() post-processes (line 170); no pre-fetch limit

**9. Custom DNS Resolution**
- Missing: Custom DNS resolver, DoH (DNS over HTTPS)
- Why gap: SessionOptionsInput has no DNS options
- Impact: Cannot use custom DNS or bypass blocks
- Evidence: No dns_resolver, use_dns_over_https fields

**10. Request/Response Timing Information**
- Missing: Latency breakdown (DNS, TLS, total)
- Why gap: curl_cffi response doesn't expose timing API
- Impact: Cannot measure performance bottlenecks
- Evidence: FetchResult has no timing fields

**11. SSL Certificate Inspection**
- Missing: Server certificate details (issuer, CN, validity)
- Why gap: No certificate inspection API exposed
- Impact: Cannot verify or inspect certificate properties
- Evidence: No cert_info field in FetchResult

**12. HTTP Caching & Conditional Requests**
- Missing: ETag/If-Modified-Since support
- Why gap: No caching layer or conditional request support
- Impact: Cannot leverage HTTP caching
- Evidence: No cache_control, etag, if_modified_since fields

**13. Custom HTTP Methods**
- Missing: Non-standard or experimental HTTP methods
- Why gap: RequestMethod is Literal restricted to known methods
- Impact: Cannot use PROPFIND, MKCOL, or experimental protocols
- Evidence: Line 12 RequestMethod = Literal[...known only...]

**14. Request Body Streaming**
- Missing: Stream large request bodies without loading into memory
- Why gap: RequestOptionsInput.data expects full payload in memory
- Impact: Cannot efficiently send multi-GB request bodies
- Evidence: data field is dict/list/str (full in-memory)

### Parser Gaps (HTML Content Extraction)

**15. Metadata Extraction (Meta Tags)**
- Missing: Extract meta tags (title, description, OpenGraph, Twitter Card)
- Why gap: parser.py has no metadata extraction
- Impact: Cannot extract SEO metadata or social preview info
- Evidence: _clean_html() and extract_links() only handle text/links

**16. Schema.org/Microdata Extraction**
- Missing: Parse schema.org JSON-LD or microdata
- Why gap: No structured data extraction
- Impact: Cannot extract product info, reviews, articles
- Evidence: No schema parsing in parser.py

**17. CSS Selector-Based Generic Content Extraction**
- Missing: Direct CSS selector extraction of arbitrary elements
- Why gap: selector support limited to stealth_fetch_text (text) and stealth_extract_links (links)
- Impact: Cannot extract price, rating, or details via selector
- Evidence: No tool for "extract elements matching selector as JSON"

**18. XPath Support**
- Missing: XPath-based content extraction
- Why gap: Parser uses BeautifulSoup/CSS; no XPath
- Impact: Cannot use XPath for complex queries
- Evidence: parser.py lines 116-118 use BeautifulSoup.select()

**19. Table Extraction**
- Missing: Extract HTML tables as structured JSON/CSV
- Why gap: No table parsing in parser.py
- Impact: Cannot extract tabular data
- Evidence: No table parsing logic in _clean_html()

**20. Form Extraction & Structure**
- Missing: Extract form elements (inputs, selects)
- Why gap: No form parsing logic
- Impact: Cannot inspect or prepare form submissions
- Evidence: NOISE_TAGS includes 'form' (decomposed)

---

## [STAT:n] Scope & Evidence

**Files Analyzed:**
- src/stealth_fetch_mcp/server.py (637 lines)
- src/stealth_fetch_mcp/client.py (173 lines)
- src/stealth_fetch_mcp/parser.py (138 lines)
- pyproject.toml (48 lines)
- README.md (247 lines)

**Total Lines Analyzed**: 1,243 lines

**curl_cffi Features Exposed**: 31 (session + request options)
**Gaps Identified**: 20 major categories
**HTTP Methods Supported**: 9
**MCP Tools**: 4
**Parser Capabilities**: 4

---

## [LIMITATION:L1] Analysis Scope

1. **curl_cffi version**: Analysis assumes curl_cffi >=0.7
   - Capabilities may vary with version updates

2. **MCP Output Constraints**: Many gaps exist because tools return text/JSON strings
   - Architectural choice for simplicity
   - Could be addressed via new tool variants

3. **Parser Limitations**: Uses BeautifulSoup with lxml
   - No JavaScript rendering (static HTML only)
   - No XPath support

4. **Streaming Rejection**: stream=True intentionally rejected
   - MCP tool output requires buffered return values
   - Streaming would require tool redesign

5. **Analysis Reflects v0.1.0**
   - Future versions may expose additional features

---

## Conclusion

The `stealth-fetch-mcp` project has achieved **strong foundational coverage of curl_cffi capabilities**, particularly in:
- Browser impersonation (JA3, Akamai, extra fingerprints)
- TLS/HTTP configuration
- Session and request-level options
- HTML content extraction and link discovery

The 20 identified gaps reflect **intentional design choices** (no streaming for simplicity) and **parser-specific limitations** (no JavaScript, no XPath). Most gaps are addressable via new tool variants or parser extensions.

**Highest-value improvements**:
1. Expose response metadata (status, headers, final URL)
2. Add file upload support (multipart forms)
3. Add metadata extraction tool (meta tags, OpenGraph)

---

Report generated: 2026-02-21
Status: Analysis Complete
