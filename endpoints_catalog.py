"""Searchable catalog of the KeyCRM internal endpoints.

endpoints.json was extracted from the production SPA bundle (build v33.0.10):
each entry is {"method", "path", "file"} keyed by the JS client method name.
"""

from __future__ import annotations

import json
import os
from typing import Any

_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "endpoints.json")


class Catalog:
    def __init__(self, path: str = _PATH):
        self.path = path
        self._rows: list[dict[str, Any]] = []
        self._load()

    def _load(self) -> None:
        with open(self.path, encoding="utf-8") as fh:
            raw = json.load(fh)
        rows = []
        for name, value in raw.items():
            path = str(value.get("path", ""))
            top = path.strip("/").split("/")[0] or "root"
            rows.append({
                "name": name,
                "method": str(value.get("method", "GET")).upper(),
                "path": path,
                "group": top,
            })
        rows.sort(key=lambda r: (r["group"], r["path"]))
        self._rows = rows

    @property
    def size(self) -> int:
        return len(self._rows)

    def groups(self) -> list[str]:
        return sorted({r["group"] for r in self._rows})

    def search(self, query: str = "", group: str = "", limit: int = 40) -> list[dict]:
        q = (query or "").strip().lower()
        g = (group or "").strip().lower()
        out = []
        for row in self._rows:
            if g and row["group"].lower() != g:
                continue
            if q and q not in row["path"].lower() and q not in row["name"].lower():
                continue
            out.append(row)
            if len(out) >= limit:
                break
        return out


catalog = Catalog()
