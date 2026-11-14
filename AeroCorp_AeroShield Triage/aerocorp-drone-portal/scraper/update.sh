#!/usr/bin/env bash
# Refresh the catalogue: scrape every active entry in scraper/catalog.json, then merge the results
# into the running portal (new drones are created, existing ones are updated).
#
#   SCRAPER_CONTACT=you@example.com scraper/update.sh
#
# Weekly, Sunday 03:00 (crontab -e):
#   0 3 * * 0  cd /path/to/aerocorp-drone-portal && SCRAPER_CONTACT=you@example.com scraper/update.sh >> logs/scrape.log 2>&1
set -euo pipefail
cd "$(dirname "$0")/.."   # project root, so docker compose finds docker-compose.yml and .env

: "${SCRAPER_CONTACT:?set SCRAPER_CONTACT to your email address first}"

python3 scraper/scrape_drones.py --sources wikipedia,pages --out scraper/output/drones_scraped.json

# Run the importer in the backend container. The scraped file is mounted read-only at /data.
docker compose run --rm -v "$PWD/scraper/output:/data:ro" backend \
    python -m app.seed --scraped /data/drones_scraped.json
