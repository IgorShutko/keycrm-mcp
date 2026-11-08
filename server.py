"""KeyCRM MCP server.

Exposes the CRM (orders, pipeline cards / leads, clients, products, tasks,
conversations, users, settings, reports) plus a universal raw-request tool that
reaches any of the 572 internal endpoints.

Transport: stdio (Claude Desktop, Claude Code, any MCP client).
"""

from __future__ import annotations

import json
import logging
from datetime import datetime, timedelta, timezone
from typing import Any

from mcp.server.fastmcp import FastMCP

# stderr must stay quiet: some MCP clients print it as warnings
logging.getLogger("httpx").setLevel(logging.WARNING)
logging.getLogger("httpcore").setLevel(logging.WARNING)

from endpoints_catalog import catalog
from keycrm_client import KeyCrmError, client, compact, dumps

mcp = FastMCP(
    "keycrm",
    instructions=(
        "KeyCRM (your-account). Two channels: 'internal' (full web-UI API, "
        "ids are CRM ids) and 'official' (openapi.keycrm.app/v1, documented, "
        "20 req/min). Use the typed tools for daily work and crm_api only for "
        "endpoints that have no dedicated tool (discover them with crm_endpoints). "
        "All dates from the CRM are UTC. Money values are in the account currency "
        "(UAH) and are returned in minor units where the API does so; check "
        "grand_total vs products_total when comparing."
    ),
)

ORDERS_COMPACT = ["id", "status_id", "grand_total", "payment_status", "client_id",
                  "manager_id", "source_id", "created_at", "ordered_at", "products_total"]
CARDS_COMPACT = ["id", "title", "status_id", "pipeline_id", "manager_id", "currency_code",
                 "products_total", "communicate_at", "created_at", "is_finished",
                 "contact.full_name", "contact.phone"]
CLIENTS_COMPACT = ["id", "full_name", "phone", "email", "orders_count", "orders_sum",
                   "manager_id", "created_at"]
PRODUCTS_COMPACT = ["id", "name", "sku", "quantity", "in_reserve", "min_price",
                    "max_price", "category_id", "is_archived", "has_offers"]
TASKS_COMPACT = ["id", "name", "description", "status", "priority", "scheduled_at",
                 "assigned_to_id", "type", "created_at"]
CONVERSATIONS_COMPACT = ["id", "client_id", "contact_id", "channel_id", "last_message_at",
                         "unread_count", "status", "assignee_id"]
USERS_COMPACT = ["id", "full_name", "email", "role_id", "status", "is_owner"]


# --------------------------------------------------------------------- helpers
def _ok(data: Any) -> str:
    return dumps({"ok": True, "data": data})


def _err(exc: Exception) -> str:
    if isinstance(exc, KeyCrmError):
        return dumps({"ok": False, "error": exc.as_dict()})
    return dumps({"ok": False, "error": {"message": f"{type(exc).__name__}: {exc}"}})


def _filters(filters: dict[str, Any] | None) -> dict[str, str]:
    """{'status_id': [1, 2]} -> {'filter[status_id]': '1,2'} (KeyCRM style)."""
    out: dict[str, str] = {}
    for key, value in (filters or {}).items():
        if value is None:
            continue
        if isinstance(value, (list, tuple)):
            out[f"filter[{key}]"] = ",".join(str(v) for v in value)
        elif isinstance(value, bool):
            out[f"filter[{key}]"] = "1" if value else "0"
        else:
            out[f"filter[{key}]"] = str(value)
    return out


def _pages(data: Any) -> tuple[list[dict], dict]:
    if isinstance(data, list):
        return data, {}
    if not isinstance(data, dict):
        return [], {}
    items = data.get("data")
    if isinstance(items, dict):
        items = [items]
    meta = {
        "current_page": data.get("current_page"),
        "last_page": data.get("last_page"),
        "per_page": data.get("per_page"),
        "total": data.get("total"),
    }
    return items or [], {k: v for k, v in meta.items() if v is not None}


def _day_range(date_from: str | None, date_to: str | None) -> tuple[str, str]:
    today = datetime.now(timezone.utc).date()
    start = date_from or (today - timedelta(days=30)).isoformat()
    end = date_to or today.isoformat()
    return start, end


def _merge(*parts: dict | None) -> dict:
    out: dict = {}
    for part in parts:
        if part:
            out.update(part)
    return out


def _names(rows: list[dict], key: str = "id", value: str = "name") -> dict[str, str]:
    return {str(r.get(key)): str(r.get(value)) for r in rows if r.get(key) is not None}


# ----------------------------------------------------------------------- meta
@mcp.tool()
def crm_status() -> str:
    """Check KeyCRM connectivity and show account summary.

    Returns the authenticated profile, which channels work (internal/official),
    the API token owner and live counters for orders, pipeline cards, clients,
    products and users. Start every session with this call.
    """
    try:
        c = client()
        profile = c.internal("GET", "/auth/profile")
        result: dict[str, Any] = {
            "domain": c.domain,
            "internal_api": f"{c.internal_base}",
            "official_api": c.official_base,
            "profile": compact(profile, ["id", "full_name", "email", "role_id", "is_owner", "status"]),
            "channels": {"internal": "ok"},
        }
        try:
            me = c.official("GET", "/users", params={"limit": 1})
            result["channels"]["official"] = "ok"
            result["official_sample_users"] = len((me or {}).get("data") or [])
        except Exception as exc:  # pragma: no cover
            result["channels"]["official"] = f"error: {exc}"
        try:
            api_client = c.internal("GET", "/config/api-client")
            result["api_client"] = compact(api_client, ["id", "name", "request_limit", "is_active"])
        except Exception:
            pass
        counters: dict[str, Any] = {}
        # orders are listed by the official API only (internal /orders is empty here)
        try:
            page = c.official("GET", "/order", params={"limit": 1})
            last = int(page.get("last_page") or 1)
            per = int(page.get("per_page") or 1)
            counters["orders"] = (last - 1) * per + len(page.get("data") or [])
        except Exception as exc:
            counters["orders"] = f"error: {exc}"
        for label, path in [("cards", "/leads"), ("clients", "/clients"),
                            ("products", "/catalog/products")]:
            try:
                items, meta = _pages(c.internal("GET", path, params={"limit": 1}))
                counters[label] = meta.get("total", len(items))
            except Exception as exc:
                counters[label] = f"error: {exc}"
        try:
            us, _ = _pages(c.internal("GET", "/users"))
            counters["users"] = len(us)
        except Exception:
            pass
        result["counters"] = counters
        return _ok(result)
    except Exception as exc:
        return _err(exc)


@mcp.tool()
def crm_capabilities() -> str:
    """What this CRM account can do right now.

    Returns active modules (orders, leads, conversations, ...), plan-level flags,
    the API request limit and the list of known broken or quirky endpoints, so
    the model does not waste calls on dead routes.
    """
    try:
        c = client()
        settings = c.internal("GET", "/config/settings/") or {}
        modules: dict[str, Any] = {}
        for key in ("orders", "leads", "conversations", "products", "clients",
                    "suppliers", "manufacturing", "shipment", "ai", "companies"):
            section = settings.get(key)
            if isinstance(section, dict):
                modules[key] = {k: v for k, v in section.items()
                                if isinstance(v, (bool, int, float)) and k.endswith("active")
                                or k in ("is_active", "enabled")}
                if not modules[key]:
                    modules[key] = {"present": True}
        general = settings.get("general") if isinstance(settings.get("general"), dict) else {}
        scalars = {k: v for k, v in general.items() if isinstance(v, (bool, int, float, str))}
        api_client: dict = {}
        try:
            api_client = c.internal("GET", "/config/api-client") or {}
        except Exception:
            pass
        return _ok({
            "account": c.domain,
            "root_is_active": settings.get("is_active"),
            "modules": modules,
            "plan_general": scalars,
            "api_request_limit": api_client.get("request_limit"),
            "api_client_name": api_client.get("name"),
            "known_issues": [
                "tasks create works with body name/priority/type/description/status/scheduled_at/assigned_to_id/period/settings; complete = PUT /tasks/{id} {\"id\", \"status\":\"done\"}",
                "DANGER: POST /batch/leads/execute/remove?filters[lead_ids]=..&column_ids=.."
                "&pipeline_id=.. deletes ALL cards of the selected status columns when the "
                "id filter is not matched exactly. Card removal is blocked in this MCP server, "
                "delete cards in the KeyCRM UI only",
                "GET /orders on the internal API returns an empty list, orders are read via official /order",
                "GET /finance/payments, /finance/transactions, /config/filter-profiles, "
                "/delivery/addresses/suggest return 500 on this tenant",
                "internal lists ignore 'limit' (use per_page, max 50); orderBy is accepted but mostly "
                "ignored: only /stocks really sorts, /orders, /clients, /users and the field:asc "
                "format return 500. Sort in code, not in the API",
                "product list is briefly cached, a deleted product can appear for a few seconds",
            ],
        })
    except Exception as exc:
        return _err(exc)


_SENSITIVE_KEYS = ("token", "password", "secret", "api_key", "api-key", "auth_key",
                   "auth-key", "authorization", "session", "cookie")


def _sanitize_secrets(obj: Any) -> Any:
    """Recursively mask credentials before writing them to a local backup file."""
    if isinstance(obj, dict):
        out: dict = {}
        for key, value in obj.items():
            low = str(key).lower()
            if any(marker in low for marker in _SENSITIVE_KEYS):
                out[key] = "***"
            else:
                out[key] = _sanitize_secrets(value)
        return out
    if isinstance(obj, list):
        return [_sanitize_secrets(item) for item in obj]
    return obj


@mcp.tool()
def crm_snapshot(folder: str = "") -> str:
    """Save a local JSON snapshot of the account before any risky operation.

    Dumps pipeline cards (with contacts), orders, products, clients, users,
    sources, statuses and settings into keycrm-mcp/backups/<timestamp>.json.
    Use it before experiments with write endpoints: this is how the 26 lost
    cards were recovered on 01.11.2026.
    """
    try:
        import os
        import time as _time
        from pathlib import Path

        c = client()
        base = Path(folder) if folder else Path(__file__).with_name("backups")
        base.mkdir(parents=True, exist_ok=True)
        cards = c.internal_pages("/leads", {"per_page": 50}, max_items=2000, page_size=50)
        orders = c.official_pages("/order", {}, max_items=500)
        pipelines = c.internal("GET", "/leads/pipelines", params={"leads": "false"})
        if isinstance(pipelines, dict):
            pipelines = pipelines.get("data") or []
        pipeline_statuses = {}
        for p in pipelines:
            try:
                pipeline_statuses[str(p["id"])] = c.internal("GET", f"/leads/statuses/{p['id']}")
            except Exception:
                pipeline_statuses[str(p["id"])] = []
        snapshot = {
            "created_at": datetime.now(timezone.utc).isoformat(),
            "domain": c.domain,
            "counts": {"cards": len(cards), "orders": len(orders)},
            "cards": cards,
            "orders": orders,
            "products": c.internal("GET", "/catalog/products", params={"per_page": 50}),
            "clients": c.internal("GET", "/clients", params={"per_page": 50}),
            "users": c.internal("GET", "/users"),
            "sources": c.internal("GET", "/sources", params={"users": 0}),
            "pipelines": pipelines,
            "pipeline_statuses": pipeline_statuses,
            "order_statuses": c.internal("GET", "/orders/statuses", params={"with_disabled": 1}),
            "settings": c.internal("GET", "/config/settings/"),
        }
        snapshot = _sanitize_secrets(snapshot)
        path = base / f"crm_snapshot_{_time.strftime('%Y%m%d_%H%M%S')}.json"
        path.write_text(dumps(snapshot), encoding="utf-8")
        return _ok({"file": str(path), "bytes": path.stat().st_size, "counts": snapshot["counts"]})
    except Exception as exc:
        return _err(exc)


@mcp.tool()
def crm_endpoints(query: str = "", group: str = "", limit: int = 40) -> str:
    """Search the reverse-engineered endpoint catalog (572 internal API routes).

    Use it to find the exact path+method before calling crm_api, e.g.
    query="tags", group="finance", query="export".
    """
    try:
        rows = catalog.search(query=query, group=group, limit=max(1, min(int(limit), 200)))
        return _ok({"count": len(rows), "endpoints": rows})
    except Exception as exc:
        return _err(exc)


@mcp.tool()
def crm_api(method: str = "GET", path: str = "/auth/profile", query: dict | None = None,
            body: dict | None = None, api: str = "internal") -> str:
    """Raw request to any KeyCRM endpoint (escape hatch).

    api='internal' -> https://<domain>.api.keycrm.app (572 routes, ids are CRM ids)
    api='official' -> https://openapi.keycrm.app/v1 (documented, filter[field]=value,
                      20 req/min)
    method: GET/POST/PUT/PATCH/DELETE, path starts with '/', query are plain query
    params (use 'filter[status_id]' style keys for official filters).
    """
    try:
        c = client()
        method = method.upper().strip()
        path = path.strip()
        if not path.startswith("/"):
            path = "/" + path
        # hard safety rails: this route wipes whole kanban columns, see docs/INCIDENT.md
        if "/batch/leads/execute/remove" in path:
            raise ValueError(
                "blocked: /batch/leads/execute/remove deletes whole status columns when "
                "the ids filter does not match exactly (this already caused a mass deletion "
                "in this account). Remove cards in the KeyCRM UI."
            )
        if "/batch/" in path and any("column_ids" in str(key) for key in (query or {})):
            raise ValueError(
                "blocked: batch request with column_ids can affect every card of the "
                "selected columns. Narrow it to explicit ids or do it in the UI."
            )
        if api == "official":
            data = c.official(method, path, params=query or None, body=body)
        else:
            data = c.internal(method, path, params=query or None, body=body)
        return _ok(data)
    except Exception as exc:
        return _err(exc)


# --------------------------------------------------------------------- orders
@mcp.tool()
def orders(action: str = "list", order_id: int | None = None, limit: int = 20,
           page: int = 1, filters: dict | None = None, include: str | None = None,
           data: dict | None = None, product_id: int | None = None,
           tag_id: int | None = None, status_id: int | None = None,
           ids: list[int] | None = None, include_disabled: bool = False) -> str:
    """Work with orders (замовлення).

    actions:
      list     - official /order with filters + pagination (compact rows)
      get      - full order by id (client, products, payments, shipping, tags)
      create   - body needs source_id (+ buyer {full_name, phone/email} + products[])
      update   - PUT /orders/{id} with a partial body
      set_status - move order to status_id
      add_product / update_product / remove_product - product_id for last two
      add_tag / remove_tag - tag_id
      remove   - delete orders by ids[]
      statuses / groups / totals / tags / sources - dictionaries
      (include_disabled=True shows hidden statuses and tags too)
    filters example: {"status_id": [1,2], "created_between": ["2026-10-01","2026-11-01"]}
    """
    try:
        c = client()
        act = action.lower().strip()
        if act == "list":
            params: dict[str, Any] = {"limit": min(max(int(limit), 1), 50), "page": max(int(page), 1)}
            params.update(_filters(filters))
            if include:
                params["include"] = include
            data_ = c.official("GET", "/order", params=params)
            items, meta = _pages(data_)
            return _ok({"orders": compact(items, ORDERS_COMPACT), "meta": meta})
        if act == "get":
            _need(order_id, "order_id")
            return _ok(c.internal("GET", f"/orders/{order_id}"))
        if act == "create":
            _need(data, "data")
            return _ok(c.internal("POST", "/orders", body=data))
        if act == "update":
            _need(order_id, "order_id"), _need(data, "data")
            return _ok(c.internal("PUT", f"/orders/{order_id}", body=data))
        if act == "set_status":
            _need(order_id, "order_id"), _need(status_id, "status_id")
            return _ok(c.internal("POST", f"/orders/{order_id}/status/{status_id}"))
        if act == "add_product":
            _need(order_id, "order_id"), _need(data, "data")
            if "products" in data:
                body = data
            else:
                line = dict(data)
                line.setdefault("order_id", order_id)
                body = {"products": [line]}
            return _ok(c.internal("POST", f"/orders/{order_id}/products", body=body))
        if act == "update_product":
            _need(order_id, "order_id"), _need(product_id, "product_id"), _need(data, "data")
            return _ok(c.internal("PUT", f"/orders/{order_id}/products/{product_id}", body=data))
        if act == "remove_product":
            _need(order_id, "order_id"), _need(product_id, "product_id")
            return _ok(c.internal("DELETE", f"/orders/{order_id}/products/{product_id}"))
        if act == "add_payment":
            _need(order_id, "order_id"), _need(data, "data")
            payment = {"destination_type": "order", "destination_id": order_id,
                       "is_expense": False, "status": "paid"}
            payment.update(data)
            return _ok(c.internal("POST", "/finance/payments", body=payment))
        if act == "expenses":
            _need(order_id, "order_id")
            raw = c.internal("GET", f"/orders/{order_id}/expenses")
            if isinstance(raw, dict) and isinstance(raw.get("data"), list):
                return _ok(raw["data"])
            return _ok(raw)
        if act == "set_marketing":
            _need(order_id, "order_id"), _need(data, "data")
            return _ok(c.internal("PUT", f"/orders/{order_id}/marketing", body=data))
        if act == "add_tag":
            _need(order_id, "order_id"), _need(tag_id, "tag_id")
            return _ok(c.internal("POST", f"/orders/{order_id}/tags/{tag_id}"))
        if act == "remove_tag":
            _need(order_id, "order_id"), _need(tag_id, "tag_id")
            return _ok(c.internal("POST", f"/orders/{order_id}/tags/{tag_id}/detach"))
        if act == "remove":
            _need(ids, "ids")
            return _ok(c.internal("POST", "/batch/orders/execute/remove", body={"ids": ids}))
        if act == "statuses":
            params = {"with_disabled": 1} if include_disabled else None
            items, _ = _pages(c.internal("GET", "/orders/statuses", params=params))
            return _ok(compact(items, ["id", "name", "alias", "group_id", "is_active", "is_closing_order"]))
        if act == "groups":
            items, _ = _pages(c.internal("GET", "/orders/groups"))
            return _ok(compact(items, ["id", "name", "alias", "is_active"]))
        if act == "totals":
            return _ok(c.internal("GET", "/orders/totals"))
        if act == "tags":
            items, _ = _pages(c.internal("GET", "/orders/tags", params={"with_disabled": 1}))
            return _ok(compact(items, ["id", "name", "color", "is_active"]))
        if act == "sources":
            items, _ = _pages(c.internal("GET", "/sources", params={"users": 0}))
            return _ok(compact(items, ["id", "name", "alias", "driver", "is_installed"]))
        raise ValueError(f"unknown action '{action}'")
    except Exception as exc:
        return _err(exc)


# ---------------------------------------------------------------------- leads
@mcp.tool()
def leads(action: str = "list", lead_id: int | None = None, limit: int = 20,
          page: int = 1, filters: dict | None = None, include: str | None = None,
          data: dict | None = None, status_id: int | None = None,
          pipeline_id: int | None = None, ids: list[int] | None = None) -> str:
    """Pipeline cards (лиды / сделки / заявки).

    actions:
      list      - cards with pagination; filters go through the official API
                  ({"status_id": 1, "pipeline_id": 1, "created_between": ["...","..."]})
      get       - full card (contact, source, products, payments)
      create    - required: status_id, communicate_at, currency_code
                  optional: title, pipeline_id, source_id, manager_id, contact{...}
      update    - PUT /leads/{id} with a partial body
      move      - set status_id (moves between pipelines too)
      pipelines - list of pipelines with their statuses
      desk      - kanban board: statuses grouped with cards
      complete  - convert card into an order (PUT /leads/{id}/order)
      add_product / copy
      remove    - BLOCKED on purpose: the batch endpoint removes whole status
                  columns when ids do not match exactly. Delete cards in the UI.
    """
    try:
        c = client()
        act = action.lower().strip()
        if act == "list":
            if filters:
                params: dict[str, Any] = {"limit": min(max(int(limit), 1), 50), "page": max(int(page), 1)}
                params.update(_filters(filters))
                if include:
                    params["include"] = include
                data_ = c.official("GET", "/pipelines/cards", params=params)
                items, meta = _pages(data_)
            else:
                data_ = c.internal("GET", "/leads", params={"per_page": min(max(int(limit), 1), 50),
                                                           "page": max(int(page), 1)})
                items, meta = _pages(data_)
            return _ok({"leads": compact(items, CARDS_COMPACT), "meta": meta})
        if act == "get":
            _need(lead_id, "lead_id")
            params = {"include": include} if include else None
            return _ok(c.internal("GET", f"/leads/{lead_id}", params=params))
        if act == "create":
            _need(data, "data")
            return _ok(c.internal("POST", "/leads", body=data))
        if act == "update":
            _need(lead_id, "lead_id"), _need(data, "data")
            return _ok(c.internal("PUT", f"/leads/{lead_id}", body=data))
        if act == "move":
            _need(lead_id, "lead_id"), _need(status_id, "status_id")
            return _ok(c.internal("PUT", f"/leads/{lead_id}", body={"status_id": status_id}))
        if act == "pipelines":
            pipelines = c.internal("GET", "/leads/pipelines", params={"leads": "false"})
            if isinstance(pipelines, dict):
                pipelines = pipelines.get("data") or []
            out = []
            for p in pipelines:
                statuses = c.internal("GET", f"/leads/statuses/{p['id']}")
                if isinstance(statuses, dict):
                    statuses = statuses.get("data") or []
                out.append({
                    "id": p["id"], "title": p.get("title"), "lead_type": p.get("lead_type"),
                    "use_payments": p.get("use_payments"), "use_products": p.get("use_products"),
                    "statuses": compact(statuses, ["id", "title", "alias", "is_final",
                                                   "position", "leads_count"]),
                })
            return _ok(out)
        if act == "desk":
            if pipeline_id:
                return _ok(c.internal("GET", f"/leads/pipelines/desk/{pipeline_id}"))
            return _ok(c.internal("GET", "/leads/pipelines/desk"))
        if act == "complete":
            _need(lead_id, "lead_id")
            return _ok(c.internal("PUT", f"/leads/{lead_id}/order", body=data or {}))
        if act == "add_product":
            _need(lead_id, "lead_id"), _need(data, "data")
            return _ok(c.internal("POST", f"/leads/{lead_id}/products", body=data))
        if act == "copy":
            _need(lead_id, "lead_id")
            return _ok(c.internal("POST", f"/leads/{lead_id}/copy"))
        if act == "remove":
            # DANGER: the only working API form of card removal is
            #   POST /batch/leads/execute/remove?filters[lead_ids]=<ids>&column_ids=<statuses>&pipeline_id=<id>
            # and when the ids filter does not match exactly the endpoint removes
            # EVERY card of the selected columns. That already caused a mass
            # deletion in this account during the reverse-engineering run.
            raise ValueError(
                "Card removal is blocked on purpose: the batch endpoint deletes whole "
                "status columns when the id filter is not matched exactly, which already "
                "caused a mass deletion in this account. Delete pipeline cards in the KeyCRM UI."
            )
        raise ValueError(f"unknown action '{action}'")
    except Exception as exc:
        return _err(exc)


# -------------------------------------------------------------------- clients
@mcp.tool()
def clients(action: str = "list", client_id: int | None = None, limit: int = 20,
            page: int = 1, search: str | None = None, data: dict | None = None,
            phone: str | None = None, email: str | None = None,
            field: str | None = None, value: str | None = None) -> str:
    """Buyers / clients (покупці).

    IMPORTANT: POST /clients ignores phone and email. Contacts live in separate
    profiles: POST /clients/{id}/profiles {"client_id", "field": "phone"|"email",
    "value"}. create() accepts phone/email and writes the profiles right after
    the client, update() does the same when phone/email are passed.

    actions:
      list        - paginated clients with meta
      get         - full client (phones, emails, profile list, shipping addresses)
      create      - data{full_name, note, manager_id, ...} plus optional phone/email
      update      - data{...} plus optional phone/email
      delete      - DELETE /clients/{id}
      search      - by name/phone/email
      set_profile - client_id + field ("phone"/"email"/custom) + value
      orders      - order history of the client
      leads       - pipeline cards of the client
    """
    try:
        c = client()
        act = action.lower().strip()

        def add_profiles(cid: int) -> list:
            written = []
            for name, val in (("phone", phone), ("email", email)):
                if val:
                    written.append(c.internal("POST", f"/clients/{cid}/profiles",
                                              body={"client_id": cid, "field": name, "value": val}))
            return written

        if act == "list":
            data_ = c.internal("GET", "/clients", params={"per_page": min(max(int(limit), 1), 50),
                                                          "page": max(int(page), 1)})
            items, meta = _pages(data_)
            return _ok({"clients": compact(items, CLIENTS_COMPACT), "meta": meta})
        if act == "get":
            _need(client_id, "client_id")
            return _ok(c.internal("GET", f"/clients/{client_id}"))
        if act == "create":
            _need(data, "data")
            created = c.internal("POST", "/clients", body=data)
            cid = (created or {}).get("id")
            if cid:
                profiles = add_profiles(cid)
                if profiles:
                    created = c.internal("GET", f"/clients/{cid}")
            return _ok(created)
        if act == "update":
            _need(client_id, "client_id")
            if not data and not (phone or email):
                raise ValueError("'data' or phone/email is required for this action")
            updated = c.internal("PUT", f"/clients/{client_id}", body=data or {})
            if phone or email:
                add_profiles(client_id)
                updated = c.internal("GET", f"/clients/{client_id}")
            return _ok(updated)
        if act == "delete":
            _need(client_id, "client_id")
            return _ok(c.internal("DELETE", f"/clients/{client_id}"))
        if act == "search":
            _need(search, "search")
            return _ok(c.internal("GET", "/clients/search", params={"query": search}))
        if act == "set_profile":
            _need(client_id, "client_id"), _need(field, "field"), _need(value, "value")
            return _ok(c.internal("POST", f"/clients/{client_id}/profiles",
                                  body={"client_id": client_id, "field": field, "value": value}))
        if act == "orders":
            _need(client_id, "client_id")
            return _ok(c.internal("GET", f"/orders/client/{client_id}"))
        if act == "leads":
            _need(client_id, "client_id")
            return _ok(c.internal("GET", f"/leads/by-client/{client_id}"))
        raise ValueError(f"unknown action '{action}'")
    except Exception as exc:
        return _err(exc)


# ------------------------------------------------------------------- products
@mcp.tool()
def products(action: str = "list", product_id: int | None = None, limit: int = 20,
             page: int = 1, search: str | None = None, data: dict | None = None) -> str:
    """Catalog products (товари).

    actions: list (with stock quantity), get, create (name required), update,
    delete, categories (tree), warehouses, search.
    """
    try:
        c = client()
        act = action.lower().strip()
        if act == "list":
            params: dict[str, Any] = {"per_page": min(max(int(limit), 1), 50), "page": max(int(page), 1)}
            if search:
                params["query"] = search
            data_ = c.internal("GET", "/catalog/products", params=params)
            items, meta = _pages(data_)
            return _ok({"products": compact(items, PRODUCTS_COMPACT), "meta": meta})
        if act == "get":
            _need(product_id, "product_id")
            return _ok(c.internal("GET", f"/catalog/products/{product_id}"))
        if act == "create":
            _need(data, "data")
            return _ok(c.internal("POST", "/catalog/products", body=data))
        if act == "update":
            _need(product_id, "product_id"), _need(data, "data")
            return _ok(c.internal("PUT", f"/catalog/products/{product_id}", body=data))
        if act == "delete":
            _need(product_id, "product_id")
            return _ok(c.internal("DELETE", f"/catalog/products/{product_id}"))
        if act == "categories":
            return _ok(c.internal("GET", "/catalog/categories/tree"))
        if act == "warehouses":
            items, _ = _pages(c.internal("GET", "/stocks/warehouses"))
            return _ok(compact(items, ["id", "name", "is_active", "is_default"]))
        raise ValueError(f"unknown action '{action}'")
    except Exception as exc:
        return _err(exc)


# ---------------------------------------------------------------------- tasks
@mcp.tool()
def tasks(action: str = "list", task_id: int | None = None, limit: int = 20, page: int = 1,
          tab: str = "actual", mine: bool = True, entity_type: str | None = None,
          entity_id: int | None = None, data: dict | None = None,
          title: str | None = None, description: str | None = None,
          assigned_to_id: int | None = None, scheduled_at: str | None = None,
          priority: int = 1, task_type: str = "task") -> str:
    """Tasks (задачі). Creating a task really works on this account.

    The API wants this body: name, priority, type, description, status,
    scheduled_at (ISO), assigned_to_id, tasked, attachments, period,
    checklist, settings.

    actions:
      list        - paginated tasks; tab="actual" (open) or "closed",
                    mine=True only own tasks
      get         - task by id
      for_entity  - tasks attached to a card/order/client: entity_type
                    (lead/order/client/task) + entity_id
      expired_count
      create      - title, description, assigned_to_id, scheduled_at (ISO),
                    priority, task_type; or pass data{} to override the whole body
      update      - data{} with fields to change
      complete    - mark as done (status=done)
      delete      - DELETE /tasks/{id}
    """
    try:
        c = client()
        act = action.lower().strip()
        if act == "list":
            params = {"page": max(int(page), 1), "per_page": min(max(int(limit), 1), 50),
                      "filters[tasks]": "own" if mine else "all", "filters[tab]": tab}
            data_ = c.internal("GET", "/tasks/search", params=params)
            items, meta = _pages(data_)
            return _ok({"tasks": compact(items, TASKS_COMPACT), "meta": meta})
        if act == "get":
            _need(task_id, "task_id")
            return _ok(c.internal("GET", f"/tasks/{task_id}"))
        if act == "for_entity":
            _need(entity_type, "entity_type"), _need(entity_id, "entity_id")
            return _ok(c.internal("GET", f"/tasks/{entity_type}/{entity_id}"))
        if act == "expired_count":
            return _ok(c.internal("GET", "/tasks/expired-count"))
        if act == "create":
            if data:
                body = dict(data)
            else:
                _need(title, "title")
                if not assigned_to_id:
                    me = c.internal("GET", "/auth/profile")
                    assigned_to_id = me.get("id") if isinstance(me, dict) else None
                if not scheduled_at:
                    scheduled_at = (datetime.now(timezone.utc) + timedelta(days=1)).strftime(
                        "%Y-%m-%dT%H:%M:%S.000Z")
                body = {
                    "name": title,
                    "priority": priority,
                    "type": task_type,
                    "description": description or "",
                    "status": "open",
                    "scheduled_at": scheduled_at,
                    "assigned_to_id": assigned_to_id,
                    "tasked": None,
                    "attachments": [],
                    "period": {"time": 0, "duration": "days"},
                    "checklist": [],
                    "settings": {"allow_editing": False},
                }
            return _ok(c.internal("POST", "/tasks", body=body))
        if act == "update":
            _need(task_id, "task_id"), _need(data, "data")
            return _ok(c.internal("PUT", f"/tasks/{task_id}", body=data))
        if act == "complete":
            _need(task_id, "task_id")
            return _ok(c.internal("PUT", f"/tasks/{task_id}",
                                  body={"id": task_id, "status": "done"}))
        if act == "delete":
            _need(task_id, "task_id")
            return _ok(c.internal("DELETE", f"/tasks/{task_id}"))
        raise ValueError(f"unknown action '{action}'")
    except Exception as exc:
        return _err(exc)


# -------------------------------------------------------------- conversations
@mcp.tool()
def conversations(action: str = "list", conversation_id: int | None = None,
                  limit: int = 20, page: int = 1, data: dict | None = None) -> str:
    """Chats (переписки): list, get, messages, unread, send (reply into a chat)."""
    try:
        c = client()
        act = action.lower().strip()
        if act == "list":
            data_ = c.internal("GET", "/conversations", params={"per_page": min(max(int(limit), 1), 50),
                                                                "page": max(int(page), 1)})
            items, meta = _pages(data_)
            return _ok({"conversations": compact(items, CONVERSATIONS_COMPACT), "meta": meta})
        if act == "get":
            _need(conversation_id, "conversation_id")
            return _ok(c.internal("GET", f"/conversations/{conversation_id}"))
        if act == "messages":
            _need(conversation_id, "conversation_id")
            return _ok(c.internal("GET", f"/conversations/{conversation_id}/messages"))
        if act == "unread":
            return _ok(c.internal("GET", "/conversations/unread"))
        if act == "send":
            _need(conversation_id, "conversation_id"), _need(data, "data")
            return _ok(c.internal("POST", f"/conversations/{conversation_id}/messages", body=data))
        raise ValueError(f"unknown action '{action}'")
    except Exception as exc:
        return _err(exc)


# ---------------------------------------------------------------------- audit
@mcp.tool()
def audit(action: str = "list", limit: int = 20, page: int = 1,
          entity_id: int | None = None, entity_type: str = "order",
          manager_id: int | None = None) -> str:
    """Change history (історія змін, /auditing).

    actions:
      list        - recent changes of the whole account (paginated, newest first)
      by_entity   - changes of one object: entity_type (order/lead/task/manufacturing)
                    + entity_id
      by_manager  - changes made by a manager: manager_id
    Each record has action, model_type, model_ids, initiator and a changes list.
    """
    try:
        c = client()
        act = action.lower().strip()
        if act == "list":
            data_ = c.internal("GET", "/auditing/all",
                               params={"per_page": min(max(int(limit), 1), 50),
                                       "page": max(int(page), 1)})
            items, meta = _pages(data_)
            return _ok({"items": compact(items, ["_id", "action", "model_type", "model_ids",
                                                 "created_at", "initiator", "subject"]),
                        "meta": meta})
        if act == "by_entity":
            _need(entity_id, "entity_id")
            return _ok(c.internal("GET", f"/auditing/{entity_type}/{entity_id}"))
        if act == "by_manager":
            _need(manager_id, "manager_id")
            return _ok(c.internal("GET", f"/auditing/manager/{manager_id}"))
        raise ValueError(f"unknown action '{action}'")
    except Exception as exc:
        return _err(exc)


# ---------------------------------------------------------------------- users
@mcp.tool()
def users(action: str = "list") -> str:
    """Team: list (members with roles), roles, permissions."""
    try:
        c = client()
        act = action.lower().strip()
        if act == "list":
            items, _ = _pages(c.internal("GET", "/users"))
            return _ok(compact(items, USERS_COMPACT))
        if act == "roles":
            items, _ = _pages(c.internal("GET", "/users/roles"))
            return _ok(compact(items, ["id", "name", "permissions_count"]))
        if act == "permissions":
            return _ok(c.internal("GET", "/users/permissions"))
        raise ValueError(f"unknown action '{action}'")
    except Exception as exc:
        return _err(exc)


# ------------------------------------------------------------------- settings
@mcp.tool()
def settings(section: str = "") -> str:
    """Account settings (config/settings). section: general, orders, products,
    leads, currencies, shipment, notifications, companies, suppliers, ai,
    manufacturing, conversations, tables, order_fields, allowed_fields or empty
    for the whole object (large)."""
    try:
        data = client().internal("GET", "/config/settings")
        if section:
            return _ok({section: (data or {}).get(section)})
        return _ok(data)
    except Exception as exc:
        return _err(exc)


# -------------------------------------------------------------------- reports
def _status_map(c: Any) -> dict[str, str]:
    try:
        items, _ = _pages(c.internal("GET", "/orders/statuses"))
        return _names(items)
    except Exception:
        return {}


def _user_map(c: Any) -> dict[str, str]:
    try:
        items, _ = _pages(c.internal("GET", "/users"))
        return {str(u.get("id")): u.get("full_name") or u.get("email") or str(u.get("id")) for u in items}
    except Exception:
        return {}


@mcp.tool()
def report(kind: str = "sales", date_from: str | None = None, date_to: str | None = None,
           max_items: int = 500, group_by: str = "status", days: int = 7) -> str:
    """Aggregate report over a date range (UTC, YYYY-MM-DD).

    kind='sales' - orders: count, revenue (grand_total), average check, breakdown
    by status_id / manager_id / payment_status.
    kind='leads' - pipeline cards: count, sum of products_total, breakdown by
    status_id / pipeline_id / manager_id, plus finished/active split.
    kind='funnel' - live funnel: cards per status per pipeline, closed share and
    conversion percent (no date range needed, taken from the pipeline board).
    kind='managers' - load per manager: cards, closed, active, conversion, products_total.
    kind='stale' - cards with no updates for more than days (default 7) days.
    """
    try:
        c = client()
        start, end = _day_range(date_from, date_to)
        kind = kind.lower().strip()
        if kind == "sales":
            params = {"filter[created_between]": f"{start},{end}", "include": "status,buyer"}
            rows = c.official_pages("/order", params, max_items=min(int(max_items), 500))
            total = sum(float(r.get("grand_total") or 0) for r in rows)
            statuses = _status_map(c)
            managers = _user_map(c)
            buckets: dict[str, dict] = {}

            def add(key: str, label: str, amount: float):
                b = buckets.setdefault(key, {"label": label, "count": 0, "sum": 0.0})
                b["count"] += 1
                b["sum"] += amount

            for r in rows:
                amount = float(r.get("grand_total") or 0)
                if group_by == "manager":
                    mid = str(r.get("manager_id"))
                    add(mid, managers.get(mid, f"manager {mid}"), amount)
                elif group_by == "payment":
                    add(str(r.get("payment_status")), str(r.get("payment_status")), amount)
                else:
                    sid = str(r.get("status_id"))
                    add(sid, statuses.get(sid, f"status {sid}"), amount)
            return _ok({
                "kind": "sales", "period": {"from": start, "to": end},
                "orders": len(rows), "revenue": round(total, 2),
                "avg_check": round(total / len(rows), 2) if rows else 0,
                "group_by": group_by, "buckets": buckets,
                "truncated": len(rows) >= int(max_items),
            })
        if kind == "leads":
            params = {"filter[created_between]": f"{start},{end}", "include": "status,manager"}
            rows = c.official_pages("/pipelines/cards", params, max_items=min(int(max_items), 500))
            managers = _user_map(c)
            pipelines: dict[str, str] = {}
            try:
                pl, _ = _pages(c.official("GET", "/pipelines", params={"limit": 50}))
                pipelines = _names(pl, "id", "title")
            except Exception:
                pass
            card_statuses: dict[str, str] = {}
            try:
                for pid in {str(r.get("pipeline_id")) for r in rows}:
                    st, _ = _pages(c.official("GET", f"/pipelines/{pid}/statuses", params={"limit": 50}))
                    card_statuses.update(_names(st, "id", "title"))
            except Exception:
                pass
            buckets = {}
            for r in rows:
                amount = float(r.get("products_total") or 0)
                if group_by == "manager":
                    mid = str(r.get("manager_id"))
                    key, label = mid, managers.get(mid, f"manager {mid}")
                elif group_by == "pipeline":
                    key = str(r.get("pipeline_id"))
                    label = pipelines.get(key, f"pipeline {key}")
                else:
                    key = str(r.get("status_id"))
                    label = card_statuses.get(key, f"status {key}")
                b = buckets.setdefault(key, {"label": label, "count": 0, "sum": 0.0})
                b["count"] += 1
                b["sum"] += amount
            finished = sum(1 for r in rows if r.get("is_finished"))
            return _ok({
                "kind": "leads", "period": {"from": start, "to": end},
                "cards": len(rows), "products_total_sum": round(sum(float(r.get("products_total") or 0) for r in rows), 2),
                "finished": finished, "active": len(rows) - finished,
                "group_by": group_by, "buckets": buckets,
                "truncated": len(rows) >= int(max_items),
            })
        if kind == "managers":
            cards = c.internal_pages("/leads", {"per_page": 50}, max_items=2000, page_size=50)
            managers = _user_map(c)
            pipelines = c.internal("GET", "/leads/pipelines", params={"leads": "false"}) or []
            final_ids: set[int] = set()
            for p in pipelines:
                statuses = c.internal("GET", f"/leads/statuses/{p['id']}") or []
                final_ids.update(int(s["id"]) for s in statuses if s.get("is_final"))
            agg: dict[str, dict] = {}
            for card in cards:
                mid = str(card.get("manager_id"))
                row = agg.setdefault(mid, {
                    "manager_id": card.get("manager_id"),
                    "name": managers.get(mid, f"manager {mid}"),
                    "cards": 0, "closed": 0, "active": 0, "products_total": 0.0,
                })
                row["cards"] += 1
                if int(card.get("status_id") or 0) in final_ids:
                    row["closed"] += 1
                else:
                    row["active"] += 1
                row["products_total"] += float(card.get("products_total") or 0)
            rows = []
            for row in agg.values():
                row["conversion_percent"] = round(row["closed"] * 100.0 / row["cards"], 1) if row["cards"] else 0
                row["products_total"] = round(row["products_total"], 2)
                rows.append(row)
            rows.sort(key=lambda r: r["cards"], reverse=True)
            return _ok({"kind": "managers", "cards": len(cards), "managers": rows})
        if kind == "stale":
            cards = c.internal_pages("/leads", {"per_page": 50}, max_items=2000, page_size=50)
            pipelines = c.internal("GET", "/leads/pipelines", params={"leads": "false"}) or []
            final_ids: set[int] = set()
            for p in pipelines:
                statuses = c.internal("GET", f"/leads/statuses/{p['id']}") or []
                final_ids.update(int(s["id"]) for s in statuses if s.get("is_final"))
            now_dt = datetime.now(timezone.utc)
            border = now_dt - timedelta(days=max(int(days), 1))
            stale = []
            for card in cards:
                if int(card.get("status_id") or 0) in final_ids:
                    continue
                raw = card.get("updated_at") or card.get("status_changed_at") or card.get("created_at")
                if not raw:
                    continue
                try:
                    seen = datetime.fromisoformat(str(raw).replace("Z", "+00:00"))
                except ValueError:
                    continue
                if seen < border:
                    stale.append({
                        "id": card.get("id"), "title": card.get("title"),
                        "status_id": card.get("status_id"), "manager_id": card.get("manager_id"),
                        "updated_at": raw,
                        "days_stale": (now_dt - seen).days,
                    })
            stale.sort(key=lambda r: r["days_stale"], reverse=True)
            return _ok({"kind": "stale", "days": int(days), "cards": len(stale), "stale_cards": stale})
        if kind == "funnel":
            pipelines = c.internal("GET", "/leads/pipelines", params={"leads": "false"})
            if isinstance(pipelines, dict):
                pipelines = pipelines.get("data") or []
            cards = c.official_pages("/pipelines/cards", {}, max_items=min(int(max_items), 500))
            by_pipeline: dict[str, list[dict]] = {}
            for card in cards:
                by_pipeline.setdefault(str(card.get("pipeline_id")), []).append(card)
            out = []
            for p in pipelines:
                statuses = c.internal("GET", f"/leads/statuses/{p['id']}")
                if isinstance(statuses, dict):
                    statuses = statuses.get("data") or []
                pipe_cards = by_pipeline.get(str(p["id"]), [])
                total = len(pipe_cards)
                counter: dict[str, int] = {}
                for card in pipe_cards:
                    counter[str(card.get("status_id"))] = counter.get(str(card.get("status_id")), 0) + 1
                closed = sum(counter.get(str(s.get("id")), 0) for s in statuses if s.get("is_final"))
                out.append({
                    "pipeline_id": p["id"], "pipeline": p.get("title"),
                    "total_cards": total, "closed": closed, "active": total - closed,
                    "conversion_percent": round(closed * 100.0 / total, 1) if total else 0,
                    "statuses": [
                        {
                            "status_id": s.get("id"), "title": s.get("title"),
                            "is_final": bool(s.get("is_final")),
                            "cards": counter.get(str(s.get("id")), 0),
                            "share_percent": round(counter.get(str(s.get("id")), 0) * 100.0 / total, 1) if total else 0,
                        }
                        for s in statuses
                    ],
                })
            return _ok({"kind": "funnel", "cards_total": len(cards), "pipelines": out})
        raise ValueError("kind must be sales, leads, funnel, managers or stale")
    except Exception as exc:
        return _err(exc)


def _need(value: Any, name: str) -> None:
    if value is None or value == "" or value == [] or value == {}:
        raise ValueError(f"'{name}' is required for this action")


# Optional extra tool modules (finance, delivery, stocks, documents, ...).
try:
    from tools_domains import register as _register_domains

    _register_domains(mcp)
except ImportError:  # module not shipped in this copy
    pass

try:
    from tools_files import register as _register_files

    _register_files(mcp)
except ImportError:
    pass
except Exception as _exc:
    import sys as _sys

    print(f"[keycrm-mcp] tools_files skipped: {_exc}", file=_sys.stderr)
except Exception as _exc:  # keep the core server alive even if an addon is broken
    import sys

    print(f"[keycrm-mcp] tools_domains skipped: {_exc}", file=sys.stderr)


def main() -> None:
    mcp.run()


if __name__ == "__main__":
    main()
