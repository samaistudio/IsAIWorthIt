#!/usr/bin/env python3
"""IsAIWorthIt. Needs only Python 3.10+, no packages.

    python3 isaiworthit.py            open the dashboard (demo businesses, plus your company after a sync)
    python3 isaiworthit.py init       create isaiworthit.config.json (every connector is off until you turn it on)
    python3 isaiworthit.py sync       read all enabled connectors into data/company.sqlite and update the dashboard
    python3 isaiworthit.py sources    list every connector and whether it is on
    python3 isaiworthit.py reports    one file per reader (management, each team lead, everyone),
                                     each containing only what that reader may see, as .html and AI-ready .md
    python3 isaiworthit.py mcp        MCP server for AI assistants (stdio; add --view management for costs)
    python3 isaiworthit.py site DIR   build the public demo website (demo data only) into DIR
                                     (DIR must be new, empty or an earlier site: it is emptied first)
"""
import functools
import http.server
import json
import secrets
import shutil
import socket
import sys
import threading
import webbrowser
from datetime import datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parent
WEB, DATA = ROOT / "web", ROOT / "data"
CONFIG = ROOT / "isaiworthit.config.json"
sys.path.insert(0, str(ROOT))


def load_config():
    if not CONFIG.exists():
        return None
    return json.loads(CONFIG.read_text())


def write_registry(cfg):
    from core.connectors import REGISTRY
    on = (cfg or {}).get("connectors", {})
    log = {}
    db = DATA / "company.sqlite"
    if db.exists():
        import sqlite3
        log = {r[0]: {"at": r[1], "ok": r[2], "rows": r[3], "message": r[4]}
               for r in sqlite3.connect(db).execute("SELECT * FROM sync_log")}
    def sample(key):  # fed with one of the example files in examples/, not a real export
        c = on.get(key, {})
        files = c.get("files") or [f for f in (c.get("file"), c.get("path")) if f]
        return any(str(f).replace("\\", "/").startswith("examples/") for f in files)

    out = [{k: v for k, v in c.items() if k != "run"} | {"enabled": bool(on.get(c["key"], {}).get("enabled")),
                                                         "last": log.get(c["key"]), "sample": sample(c["key"])}
           for c in REGISTRY.values()]
    (WEB / "data").mkdir(parents=True, exist_ok=True)
    (WEB / "data" / "connectors.json").write_text(json.dumps(out, indent=1))
    return out


def build_demo():
    """Writes the 10 fictional demo businesses. Your own company (your-company.json, from sync)
    is kept separately and never added to this list, so it can't end up in the repository."""
    from core.smb_metrics import export_all
    return export_all(WEB / "data" / "businesses")


def init():
    if CONFIG.exists():
        print(f"{CONFIG.name} already exists – edit it to turn connectors on.")
        return
    shutil.copy(ROOT / "isaiworthit.config.example.json", CONFIG)
    print(f"Created {CONFIG.name}. Every connector is off. Set \"enabled\": true for the ones you want, then run: python3 isaiworthit.py sync")


def sync():
    from core.connectors import REGISTRY, Store
    from core.company_metrics import build
    cfg = load_config()
    if not cfg:
        raise SystemExit("No config yet. Run: python3 isaiworthit.py init")
    DATA.mkdir(exist_ok=True)
    salt_file = DATA / ".salt"
    if not salt_file.exists():
        salt_file.write_text(secrets.token_hex(16))
    store = Store(DATA / "company.sqlite", salt_file.read_text())
    enabled = [(k, c) for k, c in cfg.get("connectors", {}).items() if c.get("enabled")]
    if not enabled:
        print("No connector is enabled in isaiworthit.config.json.")
    for key, ccfg in enabled:
        if key not in REGISTRY:
            print(f"  ? {key}: unknown connector, skipped")
            continue
        try:
            n = REGISTRY[key]["run"](store, ccfg)
            store.con.execute("INSERT OR REPLACE INTO sync_log VALUES (?,?,?,?,?)", (key, datetime.now().isoformat(timespec="seconds"), 1, n, ""))
            print(f"  ✓ {REGISTRY[key]['label']}: {n} rows")
        except Exception as e:  # one failing source never stops the others
            store.con.execute("INSERT OR REPLACE INTO sync_log VALUES (?,?,?,?,?)", (key, datetime.now().isoformat(timespec="seconds"), 0, 0, str(e)[:300]))
            print(f"  ✗ {REGISTRY[key]['label']}: {e}")
        store.con.commit()
    data = build(DATA / "company.sqlite", cfg)
    (WEB / "data" / "businesses").mkdir(parents=True, exist_ok=True)
    (WEB / "data" / "businesses" / "your-company.json").write_text(json.dumps(data, ensure_ascii=False, indent=1))
    build_demo()
    write_registry(cfg)
    print(f"Done: {data['people']} people, {data['current']['active_users']} active in {data['month']}. Open the dashboard: python3 isaiworthit.py")


def sources():
    for c in write_registry(load_config()):
        print(f"  [{'on ' if c['enabled'] else 'off'}] {c['label']:<46} {c['kind']:<8} {'tested' if c['status'] == 'tested' else 'from docs'}")


def reports():
    from core.views import write_reports
    cfg = load_config()
    if not cfg or not (DATA / "company.sqlite").exists():
        raise SystemExit("Run init and sync first.")
    made, skipped = write_reports(DATA / "company.sqlite", cfg, WEB, ROOT / "reports")
    for name, readers in made:
        print(f"  reports/{name}.html + .md  →  {', '.join(readers)}")
    for s in skipped:
        print(f"  skipped: {s}")
    print("See reports/README.md for who gets which file.")


def site_dir_problem(out: Path):
    """The site folder is emptied first, so only accept a new or empty folder or an earlier site."""
    if out in (ROOT, Path.home(), Path(out.anchor)) or out in ROOT.parents:
        return f"Refusing to use {out} as the site folder. Pick a new folder, for example _site."
    if out.exists() and (not out.is_dir() or (any(out.iterdir()) and not (out / ".nojekyll").exists())):
        return f"{out} is not empty and is not an earlier IsAIWorthIt site. Pick a new or empty folder."
    return None


def site():
    """Static demo website: the dashboard with the 10 fictional businesses, plus the tutorial.
    Never includes your own company or config."""
    out = Path(next((a for a in sys.argv[2:] if not a.startswith("--")), "_site")).expanduser().resolve()
    problem = site_dir_problem(out)
    if problem:
        raise SystemExit(problem)
    shutil.rmtree(out, ignore_errors=True)
    (out / "data").mkdir(parents=True)
    shutil.copy(WEB / "index.html", out / "index.html")
    from core.smb_metrics import export_all
    from core.connectors import REGISTRY
    n = export_all(out / "data" / "businesses")
    (out / "data" / "connectors.json").write_text(json.dumps(
        [{k: v for k, v in c.items() if k != "run"} | {"enabled": False, "last": None} for c in REGISTRY.values()], indent=1))
    if (WEB / "img").exists():
        shutil.copytree(WEB / "img", out / "img")  # Odoo screenshots for the "Inside Odoo" page
    shutil.copytree(ROOT / "docs" / "tutorial", out / "tutorial")
    (out / ".nojekyll").write_text("")
    print(f"Demo site with {len(n)} businesses written to {out}")


def mcp():
    from core.mcp_server import run
    build_demo()
    view = "management" if "management" in sys.argv else "everyone"
    run(WEB, view)


def free_port(preferred=8765):
    for port in [preferred] + list(range(8766, 8800)):
        with socket.socket() as s:
            if s.connect_ex(("127.0.0.1", port)):
                return port
    raise SystemExit("No free port between 8765 and 8799.")


def serve():
    businesses = build_demo()
    write_registry(load_config())
    port = free_port()
    handler = functools.partial(http.server.SimpleHTTPRequestHandler, directory=str(WEB))
    http.server.ThreadingHTTPServer.allow_reuse_address = True
    server = http.server.ThreadingHTTPServer(("127.0.0.1", port), lambda *a: handler(*a))
    url = f"http://127.0.0.1:{port}/"
    print(f"IsAIWorthIt is running at {url} ({len(businesses)} businesses). Press Ctrl+C to stop.", flush=True)
    if "--no-open" not in sys.argv:
        threading.Timer(0.6, lambda: webbrowser.open(url)).start()
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\nStopped.")


if __name__ == "__main__":
    cmd = next((a for a in sys.argv[1:] if not a.startswith("--")), "serve")
    {"init": init, "sync": sync, "sources": sources, "reports": reports, "serve": serve, "site": site, "mcp": mcp}.get(cmd, lambda: print(__doc__))()
