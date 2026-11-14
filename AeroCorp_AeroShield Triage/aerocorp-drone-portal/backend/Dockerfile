FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

WORKDIR /srv

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY app ./app

# The container user is set by docker-compose (APP_UID / APP_GID) so bind-mounted
# media, datasheets and log folders stay writable on Linux hosts.
RUN mkdir -p /srv/media /srv/datasheets /var/log/aerocorp && chmod 777 /srv/media /srv/datasheets /var/log/aerocorp

EXPOSE 8000
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
