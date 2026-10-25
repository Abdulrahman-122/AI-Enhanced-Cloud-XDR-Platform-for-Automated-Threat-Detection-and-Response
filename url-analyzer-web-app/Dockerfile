# UNTESTED sketch: one analysis container. Run it as a Kubernetes Job / short-lived Pod.
FROM python:3.12-slim
WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt \
 && playwright install --with-deps chromium
COPY . .
RUN useradd -m analyzer && chown -R analyzer /app
USER analyzer
# Non-root => Chromium can use its own sandbox (no --no-sandbox). Add a read-only rootfs,
# resource limits, activeDeadlineSeconds and an egress NetworkPolicy in the Pod spec.
ENTRYPOINT ["python", "analyze.py", "--json"]
