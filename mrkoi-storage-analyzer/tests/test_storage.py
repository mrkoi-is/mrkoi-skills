"""Regression tests use isolated temporary files only; no real cleanup occurs."""
import http.client
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import threading
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
import scan
import server
from build_report import render_report


class StorageTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory(prefix="mrkoi-storage-test-")
        self.root = Path(self.tmp.name).resolve()
        self.addCleanup(self.tmp.cleanup)

    def test_explicit_scan_real_du_and_symlink_boundary(self):
        fixture = self.root / "scan"
        fixture.mkdir()
        (fixture / "small.bin").write_bytes(b"s" * 4096)
        (fixture / "big.bin").write_bytes(b"b" * 262144)
        (fixture / "link").symlink_to(fixture / "big.bin")
        result = subprocess.run([sys.executable, str(ROOT / "scripts/scan.py"),
                                 "--path", str(fixture), "--min-kb", "0", "--limit", "1"],
                                capture_output=True, text=True, check=True)
        data = json.loads(result.stdout)
        rows = data["groups"][str(fixture)]
        self.assertEqual([r["name"] for r in rows], ["big.bin"])
        self.assertGreater(rows[0]["size_kb"], 0)
        self.assertEqual(data["scope"], [str(fixture)])

    def test_scan_requires_scope(self):
        result = subprocess.run([sys.executable, str(ROOT / "scripts/scan.py")],
                                capture_output=True, text=True)
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("--path", result.stderr)

    def test_partial_du_is_retained_below_floor(self):
        (self.root / "partial").mkdir()
        partial = subprocess.CompletedProcess([], 1, "4\tpartial\n", "Permission denied")
        with patch.object(scan.subprocess, "run", return_value=partial):
            rows = scan.du_children(str(self.root), min_kb=1024)
        self.assertEqual(len(rows), 1)
        self.assertTrue(rows[0]["incomplete"])
        self.assertTrue(rows[0]["denied"])
        self.assertEqual(rows[0]["size_kb"], 4)

    def test_timeout_is_unknown_not_zero(self):
        with patch.object(scan.subprocess, "run", side_effect=subprocess.TimeoutExpired("du", 1)):
            item = scan.du_entry(str(self.root))
        self.assertTrue(item["incomplete"])
        self.assertIsNone(item["size_kb"])

    def test_static_report_real_cli_escapes_script_terminator(self):
        payload = '</script><script>alert("x")</script> __DELETE_CONFIG__ & 中文'
        src, output = self.root / "analysis.json", self.root / "report.html"
        src.write_text(json.dumps({"system": {"os": payload}}, ensure_ascii=False))
        subprocess.run([sys.executable, str(ROOT / "scripts/build_report.py"),
                        str(src), str(output)], check=True, capture_output=True)
        html = output.read_text()
        self.assertIn("const DELETE = null;", html)
        self.assertNotIn('</script><script>alert', html)
        self.assertIn('\\u003c/script\\u003e', html)
        self.assertIn('__DELETE_CONFIG__ &', payload)
        self.assertIn('__DELETE_CONFIG__ \\u0026', html)

    def report(self):
        first, second = self.root / "cache-one", self.root / "cache-two"
        first.mkdir(exist_ok=True)
        second.mkdir(exist_ok=True)
        (first / "sentinel").write_text("must remain")
        data = {"system": {}, "green": [{"trash_paths": [str(first), str(second)]}]}
        path = self.root / "analysis.json"
        path.write_text(json.dumps(data))
        return path, str(first), str(second)

    def test_cleanup_is_opt_in_and_explicit_path_intersection(self):
        path, first, second = self.report()
        result = subprocess.run([sys.executable, str(ROOT / "scripts/server.py"), str(path)],
                                capture_output=True, text=True)
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("--enable-cleanup", result.stderr)
        with patch.object(server, "HOME", str(self.root)):
            data, _, rm, trash, _ = server.load(path, [first])
            self.assertEqual(trash, {first})
            self.assertEqual(rm, set())
            self.assertEqual(data["green"][0]["trash_paths"], [first])
            self.assertEqual(server.load(path, [first], True)[2], {first})
            with self.assertRaises(ValueError):
                server.load(path, [str(self.root)])
            with self.assertRaises(ValueError):
                server.load(path, ["/Applications"])
            with self.assertRaises(ValueError):
                server.load(path, [str(self.root / "unlisted")])

    def test_http_batch_prevalidation_and_default_no_permanent_delete(self):
        path, first, second = self.report()
        with patch.object(server, "HOME", str(self.root)):
            loaded = server.load(path, [first])
            names = ["DATA", "TPL", "RM_ALLOW", "TRASH_ALLOW", "OPEN_ALLOW"]
            with patch.multiple(server, **dict(zip(names, loaded))), patch.object(server, "move_to_trash") as move:
                httpd = server.ThreadingHTTPServer(("127.0.0.1", 0), server.Handler)
                thread = threading.Thread(target=httpd.serve_forever, daemon=True)
                thread.start()
                try:
                    def request(mode, paths):
                        conn = http.client.HTTPConnection("127.0.0.1", httpd.server_port)
                        conn.request("POST", "/action", json.dumps({"token": server.TOKEN, "mode": mode, "paths": paths}), {"Content-Type": "application/json"})
                        response = conn.getresponse()
                        status = response.status
                        body = json.loads(response.read())
                        conn.close()
                        return status, body
                    self.assertEqual(request("trash", [first, second])[0], 403)
                    move.assert_not_called()
                    self.assertEqual(request("rm", [first])[0], 403)
                    self.assertEqual(request("trash", [first])[0], 200)
                    move.assert_called_once_with(first)
                    self.assertEqual((Path(first) / "sentinel").read_text(), "must remain")
                finally:
                    httpd.shutdown()
                    httpd.server_close()
                    thread.join()

    def test_finder_failure_does_not_fallback_to_move(self):
        failure = subprocess.CompletedProcess([], 1, "", "cancelled")
        with patch.object(server.subprocess, "run", return_value=failure), patch.object(server.shutil, "move") as move:
            with self.assertRaises(OSError):
                server._trash_macos(str(self.root / "fixture"))
            move.assert_not_called()


if __name__ == "__main__":
    unittest.main()
