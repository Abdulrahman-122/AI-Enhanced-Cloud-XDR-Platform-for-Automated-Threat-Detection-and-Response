# URL Sandbox Analyzer (prototype)

Opens a URL in a disposable headless Chromium, records everything the page does, runs
independent checks on the recorded evidence, and produces an explainable risk score.
Passive analysis only: it never attacks the target.

## 

```bash
pip install -r requirements.txt
python3 -m playwright install --with-deps chromium
./run.sh                      # demo site on :8001 + dashboard on :5000
# open http://127.0.0.1:5000, click "fake scam page", press Analyze
ssh -p 2222 -N -L 5000:127.0.0.1:5000 adam@127.0.0.1
```

CLI instead of the dashboard:

```bash
python demo_server.py &                                   # harmless fake scam page
python analyze.py http://localhost:8001/gift --allow-private
python analyze.py https://example.com                     # a real URL (private targets blocked)
python -m unittest tests -v                               # 14 tests, includes end-to-end
```

`--allow-private` / `ALLOW_PRIVATE=1` exist only so the local demo works. Never enable it on a
server others can reach.

## How it maps to the architecture

| Step | File | What it does |
|---|---|---|
| 1. Submit + gatekeeping | `app.py` | API + job queue; rejects non-http(s) and internal addresses |
| 2. Disposable browser | `analyzer.py`, `egress_proxy.py` | Fresh Chromium profile per job; all traffic forced through a filtering proxy |
| 3. Record evidence | `analyzer.py` | Redirects, requests, scripts, downloads (hashed, deleted), popups, dialogs, forms, iframes, cookies, TLS, screenshot |
| 4. Analyzers | `checks.py` | URL look, redirects, downloads, forms, JS patterns, vulnerable libs, headers, cookies, TLS, reputation |
| 5. Scoring | `scoring.py` | `100 x (1 - prod(1 - weight x confidence))`, separate Threat and Hygiene scores |
| 6. AI summary | `scoring.llm_payload` | Structured-only payload to hand to an LLM (no raw page text, so no prompt injection) |
| 7. Dashboard | `static/index.html` | Live progress, verdict, findings with evidence |

Two scores on purpose: **Threat** ("is this page hostile to its visitor?") and **Hygiene** ("is this
web app sloppy?"). Hygiene covers headers, cookies, outdated libraries, leaked secrets.

## Optional reputation lookups

```bash
export VT_API_KEY=...     # VirusTotal (free key)
export GSB_API_KEY=...    # Google Safe Browsing (free key)
```
The response parsers are unit-tested, but the live calls were not run (no keys here). Note this
sends the submitted URL to those services.

## What was tested here

- Clean demo page scores Threat 0; the fake scam page scores 92 (Critical) with 19 findings.
- Redirect hop to an internal address is blocked at the proxy (403) and reported as a finding.
- Proxy tested for HTTP forwarding, CONNECT tunnelling and blocking.
- **Not tested here:** real internet sites (the build sandbox has no general internet), HTTPS
  through the proxy against a real server, the Dockerfile, and Kubernetes.

## Limitations
- Sees only what the server sends to a browser. Backend source code (Flask, PHP...) is invisible.
- Cloaking: malicious sites can behave differently for sandboxes/headless browsers. A clean
  result is not proof of safety.
- Pattern checks are heuristics (a tiny Semgrep/YARA/Retire.js stand-in). `eval` or a keystroke
  listener alone is often legitimate, hence the low confidence values. Swap in the real
  Semgrep, YARA and Retire.js for coverage.
- Fresh Chromium can still be exploited by a browser zero-day. In production add container
  isolation (gVisor/Kata), non-root, read-only filesystem, CPU/RAM/time limits, and an egress
  NetworkPolicy. `egress_proxy.py` gives the same rule on a plain VM.
- Jobs are kept in memory with a thread pool. Replace with Redis/RabbitMQ and one Kubernetes
  Job per analysis. The API has no authentication or rate limiting yet.
- Evidence snippets come from hostile pages; the dashboard renders them with `textContent` only.
  Keep it that way.

## Next steps

1. Add real Semgrep/YARA/Retire.js runs on the saved script files.
2. Add ZAP baseline + Nuclei as an **active-scan mode, only for domains on an allowlist you own**.
3. Persist reports (PostgreSQL) and screenshots (MinIO); emit events to your XDR pipeline.
4. Feed `llm_payload` to your AI agent for the dashboard summary.
