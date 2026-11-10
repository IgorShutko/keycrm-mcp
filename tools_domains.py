"""Domain tools for the KeyCRM MCP server.

Adds eight tools on top of the 12 core ones from server.py:

    finance        bills, payments, expense types, payment methods, currency
                   rates, fiscals, transactions, billing balance
    delivery       delivery services, prep centers, shipment templates,
                   carrier lookups (warehouses / locations / streets), shipment
                   price and waybill print
    publications   catalog publications (marketplaces) and their variations
    stocks         stock rows, movements, inventories, warehouses, stat and
                   the movement history of one offer
    comments       object comments (lead / order / client / deal), add / edit /
                   delete
    custom_fields  custom field definitions and per-entity values
    documents      document templates, per-scope templates, preview (HTML and
                   PDF) and print of a ready document
    automations    automation triggers (read only)

Usage from a launcher:

    from server import mcp
    from tools_domains import register
    register(mcp)

The contract matches server.py: an ``action`` string plus parameters, result
is a JSON string ``{"ok": true, "data": ...}`` or
``{"ok": false, "error": {...}}``. List answers are projected to compact rows
and capped at 50 per request.

Every path below comes from endpoints.json and was checked against the live
account (your-account). That account has no finance payments, delivery
services, prep centers, shipment templates or marketplace publications yet, so
those actions answer with empty collections. ``/finance/payments`` and
``/finance/transactions`` reply 500 on the server side; the tools surface that
error honestly instead of hiding it.
"""

from __future__ import annotations

import json
from typing import Any

from mcp.server.fastmcp import FastMCP

from keycrm_client import DATA_DIR, KeyCrmError, client, compact, dumps

# --------------------------------------------------------------- projections
BILLS = ["id", "name", "type", "amount", "balance", "currency_code", "status",
         "status_id", "bill_date", "created_at"]
PAYMENTS = ["id", "type", "amount", "currency_code", "payment_method_id", "payment_method",
            "bill_id", "order_id", "status", "comment", "created_at"]
EXPENSE_TYPES = ["id", "name", "alias", "is_active", "is_reserved", "by_order"]
PAYMENT_METHODS = ["id", "alias", "name", "is_active"]
CURRENCY_RATES = ["id", "code_in", "code_out", "rate"]
FISCALS = ["id", "type", "status", "number", "payment_id", "register_id", "created_at"]
TRANSACTIONS = ["id", "date", "amount", "currency_code", "description", "status",
                "gateway_id", "created_at"]
GATEWAYS = ["id", "name", "alias", "is_active", "is_installed", "created_at"]
BILLING_INVOICES = ["id", "amount", "created_at"]
BILLING_PAYMENTS = ["id", "total", "currency", "total_usd", "type", "source",
                    "invoice_id", "comment", "created_at"]

DELIVERY_SERVICES = ["id", "name", "alias", "driver", "is_active", "is_installed", "created_at"]
PREP_CENTERS = ["id", "name", "is_active", "warehouse_id", "delivery_service_id", "created_at"]
SHIPMENT_TEMPLATES = ["id", "name", "delivery_service_id", "is_default", "is_active", "created_at"]
PUBLICATIONS = ["id", "product_id", "product_name", "marketplace", "marketplace_id",
                "status", "status_id", "external_id", "is_active", "price", "quantity",
                "created_at", "updated_at"]
STOCK_ROWS = ["id", "product_id", "product_name", "sku", "barcode", "quantity", "in_reserve",
              "available", "price", "purchased_price", "is_archived", "is_default", "updated_at"]
MOVEMENTS = ["id", "type", "status", "movement_type", "warehouse_id", "warehouse_to_id",
             "reason", "comment", "created_at"]
HISTORY = ["id", "type", "status", "movement_type", "quantity", "warehouse_id",
           "reason", "created_at"]
WAREHOUSES = ["id", "name", "is_active", "is_default", "full_address", "created_at"]
COMMENTS = ["id", "message", "tone", "user_id", "commentable_id", "commentable_type",
            "was_edited", "was_deleted", "created_at"]
CUSTOM_FIELDS = ["id", "name", "uuid", "model", "type", "required", "position", "created_at"]
DOCUMENT_TEMPLATES = ["id", "name", "type", "scope", "is_active", "created_at"]
TRIGGERS = ["id", "name", "event", "group", "matching_type", "is_active", "period", "created_at"]

# Carrier routes that exist in endpoints.json (path prefix after /delivery/).
DELIVERY_LOOKUPS: dict[str, tuple[str, ...]] = {
    "novaposhta": ("warehouse", "location", "street"),
    "novaposhta_international": ("warehouse",),
    "ukrposhta": ("warehouse", "location"),
    "meest_express": ("warehouse", "location"),
    "rozetka_delivery": ("warehouse", "location"),
}
DELIVERY_SHIP: tuple[str, ...] = (
    "novaposhta", "novaposhta_international", "ukrposhta", "meest_express",
    "rozetka", "rozetka_delivery", "dhl_express", "fedex", "ups",
)


# ------------------------------------------------------------------- helpers
def _ok(data: Any) -> str:
    return dumps({"ok": True, "data": data})


def _err(exc: Exception) -> str:
    if isinstance(exc, KeyCrmError):
        return dumps({"ok": False, "error": exc.as_dict()})
    return dumps({"ok": False, "error": {"message": f"{type(exc).__name__}: {exc}"}})


def _need(value: Any, name: str) -> None:
    if value is None or value == "" or value == [] or value == {}:
        raise ValueError(f"'{name}' is required for this action")


def _list_params(limit: int = 20, page: int = 1, filters: dict | None = None) -> dict:
    """Paging params plus filters passed verbatim (keys as the endpoint expects)."""
    params: dict[str, Any] = {"limit": min(max(int(limit), 1), 50), "page": max(int(page), 1)}
    for key, value in (filters or {}).items():
        if value is None:
            continue
        if isinstance(value, bool):
            params[key] = "1" if value else "0"
        elif isinstance(value, (list, tuple)):
            params[key] = ",".join(str(v) for v in value)
        else:
            params[key] = value
    return params


def _meta(data: Any) -> dict:
    if not isinstance(data, dict):
        return {}
    keys = ("current_page", "last_page", "per_page", "total", "from", "to",
            "has_next", "has_previous")
    return {k: data[k] for k in keys if k in data and data[k] is not None}


def _items(data: Any) -> tuple[list, dict]:
    """Pull the item list out of the shapes this API returns."""
    if isinstance(data, list):
        return data, {}
    if not isinstance(data, dict):
        return [], {}
    for key in ("data", "publications", "items", "rows"):
        value = data.get(key)
        if isinstance(value, list):
            return value, (_meta(value) or _meta(data))
        if isinstance(value, dict) and isinstance(value.get("data"), list):
            return value["data"], (_meta(value) or _meta(data))
    item = data.get("data")
    if isinstance(item, dict):
        return [item], _meta(data)
    return [], _meta(data)


def _scalars(row: Any) -> Any:
    """Drop nested objects/arrays: honest fallback when a projection misses."""
    if not isinstance(row, dict):
        return row
    return {k: v for k, v in row.items() if not isinstance(v, (dict, list))}


def _slim(rows: list) -> list:
    return [_scalars(r) for r in rows]


def _project(rows: Any, fields: list[str]) -> list:
    """Compact projection; falls back to scalar keys when no field matched."""
    rows = rows if isinstance(rows, list) else [rows]
    projected = [compact(r, fields) for r in rows]
    if rows and all(isinstance(p, dict) and not p for p in projected):
        projected = [_scalars(r) for r in rows]
    return projected


def _one(row: Any, fields: list[str]) -> dict:
    """Project a single object to a compact dict."""
    projected = _project([row], fields)
    return projected[0] if projected else {}


def _binary_preview(data: Any) -> dict:
    if isinstance(data, str):
        return {"format": "text", "chars": len(data), "head": data[:500]}
    return {"format": "json", "data": data}


def _preview_body(data: dict | None) -> dict:
    _need(data, "data")
    body = dict(data or {})
    structure = body.get("structure")
    if structure is not None and not isinstance(structure, str):
        body["structure"] = json.dumps(structure, ensure_ascii=False)
    return body


# --------------------------------------------------------------------- tools
def register(mcp: FastMCP) -> None:
    """Register the domain tools on an existing FastMCP instance."""

    # ----------------------------------------------------------------- finance
    @mcp.tool()
    def finance(action: str = "bills", limit: int = 20, page: int = 1,
                filters: dict | None = None, currency: str | None = None) -> str:
        """Finance (фінанси): bills, payments, dictionaries, currency, billing.

        Read only on purpose: creating or moving money objects is risky, so the
        tool never writes. Actions:
          bills / accounts - list finance bills (рахунки), filters passed as-is
          payments         - list payments (answers 500 on this tenant, server side)
          payment_config   - payment form config: min/max amounts, methods, managers
          expense_types    - expense type dictionary
          payment_methods  - payment method dictionary
          payment_gateways - connected payment gateways
          currency_rates   - account currency rate table
          rates_common     - common currency rates; currency="USD,UAH" narrows it
          fiscals          - fiscal receipts / registers
          transactions     - bank transactions (answers 500 on this tenant)
          transactions_config / transactions_unlinked - bank import config / unlinked rows
          billing          - account balance, tariff and usage counters
          billing_invoices / billing_payments - subscription invoices and charges
        Example filters: {"filter[status]": "new"}; keys are sent as-is.
        """
        try:
            c = client()
            act = action.lower().strip()
            params = _list_params(limit, page, filters)
            if act in ("bills", "accounts"):
                rows, meta = _items(c.internal("GET", "/finance/bills", params=params))
                return _ok({"bills": _project(rows, BILLS), "meta": meta})
            if act == "payments":
                try:
                    rows, meta = _items(c.internal("GET", "/finance/payments", params=params))
                except KeyCrmError as exc:
                    if exc.status >= 500:
                        raise KeyCrmError(
                            500, "GET /finance/payments is broken on this tenant (500). "
                                 "Order payments are visible in orders.get (payments array) "
                                 "and added with orders action=add_payment", exc.body, "internal")
                    raise
                return _ok({"payments": _project(rows, PAYMENTS), "meta": meta})
            if act == "payment_config":
                return _ok(c.internal("GET", "/finance/payments/config"))
            if act == "expense_types":
                rows, _ = _items(c.internal("GET", "/finance/expense-types"))
                return _ok(_project(rows, EXPENSE_TYPES))
            if act == "payment_methods":
                rows, _ = _items(c.internal("GET", "/finance/payment-methods"))
                return _ok(_project(rows, PAYMENT_METHODS))
            if act == "payment_gateways":
                rows, _ = _items(c.internal("GET", "/finance/payment-gateways"))
                return _ok(_project(rows, GATEWAYS))
            if act == "currency_rates":
                rows, _ = _items(c.internal("GET", "/finance/currency-rates"))
                return _ok(_project(rows, CURRENCY_RATES))
            if act == "rates_common":
                rates = c.internal("GET", "/finance/currency-rates/common") or {}
                if currency:
                    wanted = [code.strip().upper() for code in currency.split(",") if code.strip()]
                    picked = {code: rates.get(code) for code in wanted}
                    missing = [code for code in wanted if rates.get(code) is None]
                    return _ok({"rates": picked, "missing": missing})
                return _ok({"count": len(rates), "rates": rates})
            if act == "fiscals":
                rows, meta = _items(c.internal("GET", "/finance/fiscals", params=params))
                return _ok({"fiscals": _project(rows, FISCALS), "meta": meta})
            if act == "transactions":
                try:
                    rows, meta = _items(c.internal("GET", "/finance/transactions", params=params))
                except KeyCrmError as exc:
                    if exc.status >= 500:
                        raise KeyCrmError(
                            500, "GET /finance/transactions is broken on this tenant (500). "
                                 "Use finance.bills, finance.fiscals or finance.billing instead",
                            exc.body, "internal")
                    raise
                return _ok({"transactions": _project(rows, TRANSACTIONS), "meta": meta})
            if act == "transactions_config":
                return _ok(c.internal("GET", "/finance/transactions/config"))
            if act == "transactions_unlinked":
                rows, _ = _items(c.internal("GET", "/finance/transactions/unlinked"))
                return _ok(_project(rows, TRANSACTIONS))
            if act == "billing":
                return _ok(c.internal("GET", "/billing"))
            if act == "billing_invoices":
                rows, meta = _items(c.internal("GET", "/billing/invoices", params=params))
                return _ok({"invoices": _project(rows, BILLING_INVOICES), "meta": meta})
            if act == "billing_payments":
                rows, meta = _items(c.internal("GET", "/billing/payments", params=params))
                return _ok({"payments": _project(rows, BILLING_PAYMENTS), "meta": meta})
            raise ValueError(f"unknown action '{action}'")
        except Exception as exc:
            return _err(exc)

    # ---------------------------------------------------------------- delivery
    @mcp.tool()
    def delivery(action: str = "services", service: str | None = None,
                 query: str | None = None, location_ref: str | None = None,
                 order_id: int | None = None,
                 limit: int = 20, page: int = 1, filters: dict | None = None,
                 data: dict | None = None) -> str:
        """Delivery (доставка): connected services, prep centers, templates, carrier lookups.

        Actions:
          services            - connected delivery services (empty on this tenant)
          prep_centers        - packing/prep centers, paginated
          prep_centers_active - active prep centers
          shipment_templates  - waybill templates
          warehouses          - carrier warehouse/office list: Nova Poshta, Ukrposhta and
                                Meest need location_ref (from locations), Rozetka takes query
          locations           - carrier city/place search for service + query
          streets             - Nova Poshta street search: query + location_ref
          suggest             - address suggestion by query (500 on this tenant)
          price               - POST shipment-price for order_id on service (dry run)
          print               - GET waybill document for order_id on service (text preview)
        service: novaposhta, novaposhta_international, ukrposhta, meest_express,
        rozetka, rozetka_delivery, dhl_express, fedex, ups.
        This tool never creates a shipment; that would push data to a carrier.
        """
        try:
            c = client()
            act = action.lower().strip()
            name = (service or "").lower().strip()
            params = _list_params(limit, page, filters)
            if act == "services":
                rows, meta = _items(c.internal("GET", "/delivery/delivery-services"))
                return _ok({"services": _project(rows, DELIVERY_SERVICES), "meta": meta})
            if act == "prep_centers":
                rows, meta = _items(c.internal("GET", "/delivery/prep-centers", params=params))
                return _ok({"prep_centers": _project(rows, PREP_CENTERS), "meta": meta})
            if act == "prep_centers_active":
                rows, _ = _items(c.internal("GET", "/delivery/prep-centers/active"))
                return _ok({"prep_centers": _project(rows, PREP_CENTERS)})
            if act == "shipment_templates":
                rows, _ = _items(c.internal("GET", "/delivery/shipment-templates"))
                return _ok({"shipment_templates": _project(rows, SHIPMENT_TEMPLATES)})
            if act in ("warehouses", "locations", "streets"):
                routes = DELIVERY_LOOKUPS.get(name)
                if not routes:
                    raise ValueError(
                        f"'service' must be one of {sorted(DELIVERY_LOOKUPS)} for {act}"
                    )
                route = {"warehouses": "warehouse", "locations": "location",
                         "streets": "street"}[act]
                if route not in routes:
                    raise ValueError(f"{act} is not available for carrier '{name}'")
                path = (f"/delivery/novaposhta/street" if act == "streets"
                        else f"/delivery/{name}/{route}")
                lookup: dict[str, Any] = {}
                if act == "locations":
                    if query:
                        lookup["query"] = query
                elif act == "streets":
                    if query:
                        lookup["query"] = query
                    if location_ref:
                        lookup["location_ref"] = location_ref
                else:  # warehouses
                    if name.startswith("novaposhta") or name in ("ukrposhta", "meest_express"):
                        _need(location_ref, "location_ref")
                        lookup["location_ref"] = location_ref
                    elif query:
                        lookup["query"] = query
                rows, meta = _items(c.internal("GET", path, params=lookup or None))
                return _ok({act: _slim(rows), "meta": meta})
            if act == "suggest":
                try:
                    rows, meta = _items(c.internal("GET", "/delivery/addresses/suggest",
                                                   params={"query": query} if query else None))
                except KeyCrmError as exc:
                    raise KeyCrmError(
                        exc.status, "delivery.suggest is broken on this tenant (500). "
                                    "Use delivery action=locations (carrier + query), "
                                    "then action=warehouses with location_ref",
                        exc.body, "internal")
                return _ok({"addresses": _slim(rows), "meta": meta})
            if act == "price":
                _need(name, "service"), _need(order_id, "order_id")
                if name not in DELIVERY_SHIP:
                    raise ValueError(f"'service' must be one of {list(DELIVERY_SHIP)}")
                return _ok({"price": c.internal("POST", f"/delivery/{name}/shipment-price/{order_id}",
                                                body=data or {})})
            if act == "print":
                _need(name, "service"), _need(order_id, "order_id")
                if name not in DELIVERY_SHIP:
                    raise ValueError(f"'service' must be one of {list(DELIVERY_SHIP)}")
                return _ok(_binary_preview(c.internal("GET", f"/delivery/{name}/print/{order_id}")))
            raise ValueError(f"unknown action '{action}'")
        except Exception as exc:
            return _err(exc)

    # ------------------------------------------------------------ publications
    @mcp.tool()
    def publications(action: str = "list", publication_id: int | None = None,
                     limit: int = 20, page: int = 1, filters: dict | None = None) -> str:
        """Marketplace publications (публікації): list, variations.

        Actions:
          list       - publications with marketplace/status/product columns
          variations - publication_id required, per-marketplace variations
        Empty on this tenant (no marketplaces connected). Sync/load actions are
        omitted on purpose: they push products to a live marketplace.
        """
        try:
            c = client()
            act = action.lower().strip()
            params = _list_params(limit, page, filters)
            if act == "list":
                rows, meta = _items(c.internal("GET", "/catalog/publications", params=params))
                return _ok({"publications": _project(rows, PUBLICATIONS), "meta": meta})
            if act == "variations":
                _need(publication_id, "publication_id")
                rows, meta = _items(c.internal("GET", f"/catalog/publications/{publication_id}/variations"))
                return _ok({"variations": _slim(rows), "meta": meta})
            raise ValueError(f"unknown action '{action}'")
        except Exception as exc:
            return _err(exc)

    # ------------------------------------------------------------------ stocks
    @mcp.tool()
    def stocks(action: str = "list", offer_id: int | None = None,
               movement_id: int | None = None, search: str | None = None,
               limit: int = 20, page: int = 1, filters: dict | None = None) -> str:
        """Stock (склад): stock rows, movements, inventories, warehouses, stat, history.

        Actions:
          list        - stock rows per offer (sku, quantity, in_reserve, available, price)
          movements   - stock movements, paginated
          movement    - one movement by movement_id
          inventories - movement_id required: inventory lines of that movement
          warehouses  - warehouses (read only here, stock writes are in crm_api)
          stat        - totals: quantity / purchased_price / price, positive vs negative
          filters     - filter bounds for the stock table
          history     - offer_id required: movement history of one offer
        filters keys are sent as-is, e.g. {"filter[warehouse_id]": 1}.
        """
        try:
            c = client()
            act = action.lower().strip()
            params = _list_params(limit, page, filters)
            if act == "list":
                if search:
                    params["search"] = search
                rows, meta = _items(c.internal("GET", "/stocks", params=params))
                return _ok({"stocks": _project(rows, STOCK_ROWS), "meta": meta})
            if act == "movements":
                rows, meta = _items(c.internal("GET", "/stocks/movements", params=params))
                return _ok({"movements": _project(rows, MOVEMENTS), "meta": meta})
            if act == "movement":
                _need(movement_id, "movement_id")
                return _ok(c.internal("GET", f"/stocks/movements/{movement_id}"))
            if act == "inventories":
                _need(movement_id, "movement_id")
                try:
                    rows, meta = _items(c.internal("GET", f"/stocks/inventories/{movement_id}"))
                except KeyCrmError as exc:
                    if exc.status == 404:
                        raise KeyCrmError(404, f"movement {movement_id} not found; "
                                               "list real ids with stocks action=movements",
                                          exc.body, "internal")
                    raise
                return _ok({"inventories": _slim(rows), "meta": meta})
            if act == "warehouses":
                rows, _ = _items(c.internal("GET", "/stocks/warehouses"))
                return _ok(_project(rows, WAREHOUSES))
            if act == "stat":
                return _ok(c.internal("GET", "/stocks/stat"))
            if act == "filters":
                return _ok(c.internal("GET", "/stocks/filters_data"))
            if act == "history":
                _need(offer_id, "offer_id")
                rows, meta = _items(c.internal("GET", f"/stocks/{offer_id}/history", params=params))
                return _ok({"history": _project(rows, HISTORY), "meta": meta})
            raise ValueError(f"unknown action '{action}'")
        except Exception as exc:
            return _err(exc)

    # ---------------------------------------------------------------- comments
    @mcp.tool()
    def comments(action: str = "list", entity_type: str = "lead",
                 entity_id: int | None = None, comment_id: int | None = None,
                 message: str | None = None, tone: str = "normal",
                 limit: int = 20, page: int = 1, data: dict | None = None) -> str:
        """Object comments (коментарі): list, add, edit, delete.

        entity_type: lead, order, client or deal; entity_id is the CRM id of
        that object. Actions:
          list   - comments of the object, paginated
          add    - message required (or pass a full body in data)
          edit   - comment_id required, new message or data body
          delete - comment_id required (the CRM keeps a soft-deleted flag)
        """
        try:
            c = client()
            act = action.lower().strip()
            if act == "list":
                _need(entity_type, "entity_type"), _need(entity_id, "entity_id")
                params = _list_params(limit, page, None)
                items, meta = _items(c.internal("GET", f"/communications/comments/{entity_type}/{entity_id}",
                                                params=params))
                return _ok({"comments": _project(items, COMMENTS),
                            "total": meta.get("total", len(items)), "meta": meta})
            if act == "add":
                _need(entity_type, "entity_type"), _need(entity_id, "entity_id")
                payload = dict(data or {})
                if message:
                    payload["message"] = message
                if tone:
                    payload.setdefault("tone", tone)
                _need(payload.get("message"), "message")
                return _ok(c.internal("POST", f"/communications/comments/{entity_type}/{entity_id}",
                                      body=payload))
            if act == "edit":
                _need(comment_id, "comment_id")
                payload = dict(data or {})
                if message:
                    payload["message"] = message
                _need(payload, "data")
                return _ok(c.internal("PUT", f"/communications/comments/{comment_id}", body=payload))
            if act == "delete":
                _need(comment_id, "comment_id")
                return _ok(c.internal("DELETE", f"/communications/comments/{comment_id}"))
            raise ValueError(f"unknown action '{action}'")
        except Exception as exc:
            return _err(exc)

    # ----------------------------------------------------------- custom fields
    @mcp.tool()
    def custom_fields(action: str = "list", model: str | None = None,
                      entity_id: int | None = None, field_id: int | None = None) -> str:
        """Custom fields (кастомні поля): definitions and values.

        Actions:
          list      - all custom fields; model filters them (lead / order / client)
          values    - entity_id + model required; values of that object
          field     - field_id required; one definition from the list
        Note the values path order: /config/custom-fields/{entity_id}/{model}/values.
        """
        try:
            c = client()
            act = action.lower().strip()
            rows, _ = _items(c.internal("GET", "/config/custom-fields"))
            if act in ("list", "for_model"):
                if model:
                    rows = [r for r in rows if str(r.get("model")) == model]
                return _ok(_project(rows, CUSTOM_FIELDS))
            if act == "field":
                _need(field_id, "field_id")
                for row in rows:
                    if int(row.get("id") or 0) == int(field_id):
                        return _ok(_one(row, CUSTOM_FIELDS))
                raise ValueError(f"custom field {field_id} not found")
            if act == "values":
                _need(entity_id, "entity_id"), _need(model, "model")
                values, _ = _items(c.internal("GET", f"/config/custom-fields/{entity_id}/{model}/values"))
                out = []
                for row in values:
                    field = row.get("field") if isinstance(row.get("field"), dict) else {}
                    out.append({
                        "id": row.get("id"),
                        "field_id": row.get("field_id"),
                        "value": row.get("value"),
                        "field": {"name": field.get("name"), "type": field.get("type")},
                    })
                return _ok(out)
            raise ValueError(f"unknown action '{action}'")
        except Exception as exc:
            return _err(exc)

    # --------------------------------------------------------------- documents
    @mcp.tool()
    def documents(action: str = "list", scope: str | None = None,
                  template_id: int | None = None, model_id: int | None = None,
                  data: dict | None = None) -> str:
        """Printed documents (документи): templates, preview, print.

        Actions:
          list       - document templates of the account (empty on this tenant)
          by_scope   - scope required (order / lead / client), templates for it
          export_template / export_formats - xlsx export template and formats
          print_layouts - list printing layouts (config/print)
          preview    - data required: {"type": "order", "structure": <json>};
                       structure may be a dict/list and is stringified for you;
                       returns rendered HTML view
          preview_pdf- same body, returns a short text head of the PDF (the
                       client truncates binary bodies)
          print      - template_id + scope + model_id, returns document text head
          attach     - template_id + scope + model_id + data, attaches a document
        Document writes are limited to preview/print/attach; templates are not
        created or edited here.
        """
        try:
            c = client()
            act = action.lower().strip()
            if act == "list":
                rows, _ = _items(c.internal("GET", "/config/documents"))
                return _ok(_project(rows, DOCUMENT_TEMPLATES))
            if act == "print_layouts":
                return _ok(c.internal("GET", "/config/print"))
            if act == "export_template":
                return _ok(c.internal("GET", "/config/export"))
            if act == "export_formats":
                return _ok(c.internal("GET", "/config/export/formats"))
            if act == "by_scope":
                _need(scope, "scope")
                rows, _ = _items(c.internal("GET", f"/config/documents/by-scope/{scope}"))
                return _ok(_project(rows, DOCUMENT_TEMPLATES))
            if act in ("preview", "preview_pdf"):
                body = _preview_body(data)
                if act == "preview_pdf":
                    import time as _time
                    from pathlib import Path as _Path
                    r = c.internal_bytes("POST", "/config/documents/preview-pdf", body=body)
                    out_dir = DATA_DIR / "exports"
                    out_dir.mkdir(parents=True, exist_ok=True)
                    target = out_dir / f"document_preview_{int(_time.time())}.pdf"
                    target.write_bytes(r.content)
                    return _ok({"file": str(target), "bytes": len(r.content),
                                "content_type": r.headers.get("content-type"),
                                "note": "PDF is saved to disk, content-type header is wrong on this server"})
                return _ok(c.internal("POST", "/config/documents/preview", body=body))
            if act == "print":
                _need(template_id, "template_id"), _need(scope, "scope"), _need(model_id, "model_id")
                try:
                    return _ok(c.internal("GET",
                                          f"/config/documents/print/{template_id}/{scope}/{model_id}"))
                except KeyCrmError as exc:
                    if exc.status == 404:
                        return _ok({"templates": 0,
                                    "message": "no document templates on this account, "
                                               "use preview or preview_pdf instead",
                                    "raw_status": 404})
                    raise
            if act == "attach":
                _need(template_id, "template_id"), _need(scope, "scope"), _need(model_id, "model_id")
                try:
                    return _ok(c.internal("GET",
                                          f"/config/documents/attach/{template_id}/{scope}/{model_id}"))
                except KeyCrmError as exc:
                    if exc.status == 404:
                        return _ok({"templates": 0,
                                    "message": "no document templates on this account, attach is unavailable"})
                    raise
            raise ValueError(f"unknown action '{action}'")
        except Exception as exc:
            return _err(exc)

    # ------------------------------------------------------------- automations
    @mcp.tool()
    def automations(action: str = "list", trigger_id: int | None = None,
                    event: str | None = None, group: str | None = None,
                    is_active: bool | None = None) -> str:
        """Automation triggers (автоматизації), read only.

        Actions:
          list - all triggers, compact; event / group / is_active filter locally
          get  - trigger_id required; one trigger from the list
        Creation, editing and toggling are not exposed: a trigger changes live
        CRM behaviour.
        """
        try:
            c = client()
            act = action.lower().strip()
            rows, _ = _items(c.internal("GET", "/automations/triggers"))
            if act == "get":
                _need(trigger_id, "trigger_id")
                for row in rows:
                    if int(row.get("id") or 0) == int(trigger_id):
                        return _ok(_one(row, TRIGGERS))
                raise ValueError(f"trigger {trigger_id} not found")
            if act == "list":
                if event:
                    rows = [r for r in rows if str(r.get("event")) == event]
                if group:
                    rows = [r for r in rows if str(r.get("group")) == group]
                if is_active is not None:
                    rows = [r for r in rows if bool(r.get("is_active")) is bool(is_active)]
                return _ok({"count": len(rows), "triggers": _project(rows, TRIGGERS)})
            raise ValueError(f"unknown action '{action}'")
        except Exception as exc:
            return _err(exc)
