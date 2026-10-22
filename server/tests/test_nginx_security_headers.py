"""Every page the web container serves carries the security headers.

nginx inherits `add_header` from the enclosing block only when a block sets none of
its own. The headers were declared once at server level, and the locations for `/`,
`/dosha-test`, the auth pages and every app route each added a Cache-Control — so
all of them shipped without a Content-Security-Policy or HSTS, while the config read
as though they had both. They now live in `client/security-headers.conf`, included at
server level and in each location that adds a header of its own.
"""

import re
from pathlib import Path

_CLIENT = Path(__file__).resolve().parents[2] / "client"
_INCLUDE = "include /etc/nginx/snippets/security-headers.conf;"
_HEADERS = (
    "X-Frame-Options",
    "X-Content-Type-Options",
    "Strict-Transport-Security",
    "Content-Security-Policy",
    "Referrer-Policy",
    "Permissions-Policy",
)


def _blocks(text, keyword):
    """(header, body) for each `keyword ... { ... }` block, braces matched."""
    out = []
    for m in re.finditer(rf"^\s*{keyword}\b[^{{]*\{{", text, re.M):
        depth, i = 1, m.end()
        while depth:
            depth += {"{": 1, "}": -1}.get(text[i], 0)
            i += 1
        out.append((m.group(0).strip(), text[m.end():i - 1]))
    return out


def _app_server():
    conf = (_CLIENT / "nginx.conf").read_text()
    servers = [body for _, body in _blocks(conf, "server") if "root /usr/share/nginx/html" in body]
    assert len(servers) == 1, "expected one server block serving the app"
    return servers[0]


def test_every_location_that_adds_a_header_includes_the_security_headers():
    locations = _blocks(_app_server(), "location")
    assert locations, "no location blocks parsed"
    missing = [head for head, body in locations if "add_header" in body and _INCLUDE not in body]
    assert not missing, f"these locations drop the security headers: {missing}"


def test_the_server_block_includes_them_for_locations_that_add_none():
    top_level = _app_server()
    for _, body in _blocks(top_level, "location"):
        top_level = top_level.replace(body, "")
    assert _INCLUDE in top_level


def test_the_headers_are_set_only_in_the_snippet():
    # A copy in nginx.conf would be the one someone edits, and it would be
    # silently ignored wherever the snippet is included.
    conf = (_CLIENT / "nginx.conf").read_text()
    for header in _HEADERS:
        assert f"add_header {header}" not in conf, header


def test_the_snippet_sets_every_header_and_the_image_ships_it():
    snippet = (_CLIENT / "security-headers.conf").read_text()
    for header in _HEADERS:
        assert re.search(rf"^add_header {header} .* always;$", snippet, re.M), header
    dockerfile = (_CLIENT / "Dockerfile").read_text()
    assert "COPY security-headers.conf /etc/nginx/snippets/security-headers.conf" in dockerfile


def test_the_csp_allows_what_the_app_loads():
    csp = re.search(r'Content-Security-Policy "([^"]+)"', (_CLIENT / "security-headers.conf").read_text())[1]
    directives = {d.split()[0]: d.split()[1:] for d in csp.split(";") if d.strip()}
    assert "https://*.posthog.com" in directives["script-src"], "PostHog's scripts"
    assert "blob:" in directives["img-src"], "avatar and tongue-photo previews"
    assert "blob:" in directives["worker-src"], "Sentry Replay's worker"
    assert "data:" in directives["font-src"], "font subsets Vite inlines into the CSS"
    assert directives["object-src"] == ["'none'"]
