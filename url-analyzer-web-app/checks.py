"""
checks.py  --  STEP 4 of the pipeline: independent analyzers.

Each check_* function reads the evidence collected by analyzer.py and returns a
list of FINDINGS in one common format:

    {id, group, category, severity, confidence, title, detail, evidence[]}

group = "threat"   -> "is this page trying to hurt the visitor?"
group = "hygiene"  -> "is this web app sloppy / insecure?"  (posture, not malice)

NOTE: evidence snippets come from the (possibly hostile) page. They are
sanitised to printable ASCII here, and the dashboard renders them as plain text.
"""
import base64
import os
import re
from urllib.parse import urlparse

import requests

from analyzer import base_domain

SEVERITY_ORDER = {"info": 0, "low": 1, "medium": 2, "high": 3, "critical": 4}


def finding(fid, group, severity, title, detail="", evidence=None, confidence=0.8):
    return {
        "id": fid, "group": group, "category": fid.split(".")[0],
        "severity": severity, "confidence": confidence,
        "title": title, "detail": detail,
        "evidence": [re.sub(r"[^\x20-\x7e]", ".", str(e))[:200] for e in (evidence or [])[:6]],
    }


def _snip(text, m, width=70):
    s, e = max(0, m.start() - width // 2), min(len(text), m.end() + width // 2)
    return re.sub(r"[^\x20-\x7e]", ".", text[s:e]).strip()


def _vt(v):
    """'1.12.4' -> (1, 12, 4)"""
    nums = [int(x) for x in re.findall(r"\d+", v)][:3]
    return tuple(nums + [0] * (3 - len(nums)))


# ==========================================================================
# 1. URL / domain look
# ==========================================================================
SUSPICIOUS_TLDS = {"zip", "mov", "top", "xyz", "click", "tk", "gq", "ml", "cf", "work", "country", "kim", "loan"}
PHISH_WORDS = ["login", "signin", "verify", "secure", "account", "update", "gift", "free", "bonus", "wallet", "prize", "claim"]


def check_url(ev):
    out = []
    final = ev.get("final_url") or ev["input_url"]
    u = urlparse(final)
    host = (u.hostname or "").lower()
    if re.fullmatch(r"\d{1,3}(\.\d{1,3}){3}", host) or ":" in host:
        out.append(finding("url.ip_host", "threat", "medium", "Page is served from a raw IP address",
                           "Legitimate services almost always use domain names.", [host], 0.6))
    if u.username:
        out.append(finding("url.userinfo", "threat", "medium", "URL contains a user@ part",
                           "Used to make a link look like it belongs to another site.", [final[:120]], 0.7))
    if "xn--" in host:
        out.append(finding("url.punycode", "threat", "medium", "Punycode (look-alike characters) in hostname",
                           "Can be used for homograph attacks.", [host], 0.5))
    if host.rsplit(".", 1)[-1] in SUSPICIOUS_TLDS:
        out.append(finding("url.tld", "threat", "low", "Domain uses a TLD that is often abused", "", [host], 0.4))
    if host.count(".") >= 4:
        out.append(finding("url.subdomains", "threat", "low", "Unusually many subdomains", "", [host], 0.4))
    hits = [w for w in PHISH_WORDS if w in host]
    if hits and "-" in host:
        out.append(finding("url.phish_words", "threat", "medium", "Hostname looks like a lure",
                           "Hyphenated hostname containing words typical for phishing: %s." % ", ".join(hits),
                           [host], 0.5))
    if len(final) > 200:
        out.append(finding("url.long", "threat", "low", "Very long URL", "", [final[:120] + "..."], 0.3))
    if final.startswith("http://"):
        out.append(finding("url.no_https", "hygiene", "low", "Page is served over unencrypted HTTP",
                           "Traffic can be read or modified in transit.", [final[:120]], 0.5))
    return out


# ==========================================================================
# 2. Redirects
# ==========================================================================
def check_redirects(ev):
    out = []
    chain = ev.get("redirect_chain", [])
    http_hops = max(0, len(chain) - 1)
    js_hops = max(0, len(ev.get("navigations", [])) - 1 - http_hops) if ev.get("navigations") else 0
    hops = http_hops + js_hops
    urls = [c["url"] for c in chain]
    domains = {base_domain(urlparse(u).hostname) for u in urls}
    if hops >= 3:
        out.append(finding("redirect.long_chain", "threat", "medium", "Long redirect chain (%d hops)" % hops,
                           "Malvertising and phishing kits bounce visitors through several hops to evade filters.",
                           ["%s %s" % (c["status"], c["url"][:90]) for c in chain], 0.7))
    elif hops == 2:
        out.append(finding("redirect.chain", "threat", "low", "Multiple redirects (%d hops)" % hops, "",
                           ["%s %s" % (c["status"], c["url"][:90]) for c in chain], 0.5))
    if len(domains) >= 2 and http_hops >= 1:
        sev = "medium" if len(domains) >= 3 else "low"
        out.append(finding("redirect.cross_domain", "threat", sev, "Redirects across %d different domains" % len(domains),
                           "The page you open is not the page you land on.", sorted(domains), 0.5))
    if ev.get("meta_refresh"):
        out.append(finding("redirect.meta_refresh", "threat", "low", "Page uses <meta http-equiv=refresh>",
                           "", ev["meta_refresh"], 0.4))
    return out


# ==========================================================================
# 3. Downloads / popups / dialogs
# ==========================================================================
EXEC_EXT = {"exe", "scr", "msi", "bat", "cmd", "com", "pif", "vbs", "vbe", "js", "jse", "wsf", "ps1", "jar",
            "apk", "dmg", "pkg", "hta", "lnk", "dll", "sh", "appimage", "deb", "rpm"}
RISKY_ARCHIVE_EXT = {"iso", "img", "zip", "rar", "7z", "docm", "xlsm", "pptm"}


def check_downloads(ev):
    out = []
    for d in ev.get("downloads", []):
        name = d.get("filename", "")
        ext = name.rsplit(".", 1)[-1].lower() if "." in name else ""
        info = ["%s | %d bytes | sha256 %s... | detected: %s" % (name, d.get("size", 0), d.get("sha256", "")[:16], d.get("magic"))]
        out.append(finding("download.auto", "threat", "high", "Page started a file download on its own",
                           "No click was made, so the page triggered it. The file was hashed and deleted, never opened.",
                           info, 0.7))
        magic = d.get("magic", "")
        if ext in EXEC_EXT:
            out.append(finding("download.executable", "threat", "critical", "Downloaded file is an executable type (.%s)" % ext,
                               "Executable/script file types are the usual carrier for malware.", info, 0.9))
        elif ext in RISKY_ARCHIVE_EXT:
            out.append(finding("download.risky_type", "threat", "medium", "Downloaded file is an archive/macro type (.%s)" % ext,
                               "", info, 0.6))
        if "executable" in magic.lower() and ext not in EXEC_EXT:
            out.append(finding("download.disguised", "threat", "critical", "File content is an executable but the name hides it",
                               "File header says: %s." % magic, info, 0.9))
    return out


def check_popups_dialogs(ev):
    out = []
    if ev.get("popups"):
        out.append(finding("popup.opened", "threat", "medium", "Page opened %d popup window(s) by itself" % len(ev["popups"]),
                           "", ev["popups"], 0.6))
    if ev.get("dialogs"):
        out.append(finding("dialog.alert", "threat", "low", "Page showed alert/confirm/prompt dialogs",
                           "Scareware pages use these to pressure visitors.",
                           ["%s: %s" % (d["type"], d["message"][:100]) for d in ev["dialogs"]], 0.5))
    return out


# ==========================================================================
# 4. Forms / iframes
# ==========================================================================
def check_forms_iframes(ev):
    out = []
    final = ev.get("final_url") or ev["input_url"]
    fu = urlparse(final)
    page_https = fu.scheme == "https"
    page_dom = base_domain(fu.hostname)

    if ev.get("password_fields", 0) > 0 and not page_https:
        out.append(finding("form.password_over_http", "threat", "high", "Password field on an unencrypted (HTTP) page",
                           "Anything typed here travels in clear text.", [final[:100]], 0.8))
    for f in ev.get("forms", []):
        if not f.get("hasPassword"):
            continue
        au = urlparse(f["action"])
        if au.hostname and base_domain(au.hostname) != page_dom:
            out.append(finding("form.password_cross_domain", "threat", "high", "Login form sends the password to a different domain",
                               "Classic credential-phishing behaviour.",
                               ["page: %s" % page_dom, "form posts to: %s" % f["action"][:120]], 0.85))
        elif page_https and au.scheme == "http":
            out.append(finding("form.password_downgrade", "threat", "high", "HTTPS page posts a password to an HTTP address",
                               "", [f["action"][:120]], 0.8))

    hidden = [i for i in ev.get("iframes", []) if i.get("hidden")]
    if hidden:
        cross = [i for i in hidden if i["src"] and base_domain(urlparse(i["src"]).hostname) != page_dom]
        out.append(finding("iframe.hidden", "threat", "medium" if cross else "low",
                           "Page contains %d hidden iframe(s)" % len(hidden),
                           "Hidden frames are used for tracking, drive-by loading and clickjacking.",
                           ["%s (%dx%d)" % (i["src"][:100], i["width"], i["height"]) for i in hidden], 0.65 if cross else 0.4))
    return out


# ==========================================================================
# 5. JavaScript static analysis  (a tiny Semgrep/YARA stand-in)
# ==========================================================================
# (id, regex, severity, confidence, min_matches, title, detail, group)
SCRIPT_RULES = [
    ("script.eval_decode", r"\beval\s*\(\s*(?:atob|unescape|decodeURIComponent|String\.fromCharCode)\s*\(",
     "high", 0.85, 1, "eval() of a decoded string",
     "Code is decoded at runtime and then executed - a classic way to hide malicious JavaScript.", "threat"),
    ("script.eval", r"\beval\s*\(", "low", 0.4, 1, "Use of eval()",
     "Common in legitimate code too, but it lets text become code.", "threat"),
    ("script.new_function", r"\bnew\s+Function\s*\(", "low", 0.4, 1, "Dynamic code via new Function()", "", "threat"),
    ("script.document_write", r"document\.write(?:ln)?\s*\(", "low", 0.3, 1, "document.write() used", "", "threat"),
    ("script.hex_obfuscation", r"\b_0x[a-f0-9]{4,6}\b", "medium", 0.8, 10, "Obfuscated identifiers (_0x1a2b style)",
     "Typical output of JavaScript obfuscator tools.", "threat"),
    ("script.fromcharcode", r"String\.fromCharCode", "low", 0.4, 5, "Heavy use of String.fromCharCode",
     "Strings are being assembled character by character to dodge simple scanners.", "threat"),
    ("script.encoded_blob", r"[\"'`][A-Za-z0-9+/]{300,}={0,2}[\"'`]", "low", 0.3, 1, "Very large encoded string literal", "", "threat"),
    ("script.miner", r"(?i)coin-?hive|cryptonight|webminer|minero\.cc|authedmine|deepminer|cryptoloot|jsecoin|miner\.start\(",
     "critical", 0.9, 1, "Cryptocurrency miner signature",
     "The page may use the visitor's CPU to mine cryptocurrency.", "threat"),
    ("script.getusermedia", r"getUserMedia\s*\(", "medium", 0.5, 1, "Requests camera/microphone access", "", "threat"),
    ("script.notification", r"Notification\.requestPermission", "low", 0.4, 1, "Asks for notification permission",
     "Abused for spam/scam push notifications.", "threat"),
    ("script.webrtc", r"RTCPeerConnection", "low", 0.4, 1, "Uses WebRTC", "Can reveal the visitor's real IP address.", "threat"),
    ("script.antidebug", r"\bdebugger\b\s*;", "low", 0.5, 3, "Anti-debugging statements",
     "Used to make analysis harder.", "threat"),
    # --- hygiene: secrets leaked in client-side code ---
    ("secret.aws_key", r"\bAKIA[0-9A-Z]{16}\b", "high", 0.9, 1, "AWS access key ID in client-side code", "", "hygiene"),
    ("secret.private_key", r"-----BEGIN (?:RSA |EC |OPENSSH )?PRIVATE KEY-----", "critical", 0.95, 1,
     "Private key in client-side code", "", "hygiene"),
    ("secret.google_key", r"\bAIza[0-9A-Za-z_\-]{35}\b", "low", 0.5, 1, "Google API key in client-side code",
     "Often intended to be public, but check its restrictions.", "hygiene"),
    ("secret.generic", r"(?i)\b(?:api[_-]?key|secret|access[_-]?token|client[_-]?secret)\b[\"']?\s*[:=]\s*[\"'][A-Za-z0-9_\-]{20,}[\"']",
     "medium", 0.5, 1, "Possible hard-coded secret", "", "hygiene"),
]
_COMPILED = [(r[0], re.compile(r[1]), *r[2:]) for r in SCRIPT_RULES]


def _all_sources(ev):
    srcs = [(s["url"], s["source"]) for s in ev.get("scripts", [])]
    srcs += [("inline-script #%d" % (i + 1), t) for i, t in enumerate(ev.get("inline_scripts", []))]
    return srcs


def check_scripts(ev):
    sources = _all_sources(ev)
    hits = {}  # rule id -> {"rule": rule, "evidence": [], "count": int}
    for label, text in sources:
        per_src = {}
        for rid, rx, sev, conf, min_n, title, detail, group in _COMPILED:
            ms = list(rx.finditer(text))
            if len(ms) >= min_n:
                per_src[rid] = ms
        if "script.eval_decode" in per_src:  # don't double-report plain eval in the same file
            per_src.pop("script.eval", None)
        for rid, ms in per_src.items():
            h = hits.setdefault(rid, {"count": 0, "evidence": []})
            h["count"] += len(ms)
            h["evidence"].append("%s: ...%s..." % (label.rsplit("/", 1)[-1][:40], _snip(text, ms[0])))
    out = []
    meta = {r[0]: r for r in _COMPILED}
    for rid, h in hits.items():
        _, _, sev, conf, _, title, detail, group = meta[rid]
        out.append(finding(rid, group, sev, "%s (%d match%s)" % (title, h["count"], "" if h["count"] == 1 else "es"),
                           detail, h["evidence"], conf))
    # keylogger-ish: key listener + network call in the same script
    kl = re.compile(r"addEventListener\(\s*[\"']key(?:down|press|up)[\"']")
    net = re.compile(r"XMLHttpRequest|fetch\s*\(|sendBeacon|new\s+Image\s*\(")
    for label, text in sources:
        m = kl.search(text)
        if m and net.search(text):
            out.append(finding("script.keylogger_pattern", "threat", "high",
                               "Keystroke listener combined with network calls",
                               "Could be a keylogger - or a normal search box with analytics. Check manually.",
                               ["%s: ...%s..." % (label.rsplit("/", 1)[-1][:40], _snip(text, m))], 0.5))
            break
    return out


# ==========================================================================
# 6. Known-vulnerable libraries  (a tiny Retire.js stand-in)
# ==========================================================================
LIBS = [
    {"name": "jQuery", "url_re": r"jquery[-.]?(\d+\.\d+(?:\.\d+)?)(?:\.min)?\.js", "src_re": r"jQuery(?: JavaScript Library)? v(\d+\.\d+\.\d+)",
     "vuln": lambda v: v < (3, 5, 0), "sev": "medium",
     "why": "jQuery < 3.5.0 has known XSS / prototype-pollution issues (e.g. CVE-2019-11358, CVE-2020-11022, CVE-2020-11023)."},
    {"name": "Bootstrap", "url_re": r"bootstrap[-.]?(\d+\.\d+\.\d+)", "src_re": r"Bootstrap v(\d+\.\d+\.\d+)",
     "vuln": lambda v: (3, 0, 0) <= v < (3, 4, 1) or (4, 0, 0) <= v < (4, 3, 1), "sev": "medium",
     "why": "Bootstrap 3 < 3.4.1 and 4 < 4.3.1 have an XSS flaw (CVE-2019-8331)."},
    {"name": "AngularJS", "url_re": r"angular(?:js)?[-.]?(1\.\d+\.\d+)", "src_re": r"AngularJS v(1\.\d+\.\d+)",
     "vuln": lambda v: v[0] == 1, "sev": "medium",
     "why": "AngularJS 1.x reached end-of-life in Jan 2022 and has known sandbox-escape XSS issues."},
    {"name": "lodash", "url_re": r"lodash[-@.]?(\d+\.\d+\.\d+)", "src_re": r"lodash[ @v-]+(\d+\.\d+\.\d+)",
     "vuln": lambda v: v < (4, 17, 21), "sev": "medium",
     "why": "lodash < 4.17.21 has prototype-pollution and command-injection issues (CVE-2020-8203, CVE-2021-23337)."},
]


def check_libraries(ev):
    out, seen = [], set()
    for s in ev.get("scripts", []):
        for lib in LIBS:
            m = re.search(lib["url_re"], s["url"], re.I) or re.search(lib["src_re"], s["source"][:3000])
            if not m:
                continue
            ver = m.group(1)
            key = (lib["name"], ver)
            if key in seen:
                continue
            seen.add(key)
            if lib["vuln"](_vt(ver)):
                out.append(finding("library.vulnerable", "hygiene", lib["sev"],
                                   "Outdated %s %s" % (lib["name"], ver), lib["why"], [s["url"][:120]], 0.8))
    return out


# ==========================================================================
# 7. Headers / cookies / TLS / network
# ==========================================================================
def check_headers(ev):
    h = ev.get("headers") or {}
    if not h:
        return []
    out = []
    final = ev.get("final_url") or ev["input_url"]
    https = final.startswith("https://")
    csp = h.get("content-security-policy", "")
    if not csp:
        out.append(finding("header.csp", "hygiene", "medium", "No Content-Security-Policy header",
                           "CSP is the main browser-side defence against XSS.", [], 0.7))
    elif "unsafe-eval" in csp:
        out.append(finding("header.csp_unsafe_eval", "hygiene", "low", "CSP allows 'unsafe-eval'", "", [csp[:120]], 0.5))
    if https and "strict-transport-security" not in h:
        out.append(finding("header.hsts", "hygiene", "low", "No Strict-Transport-Security (HSTS) header", "", [], 0.7))
    if "x-content-type-options" not in h:
        out.append(finding("header.nosniff", "hygiene", "low", "No X-Content-Type-Options: nosniff", "", [], 0.6))
    if "x-frame-options" not in h and "frame-ancestors" not in csp:
        out.append(finding("header.clickjacking", "hygiene", "low", "No clickjacking protection",
                           "Neither X-Frame-Options nor CSP frame-ancestors is set.", [], 0.6))
    if "referrer-policy" not in h:
        out.append(finding("header.referrer", "hygiene", "info", "No Referrer-Policy header", "", [], 0.5))
    leaks = [x for x in ("server", "x-powered-by") if re.search(r"\d", h.get(x, ""))]
    if leaks:
        out.append(finding("header.version_leak", "hygiene", "low", "Server discloses software versions",
                           "", ["%s: %s" % (x, h[x][:80]) for x in leaks], 0.4))
    if h.get("access-control-allow-origin") == "*" and h.get("access-control-allow-credentials", "").lower() == "true":
        out.append(finding("header.cors", "hygiene", "medium", "CORS: wildcard origin together with credentials", "", [], 0.7))
    return out


def check_cookies(ev):
    cookies = ev.get("cookies", [])
    if not cookies:
        return []
    out = []
    final = ev.get("final_url") or ev["input_url"]
    if final.startswith("https://"):
        bad = [c["name"] for c in cookies if not c["secure"]]
        if bad:
            out.append(finding("cookie.secure", "hygiene", "low", "Cookies without the Secure flag", "", bad, 0.7))
    bad = [c["name"] for c in cookies if not c["httpOnly"]]
    if bad:
        out.append(finding("cookie.httponly", "hygiene", "low", "Cookies readable by JavaScript (no HttpOnly)",
                           "Fine for non-sensitive cookies; risky for session cookies.", bad, 0.4))
    bad = [c["name"] for c in cookies if str(c["sameSite"]).lower() == "none" and not c["secure"]]
    if bad:
        out.append(finding("cookie.samesite", "hygiene", "low", "SameSite=None cookies without Secure", "", bad, 0.6))
    return out


def check_tls(ev):
    out = []
    err = ev.get("error") or ""
    if "ERR_CERT" in err or "SSL" in err:
        out.append(finding("tls.cert_error", "threat", "medium", "Browser reported a certificate/TLS error", "", [err[:150]], 0.6))
    elif "ERR_NAME_NOT_RESOLVED" in err:
        out.append(finding("net.unresolved", "threat", "info", "Domain does not resolve", "", [err[:150]], 0.9))
    elif err:
        out.append(finding("net.error", "threat", "info", "Navigation problem", "", [err[:150]], 0.9))
    t = ev.get("tls")
    if t:
        try:
            import time
            age_days = (time.time() - float(t.get("validFrom", 0))) / 86400
            if 0 <= age_days < 7:
                out.append(finding("tls.new_cert", "threat", "low", "TLS certificate was issued less than 7 days ago",
                                   "Weak signal on its own; common for freshly-registered phishing domains.",
                                   ["issuer: %s" % t.get("issuer", "?")], 0.5))
        except Exception:
            pass
        if t.get("protocol") in ("TLS 1.0", "TLS 1.1", "SSL 3.0"):
            out.append(finding("tls.old_protocol", "hygiene", "medium", "Server negotiated an obsolete protocol (%s)" % t["protocol"], "", [], 0.8))
    return out


def check_network(ev):
    out = []
    final = ev.get("final_url") or ev["input_url"]
    page_dom = base_domain(urlparse(final).hostname)
    if ev.get("blocked_requests"):
        out.append(finding("network.internal_probe", "threat", "high",
                           "Page tried to reach private/internal addresses (%d request(s) blocked)" % len(ev["blocked_requests"]),
                           "Sign of an SSRF / local-network scanning attempt. The sandbox blocked these.",
                           ev["blocked_requests"], 0.9))
    third = {r["base_domain"] for r in ev.get("requests", []) if r["base_domain"] and r["base_domain"] != page_dom}
    if len(third) > 15:
        out.append(finding("network.many_third_parties", "threat", "low", "Contacts %d third-party domains" % len(third),
                           "", sorted(third)[:6], 0.4))
    ip_hosts = {r["host"] for r in ev.get("requests", []) if re.fullmatch(r"\d{1,3}(\.\d{1,3}){3}", r["host"] or "")}
    ip_hosts.discard(urlparse(final).hostname)
    if ip_hosts:
        out.append(finding("network.ip_requests", "threat", "low", "Loads resources from raw IP addresses", "", sorted(ip_hosts), 0.4))
    if final.startswith("https://"):
        mixed = [r["url"] for r in ev.get("requests", []) if r["url"].startswith("http://")]
        if mixed:
            out.append(finding("network.mixed_content", "hygiene", "low", "HTTPS page loads %d resource(s) over HTTP" % len(mixed),
                               "", [m[:100] for m in mixed], 0.6))
    return out


# ==========================================================================
# 8. Reputation (optional - needs free API keys, see README)
# ==========================================================================
def _vt_findings(status, data):
    """Pure function so it can be unit-tested without network access."""
    if status == 404:
        return [finding("reputation.vt_unknown", "threat", "info", "URL not known to VirusTotal", "", [], 0.5)]
    if status != 200:
        return [finding("reputation.vt_error", "threat", "info", "VirusTotal lookup failed (HTTP %s)" % status, "", [], 0.5)]
    stats = data.get("data", {}).get("attributes", {}).get("last_analysis_stats", {})
    mal, sus = int(stats.get("malicious", 0)), int(stats.get("suspicious", 0))
    total = sum(int(v) for v in stats.values()) or 1
    ev = ["%d malicious, %d suspicious out of %d engines" % (mal, sus, total)]
    if mal >= 5:
        return [finding("reputation.vt_malicious", "threat", "critical", "VirusTotal: flagged malicious by %d engines" % mal, "", ev, 0.95)]
    if mal >= 1:
        return [finding("reputation.vt_malicious", "threat", "high", "VirusTotal: flagged by %d engine(s)" % mal, "", ev, 0.7)]
    if sus >= 1:
        return [finding("reputation.vt_suspicious", "threat", "medium", "VirusTotal: %d engine(s) mark it suspicious" % sus, "", ev, 0.5)]
    return [finding("reputation.vt_clean", "threat", "info", "VirusTotal: no engine flags this URL", "", ev, 0.6)]


def _gsb_findings(data):
    matches = data.get("matches", [])
    if not matches:
        return []
    kinds = sorted({m.get("threatType", "?") for m in matches})
    return [finding("reputation.gsb", "threat", "critical", "Google Safe Browsing lists this URL", "", kinds, 0.95)]


def check_reputation(ev):
    out = []
    url = ev["input_url"]
    vt_key, gsb_key = os.environ.get("VT_API_KEY"), os.environ.get("GSB_API_KEY")
    if vt_key:
        try:
            uid = base64.urlsafe_b64encode(url.encode()).decode().strip("=")
            r = requests.get("https://www.virustotal.com/api/v3/urls/" + uid, headers={"x-apikey": vt_key}, timeout=8)
            out += _vt_findings(r.status_code, r.json() if r.status_code == 200 else {})
        except Exception as e:
            out.append(finding("reputation.vt_error", "threat", "info", "VirusTotal lookup failed", "", [str(e)[:100]], 0.5))
    if gsb_key:
        try:
            body = {"client": {"clientId": "url-analyzer-prototype", "clientVersion": "0.1"},
                    "threatInfo": {"threatTypes": ["MALWARE", "SOCIAL_ENGINEERING", "UNWANTED_SOFTWARE", "POTENTIALLY_HARMFUL_APPLICATION"],
                                   "platformTypes": ["ANY_PLATFORM"], "threatEntryTypes": ["URL"],
                                   "threatEntries": [{"url": url}]}}
            r = requests.post("https://safebrowsing.googleapis.com/v4/threatMatches:find", params={"key": gsb_key}, json=body, timeout=8)
            out += _gsb_findings(r.json() if r.status_code == 200 else {})
        except Exception as e:
            out.append(finding("reputation.gsb_error", "threat", "info", "Safe Browsing lookup failed", "", [str(e)[:100]], 0.5))
    return out


# ==========================================================================
ALL_CHECKS = [check_url, check_redirects, check_downloads, check_popups_dialogs, check_forms_iframes,
              check_scripts, check_libraries, check_headers, check_cookies, check_tls, check_network,
              check_reputation]


def run_all(ev):
    findings = []
    for fn in ALL_CHECKS:
        try:
            findings += fn(ev)
        except Exception as e:  # one broken check must never kill the whole report
            findings.append(finding("internal.check_failed", "hygiene", "info", "Check %s crashed" % fn.__name__, "", [repr(e)[:150]], 0.2))
    findings.sort(key=lambda f: (SEVERITY_ORDER[f["severity"]], f["confidence"]), reverse=True)
    return findings
