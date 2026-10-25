"""
app.py  --  STEP 1 of the pipeline: the API + dashboard.

  POST /api/analyze        {"url": "https://..."}  -> {"id": "..."}   (job queued)
  GET  /api/jobs/<id>      -> {"status": queued|detonating|analyzing|scoring|done|error, "report": {...}}
  GET  /api/jobs/<id>/screenshot.png
  GET  /                   dashboard

Gatekeeping happens here, BEFORE a job is queued (SSRF check on the submitted URL).
In production, replace the in-memory dict + thread pool with Redis/RabbitMQ and one
Kubernetes Job per analysis (see README).

Run:   ALLOW_PRIVATE=1 python app.py      (ALLOW_PRIVATE only for the local demo!)
"""
import os
import threading
import time
import uuid
from concurrent.futures import ThreadPoolExecutor

from flask import Flask, jsonify, request, send_from_directory, Response

from analyzer import HostGuard, UnsafeURL
from pipeline import analyze_url

ALLOW_PRIVATE = os.environ.get("ALLOW_PRIVATE") == "1"
MAX_JOBS = 50

app = Flask(__name__, static_folder="static", static_url_path="/static")
pool = ThreadPoolExecutor(max_workers=int(os.environ.get("WORKERS", "2")))
jobs, shots, lock = {}, {}, threading.Lock()


def _run(job_id, url):
    def stage(s):
        with lock:
            jobs[job_id]["status"] = s

    try:
        report, shot = analyze_url(url, allow_private=ALLOW_PRIVATE, on_stage=stage)
        with lock:
            jobs[job_id].update(status="done", report=report, finished=time.time())
            if shot:
                shots[job_id] = shot
    except Exception as e:  # report failures instead of hanging the UI
        with lock:
            jobs[job_id].update(status="error", error=str(e)[:300], finished=time.time())


@app.post("/api/analyze")
def api_analyze():
    url = ((request.get_json(silent=True) or {}).get("url") or "").strip()
    if "://" not in url:
        url = "https://" + url  # allow "example.com"
    try:
        HostGuard(ALLOW_PRIVATE).validate_url(url)
    except UnsafeURL as e:
        return jsonify({"error": str(e)}), 400

    job_id = uuid.uuid4().hex[:12]
    with lock:
        jobs[job_id] = {"id": job_id, "url": url, "status": "queued", "created": time.time()}
        while len(jobs) > MAX_JOBS:  # drop oldest
            old = min(jobs, key=lambda k: jobs[k]["created"])
            jobs.pop(old, None)
            shots.pop(old, None)
    pool.submit(_run, job_id, url)
    return jsonify({"id": job_id}), 202


@app.get("/api/jobs/<job_id>")
def api_job(job_id):
    with lock:
        job = jobs.get(job_id)
        return (jsonify(job), 200) if job else (jsonify({"error": "unknown job"}), 404)


@app.get("/api/jobs/<job_id>/screenshot.png")
def api_shot(job_id):
    with lock:
        data = shots.get(job_id)
    return Response(data, mimetype="image/png") if data else ("", 404)


@app.get("/")
def index():
    return send_from_directory(app.static_folder, "index.html")


if __name__ == "__main__":
    print("Dashboard: http://127.0.0.1:5000   (private targets %s)" % ("ALLOWED - demo mode" if ALLOW_PRIVATE else "blocked"))
    app.run(host="127.0.0.1", port=5000, threaded=True)
