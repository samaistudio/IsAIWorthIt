"""The MCP server answers over JSON-RPC and never crashes on bad input."""
import json
import shutil
import unittest

from tests.helpers import demo_web

from core.mcp_server import PROTOCOL, Data, handle


def call(data, name, **args):
    out = handle(data, {"jsonrpc": "2.0", "id": 1, "method": "tools/call", "params": {"name": name, "arguments": args}})
    return out["result"]


class McpServer(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.web = demo_web()
        cls.everyone = Data(cls.web, "everyone")
        cls.management = Data(cls.web, "management")

    @classmethod
    def tearDownClass(cls):
        shutil.rmtree(cls.web, ignore_errors=True)

    def test_initialize(self):
        out = handle(self.everyone, {"jsonrpc": "2.0", "id": 1, "method": "initialize", "params": {"protocolVersion": PROTOCOL}})
        self.assertEqual(out["result"]["protocolVersion"], PROTOCOL)
        self.assertEqual(out["result"]["serverInfo"]["name"], "isaiworthit")
        self.assertIn("tools", out["result"]["capabilities"])

    def test_unknown_protocol_version_gets_ours(self):
        out = handle(self.everyone, {"jsonrpc": "2.0", "id": 1, "method": "initialize", "params": {"protocolVersion": "1999-01-01"}})
        self.assertEqual(out["result"]["protocolVersion"], PROTOCOL)

    def test_notification_gets_no_answer(self):
        self.assertIsNone(handle(self.everyone, {"jsonrpc": "2.0", "method": "notifications/initialized"}))

    def test_tools_list(self):
        out = handle(self.everyone, {"jsonrpc": "2.0", "id": 2, "method": "tools/list"})
        names = {t["name"] for t in out["result"]["tools"]}
        self.assertEqual(names, {"list_businesses", "get_report", "get_month", "compare_months", "licence_check", "how_it_measures"})

    def test_list_and_report(self):
        r = call(self.everyone, "list_businesses")
        self.assertFalse(r["isError"])
        self.assertEqual(len(json.loads(r["content"][0]["text"])), 10)
        r = call(self.everyone, "get_report", business="tax-office")
        self.assertFalse(r["isError"])
        self.assertIn("Becker & Partner", r["content"][0]["text"])
        self.assertNotIn("Licence costs", r["content"][0]["text"])

    def test_bad_slugs_are_errors_not_crashes(self):
        for slug in ("../connectors", "../../../isaiworthit.config", "", "nope", None, 42):
            with self.subTest(slug=slug):
                r = call(self.management, "get_month", business=slug, month="2026-11")
                self.assertTrue(r["isError"])
                self.assertIn("Unknown business", r["content"][0]["text"])

    def test_bad_month_is_an_error(self):
        r = call(self.everyone, "get_month", business="hotel", month="2020-01")
        self.assertTrue(r["isError"])

    def test_missing_argument_is_an_error(self):
        r = call(self.everyone, "compare_months", business="hotel")
        self.assertTrue(r["isError"])

    def test_missing_month_says_which_argument(self):
        r = call(self.everyone, "get_month", business="hotel")
        self.assertTrue(r["isError"])
        self.assertEqual(r["content"][0]["text"], "Error: Missing argument 'month' (YYYY-MM)")

    def test_non_object_message_is_invalid_request(self):
        for msg in ([1], [], "x", 42, None):
            with self.subTest(msg=msg):
                out = handle(self.everyone, msg)
                self.assertEqual(out["error"]["code"], -32600)
                self.assertIsNone(out["id"])

    def test_run_keeps_going_after_a_bad_line(self):
        import io
        import sys
        from core.mcp_server import run
        lines = ['[1]', '"x"', 'not json', '{"jsonrpc": "2.0", "id": 7, "method": "ping"}']
        old_in, old_out = sys.stdin, sys.stdout
        sys.stdin, sys.stdout = io.StringIO("\n".join(lines) + "\n"), io.StringIO()
        try:
            run(self.web, "everyone")
            replies = [json.loads(x) for x in sys.stdout.getvalue().splitlines()]
        finally:
            sys.stdin, sys.stdout = old_in, old_out
        self.assertEqual([r.get("error", {}).get("code") for r in replies], [-32600, -32600, -32700, None])
        self.assertEqual(replies[-1], {"jsonrpc": "2.0", "id": 7, "result": {}})

    def test_licence_check_only_for_management(self):
        self.assertTrue(call(self.everyone, "licence_check", business="hotel")["isError"])
        r = call(self.management, "licence_check", business="hotel")
        self.assertFalse(r["isError"])
        self.assertIn("seats", r["content"][0]["text"])

    def test_unknown_method(self):
        out = handle(self.everyone, {"jsonrpc": "2.0", "id": 3, "method": "resources/list"})
        self.assertEqual(out["error"]["code"], -32601)


if __name__ == "__main__":
    unittest.main()
