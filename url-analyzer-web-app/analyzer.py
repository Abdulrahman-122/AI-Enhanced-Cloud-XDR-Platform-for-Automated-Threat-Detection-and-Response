"""
analyzer.py  --  STEP 2 + 3 of the pipeline: "detonation".

Opens a URL in a throwaway headless Chromium and records everything the page
does (redirects, requests, scripts, downloads, popups, dialogs, forms, ...).
It returns EVIDENCE (plain data). Nothing here judges the page; that is the
job of checks.py.

Safety measures in this file
  * SSRF gate: refuses submitted URLs that resolve to private, loopback,
    link-local or otherwise non-public addresses.
  * Egress proxy (egress_proxy.py): the browser can only reach the network through
    it, and it refuses non-public destinations on EVERY connection, including
    redirect hops and DNS-rebinding tricks.
  * Downloads are saved to a temp dir only to be hashed, then deleted. They are
    never opened or executed.
  * Service workers blocked, no permissions granted, dialogs dismissed,
    popups closed.
  * Hard caps on time, requests, scripts and bytes.
  * The browser runs in a fresh profile that is destroyed afterwards.

In production, run this inside a locked-down container/Pod (see README).
"""
import hashlib
import ipaddress
import os
import socket
import tempfile
import time
from urllib.parse import urlparse

from playwright.sync_api import sync_playwright

from egress_proxy import EgressProxy

MAX_SCRIPTS = 40
MAX_SCRIPT_BYTES = 400_000
MAX_REQUESTS = 400
MAX_DOWNLOAD_HASH_BYTES = 25_000_000


class UnsafeURL(ValueError):
    """Raised when a URL is rejected by the gatekeeper."""


# --------------------------------------------------------------------------
# helpers
# --------------------------------------------------------------------------
_SECOND_LEVEL = {"co", "com", "org", "net", "gov", "ac", "edu"}


def base_domain(host):
    """Cheap 'registrable domain' (good enough for a prototype; use the
    `tldextract` package for exact results)."""
    host = (host or "").lower().strip(".")
    if not host:
        return ""
    try:
        ipaddress.ip_address(host)
        return host
    except ValueError:
        pass
    parts = host.split(".")
    if len(parts) <= 2:
        return host
    if len(parts[-1]) == 2 and parts[-2] in _SECOND_LEVEL:
        return ".".join(parts[-3:])
    return ".".join(parts[-2:])


def _ip_is_internal(ip):
    a = ipaddress.ip_address(ip.split("%")[0])
    return (not a.is_global) or a.is_multicast


class HostGuard:
    """SSRF protection with a per-analysis DNS cache."""

    def __init__(self, allow_private=False):
        self.allow_private = allow_private
        self._cache = {}

    def is_internal(self, host):
        if self.allow_private or not host:
            return False
        if host in self._cache:
            return self._cache[host]
        try:
            infos = socket.getaddrinfo(host, None)
            result = any(_ip_is_internal(i[4][0]) for i in infos)
        except (socket.gaierror, ValueError):
            result = False  # unresolvable: the browser will simply fail
        self._cache[host] = result
        return result

    def validate_url(self, url):
        p = urlparse(url)
        if p.scheme not in ("http", "https") or not p.hostname:
            raise UnsafeURL("Only http:// and https:// URLs with a hostname are allowed.")
        if self.is_internal(p.hostname):
            raise UnsafeURL(
                "That address resolves to a private/internal network and is blocked "
                "(SSRF protection). Set ALLOW_PRIVATE=1 only for local demos."
            )
        return url


def _magic(head):
    if head[:2] == b"MZ":
        return "Windows executable (PE)"
    if head[:4] == b"\x7fELF":
        return "Linux executable (ELF)"
    if head[:4] in (b"\xcf\xfa\xed\xfe", b"\xca\xfe\xba\xbe"):
        return "Mach-O / Java class"
    if head[:4] == b"PK\x03\x04":
        return "ZIP-based archive (zip/docx/apk/jar)"
    if head[:4] == b"%PDF":
        return "PDF document"
    if head[:2] == b"#!":
        return "Script (shebang)"
    return "Unknown / plain data"


_DOM_JS = r"""
() => {
  const abs = (u) => { try { return new URL(u, location.href).href } catch (e) { return String(u || '') } };
  const forms = [...document.forms].map(f => ({
    action: abs(f.getAttribute('action') || ''),
    method: (f.method || 'get').toLowerCase(),
    hasPassword: !!f.querySelector('input[type=password]'),
    inputs: [...f.querySelectorAll('input')].map(i => (i.type || 'text') + ':' + (i.name || i.autocomplete || '')).slice(0, 20)
  }));
  const iframes = [...document.querySelectorAll('iframe')].map(i => {
    const r = i.getBoundingClientRect(); const cs = getComputedStyle(i);
    return {
      src: abs(i.getAttribute('src') || ''), width: Math.round(r.width), height: Math.round(r.height),
      hidden: cs.display === 'none' || cs.visibility === 'hidden' || parseFloat(cs.opacity) === 0 || (r.width <= 2 && r.height <= 2)
    };
  });
  return {
    title: document.title || '',
    forms, iframes,
    passwordFields: document.querySelectorAll('input[type=password]').length,
    inlineScripts: [...document.scripts].filter(s => !s.src).map(s => (s.textContent || '').slice(0, 200000)).slice(0, 40),
    metaRefresh: [...document.querySelectorAll('meta[http-equiv]')]
      .filter(m => (m.httpEquiv || '').toLowerCase() === 'refresh').map(m => m.content),
    text: document.body ? document.body.innerText.slice(0, 1500) : ''
  };
}
"""


# --------------------------------------------------------------------------
# main entry point
# --------------------------------------------------------------------------
def detonate(url, allow_private=False, wait_ms=3000, nav_timeout_ms=30000, egress_blocked=None):
    """Visit `url` in a disposable browser. Returns (evidence_dict, screenshot_png_bytes_or_None).

    Network restriction: unless allow_private is set (local demo), all browser traffic is forced
    through EgressProxy, which refuses non-public destinations on every hop.
    `egress_blocked` overrides the proxy's block predicate (used by tests)."""
    guard = HostGuard(allow_private)
    guard.validate_url(url)

    started = time.time()
    ev = {
        "input_url": url, "final_url": None, "title": "", "status": None, "error": None,
        "headers": {}, "server_ip": None, "tls": None,
        "redirect_chain": [], "navigations": [],
        "requests": [], "blocked_requests": [],
        "scripts": [], "inline_scripts": [],
        "downloads": [], "popups": [], "dialogs": [],
        "console": [], "page_errors": [], "cookies": [],
        "forms": [], "iframes": [], "meta_refresh": [],
        "password_fields": 0, "visible_text": "", "elapsed_s": None,
    }
    screenshot = None
    launch_args = ["--no-sandbox"] if (os.geteuid() == 0 or os.environ.get("NO_SANDBOX") == "1") else []

    proxy = None
    if (not allow_private) or egress_blocked is not None:
        proxy = EgressProxy(blocked=egress_blocked).start()
    launch_proxy = {"server": "http://127.0.0.1:%d" % proxy.port} if proxy else None

    with tempfile.TemporaryDirectory(prefix="detonate-") as tmp, sync_playwright() as pw:
        try:
            browser = pw.chromium.launch(headless=True, args=launch_args, proxy=launch_proxy)
        except Exception:
            if proxy:
                proxy.stop()
            raise
        try:
            ctx = browser.new_context(
                accept_downloads=True,
                viewport={"width": 1280, "height": 800},
                service_workers="block",
                locale="en-US",
            )
            ctx.set_default_timeout(10_000)
            page = ctx.new_page()

            # Cheap first-line check on each routed request. NOTE: redirect hops never reach this
            # handler; the EgressProxy above is what actually enforces the network restriction.
            def on_route(route):
                req_url = route.request.url
                if req_url.startswith(("http:", "https:", "ws:", "wss:")):
                    host = urlparse(req_url).hostname or ""
                    if guard.is_internal(host):
                        ev["blocked_requests"].append(req_url[:300])
                        route.abort("blockedbyclient")
                        return
                route.continue_()

            ctx.route("**/*", on_route)

            def on_request(req):
                if len(ev["requests"]) >= MAX_REQUESTS:
                    return
                host = urlparse(req.url).hostname or ""
                ev["requests"].append({
                    "url": req.url[:500], "method": req.method, "type": req.resource_type,
                    "host": host, "base_domain": base_domain(host),
                })

            def on_response(resp):
                try:
                    if (resp.request.resource_type == "script" and 200 <= resp.status < 300
                            and len(ev["scripts"]) < MAX_SCRIPTS):
                        raw = resp.body()
                        ev["scripts"].append({
                            "url": resp.url[:500], "size": len(raw),
                            "sha256": hashlib.sha256(raw).hexdigest(),
                            "source": raw[:MAX_SCRIPT_BYTES].decode("utf-8", "replace"),
                        })
                except Exception:
                    pass

            def on_download(d):
                try:
                    path = os.path.join(tmp, "download.bin")
                    d.save_as(path)
                    h = hashlib.sha256()
                    size = os.path.getsize(path)
                    with open(path, "rb") as fh:
                        head = fh.read(8)
                        fh.seek(0)
                        read = 0
                        while read < MAX_DOWNLOAD_HASH_BYTES:
                            chunk = fh.read(1 << 20)
                            if not chunk:
                                break
                            h.update(chunk)
                            read += len(chunk)
                    os.remove(path)  # never keep or run it
                    ev["downloads"].append({
                        "filename": "".join(c for c in d.suggested_filename if c.isprintable())[:120],
                        "url": d.url[:500], "size": size, "sha256": h.hexdigest(), "magic": _magic(head),
                    })
                except Exception as e:
                    ev["downloads"].append({"filename": "(unreadable)", "url": "", "size": 0,
                                            "sha256": "", "magic": "error: %s" % str(e)[:80]})

            def on_dialog(d):
                ev["dialogs"].append({"type": d.type, "message": d.message[:200]})
                try:
                    d.dismiss()
                except Exception:
                    pass

            def on_popup(p):
                try:
                    ev["popups"].append(p.url[:300])
                    p.close()
                except Exception:
                    pass

            page.on("request", on_request)
            page.on("response", on_response)
            page.on("download", on_download)
            page.on("dialog", on_dialog)
            page.on("popup", on_popup)
            page.on("console", lambda m: ev["console"].append({"type": m.type, "text": m.text[:200]})
                    if len(ev["console"]) < 50 else None)
            page.on("pageerror", lambda e: ev["page_errors"].append(str(e)[:200])
                    if len(ev["page_errors"]) < 30 else None)
            page.on("framenavigated", lambda f: ev["navigations"].append(f.url[:500])
                    if f == page.main_frame else None)

            resp = None
            try:
                resp = page.goto(url, wait_until="load", timeout=nav_timeout_ms)
            except Exception as e:
                ev["error"] = str(e).split("\n")[0][:300]
            try:
                page.wait_for_load_state("networkidle", timeout=5000)
            except Exception:
                pass
            page.wait_for_timeout(wait_ms)  # give delayed scripts/redirects/downloads time to fire

            ev["final_url"] = page.url

            if resp is not None:
                ev["status"] = resp.status
                hdrs = {}
                for h in resp.headers_array():
                    k = h["name"].lower()
                    hdrs[k] = (hdrs[k] + "\n" + h["value"]) if k in hdrs else h["value"]
                ev["headers"] = hdrs
                try:
                    addr = resp.server_addr()
                    ev["server_ip"] = addr["ipAddress"] if addr else None
                except Exception:
                    pass
                try:
                    ev["tls"] = resp.security_details()
                except Exception:
                    pass
                # redirect chain (HTTP-level)
                chain, r = [], resp.request
                while r is not None:
                    chain.append(r)
                    r = r.redirected_from
                for r in reversed(chain):
                    rr = r.response()
                    ev["redirect_chain"].append({"url": r.url[:500], "status": rr.status if rr else None})

            try:
                dom = page.evaluate(_DOM_JS)
                ev["title"] = dom["title"][:200]
                ev["forms"] = dom["forms"]
                ev["iframes"] = dom["iframes"]
                ev["inline_scripts"] = dom["inlineScripts"]
                ev["meta_refresh"] = dom["metaRefresh"]
                ev["password_fields"] = dom["passwordFields"]
                ev["visible_text"] = dom["text"]
            except Exception:
                pass

            try:
                ev["cookies"] = [
                    {"name": c["name"], "domain": c["domain"], "secure": c["secure"],
                     "httpOnly": c["httpOnly"], "sameSite": c.get("sameSite", "None")}
                    for c in ctx.cookies()
                ]
            except Exception:
                pass

            try:
                screenshot = page.screenshot(type="png", timeout=8000)
            except Exception:
                screenshot = None
        finally:
            browser.close()
            if proxy:
                proxy.stop()
                for b in proxy.blocked_log:
                    if b not in ev["blocked_requests"]:
                        ev["blocked_requests"].append(b)

    ev["elapsed_s"] = round(time.time() - started, 2)
    return ev, screenshot
