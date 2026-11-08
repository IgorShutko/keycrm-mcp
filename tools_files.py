"""File attachments (file-storage) for the KeyCRM MCP server.

Upload protocol was reverse-engineered from the SPA and verified live:
POST /file-storage/attach/order/{order_id} as multipart with
file, filename, mime, totalSize, chunkSize, totalChunks, chunkNumber.
Files are uploaded in chunks of 1 MiB; a single chunk is enough below that.
"""

from __future__ import annotations

import base64
import mimetypes
import os
import time
from pathlib import Path
from typing import Any

from keycrm_client import KeyCrmError, client, dumps

EXPORTS = Path(__file__).with_name("exports")


def _ok(data: Any) -> str:
    return dumps({"ok": True, "data": data})


def _err(exc: Exception) -> str:
    if isinstance(exc, KeyCrmError):
        return dumps({"ok": False, "error": exc.as_dict()})
    return dumps({"ok": False, "error": {"message": f"{type(exc).__name__}: {exc}"}})


def _need(value: Any, name: str) -> None:
    if value is None or value == "" or value == [] or value == {}:
        raise ValueError(f"'{name}' is required for this action")


def files(action: str = "list_order", order_id: int | None = None,
          path: str | None = None, filename: str | None = None,
          mime: str | None = None, content_base64: str | None = None,
          file_id: int | None = None, attachment_id: int | None = None) -> str:
    """Files and attachments (файли) of orders.

    actions:
      list_order   - attachments of an order (GET /orders/{id}, field attachments)
      validate     - size limit check before upload: order_id + path
      attach_order - upload a file to an order: order_id + path (local file)
                     or content_base64, optional filename/mime; multipart,
                     single chunk, limit 250 MB per order
      download     - save a file by file_id into keycrm-mcp/exports/,
                     returns local path, size and content type
      detach       - remove attachment from its entity (attachment_id)
      delete_file  - delete file itself (file_id), cascades attachments

    Note: deleting an order does NOT delete its files, remove orphans with
    delete_file explicitly.
    """
    try:
        c = client()
        act = action.lower().strip()
        if act == "list_order":
            _need(order_id, "order_id")
            try:
                order = c.internal("GET", f"/orders/{order_id}")
            except KeyCrmError as exc:
                if exc.status == 404:
                    raise KeyCrmError(404, f"order {order_id} not found; "
                                           "list real ids with orders action=list",
                                      exc.body, "internal")
                raise
            return _ok(order.get("attachments") or [])
        if act == "validate":
            _need(order_id, "order_id")
            total = os.path.getsize(path) if path else 0
            return _ok(c.internal("POST", f"/file-storage/attach/order/{order_id}/validate",
                                  body={"total": total}))
        if act == "attach_order":
            _need(order_id, "order_id")
            if content_base64:
                raw = base64.b64decode(content_base64)
            elif path:
                raw = Path(path).read_bytes()
            else:
                raise ValueError("path or content_base64 is required")
            name = filename or (Path(path).name if path else "upload.bin")
            ctype = mime or (mimetypes.guess_type(name)[0] or "application/octet-stream")
            chunk = 1024 * 1024
            total = len(raw)
            chunks = max(1, (total + chunk - 1) // chunk)
            result: Any = None
            for number in range(1, chunks + 1):
                part = raw[(number - 1) * chunk: number * chunk]
                form = {
                    "filename": name, "mime": ctype,
                    "totalSize": str(total), "chunkSize": str(chunk),
                    "totalChunks": str(chunks), "chunkNumber": str(number),
                }
                result = c.internal_multipart(
                    f"/file-storage/attach/order/{order_id}",
                    files={"file": (name, part, ctype)}, form=form)
            return _ok({"chunks": chunks, "bytes": total, "result": result})
        if act == "download":
            _need(file_id, "file_id")
            r = c.internal_bytes("GET", f"/file-storage/{file_id}")
            EXPORTS.mkdir(exist_ok=True)
            target = EXPORTS / f"file_{file_id}_{int(time.time())}.bin"
            target.write_bytes(r.content)
            return _ok({"file": str(target), "bytes": len(r.content),
                        "content_type": r.headers.get("content-type")})
        if act == "detach":
            _need(attachment_id, "attachment_id")
            c.internal("DELETE", f"/file-storage/detach/{attachment_id}")
            return _ok({"detached": attachment_id})
        if act == "delete_file":
            _need(file_id, "file_id")
            c.internal("DELETE", f"/file-storage/{file_id}")
            return _ok({"deleted": file_id})
        raise ValueError(f"unknown action '{action}'")
    except Exception as exc:
        return _err(exc)


def register(mcp) -> None:
    mcp.tool()(files)
