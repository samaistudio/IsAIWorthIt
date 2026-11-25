"""MCP server: lets an AI assistant (Claude Desktop, Claude Code, Cursor, ...) ask IsAIWorthIt questions.

Speaks the Model Context Protocol over stdio (JSON-RPC 2.0, one message per line). Python standard
library only. It is read-only and serves the same per-reader views as the report files:

    --view everyone     (default) company summary only: no costs, no teams, no business numbers
    --view management   everything the management dashboard shows

Nothing about individual people exists in the data, so nothing about individuals can be asked.
"""
import json
import sys
from pathlib import Path

from .views import for_everyone, for_management, markdown

PROTOCOL = "2025-06-18"
SUPPORTED = (PROTOCOL, "2025-03-26", "2024-11-05")
VERSION = "0.2.0"


class Data:
    def __init__(self, web: Path, view: str):
        self.dir, self.view = web / "data" / "businesses", view

    def _load(self, slug):
        # only slugs from list_businesses: the name is never used as a free path
        if not isinstance(slug, str) or slug not in {b["slug"] for b in self.businesses()}:
            raise ValueError(f"Unknown business '{slug}'. Call list_businesses first.")
        full = json.loads((self.dir / f"{slug}.json").read_text())
        return for_management(full) if self.view == "management" else for_everyone(full)

    def businesses(self):
        out = []
        if (self.dir / "your-company.json").exists():
            d = json.loads((self.dir / "your-company.json").read_text())
            out.append({"slug": "your-company", "name": d["name"], "industry": d.get("industry"), "people": d["people"], "demo": False})
        idx = self.dir / "index.json"
        out += [{**b, "demo": True} for b in (json.loads(idx.read_text()) if idx.exists() else [])]
        return out

    def get(self, slug):
        return self._load(slug)


def _month(d, month):
    m = next((m for m in d["months"] if m["month"] == month), None)
    if not m:
        raise ValueError(f"No data for {month}. Available: {', '.join(x['month'] for x in d['months'])}")
    return m


TOOLS = [
    {"name": "list_businesses", "description": "List the businesses available (your own company after a sync, plus 10 fictional demo businesses).",
     "inputSchema": {"type": "object", "properties": {}}},
    {"name": "get_report", "description": "The AI-use report for one business as plain text: hours saved, value, licence costs, net benefit, tasks, tools, teams and how the numbers were estimated. What is included depends on the server's view (everyone or management).",
     "inputSchema": {"type": "object", "properties": {"business": {"type": "string", "description": "slug from list_businesses"}}, "required": ["business"]}},
    {"name": "get_month", "description": "Numbers for one month (YYYY-MM): active users, hours saved, value in euros and, in the management view, licence costs and net benefit.",
     "inputSchema": {"type": "object", "properties": {"business": {"type": "string"}, "month": {"type": "string", "pattern": "^\\d{4}-\\d{2}$"}}, "required": ["business", "month"]}},
    {"name": "compare_months", "description": "Change between two months (YYYY-MM) for every number available in the current view.",
     "inputSchema": {"type": "object", "properties": {"business": {"type": "string"}, "from_month": {"type": "string"}, "to_month": {"type": "string"}}, "required": ["business", "from_month", "to_month"]}},
    {"name": "licence_check", "description": "Management view only: every AI tool with seats, active users, unused seats and what unused seats cost per month.",
     "inputSchema": {"type": "object", "properties": {"business": {"type": "string"}}, "required": ["business"]}},
    {"name": "how_it_measures", "description": "How the time saved was estimated for this business: benchmark minutes per AI action, the staff-survey calibration factor and before/after business evidence.",
     "inputSchema": {"type": "object", "properties": {"business": {"type": "string"}}, "required": ["business"]}},
]


REQUIRED = {t["name"]: t["inputSchema"].get("required", []) for t in TOOLS}
HINTS = {"month": " (YYYY-MM)", "from_month": " (YYYY-MM)", "to_month": " (YYYY-MM)", "business": " (slug from list_businesses)"}


def call(data: Data, name: str, args: dict):
    if name not in REQUIRED:
        raise ValueError(f"Unknown tool '{name}'")
    if not isinstance(args, dict):
        raise ValueError("Arguments must be an object")
    for key in REQUIRED[name]:
        if key not in args:
            raise ValueError(f"Missing argument '{key}'{HINTS.get(key, '')}")
    if name == "list_businesses":
        return data.businesses()
    d = data.get(args.get("business", ""))
    if name == "get_report":
        return markdown(d)
    if name == "get_month":
        return _month(d, args["month"])
    if name == "compare_months":
        a, b = _month(d, args["from_month"]), _month(d, args["to_month"])
        return {k: {"from": a[k], "to": b[k], "change": round(b[k] - a[k], 2)} for k in b if k != "month" and isinstance(b[k], (int, float))}
    if name == "licence_check":
        if data.view != "management":
            raise ValueError("Licence costs are only available in the management view (start the server with --view management).")
        return {"tools": d["tools"], "tips": [t["text"] for t in d.get("tips", [])]}
    if name == "how_it_measures":
        return d["measurement"]
    raise ValueError(f"Unknown tool '{name}'")


def handle(data: Data, msg):
    if not isinstance(msg, dict):  # e.g. a JSON-RPC batch [..] or a bare value: not supported
        return {"jsonrpc": "2.0", "id": None, "error": {"code": -32600, "message": "Invalid Request"}}
    method, mid = msg.get("method"), msg.get("id")
    if mid is None:  # notification, e.g. notifications/initialized
        return None
    if method == "initialize":
        asked = (msg.get("params") or {}).get("protocolVersion")
        result = {"protocolVersion": asked if asked in SUPPORTED else PROTOCOL,
                  "capabilities": {"tools": {}},
                  "serverInfo": {"name": "isaiworthit", "version": VERSION},
                  "instructions": f"Read-only AI-adoption numbers for small businesses ({data.view} view). Start with list_businesses."}
    elif method == "ping":
        result = {}
    elif method == "tools/list":
        result = {"tools": TOOLS}
    elif method == "tools/call":
        p = msg.get("params") or {}
        try:
            out = call(data, p.get("name"), p.get("arguments") or {})
            text = out if isinstance(out, str) else json.dumps(out, indent=1, ensure_ascii=False)
            result = {"content": [{"type": "text", "text": text}], "isError": False}
        except (ValueError, KeyError) as e:
            result = {"content": [{"type": "text", "text": f"Error: {e}"}], "isError": True}
        except Exception as e:  # one bad call must never stop the server
            result = {"content": [{"type": "text", "text": f"Error: {type(e).__name__}: {e}"}], "isError": True}
    else:
        return {"jsonrpc": "2.0", "id": mid, "error": {"code": -32601, "message": f"Method not found: {method}"}}
    return {"jsonrpc": "2.0", "id": mid, "result": result}


def run(web: Path, view: str = "everyone"):
    data = Data(web, view)
    for line in sys.stdin:
        if not line.strip():
            continue
        try:
            msg = json.loads(line)
        except json.JSONDecodeError:
            out = {"jsonrpc": "2.0", "id": None, "error": {"code": -32700, "message": "Parse error"}}
        else:
            try:
                out = handle(data, msg)
            except Exception as e:  # last guard: one bad message must never stop the server
                out = {"jsonrpc": "2.0", "id": msg.get("id") if isinstance(msg, dict) else None,
                       "error": {"code": -32603, "message": f"Internal error: {type(e).__name__}"}}
        if out is not None:
            sys.stdout.write(json.dumps(out, ensure_ascii=False) + "\n")
            sys.stdout.flush()
