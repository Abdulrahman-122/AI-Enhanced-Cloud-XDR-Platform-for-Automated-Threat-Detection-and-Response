"""Offline tests: every network call is served from canned responses, so these run anywhere."""
import json
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
import scrape_drones as sd  # noqa: E402


class Canned(sd.Fetcher):
    """Real Fetcher logic (robots handling, throttle off) with the network replaced by a dict."""

    def __init__(self, routes):
        super().__init__(delay=0)
        self.routes, self.calls = routes, []

    def get(self, url, max_bytes=15_000_000):
        self.calls.append(url)
        for prefix, body in self.routes.items():
            if url.startswith(prefix):
                if isinstance(body, Exception):
                    raise body
                return body if isinstance(body, bytes) else json.dumps(body).encode()
        raise sd.FetchError(f"HTTP 404 for {url}")


SUMMARY = {"type": "standard", "title": "DJI Mavic 3", "extract": "The DJI Mavic 3 is a drone. It was released in 2021 [1]. " + "More text. " * 60,
           "content_urls": {"desktop": {"page": "https://en.wikipedia.org/wiki/DJI_Mavic_3"}}}
PAGEIMAGES = {"query": {"pages": {"1": {"pageimage": "DJI_Mavic_3.jpg", "thumbnail": {"source": "https://upload.wikimedia.org/thumb/DJI_Mavic_3.jpg/1000px-DJI_Mavic_3.jpg"}}}}}


def commons(licence, artist="<a href='x'>Jane Photographer</a>"):
    return {"query": {"pages": {"9": {"imageinfo": [{"extmetadata": {"LicenseShortName": {"value": licence}, "Artist": {"value": artist}}}]}}}}


def routes(licence="CC BY-SA 4.0"):
    return {
        f"{sd.WIKI}/api/rest_v1/page/summary/DJI_Mavic_3": SUMMARY,
        f"{sd.WIKI}/w/api.php?action=query": PAGEIMAGES,
        f"{sd.COMMONS}/w/api.php": commons(licence),
        f"{sd.WIKI}/w/api.php?action=parse": {"parse": {"wikitext": {"*": SYNTHETIC_INFOBOX}}},
        "https://upload.wikimedia.org/": b"\xff\xd8\xffFAKEJPEG",
    }


# Synthetic wikitext shaped like Wikipedia's {{Infobox aircraft}}. The figures are made up for the test;
# they are not copied from any article.
SYNTHETIC_INFOBOX = """{{Short description|Test aircraft used by the unit tests}}
{{Infobox aircraft
| name = Test Quad
| type = Multirotor
| endurance = 43 minutes<ref>manufacturer spec</ref>
| range = {{convert|15|km|mi|abbr=on}}
| speed = 75 km/h (47 mph)
| weight = 958 g
| wingspan = {{convert|6|ft}}
| ceiling = 6000 m
| payload = 2.5 kg
}}
Lead text. Not part of the infobox."""


DRONE = {"name": "DJI Mavic 3 Pro", "wiki_title": "DJI Mavic 3", "slug": "dji-mavic-3-pro"}


def test_slugify_matches_backend():
    sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "backend"))
    from app.util import slugify

    for name in ("DJI Mavic 3 Pro", "Zipline P1 (Zip)", "senseFly eBee X", "Northrop Grumman RQ-4 Global Hawk"):
        assert sd.slugify(name) == slugify(name)


def test_free_photo_is_downloaded_with_credit(tmp_path):
    records, problems = sd.scrape([DRONE], Canned(routes()), tmp_path, {"wikipedia"})
    rec = records[0]
    assert rec["image_url"] == "/api/media/drones/dji-mavic-3-pro.jpg"
    assert (tmp_path / "drones" / "dji-mavic-3-pro.jpg").read_bytes().startswith(b"\xff\xd8\xff")
    assert "Jane Photographer" in rec["image_credit"] and "CC BY-SA 4.0" in rec["image_credit"] and "Wikimedia Commons" in rec["image_credit"]
    assert "<a" not in rec["image_credit"]
    assert rec["sources"] == ["https://en.wikipedia.org/wiki/DJI_Mavic_3"] and not problems
    assert "description" not in rec, "curated descriptions are kept unless --use-wiki-text is set"


@pytest.mark.parametrize("licence", ["All rights reserved", "Fair use", ""])
def test_non_free_photo_is_never_downloaded(tmp_path, licence):
    records, problems = sd.scrape([DRONE], Canned(routes(licence)), tmp_path, {"wikipedia"})
    assert "image_url" not in records[0]
    assert not (tmp_path / "drones").exists()
    assert any("no freely licensed photo" in p for p in problems)


def test_wiki_text_is_short_and_clean_when_requested(tmp_path):
    records, _ = sd.scrape([DRONE], Canned(routes()), tmp_path, {"wikipedia"}, use_wiki_text=True)
    text = records[0]["description"]
    assert text.startswith("The DJI Mavic 3 is a drone.") and "[1]" not in text and len(text) <= 425


def test_search_fallback_when_title_is_missing(tmp_path):
    r = routes()
    r[f"{sd.WIKI}/w/api.php?action=opensearch"] = ["x", ["DJI Mavic 3"], [], []]
    del r[f"{sd.WIKI}/api/rest_v1/page/summary/DJI_Mavic_3"]
    fetch = Canned({**r, f"{sd.WIKI}/api/rest_v1/page/summary/DJI_Mavic_3_Pro": sd.FetchError("HTTP 404")})
    # first lookups fail (404), search returns "DJI Mavic 3", whose summary we now serve again
    fetch.routes[f"{sd.WIKI}/api/rest_v1/page/summary/DJI_Mavic_3"] = SUMMARY
    calls_before = len(fetch.calls)
    summary = sd.find_summary(fetch, {"name": "Totally Unknown Drone"})
    assert summary["title"] == "DJI Mavic 3" and len(fetch.calls) > calls_before


def test_disambiguation_pages_are_rejected(tmp_path):
    fetch = Canned({f"{sd.WIKI}/api/rest_v1/page/summary/": {"type": "disambiguation", "extract": "may refer to"},
                    f"{sd.WIKI}/w/api.php?action=opensearch": ["x", [], [], []]})
    records, problems = sd.scrape([DRONE], fetch, tmp_path, {"wikipedia"})
    assert "image_url" not in records[0] and any("wikipedia" in p for p in problems)


# --------------------------------------------------------------------------- manufacturer pages
PAGE = b"""<html><head><title>Fallback</title>
<meta property="og:title" content="Mavic 3 Pro"><meta property="og:description" content="Triple camera &amp; more">
<meta property="og:image" content="/img/mavic.jpg">
<script type="application/ld+json">{"@context":"https://schema.org","@graph":[{"@type":"Product","name":"Mavic 3 Pro",
"offers":{"@type":"Offer","priceCurrency":"USD","price":"2,199.00"}}]}</script></head><body></body></html>"""


def test_page_metadata_and_price_parsing():
    info = sd.read_page(Canned({"https://maker.example/p": PAGE}), "https://maker.example/p")
    assert info == {"title": "Mavic 3 Pro", "description": "Triple camera & more",
                    "image": "https://maker.example/img/mavic.jpg", "price_usd": 2199}


def test_non_usd_or_invalid_json_ld_gives_no_price():
    assert sd.product_price_usd(['{"@type":"Product","offers":{"priceCurrency":"EUR","price":"10"}}', "{not json"]) is None


ROBOTS_BLOCK = b"User-agent: *\nDisallow: /p\n"


def test_robots_disallow_is_respected(tmp_path):
    drone = {"name": "X", "source_url": "https://maker.example/p/x", "slug": "x"}
    fetch = Canned({"https://maker.example/robots.txt": ROBOTS_BLOCK, "https://maker.example/p": PAGE})
    records, problems = sd.scrape([drone], fetch, tmp_path, {"pages"})
    assert any("robots.txt disallows" in p for p in problems)
    assert not any(u.startswith("https://maker.example/p") for u in fetch.calls), "a disallowed page must never be requested"
    assert "price_usd" not in records[0]


def test_missing_robots_txt_means_allowed_and_server_error_means_blocked(tmp_path):
    drone = {"name": "X", "source_url": "https://maker.example/p/x", "slug": "x"}
    ok = Canned({"https://maker.example/p": PAGE})  # robots.txt -> 404
    records, _ = sd.scrape([drone], ok, tmp_path, {"pages"})
    assert records[0]["price_usd"] == 2199
    blocked = Canned({"https://maker.example/robots.txt": sd.FetchError("HTTP 503 for robots"), "https://maker.example/p": PAGE})
    records, problems = sd.scrape([drone], blocked, tmp_path, {"pages"})
    assert "price_usd" not in records[0] and any("robots.txt disallows" in p for p in problems)


def test_page_images_are_skipped_by_default_and_opt_in_otherwise(tmp_path):
    drone = {"name": "X", "source_url": "https://maker.example/p/x", "slug": "x"}
    base = {"https://maker.example/p": PAGE, "https://maker.example/img/mavic.jpg": b"IMG"}
    assert "image_url" not in sd.scrape([drone], Canned(base), tmp_path, {"pages"})[0][0]
    link = sd.scrape([drone], Canned(base), tmp_path, {"pages"}, og_images="link")[0][0]
    assert link["image_url"] == "https://maker.example/img/mavic.jpg" and "usage rights" in link["image_credit"]
    dl = sd.scrape([drone], Canned(base), tmp_path, {"pages"}, og_images="download")[0][0]
    assert dl["image_url"] == "/api/media/drones/x.jpg" and (tmp_path / "drones" / "x.jpg").read_bytes() == b"IMG"


def test_network_errors_become_notes_not_crashes(tmp_path):
    records, problems = sd.scrape([DRONE], Canned({sd.WIKI: sd.FetchError("HTTP 403 for blocked")}), tmp_path, {"wikipedia"})
    assert records[0]["slug"] == "dji-mavic-3-pro" and problems


def test_dry_run_saves_nothing(tmp_path):
    records, _ = sd.scrape([DRONE], Canned(routes()), tmp_path, {"wikipedia"}, dry_run=True)
    assert records[0]["image_url"].startswith("(dry run)") and not (tmp_path / "drones").exists()


def test_output_file_is_valid_for_the_importer(tmp_path):
    out = tmp_path / "out.json"
    catalog = tmp_path / "catalog.json"
    catalog.write_text(json.dumps([DRONE]))
    fetch = Canned(routes())
    original = sd.Fetcher
    sd.Fetcher = lambda **_: fetch
    try:
        code = sd.main(["--catalog", str(catalog), "--out", str(out), "--media-dir", str(tmp_path / "media")])
    finally:
        sd.Fetcher = original
    assert code == 0
    data = json.loads(out.read_text())
    assert data[0]["slug"] == "dji-mavic-3-pro" and data[0]["image_url"].startswith("/api/media/drones/")


def test_throttle_waits_between_requests_to_one_host(monkeypatch):
    sleeps = []
    monkeypatch.setattr(sd.time, "sleep", sleeps.append)
    fetch = sd.Fetcher(delay=2.0)
    fetch._throttle("a.example")
    fetch._throttle("a.example")
    fetch._throttle("b.example")
    assert len(sleeps) == 1 and 0 < sleeps[0] <= 2.0


# --------------------------------------------------------------------------- real specs from the infobox
def test_infobox_figures_are_converted_to_catalogue_units(tmp_path):
    records, problems = sd.scrape([DRONE], Canned(routes()), tmp_path, {"wikipedia"})
    specs = records[0]["specs"]
    assert specs == {"flight_time_min": 43, "max_range_km": 15.0, "max_speed_kmh": 75.0,
                     "weight_kg": 0.958, "wingspan_m": 1.829, "ceiling_m": 6000.0, "payload_kg": 2.5}
    assert not problems


def test_imperial_only_values_are_converted():
    text = "{{Infobox aircraft\n| range = 9 mi\n| speed = 50 mph\n| weight = 4 lb\n}}"
    assert sd.infobox_specs(text) == {"max_range_km": 14.484, "max_speed_kmh": 80.467, "weight_kg": 1.814}


def test_infobox_parser_ignores_refs_comments_and_links():
    text = "{{Infobox aircraft\n| range = [[Kilometre|km]] <!-- old: 3 km --> 12 km<ref>x</ref>\n}}"
    assert sd.infobox_specs(text) == {"max_range_km": 12.0}


def test_no_infobox_gives_no_specs_and_a_note(tmp_path):
    fetch = Canned({**routes(), f"{sd.WIKI}/w/api.php?action=parse": {"parse": {"wikitext": {"*": "No box here."}}}})
    records, problems = sd.scrape([DRONE], fetch, tmp_path, {"wikipedia"})
    assert "specs" not in records[0]
    assert any("no specs found" in p for p in problems)


def test_infobox_failure_does_not_lose_the_photo(tmp_path):
    fetch = Canned({**routes(), f"{sd.WIKI}/w/api.php?action=parse": sd.FetchError("HTTP 503")})
    records, problems = sd.scrape([DRONE], fetch, tmp_path, {"wikipedia"})
    assert records[0]["image_url"] == "/api/media/drones/dji-mavic-3-pro.jpg"
    assert any("infobox" in p for p in problems)


def test_missing_article_does_not_crash_the_infobox_step(tmp_path):
    fetch = Canned({f"{sd.WIKI}/w/api.php?action=opensearch": ["x", [], [], []]})
    records, problems = sd.scrape([{"name": "Nothing Here", "slug": "nothing-here"}], fetch, tmp_path, {"wikipedia"})
    assert "specs" not in records[0] and any("wikipedia" in p for p in problems)
    assert not any("infobox" in p for p in problems)


# --------------------------------------------------------------------------- the catalogue file
CATEGORY_MEMBERS = {"query": {"categorymembers": [{"title": "DJI Mavic 3"}, {"title": "List of drones"},
                                                  {"title": "Parrot Anafi (drone)"}]}}


def test_shipped_catalogue_is_valid():
    entries = sd.read_catalogue(sd.CATALOG_PATH)
    slugs = [sd.slugify(e["name"]) for e in entries]
    assert len(entries) >= 18 and len(set(slugs)) == len(slugs), "slugs must be unique"
    for e in entries:
        assert e["category"] in sd._categories() and e["manufacturer"], e


def test_records_carry_category_and_manufacturer_for_new_drones(tmp_path):
    drone = {"name": "Autel Dragonfish", "slug": "autel-dragonfish", "category": "Enterprise inspection",
             "manufacturer": "Autel", "source_url": "https://www.autelrobotics.com/"}
    records, _ = sd.scrape([drone], Canned({}), tmp_path, set())
    assert records[0]["category"] == "Enterprise inspection" and records[0]["manufacturer"] == "Autel"
    assert records[0]["source_url"] == "https://www.autelrobotics.com/"


def test_add_drone_validates_and_dedupes():
    entries = []
    assert sd.add_drone(entries, "Autel Dragonfish", "Enterprise inspection", "Autel")
    assert not sd.add_drone(entries, "autel  dragonfish", "Enterprise inspection", "Autel"), "same slug is rejected"
    with pytest.raises(ValueError, match="unknown category"):
        sd.add_drone(entries, "Other", "Toys", "Maker")
    with pytest.raises(ValueError):
        sd.add_drone(entries, "  ", "Mapping & survey", "Maker")
    assert entries == [{"name": "Autel Dragonfish", "manufacturer": "Autel", "category": "Enterprise inspection"}]


def test_discover_reads_category_members_and_marks_entries_pending():
    fetch = Canned({f"{sd.WIKI}/w/api.php?action=query&list=categorymembers": CATEGORY_MEMBERS})
    titles = sd.discover_titles(fetch, "Quadcopters", limit=10)
    assert titles == ["DJI Mavic 3", "Parrot Anafi (drone)"], "'List of' pages are skipped"
    assert "Category%3AQuadcopters" in fetch.calls[0]
    entries = [{"name": "DJI Mavic 3", "manufacturer": "DJI", "category": "Consumer & creator"}]
    added, already = sd.discover(entries, titles, "Consumer & creator", "Various")
    assert (added, already) == (1, ["DJI Mavic 3"])
    assert entries[-1] == {"name": "Parrot Anafi", "manufacturer": "Various", "category": "Consumer & creator",
                           "wiki_title": "Parrot Anafi (drone)", "pending": True}


def test_add_command_writes_catalogue_and_never_touches_the_network(tmp_path, monkeypatch):
    catalog = tmp_path / "catalog.json"
    monkeypatch.setattr(sd, "Fetcher", lambda **_: pytest.fail("--add must not use the network"))
    code = sd.main(["--catalog", str(catalog), "--add", "Autel Dragonfish",
                    "--category", "Enterprise inspection", "--manufacturer", "Autel"])
    assert code == 0 and json.loads(catalog.read_text())[0]["name"] == "Autel Dragonfish"


def test_discover_command_writes_pending_entries(tmp_path, monkeypatch):
    catalog = tmp_path / "catalog.json"
    monkeypatch.setattr(sd, "Fetcher", lambda **_: Canned({f"{sd.WIKI}/w/api.php?action=query&list=categorymembers": CATEGORY_MEMBERS}))
    code = sd.main(["--catalog", str(catalog), "--discover", "Category:Quadcopters",
                    "--category", "Consumer & creator", "--manufacturer", "Various"])
    entries = json.loads(catalog.read_text())
    assert code == 0 and [e["name"] for e in entries] == ["DJI Mavic 3", "Parrot Anafi"]
    assert all(e["pending"] for e in entries)


def test_pending_entries_are_skipped_unless_named_or_forced(tmp_path, monkeypatch):
    catalog = tmp_path / "catalog.json"
    catalog.write_text(json.dumps([
        {"name": "DJI Mavic 3 Pro", "manufacturer": "DJI", "category": "Consumer & creator", "wiki_title": "DJI Mavic 3"},
        {"name": "Pending Drone", "manufacturer": "X", "category": "Consumer & creator", "pending": True},
    ]))
    monkeypatch.setattr(sd, "Fetcher", lambda **_: Canned(routes()))
    common = ["--catalog", str(catalog), "--media-dir", str(tmp_path / "media")]

    out = tmp_path / "default.json"
    sd.main([*common, "--out", str(out)])
    assert [r["slug"] for r in json.loads(out.read_text())] == ["dji-mavic-3-pro"]

    out = tmp_path / "forced.json"
    sd.main([*common, "--out", str(out), "--include-pending"])
    assert [r["slug"] for r in json.loads(out.read_text())] == ["dji-mavic-3-pro", "pending-drone"]
