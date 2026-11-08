"""End-to-end smoke test for the KeyCRM MCP server.

Spawns the server over stdio (same way Claude Desktop does), calls every tool,
then performs write/create/update/delete cycles and removes every test object.

Run:  .venv\\Scripts\\python.exe test_smoke.py
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

PASS, FAIL = [], []
# Card deletion is blocked by the API on this tenant (batch/leads/execute/remove
# answers 400), so the create/move card cycle is opt-in to keep the account clean.
TEST_LEADS = os.environ.get("KEYCRM_TEST_LEADS") == "1"


class MCP:
    def __init__(self) -> None:
        env = dict(os.environ)
        env.setdefault("PYTHONIOENCODING", "utf-8")
        self.proc = subprocess.Popen(
            [PY, "server.py"], cwd=PROJ, env=env,
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

    def call(self, name: str, arguments: dict | None = None):
        resp = self.request("tools/call", {"name": name, "arguments": arguments or {}})
        if "error" in resp:
            raise RuntimeError(f"RPC error: {resp['error']}")
        result = resp.get("result") or {}
        content = result.get("content") or []
        text = content[0].get("text") if content else ""
        try:
            return json.loads(text)
        except Exception:
            return {"raw": text}

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
    ok = isinstance(data, dict) and data.get("ok") is True
    check(label, ok, json.dumps(data, ensure_ascii=False)[:400] if not ok else "")
    return data.get("data") if ok else {}


def main() -> int:
    mcp = MCP()
    created: dict[str, list[int]] = {"clients": [], "products": [], "leads": [], "orders": []}
    try:
        init = mcp.request("initialize", {
            "protocolVersion": "2025-06-18",
            "capabilities": {},
            "clientInfo": {"name": "keycrm-smoke", "version": "0.1"},
        })
        check("initialize", "result" in init, str(init)[:300])
        mcp._send({"jsonrpc": "2.0", "method": "notifications/initialized"})

        tools = mcp.request("tools/list")
        names = [t["name"] for t in (tools.get("result") or {}).get("tools", [])]
        check("tools/list has all core tools", len(names) >= 12, str(names))
        core = {"crm_status", "orders", "leads", "clients", "products", "tasks",
                "conversations", "users", "settings", "report", "crm_api", "crm_endpoints"}
        check("tools/list: core tool names present", core.issubset(set(names)), str(sorted(core - set(names))))

        status = tool_ok(mcp, "crm_status", "crm_status")
        check("crm_status: profile is owner",
              (status.get("profile") or {}).get("is_owner") in (True, 1),
              json.dumps(status, ensure_ascii=False)[:300])
        counters = status.get("counters") or {}
        check("crm_status: counters present",
              "clients" in counters and "cards" in counters, str(counters))
        # wait until asynchronous background jobs settle, then take the baseline
        baseline = dict(counters)
        for _ in range(10):
            time.sleep(1)
            probe = mcp.call("crm_status", {})
            now = (probe.get("data") or {}).get("counters") or {}
            if now == baseline:
                break
            baseline = dict(now)

        orders_list = tool_ok(mcp, "orders.list", "orders", {"action": "list", "limit": 5})
        check("orders.list: paginated envelope", "orders" in orders_list and "meta" in orders_list)

        cards = tool_ok(mcp, "leads.list", "leads", {"action": "list", "limit": 5})
        check("leads.list: returns cards", isinstance(cards.get("leads"), list))
        check("leads.list: compact projection",
              all("status_id" in row for row in (cards.get("leads") or [])))

        filtered = tool_ok(mcp, "leads.list filtered", "leads",
                           {"action": "list", "limit": 3, "filters": {"status_id": 1}})
        check("leads.list: official filter path works",
              all(int(r.get("status_id") or 0) == 1 for r in (filtered.get("leads") or [])))

        pipes = tool_ok(mcp, "leads.pipelines", "leads", {"action": "pipelines"})
        check("leads.pipelines: pipeline + statuses", bool(pipes) and bool(pipes[0].get("statuses")))

        desk = tool_ok(mcp, "leads.desk", "leads", {"action": "desk"})
        check("leads.desk: board returned", isinstance(desk, (list, dict)) and bool(desk))

        cl = tool_ok(mcp, "clients.list", "clients", {"action": "list", "limit": 5})
        check("clients.list: envelope", "clients" in cl)

        pr = tool_ok(mcp, "products.list", "products", {"action": "list", "limit": 5})
        check("products.list: returns catalog", isinstance(pr.get("products"), list))

        wh = tool_ok(mcp, "products.warehouses", "products", {"action": "warehouses"})
        check("products.warehouses: at least one", isinstance(wh, list) and len(wh) >= 1)

        st = tool_ok(mcp, "orders.statuses", "orders", {"action": "statuses"})
        check("orders.statuses: 19 statuses", isinstance(st, list) and len(st) >= 19)

        ts = tool_ok(mcp, "tasks.list", "tasks", {"action": "list"})
        check("tasks.list: ok", "tasks" in ts)

        us = tool_ok(mcp, "users.list", "users", {"action": "list"})
        check("users.list: 3 members", isinstance(us, list) and len(us) == 3)

        cfg = tool_ok(mcp, "settings.general", "settings", {"section": "general"})
        check("settings.general: returned", isinstance(cfg, dict) and "general" in cfg)

        ep = tool_ok(mcp, "crm_endpoints search", "crm_endpoints", {"query": "tags"})
        check("crm_endpoints: finds tag routes", ep.get("count", 0) > 0)

        raw = tool_ok(mcp, "crm_api raw GET", "crm_api",
                      {"method": "GET", "path": "/users", "api": "internal"})
        check("crm_api: raw internal call", isinstance(raw, (list, dict)) and bool(raw))

        rep_sales = tool_ok(mcp, "report.sales", "report", {"kind": "sales"})
        check("report.sales: totals", "revenue" in rep_sales and "orders" in rep_sales)

        rep_leads = tool_ok(mcp, "report.leads", "report", {"kind": "leads"})
        check("report.leads: cards counted", int(rep_leads.get("cards") or 0) > 0,
              json.dumps(rep_leads, ensure_ascii=False)[:300])

        rep_funnel = tool_ok(mcp, "report.funnel", "report", {"kind": "funnel"})
        check("report.funnel: pipeline totals", bool(rep_funnel.get("pipelines")),
              json.dumps(rep_funnel, ensure_ascii=False)[:200])
        rep_managers = tool_ok(mcp, "report.managers", "report", {"kind": "managers"})
        check("report.managers: rows present", isinstance(rep_managers.get("managers"), list)
              and len(rep_managers.get("managers") or []) >= 1)
        rep_stale = tool_ok(mcp, "report.stale", "report", {"kind": "stale", "days": 7})
        check("report.stale: scan works", "stale_cards" in rep_stale)

        hist = tool_ok(mcp, "audit.list", "audit", {"action": "list", "limit": 3})
        check("audit.list: history returned", bool(hist.get("items")),
              json.dumps(hist, ensure_ascii=False)[:200])

        # ---------------- write cycle: client -------------------------------
        new_client = tool_ok(mcp, "clients.create", "clients",
                             {"action": "create", "data": {"full_name": "MCP TEST CLIENT"},
                              "phone": "+380501112077", "email": "mcp.smoke@example.com"})
        cid = new_client.get("id") if isinstance(new_client, dict) else None
        check("clients.create: id returned", bool(cid))
        if cid:
            created["clients"].append(int(cid))
            check("clients.create: phone via profile saved",
                  new_client.get("phone") == "+380501112077", str(new_client.get("phone")))
            upd = tool_ok(mcp, "clients.update", "clients",
                          {"action": "update", "client_id": cid, "data": {"note": "mcp-test"}})
            check("clients.update: note saved", (upd or {}).get("note") == "mcp-test")
            upd2 = tool_ok(mcp, "clients.update phone", "clients",
                           {"action": "update", "client_id": cid, "phone": "+380501113311"})
            check("clients.update: phone profile added",
                  (upd2 or {}).get("phone") == "+380501113311", str((upd2 or {}).get("phone")))
            prof = tool_ok(mcp, "clients.set_profile", "clients",
                           {"action": "set_profile", "client_id": cid,
                            "field": "email", "value": "second.smoke@example.com"})
            check("clients.set_profile: profile created", bool((prof or {}).get("id")))

            comment = tool_ok(mcp, "comments.add", "comments",
                              {"action": "add", "entity_type": "client", "entity_id": cid,
                               "message": "MCP TEST comment"})
            cmid = (comment or {}).get("id")
            check("comments.add: id returned", bool(cmid))
            if cmid:
                lst = tool_ok(mcp, "comments.list", "comments",
                              {"action": "list", "entity_type": "client", "entity_id": cid})
                check("comments.list: comment visible",
                      any(int(c.get("id") or 0) == int(cmid) for c in (lst.get("comments") or [])))
                ed = tool_ok(mcp, "comments.edit", "comments",
                             {"action": "edit", "comment_id": cmid, "message": "MCP TEST edited"})
                check("comments.edit: message changed",
                      str((ed or {}).get("message", "")).startswith("MCP TEST edited"),
                      str((ed or {}).get("message"))[:80])
                tool_ok(mcp, "comments.delete", "comments",
                        {"action": "delete", "comment_id": cmid})

        # ---------------- write cycle: product ------------------------------
        new_product = tool_ok(mcp, "products.create", "products",
                              {"action": "create", "data": {"name": "MCP TEST PRODUCT"}})
        pid = new_product.get("id") if isinstance(new_product, dict) else None
        check("products.create: id returned", bool(pid))
        if pid:
            created["products"].append(int(pid))

        # ---------------- write cycle: lead (opt-in) -------------------------
        if TEST_LEADS:
            lead_body = {
                "title": "MCP TEST CARD",
                "pipeline_id": 1,
                "status_id": 1,
                "source_id": 1,
                "communicate_at": "2026-11-10 12:00:00",
                "currency_code": "UAH",
                "contact": {"full_name": "MCP TEST CONTACT", "phone": "+380501112299"},
            }
            new_lead = tool_ok(mcp, "leads.create", "leads", {"action": "create", "data": lead_body})
            lid = new_lead.get("id") if isinstance(new_lead, dict) else None
            check("leads.create: id returned", bool(lid),
                  json.dumps(new_lead, ensure_ascii=False)[:300])
            if lid:
                created["leads"].append(int(lid))
                moved = tool_ok(mcp, "leads.move", "leads",
                                {"action": "move", "lead_id": lid, "status_id": 2})
                check("leads.move: new status", (moved or {}).get("status_id") == 2)
                got = tool_ok(mcp, "leads.get", "leads", {"action": "get", "lead_id": lid})
                check("leads.get: full card", isinstance(got, dict) and "contact" in got)

        # ---------------- write cycle: order --------------------------------
        order_body = {
            "source_id": 1,
            "buyer": {"full_name": "MCP TEST BUYER", "phone": "+380501112288"},
            "products": [{"name": "MCP TEST ITEM", "price": 150, "quantity": 1}],
        }
        new_order = tool_ok(mcp, "orders.create", "orders", {"action": "create", "data": order_body})
        oid = new_order.get("id") if isinstance(new_order, dict) else None
        check("orders.create: id returned", bool(oid))
        if oid:
            created["orders"].append(int(oid))
            # the official list can lag a couple of seconds behind the write
            visible = False
            for _ in range(15):
                seen = mcp.call("orders", {"action": "list", "limit": 20})
                rows = ((seen.get("data") or {}).get("orders") or []) if seen.get("ok") else []
                if any(int(r.get("id") or 0) == int(oid) for r in rows):
                    visible = True
                    break
                time.sleep(1)
            check("orders.list: new order visible", visible)
            got_order = tool_ok(mcp, "orders.get", "orders", {"action": "get", "order_id": oid})
            check("orders.get: full order", isinstance(got_order, dict) and "products" in got_order)
            tool_ok(mcp, "orders.set_status", "orders",
                    {"action": "set_status", "order_id": oid, "status_id": 2})
            pay = tool_ok(mcp, "orders.add_payment", "orders",
                          {"action": "add_payment", "order_id": oid,
                           "data": {"payment_method_id": 1, "actual_amount": 50,
                                    "description": "MCP TEST payment"}})
            check("orders.add_payment: payment created", bool(pay.get("id")))
            paid = tool_ok(mcp, "orders.get", "orders", {"action": "get", "order_id": oid})
            check("orders.add_payment: payments_total updated",
                  float(paid.get("payments_total") or 0) >= 50, str(paid.get("payments_total")))

            updated = tool_ok(mcp, "orders.update", "orders",
                              {"action": "update", "order_id": oid,
                               "data": {"id": oid, "manager_comment": "MCP TEST updated"}})
            check("orders.update: manager_comment saved",
                  (updated or {}).get("manager_comment") == "MCP TEST updated")

            added = mcp.call("orders", {"action": "add_product", "order_id": oid,
                                        "data": {"name": "MCP TEST EXTRA", "price": 25,
                                                 "quantity": 2}})
            lines = (added.get("data") or []) if added.get("ok") else []
            extra = next((ln for ln in lines if ln.get("name") == "MCP TEST EXTRA"), None)
            check("orders.add_product: line added", bool(extra),
                  json.dumps(added, ensure_ascii=False)[:200])
            if extra:
                upd_line = tool_ok(mcp, "orders.update_product", "orders",
                                   {"action": "update_product", "order_id": oid,
                                    "product_id": extra.get("id"), "data": {"price": 30}})
                check("orders.update_product: price changed",
                      float((upd_line or {}).get("price") or 0) == 30,
                      str((upd_line or {}).get("price")))
                tool_ok(mcp, "orders.remove_product", "orders",
                        {"action": "remove_product", "order_id": oid,
                         "product_id": extra.get("id")})

            tag = mcp.call("crm_api", {"method": "POST", "path": "/orders/tags",
                                       "body": {"name": "MCP TEST TAG", "color": "#123456"}})
            tag_payload = (tag.get("data") or {}) if tag.get("ok") else {}
            if isinstance(tag_payload.get("data"), dict):
                tag_payload = tag_payload["data"]
            tag_id = tag_payload.get("id")
            check("orders.tag create (raw api): id", bool(tag_id),
                  json.dumps(tag, ensure_ascii=False)[:200])
            if tag_id:
                tool_ok(mcp, "orders.add_tag", "orders",
                        {"action": "add_tag", "order_id": oid, "tag_id": tag_id})
                tagged = tool_ok(mcp, "orders.get tag order", "orders",
                                 {"action": "get", "order_id": oid})
                names = [t.get("name") for t in ((tagged or {}).get("tags") or [])]
                check("orders.add_tag: tag attached", "MCP TEST TAG" in names, str(names))
                tool_ok(mcp, "orders.remove_tag", "orders",
                        {"action": "remove_tag", "order_id": oid, "tag_id": tag_id})
                tool_ok(mcp, "cleanup: tag delete", "crm_api",
                        {"method": "DELETE", "path": f"/orders/tags/{tag_id}"})

            marketing = tool_ok(mcp, "orders.set_marketing", "orders",
                                {"action": "set_marketing", "order_id": oid,
                                 "data": {"utm_source": "mcp_test", "utm_medium": "smoke"}})
            check("orders.set_marketing: accepted", bool(marketing))
            exp = tool_ok(mcp, "orders.expenses", "orders",
                          {"action": "expenses", "order_id": oid})
            check("orders.expenses: readable",
                  isinstance(exp, list) or isinstance((exp or {}).get("data"), list),
                  json.dumps(exp, ensure_ascii=False)[:150])

        # ---------------- tasks: create / complete / delete ------------------
        new_task = tool_ok(mcp, "tasks.create", "tasks",
                           {"action": "create", "title": "MCP TEST TASK SMOKE",
                            "description": "smoke test", "priority": 1})
        tkid = new_task.get("id") if isinstance(new_task, dict) else None
        check("tasks.create: id returned", bool(tkid),
              json.dumps(new_task, ensure_ascii=False)[:300])
        if tkid:
            ren = tool_ok(mcp, "tasks.update", "tasks",
                          {"action": "update", "task_id": tkid,
                           "data": {"id": tkid, "name": "MCP TEST TASK RENAMED"}})
            check("tasks.update: name changed",
                  (ren or {}).get("name") == "MCP TEST TASK RENAMED",
                  str((ren or {}).get("name"))[:80])
            done = tool_ok(mcp, "tasks.complete", "tasks", {"action": "complete", "task_id": tkid})
            check("tasks.complete: status done", (done or {}).get("status") == "done")
            tool_ok(mcp, "tasks.delete", "tasks", {"action": "delete", "task_id": tkid})

        # ---------------- safety rails --------------------------------------
        blocked = mcp.call("leads", {"action": "remove", "ids": [1]})
        check("safety: card removal blocked", blocked.get("ok") is False,
              json.dumps(blocked, ensure_ascii=False)[:200])
        blocked2 = mcp.call("crm_api", {"method": "POST",
                                        "path": "/batch/leads/execute/remove",
                                        "query": {"filters[lead_ids]": "1"}})
        check("safety: crm_api blocks dangerous batch path", blocked2.get("ok") is False,
              json.dumps(blocked2, ensure_ascii=False)[:200])

        snap = tool_ok(mcp, "crm_snapshot", "crm_snapshot", {})
        check("crm_snapshot: file written", bool(snap.get("file")) and int(snap.get("bytes") or 0) > 1000,
              json.dumps(snap, ensure_ascii=False)[:200])
        if snap.get("file") and os.path.exists(snap["file"]):
            with open(snap["file"], encoding="utf-8") as fh:
                blob = fh.read()
            check("crm_snapshot: secrets masked",
                  "eyJ" not in blob and "\"access_token\": \"" not in blob,
                  "snapshot contains raw token-like strings")
            os.remove(snap["file"])

        # ---------------- files: upload/attach/detach/delete ----------------
        import tempfile as _tempfile
        tmp_path = os.path.join(_tempfile.gettempdir(), "mcp_smoke_upload.txt")
        with open(tmp_path, "w", encoding="utf-8") as fh:
            fh.write("MCP TEST attachment\n")
        if created["orders"]:
            att_order = created["orders"][0]
            att = tool_ok(mcp, "files.attach_order", "files",
                          {"action": "attach_order", "order_id": att_order,
                           "path": tmp_path, "filename": "mcp_smoke.txt"})
            check("files.attach_order: ok", att.get("chunks") == 1, json.dumps(att)[:200])
            rows = tool_ok(mcp, "files.list_order", "files",
                           {"action": "list_order", "order_id": att_order})
            rows = rows if isinstance(rows, list) else []
            check("files.list_order: attachment visible", len(rows) >= 1, str(rows)[:200])
            if rows:
                file_id = rows[0].get("file_id") or (rows[0].get("file") or {}).get("id")
                attachment_id = rows[0].get("id")
                dl = tool_ok(mcp, "files.download", "files", {"action": "download", "file_id": file_id})
                check("files.download: file saved", int(dl.get("bytes") or 0) > 0)
                tool_ok(mcp, "files.detach", "files",
                        {"action": "detach", "attachment_id": attachment_id})
                tool_ok(mcp, "files.delete_file", "files",
                        {"action": "delete_file", "file_id": file_id})

        # ---------------- documents: preview / pdf / list --------------------
        prev = tool_ok(mcp, "documents.preview", "documents",
                       {"action": "preview", "data": {"type": "order",
                        "structure": "x{{ model.id }}", "title": "smoke"}})
        check("documents.preview: html view", "view" in json.dumps(prev)[:300] or prev,
              json.dumps(prev, ensure_ascii=False)[:200])
        pdf = tool_ok(mcp, "documents.preview_pdf", "documents",
                      {"action": "preview_pdf", "data": {"type": "order",
                       "structure": "Hello {{ model.id }}"}})
        check("documents.preview_pdf: pdf saved", int(pdf.get("bytes") or 0) > 1000)
        docs = tool_ok(mcp, "documents.list", "documents", {"action": "list"})
        check("documents.list: empty templates are ok", isinstance(docs, list))

        # ---------------- cleanup ------------------------------------------
        # batch removal is queued; retry until the order disappears
        if created["orders"]:
            for attempt in range(4):
                tool_ok(mcp, "cleanup: orders remove", "orders",
                        {"action": "remove", "ids": created["orders"]})
                time.sleep(2)
                seen = mcp.call("orders", {"action": "list", "limit": 50})
                rows = ((seen.get("data") or {}).get("orders") or []) if seen.get("ok") else []
                if not any(int(r.get("id") or 0) in created["orders"] for r in rows):
                    break
        if created["leads"]:
            dropped = mcp.call("leads", {"action": "remove", "ids": created["leads"]})
            check("cleanup: card removal (API may refuse)", True)
            print("      card cleanup result:", json.dumps(dropped, ensure_ascii=False)[:300])
        for pid_ in created["products"]:
            tool_ok(mcp, f"cleanup: product {pid_}", "products",
                    {"action": "delete", "product_id": pid_})
        for cid_ in created["clients"]:
            tool_ok(mcp, f"cleanup: client {cid_}", "clients",
                    {"action": "delete", "client_id": cid_})

        after: dict = {}
        for _ in range(15):
            res = mcp.call("crm_status", {})
            after = (res.get("data") or {}).get("counters") or {}
            if (after.get("orders") == baseline.get("orders")
                    and after.get("clients") == baseline.get("clients")
                    and after.get("products") == baseline.get("products")
                    and after.get("cards") == baseline.get("cards")):
                break
            time.sleep(1)
        check("cleanup: counters not above baseline",
              all(int(after.get(k) or 0) <= int(baseline.get(k) or 0)
                  for k in ("orders", "clients", "products", "cards")),
              f"before={baseline} after={after}")
    finally:
        mcp.close()

    print(f"\n{len(PASS)} passed, {len(FAIL)} failed")
    if FAIL:
        print("failed:", FAIL)
    if mcp.err:
        noise = [line for line in mcp.err if line.strip()]
        if noise:
            print("\nserver stderr (first 10 lines):")
            for line in noise[:10]:
                print("  ", line[:200])
    return 0 if not FAIL else 1


if __name__ == "__main__":
    sys.exit(main())
