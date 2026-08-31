#!/usr/bin/env bash
# Local preview of README.md rendered as GitHub-flavored markdown.
# Opens in the default browser. No deps beyond python3 + a CDN markdown renderer.
# Usage: scripts/preview.sh
set -euo pipefail
REPO_ROOT="$(git rev-parse --show-toplevel 2>/dev/null || pwd)"
README="$REPO_ROOT/README.md"
HTML="$REPO_ROOT/.preview.html"

python3 - "$README" "$HTML" <<'PY'
import json, pathlib, sys
readme, out = sys.argv[1], sys.argv[2]
body = pathlib.Path(readme).read_text(encoding="utf-8")
body_js = json.dumps(body)
html = f"""<!doctype html>
<html lang="en"><head><meta charset="utf-8"><title>README preview</title>
<script src="https://cdnjs.cloudflare.com/ajax/libs/marked/12.0.2/marked.min.js"></script>
<style>
  body {{ max-width: 980px; margin: 2rem auto; padding: 0 1rem;
         font-family: -apple-system, "Segoe UI", Ubuntu, sans-serif;
         color: #0a0a12; background: #fff; line-height: 1.5; }}
  img {{ max-width: 100%; }}
  table {{ border-collapse: collapse; }}
  td, th {{ border: 1px solid #ddd; padding: 6px 10px; }}
  code {{ background: #f4f4f5; padding: 2px 4px; border-radius: 3px; }}
  pre {{ background: #0a0a12; color: #f4f4f5; padding: 1rem; border-radius: 6px; overflow-x: auto; }}
  a {{ color: #ff6643; }}
  blockquote {{ border-left: 3px solid #ff6643; margin: 0; padding-left: 1rem; color: #555; }}
</style></head>
<body><div id="c"></div>
<script>
  const src = {body_js};
  document.getElementById('c').innerHTML = marked.parse(src);
</script></body></html>
"""
pathlib.Path(out).write_text(html, encoding="utf-8")
print(out)
PY

open "$HTML" 2>/dev/null || xdg-open "$HTML" 2>/dev/null || echo "Open manually: $HTML"
