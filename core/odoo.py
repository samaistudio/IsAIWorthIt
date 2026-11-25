"""Minimal client for Odoo's external JSON-RPC API (works with Odoo Community, no add-ons).
Used by the Odoo connector in core/connectors/company.py.

Uses the /jsonrpc endpoint, which fits Odoo 18. Odoo 19 and later move to /json/2 with API keys."""
import json
import urllib.request


class Odoo:
    def __init__(self, url, db, user, password):
        self.url, self.db, self.password = url.rstrip("/"), db, password
        self.uid = self._call("common", "login", db, user, password)
        if not self.uid:
            raise RuntimeError("Odoo login failed")

    def _call(self, service, method, *args):
        body = json.dumps({"jsonrpc": "2.0", "method": "call", "id": 1,
                           "params": {"service": service, "method": method, "args": args}}).encode()
        req = urllib.request.Request(f"{self.url}/jsonrpc", body, {"Content-Type": "application/json"})
        with urllib.request.urlopen(req, timeout=600) as r:
            res = json.load(r)
        if res.get("error"):
            raise RuntimeError(res["error"].get("data", {}).get("message") or res["error"])
        return res["result"]

    def x(self, model, method, *args, **kw):
        return self._call("object", "execute_kw", self.db, self.uid, self.password, model, method, list(args), kw)
