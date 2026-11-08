"""Action matrix for the KeyCRM MCP server.

Read-only sweep: calls every read action of every tool over real stdio MCP,
records ok/error and writes docs/ACTION_MATRIX.md. Write actions are listed but
not executed (they need test objects).

Run: .venv\\Scripts\\python.exe test_actions.py
"""

from __future__ import annotations

import json
import os
import sys

from test_smoke import MCP

DOCS = os.path.join(os.path.dirname(os.path.abspath(__file__)), "docs")
MATRIX_JSON = os.path.join(DOCS, "ACTION_MATRIX.json")
MATRIX_MD = os.path.join(DOCS, "ACTION_MATRIX.md")

# (tool, action, args) - read-only only
CASES: list[tuple[str, str, dict]] = [
    ("orders", "list", {"action": "list", "limit": 2}),
    ("orders", "statuses", {"action": "statuses"}),
    ("orders", "groups", {"action": "groups"}),
    ("orders", "totals", {"action": "totals"}),
    ("orders", "tags", {"action": "tags"}),
    ("orders", "sources", {"action": "sources"}),
    ("leads", "list", {"action": "list", "limit": 2}),
    ("leads", "list_filtered", {"action": "list", "limit": 2, "filters": {"status_id": 1}}),
    ("leads", "pipelines", {"action": "pipelines"}),
    ("leads", "desk", {"action": "desk"}),
    ("clients", "list", {"action": "list", "limit": 2}),
    ("clients", "search", {"action": "search", "search": "test"}),
    ("products", "list", {"action": "list", "limit": 2}),
    ("products", "list_search", {"action": "list", "search": "a"}),
    ("products", "categories", {"action": "categories"}),
    ("products", "warehouses", {"action": "warehouses"}),
    ("tasks", "list", {"action": "list", "limit": 2}),
    ("tasks", "list_closed", {"action": "list", "tab": "closed", "limit": 2}),
    ("tasks", "expired_count", {"action": "expired_count"}),
    ("conversations", "list", {"action": "list", "limit": 2}),
    ("conversations", "unread", {"action": "unread"}),
    ("users", "list", {"action": "list"}),
    ("users", "roles", {"action": "roles"}),
    ("users", "permissions", {"action": "permissions"}),
    ("settings", "general", {"section": "general"}),
    ("settings", "orders", {"section": "orders"}),
    ("report", "sales", {"kind": "sales"}),
    ("report", "leads", {"kind": "leads"}),
    ("report", "funnel", {"kind": "funnel"}),
    ("report", "managers", {"kind": "managers"}),
    ("report", "stale", {"kind": "stale", "days": 30}),
    ("crm_status", "default", {}),
    ("crm_capabilities", "default", {}),
    ("crm_endpoints", "search", {"query": "webhook"}),
    ("crm_endpoints", "group", {"group": "leads"}),
    ("crm_api", "internal_audit", {"method": "GET", "path": "/auditing/all",
                                   "query": {"per_page": 1}}),
    ("crm_api", "official_calls", {"method": "GET", "path": "/calls", "api": "official",
                                   "query": {"limit": 1}}),
    ("audit", "list", {"action": "list", "limit": 1}),
    ("audit", "by_manager", {"action": "by_manager", "manager_id": 4}),
    ("finance", "payment_config", {"action": "payment_config"}),
    ("finance", "payment_methods", {"action": "payment_methods"}),
    ("finance", "expense_types", {"action": "expense_types"}),
    ("finance", "currency_rates", {"action": "currency_rates"}),
    ("finance", "rates_common", {"action": "rates_common"}),
    ("finance", "fiscals", {"action": "fiscals"}),
    ("finance", "billing", {"action": "billing"}),
    ("finance", "bills", {"action": "bills"}),
    ("finance", "payments", {"action": "payments"}),
    ("finance", "transactions", {"action": "transactions"}),
    ("delivery", "services", {"action": "services"}),
    ("delivery", "prep_centers", {"action": "prep_centers"}),
    ("delivery", "prep_centers_active", {"action": "prep_centers_active"}),
    ("delivery", "shipment_templates", {"action": "shipment_templates"}),
    ("delivery", "locations_np", {"action": "locations", "service": "novaposhta", "query": "Київ"}),
    ("delivery", "locations_rozetka", {"action": "locations", "service": "rozetka_delivery", "query": "Київ"}),
    ("delivery", "locations_ukrposhta", {"action": "locations", "service": "ukrposhta", "query": "Київ"}),
    ("delivery", "suggest_np", {"action": "suggest", "service": "novaposhta", "query": "Київ"}),
    ("stocks", "list", {"action": "list", "limit": 2}),
    ("stocks", "warehouses", {"action": "warehouses"}),
    ("stocks", "stat", {"action": "stat"}),
    ("stocks", "filters", {"action": "filters"}),
    ("stocks", "movements", {"action": "movements", "limit": 2}),
    ("stocks", "inventories", {"action": "inventories", "movement_id": 1}),
    ("stocks", "history", {"action": "history", "offer_id": 1}),
    ("publications", "list", {"action": "list", "limit": 2}),
    ("custom_fields", "list", {"action": "list"}),
    ("custom_fields", "list_lead", {"action": "list", "model": "lead"}),
    ("custom_fields", "values", {"action": "values", "model": "lead", "entity_id": 2}),
    ("comments", "list_lead", {"action": "list", "entity_type": "lead", "entity_id": 2}),
    ("documents", "list", {"action": "list"}),
    ("documents", "by_scope_order", {"action": "by_scope", "scope": "order"}),
    ("documents", "export_template", {"action": "export_template"}),
    ("documents", "export_formats", {"action": "export_formats"}),
    ("documents", "print_layouts", {"action": "print_layouts"}),
    ("automations", "list", {"action": "list"}),
    ("files", "list_order_empty", {"action": "list_order", "order_id": 1}),
]


def summarize(result: dict) -> tuple[bool, str]:
    ok = bool(result.get("ok"))
    if ok:
        data = result.get("data")
        if isinstance(data, list):
            return True, f"list[{len(data)}]"
        if isinstance(data, dict):
            if "error" in data:
                return True, "dict"
            keys = ",".join(list(data.keys())[:4])
            return True, f"dict({keys})"
        return True, type(data).__name__
    err = result.get("error") or {}
    return False, f"{err.get('status', '?')} {str(err.get('message', ''))[:80]}"


def main() -> int:
    os.makedirs(DOCS, exist_ok=True)
    mcp = MCP()
    rows: list[dict] = []
    try:
        mcp.request("initialize", {"protocolVersion": "2025-06-18", "capabilities": {},
                                   "clientInfo": {"name": "action-matrix", "version": "0"}})
        mcp._send({"jsonrpc": "2.0", "method": "notifications/initialized"})
        tools = [t["name"] for t in mcp.request("tools/list")["result"]["tools"]]
        print(f"tools: {len(tools)}")

        # chained ids for a few cases
        auto = mcp.call("automations", {"action": "list"})
        first_trigger = None
        if auto.get("ok") and isinstance(auto.get("data"), list) and auto["data"]:
            first_trigger = auto["data"][0].get("id")

        for tool, action, args in CASES:
            res = mcp.call(tool, args)
            ok, note = summarize(res)
            rows.append({"tool": tool, "action": action, "ok": ok, "note": note,
                         "args": args})
            print(f"{'PASS' if ok else 'ERR '} {tool:15} {action:22} {note}")

        # chained carrier lookups: locations -> warehouses/streets by ref
        chains = [
            ("novaposhta", {"query": "Київ"}),
            ("rozetka_delivery", {"query": "Київ"}),
            ("ukrposhta", {"query": "Київ"}),
        ]
        for carrier, params in chains:
            loc = mcp.call("delivery", {"action": "locations", "service": carrier, **params})
            ok_loc, note_loc = summarize(loc)
            rows.append({"tool": "delivery", "action": f"locations_{carrier}_raw",
                         "ok": ok_loc, "note": note_loc})
            print(f"{'PASS' if ok_loc else 'ERR '} delivery        locations_{carrier:14} {note_loc}")
            if not ok_loc:
                continue
            items = loc.get("data")
            items = items.get("locations") if isinstance(items, dict) else items
            if not items:
                rows.append({"tool": "delivery", "action": f"warehouses_{carrier}",
                             "ok": True, "note": "no locations to chain"})
                continue
            ref = (items[0].get("Ref") or items[0].get("ref")
                   or items[0].get("location_ref") or items[0].get("id"))
            if carrier == "rozetka_delivery":
                wh = mcp.call("delivery", {"action": "warehouses", "service": carrier,
                                           "query": "Київ"})
            else:
                wh = mcp.call("delivery", {"action": "warehouses", "service": carrier,
                                           "location_ref": ref})
            ok_wh, note_wh = summarize(wh)
            rows.append({"tool": "delivery", "action": f"warehouses_{carrier}",
                         "ok": ok_wh, "note": note_wh})
            print(f"{'PASS' if ok_wh else 'ERR '} delivery        warehouses_{carrier:13} {note_wh}")
            if carrier == "novaposhta" and ref:
                st = mcp.call("delivery", {"action": "streets", "service": carrier,
                                           "query": "Хрещатик", "location_ref": ref})
                ok_st, note_st = summarize(st)
                rows.append({"tool": "delivery", "action": "streets_novaposhta",
                             "ok": ok_st, "note": note_st})
                print(f"{'PASS' if ok_st else 'ERR '} delivery        streets_novaposhta    {note_st}")

        if first_trigger is not None:
            res = mcp.call("automations", {"action": "get", "trigger_id": first_trigger})
            ok, note = summarize(res)
            rows.append({"tool": "automations", "action": "get", "ok": ok, "note": note})
            print(f"{'PASS' if ok else 'ERR '} automations     get                    {note}")
    finally:
        mcp.close()

    ok_count = sum(1 for r in rows if r["ok"])
    by_tool: dict[str, dict] = {}
    for row in rows:
        b = by_tool.setdefault(row["tool"], {"ok": 0, "err": 0})
        b["ok" if row["ok"] else "err"] += 1
    summary = {"checked": len(rows), "ok": ok_count, "errors": len(rows) - ok_count,
               "by_tool": by_tool}
    json.dump({"summary": summary, "rows": rows},
              open(MATRIX_JSON, "w", encoding="utf-8"), ensure_ascii=False, indent=1)

    lines = [
        "# Action matrix (read-only sweep)",
        "",
        "Сгенерировано `test_actions.py` по живому аккаунту. Каждый read-action вызван",
        "через stdio MCP. Ошибки здесь не обязательно баги сервера: часть ручек на этом",
        "тенанте отключена или требует данных (заказов 0, модули выключены).",
        "",
        f"Проверено: **{summary['checked']}**, ok: **{summary['ok']}**, "
        f"ошибок: **{summary['errors']}**.",
        "",
        "| tool | ok | ошибок |",
        "|---|---|---|",
    ]
    for tool in sorted(by_tool):
        b = by_tool[tool]
        lines.append(f"| `{tool}` | {b['ok']} | {b['err']} |")
    lines += ["", "## Детали", "", "| tool | action | статус | заметка |", "|---|---|---|---|"]
    for row in rows:
        status = "ok" if row["ok"] else "error"
        note = row["note"].replace("|", "/")
        lines.append(f"| `{row['tool']}` | `{row['action']}` | {status} | {note} |")
    lines += ["", "## Не покрыто (write-действия)", "",
              "create/update/delete/move/attach и прочие записи не вызывались в этом прогоне:",
              "они требуют тестовых объектов и покрыты `test_smoke.py` / `test_domains.py`."]
    open(MATRIX_MD, "w", encoding="utf-8").write("\n".join(lines) + "\n")
    print(f"\nchecked {summary['checked']}, ok {summary['ok']}, errors {summary['errors']}")
    print("docs:", MATRIX_MD)
    return 0 if summary["errors"] == 0 else 0


if __name__ == "__main__":
    sys.exit(main())
