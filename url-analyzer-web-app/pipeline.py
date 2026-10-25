"""
pipeline.py  --  glues the steps together:

    detonate (analyzer.py)  ->  checks.run_all  ->  scoring  ->  report
"""
import checks
import scoring
from analyzer import detonate


def _public_evidence(ev):
    """Evidence minus bulky/raw script bodies, safe to show in the UI."""
    pub = {k: v for k, v in ev.items() if k not in ("scripts", "inline_scripts")}
    pub["scripts"] = [{"url": s["url"], "size": s["size"], "sha256": s["sha256"]} for s in ev["scripts"]]
    pub["inline_script_count"] = len(ev["inline_scripts"])
    return pub


def analyze_url(url, allow_private=False, on_stage=None):
    stage = on_stage or (lambda s: None)

    stage("detonating")
    ev, screenshot = detonate(url, allow_private=allow_private)

    stage("analyzing")
    findings = checks.run_all(ev)

    stage("scoring")
    threat = scoring.group_score(findings, "threat")
    hygiene = scoring.group_score(findings, "hygiene")
    final = ev.get("final_url") or url

    report = {
        "url": url,
        "final_url": final,
        "threat_score": threat,
        "threat_level": scoring.threat_level(threat),
        "hygiene_score": hygiene,
        "hygiene_level": scoring.hygiene_level(hygiene),
        "summary": scoring.build_summary(final, threat, hygiene, findings),
        "findings": findings,
        "evidence": _public_evidence(ev),
        "llm_payload": scoring.llm_payload(final, threat, hygiene, findings),
        "has_screenshot": screenshot is not None,
    }
    return report, screenshot
