"""Rebuilds assets/og.html from endpoints.json. Then render it to og.png:
chrome --headless --screenshot=assets/og.png --window-size=1280,640 assets/og.html
"""
import html
import json
import pathlib

root = pathlib.Path(__file__).resolve().parent.parent
routes = json.loads((root / "endpoints.json").read_text(encoding="utf-8"))
seen, rows = set(), []
for value in routes.values():
    method, path = str(value["method"]).upper(), str(value["path"])
    if (method, path) in seen or len(path) > 30 or "{" not in path and len(path) < 9:
        continue
    seen.add((method, path))
    rows.append((method, path))
rows = rows[::11][:24]
cells = "".join(f"<li><b>{m}</b>{html.escape(p)}</li>" for m, p in rows)

page = f"""<!doctype html>
<html lang="uk"><head><meta charset="utf-8"><title>keycrm-mcp</title><style>
@font-face{{font-family:Geist;src:url("fonts/geist.woff2") format("woff2");font-weight:100 900}}
*{{box-sizing:border-box;margin:0;padding:0}}
body{{width:1280px;height:640px;overflow:hidden;background:#100f0d;color:#ece7dd;font-family:Geist,system-ui,sans-serif;position:relative}}
.grain{{position:absolute;inset:0;opacity:.3;background-image:url("data:image/svg+xml,%3Csvg xmlns='http://www.w3.org/2000/svg' width='160' height='160'%3E%3Cfilter id='n'%3E%3CfeTurbulence type='fractalNoise' baseFrequency='.85' numOctaves='3'/%3E%3C/filter%3E%3Crect width='160' height='160' filter='url(%23n)' opacity='.5'/%3E%3C/svg%3E")}}
.routes{{position:absolute;top:-22px;left:908px;width:330px;list-style:none;font:14px/30px ui-monospace,Consolas,monospace;color:#7a7468;white-space:nowrap;
  -webkit-mask-image:linear-gradient(180deg,transparent 0%,rgba(0,0,0,.12) 6%,rgba(0,0,0,.4) 12%,rgba(0,0,0,.8) 19%,#000 26%,#000 74%,rgba(0,0,0,.8) 81%,rgba(0,0,0,.4) 88%,rgba(0,0,0,.12) 94%,transparent 100%);mask-image:linear-gradient(180deg,transparent 0%,rgba(0,0,0,.12) 6%,rgba(0,0,0,.4) 12%,rgba(0,0,0,.8) 19%,#000 26%,#000 74%,rgba(0,0,0,.8) 81%,rgba(0,0,0,.4) 88%,rgba(0,0,0,.12) 94%,transparent 100%)}}
.routes b{{display:inline-block;width:66px;font-weight:400;color:#b3a57f}}
.frame{{position:relative;height:100%;padding:68px 80px 64px;display:flex;flex-direction:column}}
.mark{{font-weight:700;font-size:24px;letter-spacing:-.01em}}
.mark span{{color:#d9c79a}}
h1{{font-weight:800;font-size:58px;line-height:1.08;letter-spacing:-.03em;margin-top:auto}}
h1 em{{font-style:normal;color:#d9c79a}}
p{{margin-top:24px;font-size:25px;line-height:1.4;color:#a09a8e}}
.row{{margin-top:44px;display:flex;gap:56px;align-items:baseline}}
.row div{{display:flex;gap:12px;align-items:baseline}}
.row b{{font-weight:700;font-size:34px;letter-spacing:-.02em}}
.row span{{font-size:18px;color:#8f897d}}
</style></head>
<body>
<div class="grain"></div>
<ul class="routes">{cells}</ul>
<div class="frame">
  <div class="mark">keycrm<span>-mcp</span></div>
  <h1>Агент бачить усю KeyCRM,<br><em>а не лише офіційний API</em></h1>
  <p>Відкритий MCP-сервер для KeyCRM</p>
  <div class="row">
    <div><b>24</b><span>інструменти</span></div>
    <div><b>572</b><span>маршрути внутрішнього API</span></div>
    <div><b>MIT</b><span>безкоштовно</span></div>
  </div>
</div>
</body></html>
"""
(root / "assets" / "og.html").write_text(page, encoding="utf-8")
print(len(rows), "routes")
