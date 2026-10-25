"""Run:  python -m unittest tests -v      (needs Chromium for the end-to-end tests)"""
import http.server
import socket
import threading
import unittest

import requests
from werkzeug.serving import make_server

import checks
import scoring
from analyzer import HostGuard, UnsafeURL, base_domain, detonate
from egress_proxy import EgressProxy, default_blocked
from pipeline import analyze_url


class GateTests(unittest.TestCase):
    def test_rejects_internal_and_odd_schemes(self):
        g = HostGuard(False)
        for u in ["http://127.0.0.1/", "http://169.254.169.254/latest/meta-data/", "http://10.0.0.5/",
                  "http://[::1]/", "http://192.168.1.1/", "http://100.64.0.1/",
                  "file:///etc/passwd", "ftp://example.com/", "javascript:alert(1)"]:
            with self.assertRaises(UnsafeURL, msg=u):
                g.validate_url(u)

    def test_base_domain(self):
        self.assertEqual(base_domain("a.b.example.com"), "example.com")
        self.assertEqual(base_domain("shop.example.co.uk"), "example.co.uk")
        self.assertEqual(base_domain("127.0.0.1"), "127.0.0.1")


class _Hello(http.server.BaseHTTPRequestHandler):
    def do_GET(self):
        self.send_response(200); self.send_header("Content-Length", "5"); self.end_headers(); self.wfile.write(b"hello")

    def log_message(self, *a):
        pass


class ProxyTests(unittest.TestCase):
    def setUp(self):
        self.srv = http.server.ThreadingHTTPServer(("127.0.0.1", 0), _Hello)
        self.port = self.srv.server_address[1]
        threading.Thread(target=self.srv.serve_forever, daemon=True).start()

    def tearDown(self):
        self.srv.shutdown()
        self.srv.server_close()

    def test_default_policy_blocks_loopback_http_and_connect(self):
        p = EgressProxy().start()
        try:
            proxies = {"http": "http://127.0.0.1:%d" % p.port}
            r = requests.get("http://127.0.0.1:%d/" % self.port, proxies=proxies, timeout=5)
            self.assertEqual(r.status_code, 403)
            with socket.create_connection(("127.0.0.1", p.port), timeout=5) as s:
                s.sendall(b"CONNECT 127.0.0.1:%d HTTP/1.1\r\nHost: x\r\n\r\n" % self.port)
                self.assertIn(b"403", s.recv(100))
            self.assertEqual(len(p.blocked_log), 2)
        finally:
            p.stop()

    def test_allowed_destination_is_forwarded(self):
        p = EgressProxy(blocked=lambda h, ip: False).start()
        try:
            r = requests.get("http://127.0.0.1:%d/" % self.port, proxies={"http": "http://127.0.0.1:%d" % p.port}, timeout=5)
            self.assertEqual((r.status_code, r.text), (200, "hello"))
            with socket.create_connection(("127.0.0.1", p.port), timeout=5) as s:   # CONNECT tunnel
                s.sendall(b"CONNECT 127.0.0.1:%d HTTP/1.1\r\nHost: x\r\n\r\n" % self.port)
                self.assertIn(b"200", s.recv(100))
                s.sendall(b"GET / HTTP/1.1\r\nHost: x\r\nConnection: close\r\n\r\n")
                self.assertIn(b"hello", s.recv(1000))
        finally:
            p.stop()

    def test_default_blocked_predicate(self):
        for ip in ["127.0.0.1", "10.1.2.3", "169.254.169.254", "::1", "192.168.0.9"]:
            self.assertTrue(default_blocked("h", ip), ip)
        self.assertFalse(default_blocked("h", "8.8.8.8"))


class CheckTests(unittest.TestCase):
    def _ev(self, **kw):
        ev = {"input_url": "https://x.test/", "final_url": "https://x.test/", "headers": {"content-type": "text/html"},
              "redirect_chain": [], "navigations": [], "requests": [], "blocked_requests": [], "scripts": [],
              "inline_scripts": [], "downloads": [], "popups": [], "dialogs": [], "cookies": [], "forms": [],
              "iframes": [], "meta_refresh": [], "password_fields": 0, "error": None, "tls": None}
        ev.update(kw)
        return ev

    def test_vulnerable_libraries(self):
        s = [{"url": "https://cdn.x/jquery-1.12.4.min.js", "source": ""},
             {"url": "https://cdn.x/app.js", "source": "/*! jQuery v3.7.1 | */"},
             {"url": "https://cdn.x/b.js", "source": "/*! Bootstrap v3.3.7 */"},
             {"url": "https://cdn.x/lodash.4.17.21.js", "source": ""}]
        names = [f["title"] for f in checks.check_libraries(self._ev(scripts=s))]
        self.assertTrue(any("jQuery 1.12.4" in n for n in names))
        self.assertTrue(any("Bootstrap 3.3.7" in n for n in names))
        self.assertFalse(any("3.7.1" in n for n in names))
        self.assertFalse(any("lodash" in n for n in names))

    def test_script_rules(self):
        src = "eval(atob('abc'));var a='CoinHive';" + "var _0x1a2b=1;" * 12
        ids = {f["id"] for f in checks.check_scripts(self._ev(inline_scripts=[src]))}
        self.assertTrue({"script.eval_decode", "script.miner", "script.hex_obfuscation"} <= ids)
        self.assertNotIn("script.eval", ids)

    def test_disguised_executable(self):
        d = [{"filename": "invoice.pdf", "size": 10, "sha256": "ab" * 32, "magic": "Windows executable (PE)"}]
        ids = {f["id"] for f in checks.check_downloads(self._ev(downloads=d))}
        self.assertIn("download.disguised", ids)

    def test_virustotal_parser(self):
        mk = lambda m, s: {"data": {"attributes": {"last_analysis_stats": {"malicious": m, "suspicious": s, "harmless": 60}}}}
        self.assertEqual(checks._vt_findings(200, mk(12, 0))[0]["severity"], "critical")
        self.assertEqual(checks._vt_findings(200, mk(2, 0))[0]["severity"], "high")
        self.assertEqual(checks._vt_findings(200, mk(0, 0))[0]["severity"], "info")
        self.assertEqual(checks._vt_findings(404, {})[0]["id"], "reputation.vt_unknown")
        self.assertEqual(checks._gsb_findings({})[0:0], [])
        self.assertEqual(checks._gsb_findings({"matches": [{"threatType": "MALWARE"}]})[0]["severity"], "critical")

    def test_scoring_is_bounded_and_monotonic(self):
        one = [checks.finding("a.b", "threat", "high", "t", confidence=0.8)]
        two = one + [checks.finding("a.c", "threat", "high", "t", confidence=0.8)]
        many = [checks.finding("a.%d" % i, "threat", "critical", "t", confidence=1.0) for i in range(30)]
        a, b, c = (scoring.group_score(x, "threat") for x in (one, two, many))
        self.assertTrue(0 < a < b < c <= 100)
        self.assertEqual(scoring.group_score([], "threat"), 0)


class EndToEnd(unittest.TestCase):
    """Starts the harmless demo site and runs the real browser pipeline against it."""

    @classmethod
    def setUpClass(cls):
        import demo_server
        cls.srv = make_server("127.0.0.1", demo_server.PORT, demo_server.app, threaded=True)
        threading.Thread(target=cls.srv.serve_forever, daemon=True).start()

    @classmethod
    def tearDownClass(cls):
        cls.srv.shutdown()

    def test_clean_page_scores_low(self):
        r, shot = analyze_url("http://localhost:8001/safe", allow_private=True)
        self.assertEqual(r["threat_level"], "Low")
        self.assertLess(r["threat_score"], 15)
        self.assertTrue(shot and shot[:4] == b"\x89PNG")

    def test_scam_page_is_critical_with_expected_findings(self):
        r, _ = analyze_url("http://localhost:8001/gift", allow_private=True)
        ids = {f["id"] for f in r["findings"]}
        self.assertEqual(r["threat_level"], "Critical")
        for expected in ["download.executable", "script.miner", "script.eval_decode", "form.password_cross_domain",
                         "form.password_over_http", "redirect.long_chain", "iframe.hidden", "dialog.alert",
                         "library.vulnerable", "header.csp"]:
            self.assertIn(expected, ids)
        self.assertEqual(r["evidence"]["downloads"][0]["filename"], "giftcard.exe")

    def test_private_target_refused_when_not_allowed(self):
        with self.assertRaises(UnsafeURL):
            detonate("http://localhost:8001/safe", allow_private=False)

    def test_redirect_hop_to_internal_host_is_blocked(self):
        ev, _ = detonate("http://localhost:8001/gift", allow_private=True,
                         egress_blocked=lambda host, ip: host == "127.0.0.1")
        self.assertEqual(ev["redirect_chain"][-1]["status"], 403)
        self.assertTrue(ev["blocked_requests"])
        self.assertIn("network.internal_probe", {f["id"] for f in checks.run_all(ev)})


if __name__ == "__main__":
    unittest.main(verbosity=2)
