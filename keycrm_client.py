"""KeyCRM transport layer.

Two independent channels to the same account:

* internal API  - https://<domain>.api.keycrm.app
  Auth: email + password -> access_token (+ refresh_token), 24h lifetime.
  Full surface that the CRM web UI uses (572 endpoints).

* official API  - https://openapi.keycrm.app/v1
  Auth: Bearer <api_token> (taken from the account settings, auto-discovered
  through the internal API when KEYCRM_API_TOKEN is not set).
  Documented, stable, 20 requests/minute limit.
"""

from __future__ import annotations

import json
import os
import threading
import time
from pathlib import Path
from typing import Any

import httpx

try:  # optional, handy for local .env files
    from dotenv import load_dotenv

    load_dotenv(Path(__file__).with_name(".env"))
except Exception:  # pragma: no cover
    pass


UA = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36"
)


class KeyCrmError(RuntimeError):
    def __init__(self, status: int, message: str, body: Any = None, api: str = "internal"):
        self.status = status
        self.message = message
        self.body = body
        self.api = api
        super().__init__(f"[{api} {status}] {message}")

    def as_dict(self) -> dict:
        return {"status": self.status, "api": self.api, "message": self.message, "body": self.body}


def _extract_message(body: Any) -> str:
    if isinstance(body, dict):
        msg = body.get("message")
        errs = body.get("errors")
        if errs and isinstance(errs, dict):
            parts = []
            for field, problems in errs.items():
                if isinstance(problems, list):
                    parts.append(f"{field}: {'; '.join(str(p) for p in problems)}")
                else:
                    parts.append(f"{field}: {problems}")
            return (msg + " | " if msg else "") + ", ".join(parts)
        if msg:
            return str(msg)
    if isinstance(body, str) and body.strip():
        return body.strip()[:500]
    return "request failed"


class KeyCrm:
    """Minimal, dependency-light KeyCRM client used by the MCP server."""

    def __init__(
        self,
        domain: str | None = None,
        email: str | None = None,
        password: str | None = None,
        api_token: str | None = None,
        timeout: float = 60.0,
    ):
        env = os.environ.get
        self.domain = (domain or env("KEYCRM_DOMAIN") or "").strip()
        if not self.domain:
            raise RuntimeError("KEYCRM_DOMAIN is not set: put your account subdomain into .env")
        self.email = (email or env("KEYCRM_EMAIL") or "").strip()
        self.password = (password or env("KEYCRM_PASSWORD") or "").strip()
        self._api_token = (api_token or env("KEYCRM_API_TOKEN") or "").strip() or None
        self.timeout = timeout

        self.internal_base = f"https://{self.domain}.api.keycrm.app"
        self.official_base = env("KEYCRM_OPENAPI_BASE") or "https://openapi.keycrm.app/v1"
        self.app_origin = env("KEYCRM_APP_ORIGIN") or f"https://{self.domain}.keycrm.app"

        self._lock = threading.Lock()
        self._access_token: str | None = None
        self._refresh_token: str | None = None
        self._expires_at: float = 0.0

        self._internal = httpx.Client(base_url=self.internal_base, timeout=timeout, headers={
            "User-Agent": UA,
            "Accept": "application/json, text/plain, */*",
            "UserLocale": "ru",
            "Origin": self.app_origin,
            "Referer": self.app_origin + "/",
        })
        self._official = httpx.Client(base_url=self.official_base, timeout=timeout, headers={
            "User-Agent": UA,
            "Accept": "application/json",
        })

    # ------------------------------------------------------------------ auth
    @property
    def has_password_auth(self) -> bool:
        return bool(self.email and self.password)

    def login(self, force: bool = False) -> str:
        """Return a valid internal access token, logging in when needed."""
        with self._lock:
            if not force and self._access_token and time.time() < self._expires_at:
                return self._access_token
            if not self.has_password_auth:
                raise KeyCrmError(0, "KEYCRM_EMAIL / KEYCRM_PASSWORD are not configured", None, "auth")
            r = self._internal.post("/auth/login", json={"username": self.email, "password": self.password})
            if r.status_code >= 400:
                raise KeyCrmError(r.status_code, _extract_message(_safe_json(r)), _safe_json(r), "auth")
            data = r.json()
            self._access_token = data["access_token"]
            self._refresh_token = data.get("refresh_token")
            self._expires_at = time.time() + float(data.get("expires_in", 3600)) - 120
            return self._access_token

    def _refresh(self) -> bool:
        if not self._refresh_token:
            return False
        try:
            r = self._internal.post("/auth/refresh", json={"token": self._refresh_token})
            if r.status_code >= 400:
                return False
            data = r.json()
            if not data.get("access_token"):
                return False
            self._access_token = data["access_token"]
            self._refresh_token = data.get("refresh_token", self._refresh_token)
            self._expires_at = time.time() + float(data.get("expires_in", 3600)) - 120
            return True
        except Exception:
            return False

    @property
    def api_token(self) -> str:
        """Official OpenAPI token. Auto-discovered from the account settings."""
        if self._api_token:
            return self._api_token
        data = self.internal("GET", "/config/api-client")
        token = (data or {}).get("api_token")
        if not token:
            raise KeyCrmError(0, "api_token not found in /config/api-client", data, "auth")
        self._api_token = token
        return token

    # -------------------------------------------------------------- requests
    def internal(self, method: str, path: str, params: dict | None = None,
                 body: Any = None) -> Any:
        return self._request("internal", method, path, params, body)

    def official(self, method: str, path: str, params: dict | None = None,
                 body: Any = None) -> Any:
        return self._request("official", method, path, params, body)

    def _request(self, api: str, method: str, path: str, params: dict | None,
                 body: Any, _retry: int = 0) -> Any:
        method = method.upper()
        if api == "internal":
            self.login()
            client = self._internal
            headers = {"Authorization": f"Bearer {self._access_token}", "Content-Type": "application/json"}
        else:
            client = self._official
            headers = {"Authorization": f"Bearer {self.api_token}", "Content-Type": "application/json"}
        if not path.startswith("/"):
            path = "/" + path

        try:
            r = client.request(method, path, params=params, json=body, headers=headers)
        except httpx.HTTPError as exc:
            raise KeyCrmError(0, f"network error: {exc}", None, api) from exc

        if r.status_code == 401 and _retry < 2:
            if api == "internal":
                with self._lock:
                    if not self._refresh():
                        self._access_token = None
                        self.login(force=True)
            else:
                self._api_token = None  # re-discover
            return self._request(api, method, path, params, body, _retry + 1)

        if r.status_code == 429 and _retry < 3:
            retry_after = float(r.headers.get("Retry-After") or 2)
            time.sleep(min(retry_after, 10))
            return self._request(api, method, path, params, body, _retry + 1)

        data = _safe_json(r)
        if r.status_code >= 400:
            raise KeyCrmError(r.status_code, _extract_message(data), data, api)
        return data

    def internal_bytes(self, method: str, path: str, params: dict | None = None,
                       body: Any = None) -> httpx.Response:
        """Raw response, for endpoints that return PDF/HTML/files instead of JSON."""
        self.login()
        if not path.startswith("/"):
            path = "/" + path
        r = self._internal.request(method, path, params=params, json=body,
                                   headers={"Authorization": f"Bearer {self._access_token}"})
        if r.status_code >= 400:
            raise KeyCrmError(r.status_code, _extract_message(_safe_json(r)), None, "internal")
        return r

    def internal_multipart(self, path: str, files: dict | None = None,
                           form: dict | None = None) -> Any:
        """POST multipart/form-data (file upload endpoints)."""
        self.login()
        if not path.startswith("/"):
            path = "/" + path
        r = self._internal.post(path, files=files, data=form or {},
                                headers={"Authorization": f"Bearer {self._access_token}"})
        data = _safe_json(r)
        if r.status_code >= 400:
            raise KeyCrmError(r.status_code, _extract_message(data), data, "internal")
        return data

    # ------------------------------------------------------------- paginated
    def official_pages(self, path: str, params: dict | None = None,
                       max_items: int = 200, page_size: int = 50) -> list[dict]:
        """Collect items from a paginated OpenAPI list endpoint."""
        items: list[dict] = []
        page = 1
        base = dict(params or {})
        while len(items) < max_items:
            query = dict(base)
            query["limit"] = min(page_size, max_items - len(items))
            query["page"] = page
            data = self.official("GET", path, params=query)
            chunk = (data or {}).get("data") or []
            items.extend(chunk)
            meta = (data or {}).get("meta") or {}
            last = data.get("last_page") or meta.get("last_page")
            if not chunk or (last and page >= int(last)):
                break
            page += 1
        return items[:max_items]

    def internal_pages(self, path: str, params: dict | None = None,
                       max_items: int = 200, page_size: int = 50) -> list[dict]:
        items: list[dict] = []
        page = 1
        base = dict(params or {})
        base.pop("limit", None)
        while len(items) < max_items:
            query = dict(base)
            query["per_page"] = page_size
            query["page"] = page
            data = self.internal("GET", path, params=query)
            if isinstance(data, list):
                items.extend(data)
                break
            chunk = (data or {}).get("data") or []
            items.extend(chunk)
            meta = (data or {}).get("meta") or {}
            total = meta.get("total")
            last = data.get("last_page") or meta.get("last_page")
            if not chunk:
                break
            if last and page >= int(last):
                break
            if total and len(items) >= int(total):
                break
            page += 1
        return items[:max_items]


def _safe_json(r: httpx.Response) -> Any:
    if r.status_code == 204 or not r.content:
        return {}
    try:
        return r.json()
    except Exception:
        return r.text[:2000]


_default: KeyCrm | None = None


def client() -> KeyCrm:
    """Process-wide singleton, so the token cache survives between tool calls."""
    global _default
    if _default is None:
        _default = KeyCrm()
    return _default


def compact(obj: Any, fields: list[str]) -> Any:
    """Keep only requested fields; supports dotted paths and keeps None keys out."""
    if isinstance(obj, list):
        return [compact(x, fields) for x in obj]
    if not isinstance(obj, dict):
        return obj
    out: dict[str, Any] = {}
    for path in fields:
        cur: Any = obj
        ok = True
        for part in path.split("."):
            if isinstance(cur, dict) and part in cur:
                cur = cur[part]
            else:
                ok = False
                break
        if ok and cur is not None:
            out[path.split(".")[-1] if "." not in path else path] = cur
    return out


def dumps(data: Any) -> str:
    return json.dumps(data, ensure_ascii=False, indent=1, default=str)
