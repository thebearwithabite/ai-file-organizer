#!/usr/bin/env python3
"""
Converts the FastAPI openapi.json file into a readable Markdown reference.

Usage:
    python scripts/generate_api_docs.py
"""

import json
import pathlib

spec_path = pathlib.Path("docs/openapi.json")
out_path = pathlib.Path("docs/API_Endpoints.md")

spec = json.loads(spec_path.read_text())

md = [
    "# 📘 API Endpoints Reference",
    "",
    f"Generated automatically from **{spec_path}**",
    "",
    f"**Title:** {spec['info'].get('title','N/A')}  ",
    f"**Version:** {spec['info'].get('version','N/A')}  ",
    "",
    "| Method | Path | Summary |",
    "|--------|------|----------|",
]

for path, methods in spec["paths"].items():
    for method, data in methods.items():
        md.append(
            f"| `{method.upper()}` | `{path}` | {data.get('summary','—')} |"
        )

out_path.write_text("\n".join(md))
print(f"✅ API documentation generated → {out_path}")
