"""Assemble the single-file page (index.html) and a locally testable wrapper."""
import json
from pathlib import Path

P = Path("/home/claude/chess_sim/page")
css = (P / "style.css").read_text()
body = (P / "body.html").read_text()
core = (P / "core.js").read_text()
app = (P / "app.js").read_text()
data = json.dumps(json.load(open(P / "data.json")), ensure_ascii=False, separators=(",", ":")).replace("<", "\\u003c")

head = (
    '<title>Thresholds, Risk and Settlement</title>\n'
    '<link rel="stylesheet" href="https://fonts.googleapis.com/css2?family=IBM+Plex+Mono:wght@400;500&family=Public+Sans:wght@400;500;600;700&display=swap">\n'
    f"<style>\n{css}\n</style>\n"
)
page = head + body + f"\n<script>window.__DATA__={data};</script>\n<script>\n{core}\n</script>\n<script>\n{app}\n</script>\n"
(P / "index.html").write_text(page)

# local wrapper mimicking the publish skeleton
skeleton = ('<!doctype html><html lang="en"><head><meta charset="utf-8">'
            '<meta name="viewport" content="width=device-width,initial-scale=1,viewport-fit=cover">'
            '<style>:root{color-scheme:light;padding-top:env(safe-area-inset-top,0px);padding-bottom:env(safe-area-inset-bottom,0px)}'
            'body{margin:0;font:14px system-ui,sans-serif;background:#f9f9f7}img{max-width:100%}[hidden]{display:none!important}</style>'
            "</head><body>")
(P / "test.html").write_text(skeleton + page + "</body></html>")
print("index.html", round(len(page) / 1024), "KB")
