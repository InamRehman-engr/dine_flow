"""Resolve the public base URL dynamically so QR codes survive ngrok URL changes.

Priority:
1. Incoming request Host / X-Forwarded-* (when client hits via ngrok or real domain)
2. Live ngrok local API (http://host.docker.internal:4040/api/tunnels)
3. PUBLIC_BASE_URL env (optional static fallback; placeholders ignored)
4. http://localhost:3080
"""
from __future__ import annotations

import json
import urllib.error
import urllib.request
from time import time

from flask import current_app, has_app_context, has_request_context, request


_ngrok_cache = {"url": None, "at": 0.0}
_NGROK_TTL = 15.0  # seconds


def _normalize(url: str | None) -> str | None:
    if not url:
        return None
    u = url.strip().rstrip("/")
    if not u:
        return None
    if not u.startswith("http://") and not u.startswith("https://"):
        u = "https://" + u
    return u


def _is_local_host(host: str) -> bool:
    h = (host or "").split(":")[0].lower()
    return h in ("localhost", "127.0.0.1", "0.0.0.0", "::1") or h.endswith(".local")


def _from_request(*, allow_local: bool = False) -> str | None:
    if not has_request_context():
        return None
    proto = (
        request.headers.get("X-Forwarded-Proto")
        or request.scheme
        or "https"
    ).split(",")[0].strip()
    host = (
        request.headers.get("X-Forwarded-Host")
        or request.headers.get("Host")
        or request.host
    )
    if not host:
        return None
    host = host.split(",")[0].strip()
    if _is_local_host(host) and not allow_local:
        return None
    return _normalize(f"{proto}://{host}")


def _fetch_ngrok_tunnels(api_base: str) -> str | None:
    url = api_base.rstrip("/") + "/api/tunnels"
    try:
        req = urllib.request.Request(url, headers={"Accept": "application/json"})
        with urllib.request.urlopen(req, timeout=1.5) as resp:
            data = json.loads(resp.read().decode("utf-8"))
    except (urllib.error.URLError, TimeoutError, json.JSONDecodeError, OSError, ValueError):
        return None
    tunnels = data.get("tunnels") or []
    https = None
    http = None
    for t in tunnels:
        pub = t.get("public_url") or ""
        if pub.startswith("https://"):
            https = pub
            break
        if pub.startswith("http://") and not http:
            http = pub
    return _normalize(https or http)


def _cfg_get(key: str, default=None):
    if has_app_context():
        return current_app.config.get(key, default)
    return default


def _from_ngrok_api() -> str | None:
    now = time()
    if _ngrok_cache["url"] and (now - _ngrok_cache["at"]) < _NGROK_TTL:
        return _ngrok_cache["url"]

    candidates = []
    explicit = _cfg_get("NGROK_API_URL")
    if explicit:
        candidates.append(str(explicit).rstrip("/"))
    candidates.extend(
        [
            "http://host.docker.internal:4040",
            "http://172.17.0.1:4040",
            "http://127.0.0.1:4040",
        ]
    )

    seen = set()
    for base in candidates:
        if base in seen:
            continue
        seen.add(base)
        found = _fetch_ngrok_tunnels(base)
        if found:
            _ngrok_cache["url"] = found
            _ngrok_cache["at"] = now
            return found
    return None


def _from_env() -> str | None:
    raw = (_cfg_get("PUBLIC_BASE_URL") or "") if has_app_context() else ""
    if not raw:
        return None
    lowered = raw.lower()
    if "your-subdomain" in lowered or "example.com" in lowered or "changeme" in lowered:
        return None
    return _normalize(raw)


def resolve_public_base_url(*, prefer_request: bool = True) -> str:
    if prefer_request:
        req_url = _from_request(allow_local=False)
        if req_url:
            return req_url

    ngrok = _from_ngrok_api()
    if ngrok:
        return ngrok

    env = _from_env()
    if env:
        return env

    local_req = _from_request(allow_local=True)
    if local_req:
        # nginx $host strips non-default ports; ensure :3080 for local compose
        if local_req in ("http://localhost", "https://localhost", "http://127.0.0.1", "https://127.0.0.1"):
            return local_req.replace("://localhost", "://localhost:3080").replace(
                "://127.0.0.1", "://127.0.0.1:3080"
            )
        return local_req

    return "http://localhost:3080"


def public_url_status() -> dict:
    req_url = _from_request(allow_local=False)
    ngrok = _from_ngrok_api()
    env = _from_env()
    resolved = resolve_public_base_url()
    source = "localhost"
    if req_url and resolved == req_url:
        source = "request"
    elif ngrok and resolved == ngrok:
        source = "ngrok"
    elif env and resolved == env:
        source = "env"
    elif _from_request(allow_local=True) and resolved == _from_request(allow_local=True):
        source = "local"
    return {
        "public_base_url": resolved,
        "source": source,
        "detected": {
            "request": req_url,
            "ngrok": ngrok,
            "env": env,
        },
        "hint": (
            "Start ngrok with: ngrok http 3080 — QR export will pick up the tunnel automatically."
            if source in ("localhost", "local", "env") and not ngrok
            else None
        ),
    }
