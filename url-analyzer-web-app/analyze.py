#!/usr/bin/env python3
"""
Command-line version: analyze one URL and print the report.

    python analyze.py https://example.com
    python analyze.py http://localhost:8001/gift --allow-private     # local demo
    python analyze.py URL --json > report.json
"""
import argparse
import json
import sys

from analyzer import UnsafeURL
from pipeline import analyze_url

COLORS = {"critical": "\033[91m", "high": "\033[31m", "medium": "\033[33m", "low": "\033[34m", "info": "\033[90m"}
RESET = "\033[0m"


def main():
    ap = argparse.ArgumentParser(description="Sandboxed URL analysis prototype")
    ap.add_argument("url")
    ap.add_argument("--allow-private", action="store_true", help="allow localhost/private targets (demo only)")
    ap.add_argument("--json", action="store_true", help="print the full report as JSON")
    ap.add_argument("--screenshot", metavar="FILE", help="save the page screenshot to FILE (png)")
    args = ap.parse_args()

    url = args.url if "://" in args.url else "https://" + args.url
    try:
        report, shot = analyze_url(url, allow_private=args.allow_private,
                                   on_stage=lambda s: print("  [%s]" % s, file=sys.stderr))
    except UnsafeURL as e:
        sys.exit("Blocked: %s" % e)

    if args.screenshot and shot:
        with open(args.screenshot, "wb") as f:
            f.write(shot)
    if args.json:
        print(json.dumps(report, indent=2))
        return

    ev = report["evidence"]
    print("\nURL:        %s" % report["url"])
    print("Landed on:  %s" % report["final_url"])
    print("Threat:     %d/100  %s" % (report["threat_score"], report["threat_level"].upper()))
    print("Hygiene:    %d/100  %s" % (report["hygiene_score"], report["hygiene_level"]))
    print("Seen:       %d requests, %d scripts, %d downloads, %d dialogs, %d redirects  (%.1fs)" % (
        len(ev["requests"]), len(ev["scripts"]) + ev["inline_script_count"], len(ev["downloads"]),
        len(ev["dialogs"]), max(0, len(ev["redirect_chain"]) - 1), ev["elapsed_s"]))
    print("\n%s\n" % report["summary"])
    for f in report["findings"]:
        c = COLORS[f["severity"]]
        print("%s[%-8s]%s %-6s %s  (conf %.2f)" % (c, f["severity"].upper(), RESET, f["group"], f["title"], f["confidence"]))
        for e in f["evidence"][:2]:
            print("             - %s" % e[:110])


if __name__ == "__main__":
    main()
