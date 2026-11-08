"""End-to-end test for the domain tools (tools_domains.py).

Spawns _dev_server.py over stdio, the same way an MCP client does, and checks
every new tool against the live KeyCRM account. Read-only checks for finance,
delivery, publications, stocks, custom fields, documents and automations; the
comment tool performs a create / edit / delete cycle and soft-deletes what it
created.

Run:  .venv\\Scripts\\python.exe test_domains.py
Exit code 0 means every check passed.
"""

from __future__ import annotations

import json
import os
import queue
import subprocess
import sys
import threading
import time

PROJ = os.path.dirname(os.path.abspath(__file__))
PY = os.path.join(PROJ, ".venv", "Scripts", "python.exe")
if not os.path.exists(PY):
    PY = sys.executable

PASS: list[str] = []
FAIL: list[str] = []
DOMAIN_TOOLS = {"finance", "delivery", "publications", "stocks", "comments",
                "custom_fields", "documents", "automations"}
CORE_TOOLS = {"crm_status", "crm_endpoints", "crm_api", "orders", "leads", "clients",
              "products", "tasks", "conversations", "users", "settings", "report"}


class MCP:
    def __init__(self) -> None:
        env = dict(os.environ)
        env.setdefault("PYTHONIOENCODING", "utf-8")
        self.proc = subprocess.Popen(
            [PY, "_dev_server.py"], cwd=PROJ, env=env,
            stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.PIPE,
        )
        self.q: queue.Queue = queue.Queue()
        self.err: list[str] = []
        self._id = 0
        threading.Thread(target=self._reader, daemon=True).start()
        threading.Thread(target=self._err_reader, daemon=True).start()

    def _reader(self) -> None:
        assert self.proc.stdout is not None
        for raw in self.proc.stdout:
            line = raw.decode("utf-8", "replace").strip()
            if not line:
                continue
            try:
                self.q.put(json.loads(line))
            except Exception:
                self.err.append("NON-JSON: " + line[:300])

    def _err_reader(self) -> None:
        assert self.proc.stderr is not None
        for raw in self.proc.stderr:
            self.err.append(raw.decode("utf-8", "replace").rstrip())

    def _send(self, obj: dict) -> None:
        assert self.proc.stdin is not None
        self.proc.stdin.write((json.dumps(obj) + "\n").encode("utf-8"))
        self.proc.stdin.flush()

    def request(self, method: str, params: dict | None = None, timeout: float = 180.0) -> dict:
        self._id += 1
        self._send({"jsonrpc": "2.0", "id": self._id, "method": method, "params": params or {}})
        deadline = time.time() + timeout
        while time.time() < deadline:
            try:
                msg = self.q.get(timeout=max(0.5, deadline - time.time()))
            except queue.Empty:
                break
            if msg.get("id") == self._id:
                return msg
        raise TimeoutError(f"no response to {method}")

    def call(self, name: str, arguments: dict | None = None) -> dict:
        resp = self.request("tools/call", {"name": name, "arguments": arguments or {}})
        if "error" in resp:
            raise RuntimeError(f"RPC error: {resp['error']}")
        result = resp.get("result") or {}
        content = result.get("content") or []
        text = content[0].get("text") if content else ""
        try:
            parsed = json.loads(text)
        except Exception:
            parsed = {"raw": text}
        return parsed if isinstance(parsed, dict) else {"raw": parsed}

    def close(self) -> None:
        try:
            self.proc.stdin.close()
        except Exception:
            pass
        self.proc.terminate()


def check(label: str, condition: bool, detail: str = "") -> None:
    if condition:
        PASS.append(label)
        print(f"PASS  {label}")
    else:
        FAIL.append(label)
        print(f"FAIL  {label}  {detail}")


def tool_ok(mcp: MCP, label: str, name: str, args: dict | None = None) -> dict:
    data = mcp.call(name, args)
    ok = data.get("ok") is True
    check(label, ok, json.dumps(data, ensure_ascii=False)[:400] if not ok else "")
    return data.get("data") if ok else {}


def tool_err(mcp: MCP, label: str, name: str, args: dict, status: int | None = None,
             hint: str = "") -> dict:
    data = mcp.call(name, args)
    err = data.get("error") or {}
    ok = data.get("ok") is False
    if status is not None:
        ok = ok and err.get("status") == status
    if hint:
        ok = ok and hint in json.dumps(err, ensure_ascii=False)
    check(label, ok, json.dumps(data, ensure_ascii=False)[:400])
    return data


def lenient_500(label: str, raw: dict) -> None:
    """Accept real data or the honest server-side 500 this tenant returns."""
    if raw.get("ok") is True:
        check(label + " (data)", True)
    else:
        err = raw.get("error") or {}
        check(label + " (honest server 500)", err.get("status") == 500,
              json.dumps(raw, ensure_ascii=False)[:300])


def main() -> int:
    mcp = MCP()
    try:
        init = mcp.request("initialize", {
            "protocolVersion": "2025-06-18",
            "capabilities": {},
            "clientInfo": {"name": "keycrm-domains", "version": "0.1"},
        })
        check("initialize", "result" in init, str(init)[:300])
        mcp._send({"jsonrpc": "2.0", "method": "notifications/initialized"})

        tools = mcp.request("tools/list")
        names = [t["name"] for t in (tools.get("result") or {}).get("tools", [])]
        check("tools/list: at least 20 tools (core + 8 domain)", len(names) >= 20, str(names))
        check("tools/list: all 8 domain tools present", DOMAIN_TOOLS.issubset(set(names)),
              str(sorted(DOMAIN_TOOLS - set(names))))
        check("tools/list: 12 core tools still present", CORE_TOOLS.issubset(set(names)),
              str(sorted(CORE_TOOLS - set(names))))

        # ---------------------------------------------------------- discover ids
        leads = tool_ok(mcp, "core leads.list still works", "leads",
                        {"action": "list", "limit": 1})
        lead_rows = leads.get("leads") or []
        lead_id = int(lead_rows[0]["id"]) if lead_rows else 1

        # --------------------------------------------------------------- finance
        billing = tool_ok(mcp, "finance.billing", "finance", {"action": "billing"})
        check("finance.billing: tariff and amount",
              isinstance(billing.get("tariff"), dict) and "amount" in billing,
              json.dumps(billing, ensure_ascii=False)[:300])

        invoices = tool_ok(mcp, "finance.billing_invoices", "finance",
                           {"action": "billing_invoices", "limit": 5})
        check("finance.billing_invoices: rows", isinstance(invoices.get("invoices"), list)
              and len(invoices.get("invoices") or []) >= 1)

        billing_payments = tool_ok(mcp, "finance.billing_payments", "finance",
                                   {"action": "billing_payments", "limit": 5})
        check("finance.billing_payments: rows",
              isinstance(billing_payments.get("payments"), list)
              and len(billing_payments.get("payments") or []) >= 1)

        expense_types = tool_ok(mcp, "finance.expense_types", "finance",
                                {"action": "expense_types"})
        check("finance.expense_types: dictionary rows",
              len(expense_types) >= 1 and "alias" in expense_types[0])

        methods = tool_ok(mcp, "finance.payment_methods", "finance",
                          {"action": "payment_methods"})
        check("finance.payment_methods: dictionary rows", len(methods) >= 1 and "name" in methods[0])

        rates = tool_ok(mcp, "finance.currency_rates", "finance", {"action": "currency_rates"})
        check("finance.currency_rates: rows", len(rates) >= 1 and "rate" in rates[0])

        common = tool_ok(mcp, "finance.rates_common", "finance", {"action": "rates_common"})
        check("finance.rates_common: full table",
              int(common.get("count") or 0) > 50 and "USD" in (common.get("rates") or {}))

        common_sub = tool_ok(mcp, "finance.rates_common narrowed", "finance",
                             {"action": "rates_common", "currency": "USD,UAH"})
        check("finance.rates_common: currency filter",
              sorted((common_sub.get("rates") or {})) == ["UAH", "USD"]
              and not common_sub.get("missing"))

        fiscals = tool_ok(mcp, "finance.fiscals", "finance", {"action": "fiscals"})
        check("finance.fiscals: list envelope", isinstance(fiscals.get("fiscals"), list))

        gateways = tool_ok(mcp, "finance.payment_gateways", "finance",
                           {"action": "payment_gateways"})
        check("finance.payment_gateways: list", isinstance(gateways, list))

        tx_config = tool_ok(mcp, "finance.transactions_config", "finance",
                            {"action": "transactions_config"})
        check("finance.transactions_config: gateways key", "gateways" in tx_config)

        unlinked = tool_ok(mcp, "finance.transactions_unlinked", "finance",
                           {"action": "transactions_unlinked"})
        check("finance.transactions_unlinked: list", isinstance(unlinked, list))

        bills = tool_ok(mcp, "finance.bills", "finance", {"action": "bills"})
        check("finance.bills: list envelope", isinstance(bills.get("bills"), list))

        lenient_500("finance.payments", mcp.call("finance", {"action": "payments"}))
        lenient_500("finance.transactions", mcp.call("finance", {"action": "transactions"}))

        # -------------------------------------------------------------- delivery
        services = tool_ok(mcp, "delivery.services", "delivery", {"action": "services"})
        check("delivery.services: list envelope", isinstance(services.get("services"), list))

        prep = tool_ok(mcp, "delivery.prep_centers", "delivery",
                       {"action": "prep_centers", "limit": 5})
        check("delivery.prep_centers: list envelope", isinstance(prep.get("prep_centers"), list))

        prep_active = tool_ok(mcp, "delivery.prep_centers_active", "delivery",
                              {"action": "prep_centers_active"})
        check("delivery.prep_centers_active: list", isinstance(prep_active.get("prep_centers"), list))

        templates = tool_ok(mcp, "delivery.shipment_templates", "delivery",
                            {"action": "shipment_templates"})
        check("delivery.shipment_templates: list",
              isinstance(templates.get("shipment_templates"), list))

        tool_err(mcp, "delivery.warehouses: carrier required", "delivery",
                 {"action": "warehouses"}, hint="service")

        # ---------------------------------------------------------- publications
        pubs = tool_ok(mcp, "publications.list", "publications",
                       {"action": "list", "limit": 5})
        check("publications.list: list envelope", isinstance(pubs.get("publications"), list))

        # ---------------------------------------------------------------- stocks
        stock_rows = tool_ok(mcp, "stocks.list", "stocks", {"action": "list", "limit": 5})
        rows = stock_rows.get("stocks") or []
        check("stocks.list: rows with sku", len(rows) >= 1 and "sku" in rows[0]
              and "product_id" in rows[0])
        offer_id = int(rows[0]["id"]) if rows else 1

        movements = tool_ok(mcp, "stocks.movements", "stocks",
                            {"action": "movements", "limit": 5})
        check("stocks.movements: list envelope", isinstance(movements.get("movements"), list))

        warehouses = tool_ok(mcp, "stocks.warehouses", "stocks", {"action": "warehouses"})
        check("stocks.warehouses: at least one", isinstance(warehouses, list)
              and len(warehouses) >= 1 and "name" in warehouses[0])

        stat = tool_ok(mcp, "stocks.stat", "stocks", {"action": "stat"})
        check("stocks.stat: quantity block", "quantity" in stat and "price" in stat)

        bounds = tool_ok(mcp, "stocks.filters", "stocks", {"action": "filters"})
        check("stocks.filters: bounds", "in_reserve" in bounds)

        history = tool_ok(mcp, f"stocks.history offer {offer_id}", "stocks",
                          {"action": "history", "offer_id": offer_id, "limit": 5})
        check("stocks.history: list envelope", isinstance(history.get("history"), list))

        tool_err(mcp, "stocks unknown action", "stocks", {"action": "nope"},
                 hint="unknown action")

        # -------------------------------------------------------------- comments
        listed = tool_ok(mcp, f"comments.list lead {lead_id}", "comments",
                         {"action": "list", "entity_type": "lead",
                          "entity_id": lead_id, "limit": 20})
        check("comments.list: list shape", isinstance(listed.get("comments"), list)
              and "total" in listed,
              json.dumps(listed, ensure_ascii=False)[:300])

        created = tool_ok(mcp, "comments.add", "comments",
                          {"action": "add", "entity_type": "lead", "entity_id": lead_id,
                           "message": "MCP DOMAIN TEST COMMENT"})
        comment_id = int(created.get("id") or 0)
        check("comments.add: id and text",
              comment_id > 0 and created.get("message") == "MCP DOMAIN TEST COMMENT")

        after_add = tool_ok(mcp, "comments.list after add", "comments",
                            {"action": "list", "entity_type": "lead",
                             "entity_id": lead_id, "limit": 20})
        ids = [int(row.get("id") or 0) for row in (after_add.get("comments") or [])]
        check("comments.list: new comment visible",
              comment_id in ids and int(after_add.get("total") or 0) >= 1)

        edited = tool_ok(mcp, "comments.edit", "comments",
                         {"action": "edit", "comment_id": comment_id,
                          "message": "MCP DOMAIN TEST COMMENT EDITED"})
        check("comments.edit: text changed and flag set",
              edited.get("message") == "MCP DOMAIN TEST COMMENT EDITED"
              and edited.get("was_edited") is True)

        removed = tool_ok(mcp, "comments.delete", "comments",
                          {"action": "delete", "comment_id": comment_id})
        check("comments.delete: soft-deleted", removed.get("was_deleted") is True)

        # --------------------------------------------------------- custom fields
        fields = tool_ok(mcp, "custom_fields.list", "custom_fields", {"action": "list"})
        check("custom_fields.list: definitions", isinstance(fields, list) and len(fields) >= 12
              and "uuid" in fields[0])

        lead_fields = tool_ok(mcp, "custom_fields.list model=lead", "custom_fields",
                              {"action": "list", "model": "lead"})
        check("custom_fields.list: model filter",
              len(lead_fields) >= 1
              and all(row.get("model") == "lead" for row in lead_fields))

        if fields:
            one = tool_ok(mcp, "custom_fields.field", "custom_fields",
                          {"action": "field", "field_id": int(fields[0]["id"])})
            check("custom_fields.field: id match", int(one.get("id") or 0) == int(fields[0]["id"]))

        values = tool_ok(mcp, f"custom_fields.values lead {lead_id}", "custom_fields",
                         {"action": "values", "entity_id": lead_id, "model": "lead"})
        check("custom_fields.values: field values",
              isinstance(values, list) and len(values) >= 1
              and "field_id" in values[0] and isinstance(values[0].get("field"), dict)
              and "name" in values[0]["field"],
              json.dumps(values, ensure_ascii=False)[:300])

        # ------------------------------------------------------------- documents
        docs = tool_ok(mcp, "documents.list", "documents", {"action": "list"})
        check("documents.list: templates", isinstance(docs, list))

        scoped = tool_ok(mcp, "documents.by_scope order", "documents",
                         {"action": "by_scope", "scope": "order"})
        check("documents.by_scope: order list", isinstance(scoped, list))

        preview = tool_ok(mcp, "documents.preview", "documents",
                          {"action": "preview", "data": {"type": "order", "structure": "[]"}})
        check("documents.preview: rendered view", "view" in preview,
              json.dumps(preview, ensure_ascii=False)[:300])

        pdf = tool_ok(mcp, "documents.preview_pdf", "documents",
                      {"action": "preview_pdf", "data": {"type": "order", "structure": "Hello {{ model.id }}"}})
        check("documents.preview_pdf: pdf saved", int(pdf.get("bytes") or 0) > 1000,
              json.dumps(pdf, ensure_ascii=False)[:300])

        tool_err(mcp, "documents.preview: invalid type rejected", "documents",
                 {"action": "preview", "data": {"type": "nope", "structure": "[]"}},
                 status=422)

        # ----------------------------------------------------------- automations
        triggers = tool_ok(mcp, "automations.list", "automations", {"action": "list"})
        check("automations.list: triggers", int(triggers.get("count") or 0) >= 1
              and isinstance(triggers.get("triggers"), list))

        trigger_rows = triggers.get("triggers") or []
        if trigger_rows:
            tid = int(trigger_rows[0]["id"])
            one_trigger = tool_ok(mcp, "automations.get", "automations",
                                  {"action": "get", "trigger_id": tid})
            check("automations.get: id match", int(one_trigger.get("id") or 0) == tid)

        lead_triggers = tool_ok(mcp, "automations.list group=lead", "automations",
                                {"action": "list", "group": "lead"})
        check("automations.list: group filter",
              all(row.get("group") == "lead" for row in (lead_triggers.get("triggers") or [])))
    finally:
        mcp.close()

    print(f"\n{len(PASS)} passed, {len(FAIL)} failed")
    if FAIL:
        print("failed:", FAIL)
    if mcp.err:
        noise = [line for line in mcp.err if line.strip()
                 and "Processing request of type" not in line]
        if noise:
            print("\nserver stderr (first 10 lines):")
            for line in noise[:10]:
                print("  ", line[:200])
    return 0 if not FAIL else 1


if __name__ == "__main__":
    sys.exit(main())
