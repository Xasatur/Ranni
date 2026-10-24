"""Shared authenticated Home Assistant REST transport; never follow redirects."""
import json
from urllib.parse import urlsplit
from urllib.request import HTTPRedirectHandler, Request, build_opener


def valid_url(value):
    try:
        parsed = urlsplit(value)
        return (parsed.scheme in ("http", "https") and bool(parsed.hostname)
                and parsed.port != 0 and parsed.username is None
                and parsed.password is None and not parsed.query
                and not parsed.fragment and parsed.path in ("", "/")
                and not any(char.isspace() for char in value))
    except ValueError:
        return False


class _NoRedirect(HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        return None


def request_json(base_url, token, path, payload=None):
    headers = {"Authorization": "Bearer " + token, "Accept": "application/json"}
    data = None
    if payload is not None:
        data = json.dumps(payload).encode("utf-8")
        headers["Content-Type"] = "application/json"
    request = Request(base_url.rstrip("/") + path, headers=headers, data=data)
    with build_opener(_NoRedirect()).open(request, timeout=6) as response:
        return json.load(response)
