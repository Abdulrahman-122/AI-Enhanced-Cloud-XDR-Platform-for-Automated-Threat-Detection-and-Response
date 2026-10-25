"""
scoring.py  --  STEP 5 of the pipeline: findings -> explainable risk score.

Each finding contributes  weight(severity) x confidence  as an independent
"probability of harm". Scores combine like independent risks:

    score = 100 x ( 1 - PRODUCT( 1 - weight x confidence ) )

So many weak signals add up slowly, one strong signal moves the needle a lot,
and the result can never exceed 100. Every point of the score can be traced to a
finding, which is what makes it explainable on a dashboard.
"""
from checks import SEVERITY_ORDER

WEIGHT = {"info": 0.0, "low": 0.04, "medium": 0.12, "high": 0.28, "critical": 0.50}


def group_score(findings, group):
    p = 1.0
    for f in findings:
        if f["group"] == group:
            p *= 1.0 - WEIGHT[f["severity"]] * f["confidence"]
    return round(100 * (1.0 - p))


def threat_level(score):
    return "Low" if score < 15 else "Medium" if score < 40 else "High" if score < 65 else "Critical"


def hygiene_level(score):
    return "Good" if score < 15 else "Fair" if score < 40 else "Poor"


def build_summary(final_url, threat, hygiene, findings):
    """Plain rule-based summary (no LLM needed)."""
    top = [f for f in findings if f["group"] == "threat" and f["severity"] != "info"][:4]
    t_lvl, h_lvl = threat_level(threat), hygiene_level(hygiene)
    if not top:
        head = "No threat indicators were observed when this page was opened in the sandbox."
    else:
        head = "Threat level %s (%d/100). Main reasons: %s." % (
            t_lvl, threat, "; ".join(f["title"].rstrip(".") for f in top))
    tail = "Security hygiene is %s (%d/100)." % (h_lvl.lower(), hygiene)
    if t_lvl in ("High", "Critical"):
        advice = "Do not open this URL on a real device and consider blocking the domain."
    elif t_lvl == "Medium":
        advice = "Treat with caution and review the findings before trusting this page."
    else:
        advice = "Nothing here suggests the page is malicious, but a clean sandbox visit is not a guarantee."
    return " ".join([head, tail, advice])


def llm_payload(url, threat, hygiene, findings):
    """What you would hand to an LLM agent to write a nicer summary.
    Deliberately contains ONLY structured fields (ids, severities, titles) and no
    raw page text, so a malicious page cannot inject instructions into the model."""
    return {
        "url": url, "threat_score": threat, "hygiene_score": hygiene,
        "findings": [{"id": f["id"], "group": f["group"], "severity": f["severity"],
                      "confidence": f["confidence"], "title": f["title"]} for f in findings],
    }
