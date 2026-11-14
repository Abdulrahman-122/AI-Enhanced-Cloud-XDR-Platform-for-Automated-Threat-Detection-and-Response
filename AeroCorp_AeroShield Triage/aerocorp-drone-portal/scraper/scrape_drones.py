#!/usr/bin/env python3
"""Collect drone descriptions, photos and prices for the AeroCorp catalogue (standard library only).

Sources
  wikipedia : page summary from the Wikipedia API, plus the page's main photo from Wikimedia Commons.
              A photo is downloaded ONLY when Commons reports a free licence (CC, public domain, ...);
              the author and licence are saved so the site can credit them.
  pages     : each drone's manufacturer page (`source_url`). Reads only page metadata (OpenGraph tags and
              schema.org Product data: title, description, price). Skips any page that robots.txt
              disallows, and waits between requests.

Catalogue: scraper/catalog.json lists the drones to fetch. Add to it without editing code:
    python scrape_drones.py --add "Autel Dragonfish" --category "Enterprise inspection" --manufacturer Autel
    python scrape_drones.py --discover "Category:Quadcopters" --category "Consumer & creator" --manufacturer Various
  --discover adds entries marked "pending" (skipped by the scraper until you remove that flag).

Output: a JSON list that the backend merges into PostgreSQL:
    python -m app.seed --scraped /data/drones_scraped.json

Examples
    python scrape_drones.py --sources wikipedia
    python scrape_drones.py --sources wikipedia,pages --only dji-mavic-3-pro,skydio-x10
    python scrape_drones.py --dry-run --limit 3
"""
from __future__ import annotations

import argparse
import html
import json
import os
import re
import sys
import time
import urllib.error
import urllib.parse
import urllib.request
import urllib.robotparser
from datetime import datetime, timezone
from html.parser import HTMLParser
from pathlib import Path

CONTACT = os.getenv("SCRAPER_CONTACT", "set-SCRAPER_CONTACT@example.invalid")
USER_AGENT = f"AeroCorpDronePortalBot/1.0 (educational lab project; contact: {CONTACT})"
WIKI = "https://en.wikipedia.org"
COMMONS = "https://commons.wikimedia.org"
FREE_LICENSE = re.compile(r"^(CC[ -]|Public domain|PD[ -]|GFDL|Attribution|Copyrighted free use)", re.I)
IMAGE_EXT = {".jpg", ".jpeg", ".png", ".webp"}
CATALOG_PATH = Path(__file__).resolve().parent / "catalog.json"
DISAMBIGUATION = re.compile(r"\s*\((?:drone|aircraft|UAV|UAS|unmanned aerial vehicle|helicopter|fixed-wing aircraft)\)$", re.I)


class FetchError(Exception):
    pass


def slugify(text: str) -> str:  # must match backend/app/util.py
    return re.sub(r"[^a-z0-9]+", "-", text.lower()).strip("-") or "item"


# --------------------------------------------------------------------------- HTTP with manners
class Fetcher:
    """urllib wrapper that identifies itself, throttles per host and honours robots.txt."""

    def __init__(self, delay: float = 1.5, timeout: float = 20.0) -> None:
        self.delay, self.timeout = delay, timeout
        self._last_hit: dict[str, float] = {}
        self._robots: dict[str, urllib.robotparser.RobotFileParser | None] = {}

    def _throttle(self, host: str) -> None:
        wait = self._last_hit.get(host, 0) + self.delay - time.monotonic()
        if wait > 0:
            time.sleep(wait)
        self._last_hit[host] = time.monotonic()

    def get(self, url: str, max_bytes: int = 15_000_000) -> bytes:
        host = urllib.parse.urlsplit(url).netloc
        self._throttle(host)
        request = urllib.request.Request(url, headers={"User-Agent": USER_AGENT, "Accept": "*/*"})
        try:
            with urllib.request.urlopen(request, timeout=self.timeout) as response:
                data = response.read(max_bytes + 1)
        except urllib.error.HTTPError as exc:
            raise FetchError(f"HTTP {exc.code} for {url}") from exc
        except (urllib.error.URLError, TimeoutError, OSError) as exc:
            raise FetchError(f"{type(exc).__name__}: {exc} for {url}") from exc
        if len(data) > max_bytes:
            raise FetchError(f"response too large for {url}")
        return data

    def allowed(self, url: str) -> bool:
        """robots.txt per RFC 9309: 4xx -> no rules (allowed); 5xx or unreachable -> treat as disallowed."""
        parts = urllib.parse.urlsplit(url)
        origin = f"{parts.scheme}://{parts.netloc}"
        if origin not in self._robots:
            parser = urllib.robotparser.RobotFileParser()
            try:
                parser.parse(self.get(f"{origin}/robots.txt").decode("utf-8", "replace").splitlines())
                self._robots[origin] = parser
            except FetchError as exc:
                if re.search(r"HTTP 4\d\d", str(exc)):  # no robots.txt published: nothing is disallowed
                    parser.parse([])
                    self._robots[origin] = parser
                else:  # server error or unreachable: do not crawl
                    self._robots[origin] = None
        parser = self._robots[origin]
        return parser is not None and parser.can_fetch(USER_AGENT, url)


# --------------------------------------------------------------------------- Wikipedia / Commons
def _quote(title: str) -> str:
    return urllib.parse.quote(title.replace(" ", "_"), safe="")


def wiki_summary(fetch, title: str) -> dict:
    data = json.loads(fetch.get(f"{WIKI}/api/rest_v1/page/summary/{_quote(title)}"))
    if data.get("type") == "disambiguation" or not data.get("extract"):
        raise FetchError(f"no usable article for '{title}'")
    return data


def wiki_search(fetch, term: str) -> str | None:
    query = urllib.parse.urlencode({"action": "opensearch", "search": term, "limit": 1, "format": "json"})
    data = json.loads(fetch.get(f"{WIKI}/w/api.php?{query}"))
    return data[1][0] if len(data) > 1 and data[1] else None


def find_summary(fetch, drone: dict) -> dict:
    candidates = [t for t in (drone.get("wiki_title"), drone["name"]) if t]
    for title in candidates:
        try:
            return wiki_summary(fetch, title)
        except FetchError:
            continue
    for term in candidates[::-1]:
        found = wiki_search(fetch, term)
        if found:
            try:
                return wiki_summary(fetch, found)
            except FetchError:
                continue
    raise FetchError(f"no Wikipedia article found for {drone['name']}")


def strip_tags(value: str) -> str:
    return re.sub(r"\s+", " ", html.unescape(re.sub(r"<[^>]+>", " ", value or ""))).strip()


def free_commons_image(fetch, title: str) -> dict | None:
    """Main photo of a Wikipedia article, only if Commons says its licence is free."""
    query = urllib.parse.urlencode({
        "action": "query", "format": "json", "prop": "pageimages", "piprop": "thumbnail|name",
        "pithumbsize": 1000, "redirects": 1, "titles": title,
    })
    page = next(iter(json.loads(fetch.get(f"{WIKI}/w/api.php?{query}"))["query"]["pages"].values()))
    name, thumb = page.get("pageimage"), (page.get("thumbnail") or {}).get("source")
    if not name or not thumb:
        return None
    query = urllib.parse.urlencode({
        "action": "query", "format": "json", "prop": "imageinfo", "iiprop": "extmetadata", "titles": f"File:{name}",
    })
    info_page = next(iter(json.loads(fetch.get(f"{COMMONS}/w/api.php?{query}"))["query"]["pages"].values()))
    meta = ((info_page.get("imageinfo") or [{}])[0]).get("extmetadata", {})
    licence = (meta.get("LicenseShortName") or {}).get("value", "")
    if not FREE_LICENSE.match(licence):
        return None
    return {
        "thumb": thumb,
        "licence": licence,
        "artist": strip_tags((meta.get("Artist") or {}).get("value", "")) or "Unknown author",
        "file_page": f"{COMMONS}/wiki/File:{_quote(name)}",
    }


# --------------------------------------------------------------------------- real specs from the article infobox
# Wikipedia aircraft articles carry an {{Infobox aircraft}} with range, speed, weight and so on.
# We read the article's wikitext and convert every figure to the metric units the catalogue uses.
ENDURANCE_KEYS = ("endurance", "flight time", "flight endurance")
INFOBOX_FIELDS = {  # infobox parameter names (first one present wins) -> (spec key, unit factors to base unit)
    ("range", "max range", "maximum range"): ("max_range_km", {"km": 1.0, "mi": 1.609344, "nmi": 1.852}),
    ("speed", "max speed", "maximum speed", "cruise speed"): (
        "max_speed_kmh", {"km/h": 1.0, "kmh": 1.0, "mph": 1.609344, "kn": 1.852, "knots": 1.852, "m/s": 3.6}),
    ("ceiling", "service ceiling", "max altitude"): ("ceiling_m", {"m": 1.0, "ft": 0.3048, "km": 1000.0}),
    ("wingspan",): ("wingspan_m", {"m": 1.0, "ft": 0.3048}),
    ("empty weight", "weight", "max takeoff weight", "takeoff weight", "gross weight"): (
        "weight_kg", {"kg": 1.0, "g": 0.001, "lb": 0.45359237, "lbs": 0.45359237, "t": 1000.0}),
    ("payload", "payload capacity", "max payload"): ("payload_kg", {"kg": 1.0, "lb": 0.45359237, "lbs": 0.45359237}),
}


def wiki_wikitext(fetch, title: str) -> str:
    """Wikitext of the article's lead section, where the infobox lives."""
    query = urllib.parse.urlencode({"action": "parse", "format": "json", "prop": "wikitext", "section": 0,
                                    "redirects": 1, "page": title})
    return json.loads(fetch.get(f"{WIKI}/w/api.php?{query}"))["parse"]["wikitext"]["*"]


def _clean_wikitext(value: str) -> str:
    value = re.sub(r"<!--.*?-->", "", value, flags=re.S)
    value = re.sub(r"<ref[^>]*/>|<ref[^>]*>.*?</ref>", "", value, flags=re.S)
    value = re.sub(r"\{\{\s*(?:convert|cvt)\s*\|\s*([\d.,]+)\s*\|\s*([^|}]+)[^}]*\}\}", r"\1 \2", value, flags=re.I)
    for _ in range(3):  # remove nested templates, innermost first
        value = re.sub(r"\{\{[^{}]*\}\}", "", value)
    value = re.sub(r"\[\[(?:[^|\]]*\|)?([^\]]*)\]\]", r"\1", value)
    value = re.sub(r"<[^>]+>", " ", value)
    return html.unescape(value).replace("'''", "").replace("''", "").strip()


def parse_infobox(wikitext: str) -> dict[str, str]:
    """Top-level `| name = value` lines of the first {{Infobox ...}} template."""
    start = wikitext.find("{{Infobox")
    if start == -1:
        return {}
    depth, i, end = 0, start, len(wikitext)
    while i < len(wikitext) - 1:
        pair = wikitext[i:i + 2]
        if pair == "{{":
            depth, i = depth + 1, i + 2
        elif pair == "}}":
            depth, i = depth - 1, i + 2
            if depth == 0:
                end = i
                break
        else:
            i += 1
    body = wikitext[start + 2:end - 2]
    params: dict[str, str] = {}
    for line in re.split(r"\n\s*\|", body)[1:]:
        name, sep, value = line.partition("=")
        if sep and name.strip():
            params[name.strip().lower()] = value
    return params


def infobox_diagnosis(wikitext: str) -> str:
    """Says why no specs were read, so the field mapping can be fixed from real article data."""
    if "{{Infobox" not in wikitext:
        return "the article's lead section has no {{Infobox ...}} template"
    keys = sorted(parse_infobox(wikitext))
    return "infobox fields found: " + (", ".join(keys[:30]) or "(none could be read)")


def _quantity(text: str, factors: dict[str, float]) -> float | None:
    """First `number unit` pair in the text whose unit we know, converted with the given factors."""
    for match in re.finditer(r"(\d[\d,]*(?:\.\d+)?)\s*([A-Za-z][A-Za-z/]*)", text):
        unit = match.group(2).lower()
        if unit in factors:
            return float(match.group(1).replace(",", "")) * factors[unit]
    return None


def infobox_specs(wikitext: str) -> dict:
    params = {k: _clean_wikitext(v) for k, v in parse_infobox(wikitext).items()}
    specs: dict = {}

    def first(keys):
        return next((params[k] for k in keys if params.get(k)), "")

    minutes = _quantity(first(ENDURANCE_KEYS), {"min": 1.0, "minutes": 1.0, "minute": 1.0, "h": 60.0, "hour": 60.0, "hours": 60.0})
    if minutes:
        specs["flight_time_min"] = round(minutes)
    for keys, (spec_key, factors) in INFOBOX_FIELDS.items():
        value = _quantity(first(keys), factors)
        if value:
            specs[spec_key] = round(value, 3)
    return specs


# --------------------------------------------------------------------------- manufacturer pages
class PageMeta(HTMLParser):
    """Collects <title>, <meta> tags and JSON-LD blocks from an HTML page."""

    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self.meta: dict[str, str] = {}
        self.title = ""
        self.json_ld: list[str] = []
        self._in_title = False
        self._in_ld = False

    def handle_starttag(self, tag, attrs):
        attrs = dict(attrs)
        if tag == "title":
            self._in_title = True
        elif tag == "meta":
            key = attrs.get("property") or attrs.get("name")
            if key and attrs.get("content"):
                self.meta.setdefault(key.lower(), attrs["content"])
        elif tag == "script" and (attrs.get("type") or "").lower() == "application/ld+json":
            self._in_ld = True
            self.json_ld.append("")

    def handle_endtag(self, tag):
        if tag == "title":
            self._in_title = False
        elif tag == "script":
            self._in_ld = False

    def handle_data(self, data):
        if self._in_title:
            self.title += data
        elif self._in_ld:
            self.json_ld[-1] += data


def _walk(node):
    if isinstance(node, dict):
        yield node
        for value in node.values():
            yield from _walk(value)
    elif isinstance(node, list):
        for value in node:
            yield from _walk(value)


def product_price_usd(blocks: list[str]) -> int | None:
    for raw in blocks:
        try:
            data = json.loads(raw)
        except ValueError:
            continue
        for node in _walk(data):
            kinds = node.get("@type")
            kinds = kinds if isinstance(kinds, list) else [kinds]
            if "Product" not in kinds:
                continue
            for offer in _walk(node.get("offers", [])):
                if str(offer.get("priceCurrency", "")).upper() == "USD" and offer.get("price") not in (None, ""):
                    try:
                        return int(float(str(offer["price"]).replace(",", "")))
                    except ValueError:
                        pass
    return None


def read_page(fetch, url: str) -> dict:
    parser = PageMeta()
    parser.feed(fetch.get(url, max_bytes=3_000_000).decode("utf-8", "replace"))
    meta = parser.meta
    return {
        "title": strip_tags(meta.get("og:title") or parser.title),
        "description": strip_tags(meta.get("og:description") or meta.get("description") or ""),
        "image": urllib.parse.urljoin(url, meta["og:image"]) if meta.get("og:image") else None,
        "price_usd": product_price_usd(parser.json_ld),
    }


# --------------------------------------------------------------------------- orchestration
def short_text(text: str, limit: int = 420) -> str:
    text = re.sub(r"\s*\[\d+\]", "", text).strip()
    if len(text) <= limit:
        return text
    cut = text[:limit]
    end = max(cut.rfind(". "), cut.rfind("! "))
    return cut[: end + 1] if end > 120 else cut.rsplit(" ", 1)[0] + "..."


def save_image(fetch, url: str, slug: str, media_dir: Path) -> str:
    ext = Path(urllib.parse.urlsplit(url).path).suffix.lower()
    ext = ext if ext in IMAGE_EXT else ".jpg"
    target = media_dir / "drones" / f"{slug}{ext}"
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_bytes(fetch.get(url))
    return f"/api/media/drones/{slug}{ext}"


def scrape(drones, fetch, media_dir: Path, sources: set[str], use_wiki_text=False, og_images="skip", dry_run=False):
    records, problems = [], []
    for drone in drones:
        slug = drone.get("slug") or slugify(drone["name"])
        record = {"slug": slug, "name": drone["name"], "sources": [],
                  "scraped_at": datetime.now(timezone.utc).isoformat(timespec="seconds")}
        # The importer needs category (to create a new drone) and manufacturer; the rest are optional.
        for key in ("category", "manufacturer", "source_url", "description"):
            if drone.get(key):
                record[key] = drone[key]

        if "wikipedia" in sources:
            title = None
            try:
                summary = find_summary(fetch, drone)
                title = summary.get("title") or drone["name"]
                record["sources"].append(summary.get("content_urls", {}).get("desktop", {}).get("page", f"{WIKI}/wiki/{_quote(title)}"))
                if use_wiki_text:
                    record["description"] = short_text(summary["extract"])
                image = free_commons_image(fetch, title)
                if image is None:
                    problems.append(f"{slug}: no freely licensed photo on Wikimedia Commons")
                elif not dry_run:
                    record["image_url"] = save_image(fetch, image["thumb"], slug, media_dir)
                    record["image_credit"] = f"{image['artist']}, {image['licence']}, via Wikimedia Commons ({image['file_page']})"[:300]
                else:
                    record["image_url"] = "(dry run) " + image["thumb"]
            except (FetchError, KeyError, ValueError, StopIteration) as exc:
                problems.append(f"{slug}: wikipedia - {exc}")
            try:
                wikitext = wiki_wikitext(fetch, title) if title else ""
                specs = infobox_specs(wikitext) if wikitext else {}
                if specs:
                    record["specs"] = specs
                elif title:
                    problems.append(f"{slug}: no specs found in the Wikipedia infobox - {infobox_diagnosis(wikitext)}")
            except (FetchError, KeyError, ValueError) as exc:
                problems.append(f"{slug}: infobox - {exc}")

        page_url = drone.get("source_url")
        if "pages" in sources and page_url:
            try:
                if not fetch.allowed(page_url):
                    problems.append(f"{slug}: robots.txt disallows {page_url} - skipped")
                else:
                    page = read_page(fetch, page_url)
                    record["sources"].append(page_url)
                    if page["price_usd"]:
                        record["price_usd"] = page["price_usd"]
                    if page["image"] and "image_url" not in record and og_images != "skip":
                        if og_images == "download" and not dry_run:
                            record["image_url"] = save_image(fetch, page["image"], slug, media_dir)
                        else:
                            record["image_url"] = page["image"]
                        record["image_credit"] = f"Image from {urllib.parse.urlsplit(page_url).netloc} (check usage rights before publishing)"
            except (FetchError, ValueError) as exc:
                problems.append(f"{slug}: page - {exc}")

        records.append(record)
    return records, problems


# --------------------------------------------------------------------------- the catalogue file
def _categories() -> list[str]:
    """The category list lives in the backend; importing it needs no database."""
    sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "backend"))
    from app.seed_data import CATEGORIES

    return CATEGORIES


def read_catalogue(path: Path) -> list[dict]:
    """Entries exactly as written in the file (an empty list if the file does not exist yet)."""
    if not path.exists():
        return []
    return json.loads(path.read_text(encoding="utf-8"))


def save_catalogue(path: Path, entries: list[dict]) -> None:
    path.write_text(json.dumps(entries, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")


def load_catalogue(path: Path) -> list[dict]:
    """Entries ready to scrape: each gets a slug (from the file, or derived from the name)."""
    if not path.exists():
        raise SystemExit(f"Catalogue not found: {path}  (create an entry with --add, or pass --catalog)")
    return [dict(e, slug=e.get("slug") or slugify(e["name"])) for e in read_catalogue(path)]


def add_drone(entries: list[dict], name: str, category: str, manufacturer: str, *,
              wiki_title: str | None = None, source_url: str | None = None, pending: bool = False) -> bool:
    """Append one drone to the catalogue. Returns False if the slug is already listed."""
    name, manufacturer = name.strip(), manufacturer.strip()
    if not name or not manufacturer:
        raise ValueError("a name and a manufacturer are required")
    if category not in _categories():
        raise ValueError(f"unknown category '{category}'. Use one of: {', '.join(_categories())}")
    slug = slugify(name)
    if any((e.get("slug") or slugify(e["name"])) == slug for e in entries):
        return False
    entry = {"name": name, "manufacturer": manufacturer, "category": category}
    if wiki_title:
        entry["wiki_title"] = wiki_title
    if source_url:
        entry["source_url"] = source_url
    if pending:
        entry["pending"] = True
    entries.append(entry)
    return True


def discover_titles(fetch, category: str, limit: int = 100) -> list[str]:
    """Article titles in a Wikipedia category (main namespace only; 'List of ...' pages are skipped)."""
    title = category if category.lower().startswith("category:") else f"Category:{category}"
    query = urllib.parse.urlencode([("action", "query"), ("list", "categorymembers"), ("cmtitle", title),
                                    ("cmnamespace", 0), ("cmlimit", min(limit, 500)), ("format", "json")])
    members = json.loads(fetch.get(f"{WIKI}/w/api.php?{query}"))["query"]["categorymembers"]
    titles = [m["title"] for m in members if not m["title"].lower().startswith("list of")]
    return titles[:limit]


def discover(entries: list[dict], titles: list[str], category: str, manufacturer: str) -> tuple[int, list[str]]:
    """Add each article as a pending entry. Returns (added, names already listed)."""
    added, already = 0, []
    for title in titles:
        name = DISAMBIGUATION.sub("", title).strip()
        if add_drone(entries, name, category, manufacturer, wiki_title=title, pending=True):
            added += 1
        else:
            already.append(name)
    return added, already


def edit_catalogue(ap: argparse.ArgumentParser, args) -> int:
    """--add and --discover: change catalog.json only. Run the scraper afterwards to fetch the details."""
    if not (args.category and args.manufacturer):
        ap.error("--add and --discover need --category and --manufacturer")
    try:
        entries = read_catalogue(args.catalog)
        if args.add:
            if not add_drone(entries, args.add, args.category, args.manufacturer,
                             wiki_title=args.wiki_title, source_url=args.source_url):
                print(f"'{args.add}' is already in {args.catalog}.")
                return 1
            save_catalogue(args.catalog, entries)
            print(f"Added '{args.add}' to {args.catalog}.")
            print(f"Next: python scrape_drones.py --only {slugify(args.add)}   (or scraper/update.sh for everything)")
            return 0
        if args.category not in _categories():  # checked before any network call
            raise ValueError(f"unknown category '{args.category}'. Use one of: {', '.join(_categories())}")
        titles = discover_titles(Fetcher(delay=args.delay), args.discover, args.discover_limit)
        added, already = discover(entries, titles, args.category, args.manufacturer)
        save_catalogue(args.catalog, entries)
        print(f"{args.discover}: {len(titles)} article(s) found, {added} added as pending, {len(already)} already listed.")
        print(f"Review {args.catalog}: remove \"pending\" from the entries you want, then run the scraper.")
        return 0
    except ValueError as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 2
    except (FetchError, KeyError) as exc:
        print(f"error: could not read Wikipedia - {exc}", file=sys.stderr)
        return 1


def main(argv=None) -> int:
    root = Path(__file__).resolve().parent
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--sources", default="wikipedia", help="comma list: wikipedia,pages (default: wikipedia)")
    ap.add_argument("--catalog", type=Path, default=CATALOG_PATH, help="catalogue file (default: scraper/catalog.json)")
    ap.add_argument("--only", help="comma list of slugs to scrape (also scrapes pending entries named here)")
    ap.add_argument("--include-pending", action="store_true", help="also scrape entries added by --discover that are still marked pending")
    ap.add_argument("--add", metavar="NAME", help="add one drone to the catalogue and exit (no scraping)")
    ap.add_argument("--discover", metavar="CATEGORY", help="add the articles of a Wikipedia category as pending entries and exit")
    ap.add_argument("--discover-limit", type=int, default=100, help="how many articles --discover reads (max 500)")
    ap.add_argument("--category", help="for --add and --discover: one of the site's categories")
    ap.add_argument("--manufacturer", help="for --add and --discover: the maker's name")
    ap.add_argument("--wiki-title", help="for --add: the Wikipedia article title, if it differs from the name")
    ap.add_argument("--source-url", help="for --add: the manufacturer's product page")
    ap.add_argument("--limit", type=int, help="stop after N drones")
    ap.add_argument("--delay", type=float, default=1.5, help="seconds between requests to the same host")
    ap.add_argument("--out", type=Path, default=root / "output" / "drones_scraped.json")
    ap.add_argument("--media-dir", type=Path, default=root.parent / "backend" / "media")
    ap.add_argument("--use-wiki-text", action="store_true", help="also replace descriptions with the Wikipedia summary (CC BY-SA, attribution is kept in `sources`)")
    ap.add_argument("--og-images", choices=["skip", "link", "download"], default="skip", help="manufacturer-page images; check usage rights first (default: skip)")
    ap.add_argument("--dry-run", action="store_true", help="fetch and report, but save no images")
    args = ap.parse_args(argv)

    sources = {s.strip() for s in args.sources.split(",") if s.strip()}
    unknown = sources - {"wikipedia", "pages"}
    if unknown:
        ap.error(f"unknown source(s): {', '.join(sorted(unknown))}")

    if args.add or args.discover:
        return edit_catalogue(ap, args)

    drones = load_catalogue(args.catalog)
    if args.only:
        wanted = {s.strip() for s in args.only.split(",")}
        drones = [d for d in drones if d["slug"] in wanted]
    elif not args.include_pending:
        held = [d for d in drones if d.get("pending")]
        drones = [d for d in drones if not d.get("pending")]
        if held:
            print(f"Skipping {len(held)} pending entr{'y' if len(held) == 1 else 'ies'} from --discover "
                  "(remove \"pending\" in catalog.json, or pass --include-pending).")
    if args.limit:
        drones = drones[: args.limit]

    print(f"Scraping {len(drones)} drone(s) from: {', '.join(sorted(sources))}  (User-Agent: {USER_AGENT})")
    records, problems = scrape(drones, Fetcher(delay=args.delay), args.media_dir, sources,
                               use_wiki_text=args.use_wiki_text, og_images=args.og_images, dry_run=args.dry_run)

    if not args.dry_run:
        args.out.parent.mkdir(parents=True, exist_ok=True)
        args.out.write_text(json.dumps(records, indent=2, ensure_ascii=False), encoding="utf-8")
        print(f"Wrote {args.out}")
    with_image = sum(1 for r in records if r.get("image_url"))
    print(f"Done: {len(records)} record(s), {with_image} with a photo, {len(problems)} note(s).")
    for line in problems:
        print("  -", line)
    return 0 if records else 1


if __name__ == "__main__":
    sys.exit(main())
