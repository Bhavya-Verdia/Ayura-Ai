"""nginx answers a path App.jsx does not know with a 404.

It used to serve the app shell with a 200 for every path, so `/no-such-page` was a
page as far as a crawler could tell. Now the app routes are named in one regex
location and everything else falls through to `try_files ... =404`, whose
error_page still boots the app on the NotFound screen. The cost is a second list
of routes, and a route added to App.jsx but not here would 404 on a hard refresh,
so this test holds the two together.
"""

import re
from pathlib import Path

_CLIENT = Path(__file__).resolve().parents[2] / "client"

# Served by their own exact-match or regex locations rather than the app regex.
_OWN_LOCATION = {"/", "/login", "/register", "/forgot-password", "/reset-password",
                 "/dosha-test", "/privacy", "/terms"}


def _app_routes():
    jsx = (_CLIENT / "src" / "App.jsx").read_text()
    paths = re.findall(r'<Route path="([^"]+)"', jsx)
    return {p.removesuffix("/*") for p in paths if p != "*"}


def _nginx_app_regex():
    conf = (_CLIENT / "nginx.conf").read_text()
    m = re.search(r"location ~ (\^/\((?:dashboard)[^ ]*) \{", conf)
    assert m, "the app-route regex location is missing from nginx.conf"
    return re.compile(m.group(1))


def test_every_app_route_is_served_by_nginx():
    regex = _nginx_app_regex()
    missing = sorted(p for p in _app_routes() - _OWN_LOCATION if not regex.match(p))
    assert not missing, f"App.jsx routes that would 404 on a hard refresh: {missing}"


def test_sub_routes_of_the_dashboard_are_served():
    assert _nginx_app_regex().match("/dashboard/diet")


def test_an_unknown_path_is_not_an_app_route():
    regex = _nginx_app_regex()
    for path in ("/no-such-page", "/dashboards", "/chatroom", "/wp-login.php"):
        assert not regex.match(path), path


def test_the_fallback_returns_a_404_status():
    conf = (_CLIENT / "nginx.conf").read_text()
    fallback = re.search(r"location / \{(.*?)\n    \}", conf, re.S).group(1)
    assert "try_files $uri $uri/ =404;" in fallback
    assert "error_page 404 /app.html;" in fallback, "an `=` here would turn the 404 back into a 200"
