"""Offline check, no KeyCRM account needed: the server imports, registers
all 24 tools and answers with a readable error when credentials are missing.
Run: python test_offline.py
"""

import asyncio
import os

for key in ("KEYCRM_DOMAIN", "KEYCRM_EMAIL", "KEYCRM_PASSWORD", "KEYCRM_API_TOKEN"):
    os.environ[key] = ""

import server  # noqa: E402

EXPECTED = 24


async def main() -> None:
    tools = await server.mcp.list_tools()
    names = sorted(t.name for t in tools)
    assert len(names) == EXPECTED, f"expected {EXPECTED} tools, got {len(names)}: {names}"
    assert all(t.description for t in tools), "every tool needs a description"

    found = await server.mcp.call_tool("crm_endpoints", {"query": "leads"})
    assert "leads" in str(found), "endpoint catalog search returned nothing"

    status = str(await server.mcp.call_tool("crm_status", {}))
    assert "KEYCRM_DOMAIN" in status, f"missing-credentials error is not readable: {status[:300]}"
    print(f"ok: {len(names)} tools, catalog search works, missing credentials reported")


if __name__ == "__main__":
    asyncio.run(main())
