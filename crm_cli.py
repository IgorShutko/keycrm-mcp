"""Small CLI for KeyCRM, useful for scripts and agents without an MCP client.

Examples:
  python crm_cli.py status
  python crm_cli.py get /leads?limit=3
  python crm_cli.py official GET /pipelines
  python crm_cli.py post /leads '{"status_id":1,"communicate_at":"2026-11-10 12:00:00","currency_code":"UAH"}'
"""

from __future__ import annotations

import json
import sys

from keycrm_client import KeyCrmError, client, dumps


def main(argv: list[str]) -> int:
    c = client()
    if not argv or argv[0] in ("-h", "--help", "help"):
        print(__doc__)
        return 0
    cmd = argv[0].lower()
    try:
        if cmd == "status":
            profile = c.internal("GET", "/auth/profile")
            print(dumps({"profile": {k: profile.get(k) for k in ("id", "full_name", "email", "is_owner")},
                         "domain": c.domain,
                         "official_token": bool(c.api_token)}))
            return 0
        if cmd == "get":
            path = argv[1]
            print(dumps(c.internal("GET", path)))
            return 0
        if cmd == "official":
            method = argv[1].upper()
            path = argv[2]
            body = json.loads(argv[3]) if len(argv) > 3 else None
            print(dumps(c.official(method, path, body=body)))
            return 0
        if cmd in ("post", "put", "patch", "delete"):
            path = argv[1]
            if "/batch/leads/execute/remove" in path or "column_ids" in path:
                print(dumps({"ok": False, "error": {
                    "reason": "blocked: this batch route wipes whole kanban columns, "
                              "card removal is UI-only, see docs/INCIDENT.md"}}))
                return 2
            body = json.loads(argv[2]) if len(argv) > 2 else None
            print(dumps(c.internal(cmd.upper(), path, body=body)))
            return 0
        if cmd == "check":
            cards = c.internal_pages("/leads", {"per_page": 50}, max_items=2000)
            clients = c.internal_pages("/clients", {"per_page": 50}, max_items=1000)
            orders = c.official_pages("/order", {}, max_items=200)
            tasks = c.internal("GET", "/tasks/search", params={"per_page": 50})
            task_items = (tasks or {}).get("data") or []
            products = c.internal_pages("/catalog/products", {"per_page": 50}, max_items=500)
            def garbage(rows, key):
                return [{"id": r.get("id"), key: r.get(key)} for r in rows
                        if "MCP TEST" in str(r.get(key) or "")]
            print(dumps({
                "counters": {"cards": len(cards), "clients": len(clients),
                             "orders": len(orders), "tasks": len(task_items),
                             "products": len(products)},
                "leftovers": {
                    "cards": garbage(cards, "title"),
                    "clients": garbage(clients, "full_name"),
                    "orders": garbage(orders, "manager_comment"),
                    "tasks": garbage(task_items, "name"),
                    "products": garbage(products, "name"),
                },
            }))
            return 0
        if cmd == "search-endpoints":
            from endpoints_catalog import catalog
            print(dumps(catalog.search(argv[1] if len(argv) > 1 else "")))
            return 0
    except KeyCrmError as exc:
        print(dumps({"ok": False, "error": exc.as_dict()}))
        return 2
    print(f"unknown command: {cmd}")
    return 1


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
