from __future__ import annotations

import csv
import difflib
import html
import json
import re
import shutil
import sys
import urllib.parse
import urllib.request
from collections import Counter, defaultdict
from dataclasses import dataclass
from datetime import datetime, timezone
from http.cookiejar import CookieJar
from pathlib import Path
from typing import Any

from lxml import html as lxml_html


ROOT = Path(__file__).resolve().parent
RAW_OFFICIAL_DIR = ROOT / "data" / "raw_official"
RAW_PUBLIC_DIR = ROOT / "data" / "raw_public"
PROCESSED_DIR = ROOT / "data" / "processed"
SITE_DIR = ROOT / "site"
SITE_DATA_DIR = SITE_DIR / "data"
SITE_DOWNLOADS_DIR = SITE_DIR / "downloads"
SITE_SHARE_DIR = SITE_DIR / "share"
OUTPUTS_DIR = ROOT / "outputs"
RAW_AFFIDAVIT_DIR = ROOT / "data" / "raw_affidavit"

SUPABASE_BASE = "https://ljbewpsksaetftwuaqaz.supabase.co/rest/v1"
FORM7A_LIST_URL = "https://erolls.tn.gov.in/acwithcandidate_tnla2026/AC_List.aspx"
FORM7A_BASE_URL = "https://erolls.tn.gov.in/acwithcandidate_tnla2026/Form7A.aspx"
AFFIDAVIT_BROWSER_URL = "https://voterlist.co.in/affidavit/"
AFFIDAVIT_MIRROR_AJAX_URL = "https://voterlist.co.in/wp-admin/admin-ajax.php"
AFFIDAVIT_MIRROR_STATE = "Tamil Nadu"
AFFIDAVIT_MIRROR_ACTIONS = {
    "bootstrap": "affidavit_extractor_frontend_bootstrap",
    "constituencies": "affidavit_extractor_frontend_constituencies",
    "candidates": "affidavit_extractor_frontend_candidates",
    "search": "affidavit_frontend_search",
}
SUPABASE_KEY = (
    "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9."
    "eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6ImxqYmV3cHNrc2FldGZ0d3VhcWF6Iiwicm9sZSI6ImFub24iLCJpYXQiOjE3NzM5MTkzMTAs"
    "ImV4cCI6MjA4OTQ5NTMxMH0.uX-cnXxHFXXBUed-B9j-02qQriYRuYihiOgiU9E_-CM"
)

USER_AGENT = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/135.0 Safari/537.36"
PAGE_PATH_OPTIONS = [
    "departments/election/tnlae-2026/expenditure/",
    "election-department/tnlae-2026/expenditure/",
]

DISTRICT_DOMAIN_OPTIONS = {
    "Tiruvallur": ["tiruvallur", "thiruvallur"],
    "Chennai": ["chennai"],
    "Chengalpattu": ["chengalpattu"],
    "Kanchipuram": ["kancheepuram", "kanchipuram"],
    "Ranipet": ["ranipet"],
    "Vellore": ["vellore"],
    "Tirupathur": ["tirupattur", "tirupathur"],
    "Krishnagiri": ["krishnagiri"],
    "Dharmapuri": ["dharmapuri"],
    "Tiruvannamalai": ["tiruvannamalai", "thiruvannamalai"],
    "Villupuram": ["viluppuram", "villupuram"],
    "Kallakurichi": ["kallakurichi"],
    "Salem": ["salem"],
    "Namakkal": ["namakkal"],
    "Erode": ["erode"],
    "Tirupur": ["tiruppur", "tirupur"],
    "Nilgiris": ["nilgiris", "the_nilgiris", "the-nilgiris"],
    "Coimbatore": ["coimbatore"],
    "Dindigul": ["dindigul"],
    "Karur": ["karur"],
    "Tiruchirappalli": ["tiruchirappalli", "trichy"],
    "Perambalur": ["perambalur"],
    "Ariyalur": ["ariyalur"],
    "Cuddalore": ["cuddalore"],
    "Mayiladuthurai": ["mayiladuthurai"],
    "Nagapattinam": ["nagapattinam"],
    "Tiruvarur": ["tiruvarur", "thiruvarur"],
    "Thanjavur": ["thanjavur", "tanjore"],
    "Pudukkottai": ["pudukkottai"],
    "Sivaganga": ["sivaganga"],
    "Madurai": ["madurai"],
    "Theni": ["theni"],
    "Virudhunagar": ["virudhunagar"],
    "Ramanathapuram": ["ramanathapuram", "ramnad"],
    "Thoothukudi": ["thoothukudi", "tuticorin"],
    "Tenkasi": ["tenkasi"],
    "Tirunelveli": ["tirunelveli"],
    "Kanyakumari": ["kanniyakumari", "kanyakumari", "nagercoil"],
}

PARTY_ABBREVIATIONS = {
    "ALL INDIA ANNA DRAVIDA MUNNETRA KAZHAGAM": "AIADMK",
    "ALL INDIA PURATCHI THALAIVAR MAKKAL MUNNETTRA KAZHAGAM": "AIPTMMK",
    "ANNA PURATCHI THALAIVAR AMMA DRAVIDA MUNNETRA KAZHAGAM": "APTADMK",
    "BAHUJAN SAMAJ PARTY": "BSP",
    "BHARATIYA JANATA PARTY": "BJP",
    "DRAVIDA MUNNETRA KAZHAGAM": "DMK",
    "GANASANGAM PARTY OF INDIA": "GSPI",
    "INDIAN NATIONAL CONGRESS": "INC",
    "INDEPENDENT": "IND",
    "INDEPENDEDNT": "IND",
    "NAAM TAMILAR KATCHI": "NTK",
    "NEW GENERATION PEOPLE’S PARTY": "NGPP",
    "PARTY FOR THE RIGHTS OF OTHER BACKWARD CLASSES": "PROBC",
    "RASHTRIYA SAMAJ DAL (R)": "RSD(R)",
    "SAMANIYA MAKKAL NALA KATCHI": "SMNK",
    "TAMILAGA MAKKAL NALA KATCHI": "TMNK",
    "TAMILAGA VETTRI KAZHAGAM": "TVK",
    "TAMIZHAGA MURPOKKU MAKKAL KATCHI": "TMMK",
    "TAMIZHAGA VAAZHVURIMAI KATCHI": "TVVK",
    "THAMIZHAKA PADAIPPALAR MAKKAL KATCHI": "TPMK",
    "VERATH THIYAGI VISWANATHADOSS THOZHILALARKAL KATCHI": "VTVTK",
}

PARTY_SYMBOLS = {
    "AIADMK": "Two Leaves",
    "BJP": "Lotus",
    "BSP": "Elephant",
    "DMK": "Rising Sun",
    "INC": "Hand",
    "NTK": "Microphone",
    "TVK": "To be verified",
    "IND": "",
}

PARTY_PRIORITY = [
    "DMK",
    "AIADMK",
    "BJP",
    "INC",
    "NTK",
    "TVK",
    "BSP",
    "IND",
]

UI_TEXT = {
    "brand": {"en": "Tamil Nadu 2026 Voter Facts", "ta": "தமிழ்நாடு 2026 வாக்காளர் தகவல்கள்"},
    "tagline": {
        "en": "Official contesting candidates, constituency context, and downloadable voter facts.",
        "ta": "அதிகாரப்பூர்வ வேட்பாளர் பட்டியல், தொகுதி தகவல்கள், பதிவிறக்கக் கூடிய வாக்காளர் உண்மைகள்.",
    },
    "home": {"en": "Home", "ta": "முகப்பு"},
    "constituencies": {"en": "Constituencies", "ta": "தொகுதிகள்"},
    "downloads": {"en": "Downloads", "ta": "பதிவிறக்கங்கள்"},
    "compare": {"en": "Compare", "ta": "ஒப்பிடு"},
    "district": {"en": "District", "ta": "மாவட்டம்"},
    "party": {"en": "Party", "ta": "கட்சி"},
    "candidate": {"en": "Candidate", "ta": "வேட்பாளர்"},
    "candidate_count": {"en": "Candidates", "ta": "வேட்பாளர்கள்"},
    "voters_2026": {"en": "Voters (2026)", "ta": "வாக்காளர்கள் (2026)"},
    "turnout_2021": {"en": "Turnout 2021", "ta": "2021 வாக்குப்பதிவு"},
    "margin_2021": {"en": "Margin 2021", "ta": "2021 வெற்றி வித்தியாசம்"},
    "winner_2021": {"en": "Winner 2021", "ta": "2021 வெற்றியாளர்"},
    "runner_up_2021": {"en": "Runner-up 2021", "ta": "2021 இரண்டாம் இடம்"},
    "assets": {"en": "Declared Assets", "ta": "அறிவித்த சொத்துகள்"},
    "liabilities": {"en": "Liabilities", "ta": "பாதகத் தொகைகள்"},
    "criminal_cases": {"en": "Criminal Cases", "ta": "குற்ற வழக்குகள்"},
    "education": {"en": "Education", "ta": "கல்வி"},
    "age": {"en": "Age", "ta": "வயது"},
    "affidavit": {"en": "Affidavit", "ta": "சத்தியப்பிரமாணம்"},
    "source": {"en": "Source", "ta": "மூலம்"},
    "source_date": {"en": "Source date", "ta": "மூல தேதி"},
    "last_updated": {"en": "Generated", "ta": "உருவாக்கப்பட்டது"},
    "search_placeholder": {
        "en": "Search candidate, constituency, district, or party",
        "ta": "வேட்பாளர், தொகுதி, மாவட்டம் அல்லது கட்சியைத் தேடுங்கள்",
    },
    "facts_notice": {
        "en": "Roster truth comes from the official statewide Form 7A HTML pages. Enrichment fields are matched cautiously from public historical data.",
        "ta": "வேட்பாளர் பட்டியல் அதிகாரப்பூர்வ மாவட்ட தேர்தல் பக்கங்களில் இருந்து பெறப்பட்டது. கூடுதல் தகவல்கள் பொதுப் பதிவுகளிலிருந்து கவனமாக பொருத்தப்பட்டவை.",
    },
}

UI_TEXT["facts_notice"]["ta"] = (
    "வேட்பாளர் பட்டியல் மாநில அளவிலான அதிகாரப்பூர்வ Form 7A HTML பக்கங்களில் இருந்து பெறப்பட்டது. "
    "கூடுதல் தகவல்கள் பொதுப் பதிவுகளிலிருந்து கவனமாக பொருத்தப்பட்டவை."
)


@dataclass
class DistrictFetchResult:
    district: str
    url: str
    last_updated: str | None
    html_path: str


def ensure_dirs() -> None:
    for path in [
        RAW_OFFICIAL_DIR,
        RAW_PUBLIC_DIR,
        PROCESSED_DIR,
        RAW_AFFIDAVIT_DIR,
        SITE_DIR,
        SITE_DATA_DIR,
        SITE_DOWNLOADS_DIR,
        SITE_SHARE_DIR / "constituencies",
        SITE_SHARE_DIR / "candidates",
        SITE_SHARE_DIR / "compare",
        OUTPUTS_DIR,
    ]:
        path.mkdir(parents=True, exist_ok=True)


def log(message: str) -> None:
    print(message, flush=True)


def slugify(text: str) -> str:
    cleaned = re.sub(r"[^a-z0-9]+", "-", text.lower()).strip("-")
    return cleaned or "item"


def normalize_text(text: str | None) -> str:
    if not text:
        return ""
    lowered = text.lower()
    lowered = lowered.replace("&", " and ")
    lowered = lowered.replace("@", " ")
    lowered = re.sub(r"\balias\b", " ", lowered)
    lowered = re.sub(r"\bdr\b\.?", " ", lowered)
    lowered = re.sub(r"\bsmt\b\.?", " ", lowered)
    lowered = re.sub(r"\bbe\b\.?", " ", lowered)
    lowered = re.sub(r"[^a-z0-9]+", " ", lowered)
    return " ".join(lowered.split())


def request_text(url: str, headers: dict[str, str] | None = None) -> str:
    req = urllib.request.Request(
        url,
        headers={
            "User-Agent": USER_AGENT,
            "Accept-Language": "en-US,en;q=0.9",
            **(headers or {}),
        },
    )
    with urllib.request.urlopen(req, timeout=25) as response:
        return response.read().decode("utf-8", errors="ignore")


def candidate_table_count(text: str) -> int:
    try:
        doc = lxml_html.fromstring(text)
    except Exception:  # noqa: BLE001
        return 0
    count = 0
    for table in doc.xpath("//table"):
        caption = " ".join(table.xpath("normalize-space(caption)").split()).lower()
        headers = " ".join(" ".join(cell.text_content().split()) for cell in table.xpath(".//th")).lower()
        if "candidate" in headers and "party" in headers:
            count += 1
        elif "assembly constituency" in caption:
            count += 1
    return count


def looks_like_candidate_page(text: str) -> bool:
    lowered = text.lower()
    return (
        "candidate" in lowered
        and "expenditure" in lowered
        and ("2026" in lowered or "getnla-2026" in lowered or "tnla" in lowered)
        and candidate_table_count(text) > 0
    )


def discover_candidate_page(base_url: str) -> str | None:
    try:
        root_text = request_text(base_url)
    except Exception:  # noqa: BLE001
        return None

    base_host = urllib.parse.urlparse(base_url).netloc
    seen = {base_url}
    queue: list[tuple[str, str, int]] = [(base_url, root_text, 0)]

    while queue:
        current_url, current_text, depth = queue.pop(0)
        if looks_like_candidate_page(current_text):
            return current_url
        if depth >= 2:
            continue

        try:
            doc = lxml_html.fromstring(current_text)
        except Exception:  # noqa: BLE001
            continue

        scored_links: list[tuple[int, str]] = []
        for anchor in doc.xpath("//a[@href]"):
            href = urllib.parse.urljoin(current_url, anchor.get("href"))
            parsed = urllib.parse.urlparse(href)
            if parsed.netloc != base_host:
                continue
            text = " ".join(anchor.text_content().split())
            haystack = f"{text} {href}".lower()
            score = 0
            if "candidate" in haystack and "expenditure" in haystack:
                score += 7
            if "tnla" in haystack or "2026" in haystack or "election" in haystack:
                score += 3
            if "know your candidate" in haystack:
                score += 1
            if "affidavit" in haystack:
                score += 1
            if score and href not in seen:
                scored_links.append((score, href))

        for _, href in sorted(scored_links, key=lambda item: (-item[0], item[1]))[:15]:
            seen.add(href)
            try:
                text = request_text(href)
                queue.append((href, text, depth + 1))
            except Exception:  # noqa: BLE001
                continue
    return None


def fetch_official_pages(constituencies: list[dict[str, Any]]) -> list[DistrictFetchResult]:
    districts = []
    for row in constituencies:
        if row["district"] not in districts:
            districts.append(row["district"])

    results: list[DistrictFetchResult] = []
    failures: list[str] = []
    cached_manifest_path = RAW_OFFICIAL_DIR / "manifest.json"
    cached_manifest = {}
    if cached_manifest_path.exists():
        try:
            cached_manifest = {
                item["district"]: item
                for item in json.loads(cached_manifest_path.read_text(encoding="utf-8"))
            }
        except Exception:  # noqa: BLE001
            cached_manifest = {}

    for district in districts:
        cached_path = RAW_OFFICIAL_DIR / f"{slugify(district)}.html"
        cached_item = cached_manifest.get(district)
        if cached_path.exists():
            cached_text = cached_path.read_text(encoding="utf-8", errors="ignore")
            if looks_like_candidate_page(cached_text):
                results.append(
                    DistrictFetchResult(
                        district=district,
                        url=(cached_item or {}).get("url", ""),
                        last_updated=(cached_item or {}).get("last_updated"),
                        html_path=str(cached_path),
                    )
                )
                log(f"[official] reused {district}: {cached_path.name}")
                continue

        slug_options = DISTRICT_DOMAIN_OPTIONS.get(district, [slugify(district)])
        success = None
        last_error = None

        for domain_slug in slug_options:
            base_url = f"https://{domain_slug}.nic.in/"
            for path in PAGE_PATH_OPTIONS:
                url = urllib.parse.urljoin(base_url, path)
                try:
                    text = request_text(url)
                    if not looks_like_candidate_page(text):
                        raise ValueError("expected candidate page marker not found")
                    match = re.search(r"Last Updated:\s*<strong>([^<]+)</strong>", text, re.I)
                    file_path = RAW_OFFICIAL_DIR / f"{slugify(district)}.html"
                    file_path.write_text(text, encoding="utf-8")
                    success = DistrictFetchResult(
                        district=district,
                        url=url,
                        last_updated=match.group(1).strip() if match else None,
                        html_path=str(file_path),
                    )
                    break
                except Exception as exc:  # noqa: BLE001
                    last_error = str(exc)
            if success:
                break

            discovered_url = discover_candidate_page(base_url)
            if discovered_url:
                try:
                    text = request_text(discovered_url)
                    match = re.search(r"Last Updated:\s*<strong>([^<]+)</strong>", text, re.I)
                    file_path = RAW_OFFICIAL_DIR / f"{slugify(district)}.html"
                    file_path.write_text(text, encoding="utf-8")
                    success = DistrictFetchResult(
                        district=district,
                        url=discovered_url,
                        last_updated=match.group(1).strip() if match else None,
                        html_path=str(file_path),
                    )
                    break
                except Exception as exc:  # noqa: BLE001
                    last_error = str(exc)

        if success:
            log(f"[official] fetched {district}: {success.url}")
            results.append(success)
        else:
            failures.append(f"{district}: {last_error or 'unknown error'}")

    manifest_path = RAW_OFFICIAL_DIR / "manifest.json"
    manifest_path.write_text(
        json.dumps([result.__dict__ for result in results], indent=2, ensure_ascii=False),
        encoding="utf-8",
    )

    if failures:
        (RAW_OFFICIAL_DIR / "failures.json").write_text(
            json.dumps(failures, indent=2, ensure_ascii=False),
            encoding="utf-8",
        )
        raise RuntimeError("Official page fetch failures:\n" + "\n".join(failures))

    return results


def fetch_supabase_rows(
    table: str,
    query: str = "",
    page_size: int = 1000,
) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    start = 0
    while True:
        end = start + page_size - 1
        headers = {
            "apikey": SUPABASE_KEY,
            "Authorization": f"Bearer {SUPABASE_KEY}",
            "Range-Unit": "items",
            "Range": f"{start}-{end}",
        }
        url = f"{SUPABASE_BASE}/{table}"
        if query:
            url += "?" + query
        payload = request_text(url, headers=headers)
        page = json.loads(payload or "[]")
        if not page:
            break
        rows.extend(page)
        if len(page) < page_size:
            break
        start += page_size
    return rows


def fetch_public_context() -> dict[str, list[dict[str, Any]]]:
    context = {
        "constituencies": fetch_supabase_rows(
            "constituencies",
            urllib.parse.urlencode(
                {
                    "select": "id,name,district,total_voters_2021,turnout_2021,voters_total_2026,"
                    "voters_male_2026,voters_female_2026,voters_third_gender_2026,current_mla,current_mla_party,is_swing_seat",
                    "order": "id",
                }
            ),
        ),
        "election_results": fetch_supabase_rows(
            "election_results",
            urllib.parse.urlencode(
                {
                    "select": "*",
                    "election_year": "eq.2021",
                    "order": "constituency_id",
                }
            ),
        ),
        "candidates_2021": fetch_supabase_rows(
            "candidates",
            urllib.parse.urlencode(
                {
                    "select": "*",
                    "election_year": "eq.2021",
                    "order": "constituency_id,id",
                }
            ),
        ),
    }

    for key, rows in context.items():
        (RAW_PUBLIC_DIR / f"{key}.json").write_text(
            json.dumps(rows, indent=2, ensure_ascii=False),
            encoding="utf-8",
        )
    return context


def fetch_affidavit_browser_nonce() -> str:
    page_text = request_text(AFFIDAVIT_BROWSER_URL)
    (RAW_AFFIDAVIT_DIR / "browser.html").write_text(page_text, encoding="utf-8")
    match = re.search(r'"nonce":"([^"]+)"', page_text)
    if not match:
        raise ValueError("Unable to locate affidavit browser nonce")
    return match.group(1)


def post_affidavit_browser(action: str, nonce: str, params: dict[str, Any] | None = None) -> dict[str, Any]:
    body = {"action": action, "nonce": nonce, **(params or {})}
    req = urllib.request.Request(
        AFFIDAVIT_MIRROR_AJAX_URL,
        data=urllib.parse.urlencode(body).encode(),
        headers={
            "User-Agent": USER_AGENT,
            "Content-Type": "application/x-www-form-urlencoded; charset=UTF-8",
            "Accept": "application/json, text/javascript, */*; q=0.01",
            "Referer": AFFIDAVIT_BROWSER_URL,
        },
    )
    with urllib.request.urlopen(req, timeout=25) as response:
        return json.loads(response.read().decode("utf-8", errors="ignore"))


def parse_affidavit_download_key(url: str | None) -> tuple[int, int]:
    if not url:
        return (0, -1)
    match = re.search(r"/affidavit-download/(\d+)/(\d+)/", url)
    if not match:
        return (0, -1)
    return (int(match.group(1)), int(match.group(2)))


def latest_affidavit_download_url(candidate: dict[str, Any]) -> str:
    links = candidate.get("affidavit_download_links") or []
    if not links:
        return ""
    return max(links, key=parse_affidavit_download_key)


def resolve_mirror_reference_url(candidate: dict[str, Any]) -> str:
    latest_url = latest_affidavit_download_url(candidate)
    return latest_url or ""


def image_timestamp_key(candidate: dict[str, Any]) -> str:
    match = re.search(r"(\d{14})(?=\.[A-Za-z]+$)", candidate.get("image_url", ""))
    return match.group(1) if match else ""


def fetch_affidavit_mirror_context(state_name: str = AFFIDAVIT_MIRROR_STATE) -> dict[str, Any]:
    nonce = fetch_affidavit_browser_nonce()
    bootstrap = post_affidavit_browser(AFFIDAVIT_MIRROR_ACTIONS["bootstrap"], nonce)
    constituencies_payload = post_affidavit_browser(
        AFFIDAVIT_MIRROR_ACTIONS["constituencies"],
        nonce,
        {"state": state_name},
    )
    constituencies = constituencies_payload.get("data", {}).get("constituencies", [])
    (RAW_AFFIDAVIT_DIR / "bootstrap.json").write_text(json.dumps(bootstrap, indent=2, ensure_ascii=False), encoding="utf-8")
    (RAW_AFFIDAVIT_DIR / "constituencies.json").write_text(
        json.dumps(constituencies_payload, indent=2, ensure_ascii=False),
        encoding="utf-8",
    )

    all_candidates: list[dict[str, Any]] = []
    for constituency in constituencies:
        constituency_name = constituency["constituency"]
        payload = post_affidavit_browser(
            AFFIDAVIT_MIRROR_ACTIONS["candidates"],
            nonce,
            {"state": state_name, "constituency": constituency_name},
        )
        raw_name = f"{slugify(constituency_name)}.json"
        (RAW_AFFIDAVIT_DIR / raw_name).write_text(json.dumps(payload, indent=2, ensure_ascii=False), encoding="utf-8")
        for candidate in payload.get("data", {}).get("candidates", []):
            enriched = dict(candidate)
            enriched["mirror_state"] = state_name
            enriched["mirror_constituency"] = constituency_name
            enriched["mirror_latest_affidavit_url"] = latest_affidavit_download_url(candidate)
            enriched["mirror_image_timestamp"] = image_timestamp_key(candidate)
            all_candidates.append(enriched)
        log(f"[affidavit] fetched {constituency_name}")

    combined = {
        "state": state_name,
        "nonce": nonce,
        "constituencies": constituencies,
        "candidates": all_candidates,
        "disclaimer": bootstrap.get("data", {}).get("disclaimer") or constituencies_payload.get("data", {}).get("disclaimer", ""),
    }
    (RAW_AFFIDAVIT_DIR / "combined.json").write_text(json.dumps(combined, indent=2, ensure_ascii=False), encoding="utf-8")
    return combined


def build_affidavit_constituency_alias_map(
    official_rows: list[dict[str, Any]],
    affidavit_candidates: list[dict[str, Any]],
) -> dict[str, str]:
    affidavit_keys = sorted({normalize_text(row.get("mirror_constituency")) for row in affidavit_candidates if row.get("mirror_constituency")})
    alias_map: dict[str, str] = {}
    for official_name in sorted({row["constituency_name"] for row in official_rows}):
        official_key = normalize_text(official_name)
        if official_key in affidavit_keys:
            alias_map[official_key] = official_key
            continue
        matches = difflib.get_close_matches(official_key, affidavit_keys, n=1, cutoff=0.84)
        if matches:
            alias_map[official_key] = matches[0]
    return alias_map


def choose_affidavit_candidate(
    official_row: dict[str, Any],
    candidates: list[dict[str, Any]],
) -> tuple[dict[str, Any] | None, str]:
    if not candidates:
        return None, "none"

    official_name = normalize_text(official_row["candidate_name"])
    official_name_loose = normalize_text(re.sub(r"\([^)]*\)", " ", official_row["candidate_name"]))
    official_party_name = normalize_text(official_row["party_name"])
    official_party_abbrev = official_row["party_abbrev"]

    def party_match(candidate: dict[str, Any]) -> int:
        candidate_party_name = normalize_text(candidate.get("party"))
        candidate_party_abbrev = party_abbreviation(candidate.get("party", ""))
        return int(candidate_party_abbrev == official_party_abbrev or candidate_party_name == official_party_name)

    def candidate_score(candidate: dict[str, Any]) -> tuple[Any, ...]:
        return (
            party_match(candidate),
            int(bool(candidate.get("gender"))),
            int(bool(candidate.get("age"))),
            parse_affidavit_download_key(candidate.get("mirror_latest_affidavit_url")),
            candidate.get("mirror_image_timestamp", ""),
            len(candidate.get("affidavit_download_links") or []),
            len(candidate.get("name", "")),
        )

    exact = [candidate for candidate in candidates if normalize_text(candidate.get("name")) == official_name]
    if exact:
        return max(exact, key=candidate_score), "affidavit_exact"

    loose = [candidate for candidate in candidates if normalize_text(re.sub(r"\([^)]*\)", " ", candidate.get("name", ""))) == official_name_loose]
    if loose:
        return max(loose, key=candidate_score), "affidavit_loose"

    return None, "none"


def build_form7a_opener() -> urllib.request.OpenerDirector:
    return urllib.request.build_opener(urllib.request.HTTPCookieProcessor(CookieJar()))


def extract_hidden_fields(page_text: str) -> dict[str, str]:
    return {
        match.group(1): match.group(2)
        for match in re.finditer(r'<input type="hidden" name="([^"]+)" id="[^"]*" value="([^"]*)"', page_text)
    }


def fetch_statewide_form7a_rows(constituencies_public: list[dict[str, Any]]) -> list[dict[str, Any]]:
    opener = build_form7a_opener()
    list_html = opener.open(urllib.request.Request(FORM7A_LIST_URL, headers={"User-Agent": USER_AGENT}), timeout=25).read().decode(
        "utf-8",
        errors="ignore",
    )
    (RAW_OFFICIAL_DIR / "ac_list.html").write_text(list_html, encoding="utf-8")

    hidden_fields = extract_hidden_fields(list_html)
    list_doc = lxml_html.fromstring(list_html)
    constituency_rows = []
    for tr in list_doc.xpath("//table[contains(@class,'tableList')]//tr[td]"):
        cells = tr.xpath("./td")
        if len(cells) != 2:
            continue
        number_text = " ".join(cells[0].text_content().split())
        try:
            constituency_no = int(number_text)
        except ValueError:
            continue
        anchor = cells[1].xpath(".//a")[0]
        href = anchor.get("href", "")
        event_match = re.search(r"__doPostBack\('([^']+)'", href)
        if not event_match:
            continue
        constituency_rows.append(
            {
                "constituency_no": constituency_no,
                "constituency_name": " ".join(anchor.text_content().split()),
                "event_target": event_match.group(1),
            }
        )

    constituency_lookup_by_id = {row["id"]: row for row in constituencies_public}
    constituency_lookup_by_name = {normalize_text(row.get("name")): row for row in constituencies_public}
    official_rows: list[dict[str, Any]] = []
    fetch_date = datetime.now(timezone.utc).date().isoformat()

    for item in constituency_rows:
        form_fields = dict(hidden_fields)
        form_fields["__EVENTTARGET"] = item["event_target"]
        form_fields["__EVENTARGUMENT"] = ""
        form_fields["__LASTFOCUS"] = ""
        post_data = urllib.parse.urlencode(form_fields).encode()
        response_html = opener.open(
            urllib.request.Request(
                FORM7A_LIST_URL,
                data=post_data,
                headers={
                    "User-Agent": USER_AGENT,
                    "Content-Type": "application/x-www-form-urlencoded",
                },
            ),
            timeout=25,
        ).read().decode("utf-8", errors="ignore")

        raw_path = RAW_OFFICIAL_DIR / f"form7a-{item['constituency_no']:03d}-{slugify(item['constituency_name'])}.html"
        raw_path.write_text(response_html, encoding="utf-8")

        doc = lxml_html.fromstring(response_html)
        table = doc.xpath("//table")[0]
        response_constituency_name = item["constituency_name"]
        heading = doc.xpath("normalize-space(//h2)")
        heading_match = re.search(r"Name of the Assembly Constituency:\s*(.+)", heading)
        if heading_match:
            response_constituency_name = heading_match.group(1).strip()
        constituency_ref = constituency_lookup_by_id.get(item["constituency_no"]) or constituency_lookup_by_name.get(
            normalize_text(response_constituency_name)
        ) or constituency_lookup_by_name.get(normalize_text(item["constituency_name"]))
        district = constituency_ref.get("district", "") if constituency_ref else ""
        public_constituency_id = constituency_ref.get("id", item["constituency_no"]) if constituency_ref else item["constituency_no"]

        seen = set()
        for tr in table.xpath(".//tr[td]"):
            cells = [" ".join(td.text_content().split()) for td in tr.xpath("./td")]
            if len(cells) != 4:
                continue
            if cells[0].lower().startswith("sl.no"):
                continue
            try:
                serial = int(cells[0])
            except ValueError:
                continue
            candidate_name = cells[1].strip()
            party_name = cells[2].strip()
            symbol = cells[3].strip()
            dedupe_key = (item["constituency_no"], normalize_text(candidate_name), normalize_text(party_name), normalize_text(symbol))
            if dedupe_key in seen:
                continue
            seen.add(dedupe_key)
            official_rows.append(
                {
                    "candidate_uid": f"tn2026-{item['constituency_no']:03d}-{len(official_rows)+1:04d}",
                    "candidate_name": candidate_name,
                    "party_name": party_name,
                    "party_abbrev": party_abbreviation(party_name),
                    "constituency_no": item["constituency_no"],
                    "public_constituency_id": public_constituency_id,
                    "constituency_name": response_constituency_name,
                    "district": district,
                    "symbol": symbol,
                    "gender": "",
                    "source_url": FORM7A_BASE_URL,
                    "source_document": f"Form 7A - {response_constituency_name}",
                    "source_date": fetch_date,
                    "serial_no": serial,
                }
            )
        log(f"[official] fetched Form 7A {item['constituency_no']:03d} {response_constituency_name}")

    (RAW_OFFICIAL_DIR / "manifest.json").write_text(
        json.dumps(
            [
                {
                    "constituency_no": row["constituency_no"],
                    "constituency_name": row["constituency_name"],
                    "source_url": FORM7A_BASE_URL,
                    "source_date": fetch_date,
                }
                for row in constituency_rows
            ],
            indent=2,
            ensure_ascii=False,
        ),
        encoding="utf-8",
    )
    return official_rows


def parse_date_label(value: str | None) -> str | None:
    if not value:
        return None
    for fmt in ("%b %d, %Y", "%B %d, %Y"):
        try:
            return datetime.strptime(value.strip(), fmt).date().isoformat()
        except ValueError:
            continue
    return value


def party_abbreviation(party_name: str) -> str:
    upper = party_name.upper().strip()
    if upper in PARTY_ABBREVIATIONS:
        return PARTY_ABBREVIATIONS[upper]
    letters = [token[0] for token in re.findall(r"[A-Z]+", upper)]
    if letters:
        return "".join(letters[:8])
    return upper[:12]


def load_official_rows(manifest: list[DistrictFetchResult]) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    seen = set()

    for item in manifest:
        doc = lxml_html.fromstring(Path(item.html_path).read_text(encoding="utf-8", errors="ignore"))
        title = doc.xpath("normalize-space(//title)")
        for table in doc.xpath("//table[@id]"):
            caption = " ".join(table.xpath("normalize-space(caption)").split())
            match = re.match(r"(\d+)\s*-\s*(.+?)\s*,?\s+ASSEMBLY CONSTITUENCY", caption, re.I)
            if not match:
                continue
            constituency_no = int(match.group(1))
            constituency_name = match.group(2).strip()

            for tr in table.xpath("./tbody/tr"):
                cells = [" ".join("".join(td.itertext()).split()) for td in tr.xpath("./td")]
                if len(cells) < 3:
                    continue
                s_no = cells[0].strip()
                candidate_name = cells[1].strip()
                party_name = cells[2].strip()
                if not candidate_name or not party_name:
                    continue

                dedupe_key = (constituency_no, normalize_text(candidate_name), normalize_text(party_name))
                if dedupe_key in seen:
                    continue
                seen.add(dedupe_key)

                abbrev = party_abbreviation(party_name)
                rows.append(
                    {
                        "candidate_uid": f"tn2026-{constituency_no:03d}-{len(rows)+1:04d}",
                        "candidate_name": candidate_name,
                        "party_name": party_name,
                        "party_abbrev": abbrev,
                        "constituency_no": constituency_no,
                        "constituency_name": constituency_name,
                        "district": item.district,
                        "symbol": PARTY_SYMBOLS.get(abbrev, ""),
                        "gender": "",
                        "source_url": item.url,
                        "source_document": title or "GENERAL ELECTIONS TO TNLA 2026 – Candidate Election Expenditure",
                        "source_date": parse_date_label(item.last_updated),
                        "serial_no": s_no,
                    }
                )
    return rows


def match_and_enrich(
    official_rows: list[dict[str, Any]],
    public_context: dict[str, list[dict[str, Any]]],
    affidavit_context: dict[str, Any] | None = None,
) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    constituency_by_id = {row["id"]: row for row in public_context["constituencies"]}
    constituency_by_name = {normalize_text(row.get("name")): row for row in public_context["constituencies"]}
    result_by_constituency = {row["constituency_id"]: row for row in public_context["election_results"]}
    result_by_name: dict[str, dict[str, Any]] = {}
    for result in public_context["election_results"]:
        constituency = constituency_by_id.get(result["constituency_id"])
        if constituency:
            result_by_name[normalize_text(constituency.get("name"))] = result

    candidate_index: dict[tuple[int, str], list[dict[str, Any]]] = defaultdict(list)
    loose_candidate_index: dict[tuple[int, str], list[dict[str, Any]]] = defaultdict(list)
    for row in public_context["candidates_2021"]:
        exact_key = (row["constituency_id"], normalize_text(row.get("name")))
        loose_key = (row["constituency_id"], normalize_text(re.sub(r"\([^)]*\)", " ", row.get("name", ""))))
        candidate_index[exact_key].append(row)
        loose_candidate_index[loose_key].append(row)

    affidavit_candidates = affidavit_context.get("candidates", []) if affidavit_context else []
    affidavit_constituency_alias_map = build_affidavit_constituency_alias_map(official_rows, affidavit_candidates) if affidavit_candidates else {}
    affidavit_by_constituency: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for candidate in affidavit_candidates:
        affidavit_by_constituency[normalize_text(candidate.get("mirror_constituency"))].append(candidate)

    enrichment_rows: list[dict[str, Any]] = []
    enriched_master: list[dict[str, Any]] = []

    for row in official_rows:
        public_constituency_id = row.get("public_constituency_id") or row["constituency_no"]
        constituency = constituency_by_id.get(public_constituency_id) or constituency_by_name.get(normalize_text(row["constituency_name"]))
        if constituency:
            public_constituency_id = constituency["id"]
        result_2021 = result_by_constituency.get(public_constituency_id) or result_by_name.get(normalize_text(row["constituency_name"]))
        exact_matches = candidate_index.get((public_constituency_id, normalize_text(row["candidate_name"])), [])
        loose_matches = loose_candidate_index.get(
            (
                public_constituency_id,
                normalize_text(re.sub(r"\([^)]*\)", " ", row["candidate_name"])),
            ),
            [],
        )

        match_method = "none"
        matched = None
        ambiguous = False
        if len(exact_matches) == 1:
            matched = exact_matches[0]
            match_method = "exact_normalized"
        elif len(exact_matches) > 1:
            ambiguous = True
            match_method = "ambiguous_exact"
        elif len(loose_matches) == 1:
            matched = loose_matches[0]
            match_method = "exact_loose"
        elif len(loose_matches) > 1:
            ambiguous = True
            match_method = "ambiguous_loose"

        affidavit_candidates_for_constituency = affidavit_by_constituency.get(
            affidavit_constituency_alias_map.get(normalize_text(row["constituency_name"]), normalize_text(row["constituency_name"])),
            [],
        )
        affidavit_match, affidavit_match_method = choose_affidavit_candidate(row, affidavit_candidates_for_constituency)
        affidavit_reference_url = resolve_mirror_reference_url(affidavit_match) if affidavit_match else ""

        age_value = affidavit_match.get("age") if affidavit_match and affidavit_match.get("age") else matched.get("age") if matched else ""
        gender_value = affidavit_match.get("gender") if affidavit_match and affidavit_match.get("gender") else row.get("gender", "")
        education_value = matched.get("education") if matched else ""
        assets_value = matched.get("net_worth") if matched else ""
        liabilities_value = matched.get("liabilities") if matched else ""
        criminal_cases_value = matched.get("criminal_cases_declared") if matched else ""
        criminal_cases_flag = ""
        if criminal_cases_value not in ("", None):
            try:
                criminal_cases_flag = "Y" if float(criminal_cases_value) > 0 else "N"
            except (TypeError, ValueError):
                criminal_cases_flag = "Y" if str(criminal_cases_value).strip() else ""

        enrichment = {
            "candidate_uid": row["candidate_uid"],
            "public_constituency_id": public_constituency_id,
            "match_method": match_method,
            "match_ambiguous": ambiguous,
            "matched_candidate_2021_id": matched["id"] if matched else "",
            "affidavit_match_method": affidavit_match_method,
            "age": age_value,
            "age_source": "2026 affidavit mirror" if affidavit_match and affidavit_match.get("age") else "2021 public match" if matched and matched.get("age") else "",
            "gender": gender_value,
            "gender_source": "2026 affidavit mirror" if affidavit_match and affidavit_match.get("gender") else "",
            "education": education_value,
            "education_source": "2021 public match" if education_value not in ("", None) else "",
            "declared_assets": assets_value,
            "declared_assets_source": "2021 public match" if assets_value not in ("", None) else "",
            "assets_movable": matched.get("assets_movable") if matched else "",
            "assets_immovable": matched.get("assets_immovable") if matched else "",
            "liabilities": liabilities_value,
            "liabilities_source": "2021 public match" if liabilities_value not in ("", None) else "",
            "criminal_cases_declared": criminal_cases_value,
            "criminal_cases_flag": criminal_cases_flag,
            "criminal_cases_source": "2021 public match" if criminal_cases_value not in ("", None) else "",
            "affidavit_url": matched.get("affidavit_url") if matched else "",
            "affidavit_reference_url": affidavit_reference_url,
            "candidate_reference_url": affidavit_reference_url or (matched.get("affidavit_url") if matched else ""),
            "affidavit_reference_source": "voterlist.co.in mirror of affidavit.eci.gov.in" if affidavit_reference_url else "",
            "affidavit_parse_status": "reference_link_available_pdf_blocked" if affidavit_reference_url else "not_available",
            "votes_2021": matched.get("votes_received") if matched else "",
            "vote_share_2021": matched.get("vote_share") if matched else "",
            "winner_2021": result_2021.get("winner_name") if result_2021 else "",
            "winner_party_2021": result_2021.get("winner_party") if result_2021 else "",
            "runner_up_2021": result_2021.get("runner_up_name") if result_2021 else "",
            "runner_up_party_2021": result_2021.get("runner_up_party") if result_2021 else "",
            "margin_2021": result_2021.get("margin") if result_2021 else "",
            "turnout_2021": result_2021.get("turnout") if result_2021 else constituency.get("turnout_2021") if constituency else "",
            "total_votes_2021": result_2021.get("total_votes") if result_2021 else "",
            "total_candidates_2021": result_2021.get("total_candidates") if result_2021 else "",
            "current_mla": constituency.get("current_mla") if constituency else "",
            "current_mla_party": constituency.get("current_mla_party") if constituency else "",
            "voters_total_2026": constituency.get("voters_total_2026") if constituency else "",
            "voters_male_2026": constituency.get("voters_male_2026") if constituency else "",
            "voters_female_2026": constituency.get("voters_female_2026") if constituency else "",
            "voters_third_gender_2026": constituency.get("voters_third_gender_2026") if constituency else "",
            "is_swing_seat": constituency.get("is_swing_seat") if constituency else "",
        }
        enrichment_rows.append(enrichment)
        enriched_master.append({**row, **enrichment})

    return enriched_master, enrichment_rows


def make_constituency_summaries(full_rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    by_constituency: dict[int, list[dict[str, Any]]] = defaultdict(list)
    for row in full_rows:
        by_constituency[row["constituency_no"]].append(row)

    summaries: list[dict[str, Any]] = []
    for constituency_no, rows in sorted(by_constituency.items()):
        first = rows[0]
        party_counts = Counter(row["party_abbrev"] for row in rows)
        top_parties = ", ".join(
            f"{abbr}:{count}"
            for abbr, count in sorted(
                party_counts.items(),
                key=lambda item: (PARTY_PRIORITY.index(item[0]) if item[0] in PARTY_PRIORITY else 999, -item[1], item[0]),
            )[:5]
        )
        summaries.append(
            {
                "constituency_no": constituency_no,
                "constituency_name": first["constituency_name"],
                "constituency_slug": slugify(first["constituency_name"]),
                "district": first["district"],
                "candidate_count_2026": len(rows),
                "party_count_2026": len({row["party_name"] for row in rows}),
                "independent_count_2026": sum(1 for row in rows if row["party_abbrev"] == "IND"),
                "top_parties_2026": top_parties,
                "winner_2021": first["winner_2021"],
                "winner_party_2021": first["winner_party_2021"],
                "runner_up_2021": first["runner_up_2021"],
                "runner_up_party_2021": first["runner_up_party_2021"],
                "margin_2021": first["margin_2021"],
                "turnout_2021": first["turnout_2021"],
                "voters_total_2026": first["voters_total_2026"],
                "voters_male_2026": first["voters_male_2026"],
                "voters_female_2026": first["voters_female_2026"],
                "voters_third_gender_2026": first["voters_third_gender_2026"],
                "current_mla": first["current_mla"],
                "current_mla_party": first["current_mla_party"],
                "source_url": first["source_url"],
                "source_date": first["source_date"],
            }
        )
    return summaries


def csv_write(path: Path, rows: list[dict[str, Any]]) -> None:
    if not rows:
        raise ValueError(f"No rows available for {path.name}")
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(rows[0].keys()))
        writer.writeheader()
        writer.writerows(rows)


def html_text(value: Any) -> str:
    if value is None or value == "":
        return "—"
    if isinstance(value, float):
        if value.is_integer():
            return f"{int(value):,}"
        return f"{value:,.2f}"
    if isinstance(value, int):
        return f"{value:,}"
    return html.escape(str(value))


def currency_text(value: Any) -> str:
    if value in ("", None):
        return "—"
    try:
        amount = float(value)
    except (TypeError, ValueError):
        return html.escape(str(value))
    return f"₹{amount:,.0f}"


def cases_flag_text(value: Any) -> str:
    if value in ("", None):
        return "â€”"
    text = str(value).strip().upper()
    if text in {"Y", "N"}:
        return text
    try:
        return "Y" if float(value) > 0 else "N"
    except (TypeError, ValueError):
        return html.escape(str(value))


def bi_text(en: str, ta: str) -> str:
    return f'<span class="lang-en">{html.escape(en)}</span><span class="lang-ta">{html.escape(ta)}</span>'


def symbol_monogram(symbol: Any, fallback: str = "") -> str:
    words = re.findall(r"[A-Za-z0-9]+", str(symbol or "").strip())
    if not words:
        words = re.findall(r"[A-Za-z0-9]+", str(fallback or "").strip())
    if not words:
        return "IND"
    if len(words) == 1:
        return words[0][:3].upper()
    return "".join(word[0].upper() for word in words[:3])


def symbol_icon(symbol: Any, fallback: str = "") -> str:
    label = f"{symbol or ''} {fallback or ''}".lower()
    icon_map = [
        ("rising sun", "🌅"),
        ("sun", "☀"),
        ("lotus", "🪷"),
        ("elephant", "🐘"),
        ("camera", "📷"),
        ("two leaves", "🍃"),
        ("leaf", "🍃"),
        ("leaves", "🍃"),
        ("farmer carrying plough", "🚜"),
        ("gas cylinder", "🛢"),
        ("balloon", "🎈"),
        ("bangles", "⭕"),
        ("pestle and mortar", "⚗"),
        ("coconut", "🥥"),
        ("bow and arrow", "🏹"),
        ("torch", "🔦"),
        ("kite", "🪁"),
        ("ganna kisan", "🌾"),
        ("air conditioner", "❄"),
        ("phone", "☎"),
        ("auto rickshaw", "🛺"),
        ("drum", "🥁"),
        ("cup and saucer", "☕"),
        ("pen", "🖊"),
        ("ring", "💍"),
        ("table", "🪑"),
        ("sewing machine", "🧵"),
        ("road roller", "🚧"),
        ("ship", "🚢"),
        ("mango", "🥭"),
        ("fish", "🐟"),
        ("chair", "🪑"),
        ("star", "⭐"),
        ("clock", "🕒"),
    ]
    for needle, icon in icon_map:
        if needle in label:
            return icon
    if "ind" in label or "independent" in label:
        return "🗳"
    return "◉"


def render_layout(title: str, body: str, relative_prefix: str = "") -> str:
    nav = f"""
    <header class="topbar">
      <div class="wrap topbar-inner">
        <a class="brand" href="{relative_prefix}index.html">{bi_text(UI_TEXT['brand']['en'], UI_TEXT['brand']['ta'])}</a>
        <nav class="nav">
          <a href="{relative_prefix}index.html">{bi_text(UI_TEXT['home']['en'], UI_TEXT['home']['ta'])}</a>
          <a href="{relative_prefix}constituencies/index.html">{bi_text(UI_TEXT['constituencies']['en'], UI_TEXT['constituencies']['ta'])}</a>
          <a href="{relative_prefix}downloads/index.html">{bi_text(UI_TEXT['downloads']['en'], UI_TEXT['downloads']['ta'])}</a>
        </nav>
        <button class="lang-toggle" type="button" onclick="toggleLanguage()">தமிழ் / EN</button>
      </div>
    </header>
    """
    return f"""<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>{html.escape(title)}</title>
  <link rel="stylesheet" href="{relative_prefix}styles.css">
</head>
<body data-lang="en">
  {nav}
  <main class="wrap">
    {body}
  </main>
  <script src="{relative_prefix}app.js"></script>
</body>
</html>
"""


def write_common_assets(site_meta: dict[str, Any]) -> None:
    styles = """
:root{
  --bg:#f5efe3;
  --card:#fffaf1;
  --ink:#1f2933;
  --muted:#64748b;
  --accent:#9a3412;
  --accent-soft:#fed7aa;
  --line:#e7d7c2;
}
*{box-sizing:border-box}
body{margin:0;font-family:Georgia,"Noto Serif Tamil",serif;background:linear-gradient(180deg,#f7f1e8 0,#efe5d3 100%);color:var(--ink)}
a{color:var(--accent);text-decoration:none}
a:hover{text-decoration:underline}
.wrap{width:min(1180px,calc(100% - 32px));margin:0 auto}
.topbar{position:sticky;top:0;z-index:10;background:rgba(255,250,241,.94);backdrop-filter:blur(8px);border-bottom:1px solid var(--line)}
.topbar-inner{display:flex;gap:16px;align-items:center;justify-content:space-between;padding:14px 0}
.brand{font-size:1.05rem;font-weight:700;max-width:320px}
.nav{display:flex;gap:16px;flex-wrap:wrap;justify-content:center}
.nav a{font-weight:600}
.lang-toggle{border:1px solid var(--accent);background:#fff;border-radius:999px;padding:8px 12px;color:var(--accent);font-weight:700;cursor:pointer}
.hero{padding:40px 0 20px}
.hero h1{font-size:clamp(2rem,4vw,3.3rem);line-height:1.04;margin:0 0 10px}
.hero p{max-width:760px;color:var(--muted);font-size:1.05rem}
.notice,.card,.kpi,.table-card{background:var(--card);border:1px solid var(--line);border-radius:20px;box-shadow:0 10px 24px rgba(96,69,28,.06)}
.notice{padding:16px 18px;margin:20px 0;color:#5b4636}
.grid{display:grid;gap:18px}
.kpi-grid{display:grid;grid-template-columns:repeat(auto-fit,minmax(180px,1fr));gap:16px;margin:22px 0}
.kpi{padding:18px}
.kpi strong{display:block;font-size:2rem;color:var(--accent)}
.kpi span{color:var(--muted)}
.section-title{display:flex;align-items:end;justify-content:space-between;gap:16px;margin:28px 0 14px}
.section-title h2{margin:0;font-size:1.55rem}
.cards{display:grid;grid-template-columns:repeat(auto-fit,minmax(250px,1fr));gap:16px}
.card{padding:18px}
.card h3,.card h2{margin:0 0 10px}
.pill{display:inline-block;padding:4px 10px;border-radius:999px;background:var(--accent-soft);color:#8a2d0a;font-size:.8rem;font-weight:700}
.meta{display:grid;grid-template-columns:repeat(auto-fit,minmax(180px,1fr));gap:12px;margin:18px 0}
.meta .card{padding:14px}
.meta-label{font-size:.82rem;color:var(--muted)}
.meta-value{font-size:1.15rem;font-weight:700;margin-top:4px}
.table-card{padding:16px;overflow:auto}
table{width:100%;border-collapse:collapse}
th,td{padding:10px 8px;border-bottom:1px solid var(--line);vertical-align:top;text-align:left}
th{font-size:.85rem;color:var(--muted);text-transform:uppercase;letter-spacing:.03em}
.search-box,.select{width:100%;padding:12px 14px;border-radius:14px;border:1px solid var(--line);background:#fff}
.filters{display:grid;grid-template-columns:2fr 1fr 1fr;gap:12px;margin:18px 0}
.filters.single{grid-template-columns:1fr}
.link-list{display:grid;gap:10px}
.link-item{display:flex;justify-content:space-between;gap:16px;padding:14px 16px;border:1px solid var(--line);border-radius:16px;background:#fff}
.footer-note{margin:36px 0 28px;color:var(--muted);font-size:.92rem}
.lang-ta{display:none}
body[data-lang='ta'] .lang-en{display:none}
body[data-lang='ta'] .lang-ta{display:inline}
body[data-lang='ta'] .lang-en.block{display:none}
body[data-lang='ta'] .lang-ta.block{display:block}
.lang-en.block{display:block}
.lang-ta.block{display:none}
.btn{display:inline-block;padding:10px 14px;border-radius:12px;background:var(--accent);color:#fff;font-weight:700}
.small{font-size:.9rem;color:var(--muted)}
.candidate-grid{display:grid;grid-template-columns:repeat(auto-fit,minmax(260px,1fr));gap:16px}
.party-cell{display:flex;align-items:center;gap:0;min-width:220px}
.party-icon{display:none}
.affidavit-link{font-weight:700;white-space:nowrap}
@media (max-width:860px){.filters{grid-template-columns:1fr}.topbar-inner{align-items:flex-start;flex-direction:column}.nav{justify-content:flex-start}}
"""
    app = f"""
window.SITE_META = {json.dumps(site_meta, ensure_ascii=False)};
function toggleLanguage() {{
  const current = document.body.dataset.lang === "ta" ? "ta" : "en";
  const next = current === "en" ? "ta" : "en";
  document.body.dataset.lang = next;
  window.localStorage.setItem("tn2026_lang", next);
}}
(function initLanguage() {{
  const saved = window.localStorage.getItem("tn2026_lang");
  if (saved === "ta" || saved === "en") {{
    document.body.dataset.lang = saved;
  }}
}})();

async function loadJson(path) {{
  const response = await fetch(path);
  return response.json();
}}

function formatNumber(value) {{
  if (value === null || value === undefined || value === "") return "—";
  return new Intl.NumberFormat("en-IN").format(Number(value));
}}

function formatCurrency(value) {{
  if (value === null || value === undefined || value === "") return "—";
  return "₹" + new Intl.NumberFormat("en-IN").format(Math.round(Number(value)));
}}

"""
    (SITE_DIR / "styles.css").write_text(styles.strip() + "\n", encoding="utf-8")
    (SITE_DIR / "app.js").write_text(app.strip() + "\n", encoding="utf-8")


def copy_download_artifacts(paths: list[Path]) -> None:
    for path in paths:
        shutil.copy2(path, SITE_DOWNLOADS_DIR / path.name)


def svg_card(title: str, subtitle: str, lines: list[str], accent: str = "#9a3412") -> str:
    safe_lines = "".join(
        f'<text x="40" y="{160 + idx*48}" font-size="28" fill="#1f2933">{html.escape(line)}</text>'
        for idx, line in enumerate(lines[:6])
    )
    return f"""<svg xmlns="http://www.w3.org/2000/svg" width="1200" height="630" viewBox="0 0 1200 630">
  <rect width="1200" height="630" fill="#f7f1e8"/>
  <rect x="28" y="28" width="1144" height="574" rx="34" fill="#fffaf1" stroke="#e7d7c2" stroke-width="4"/>
  <rect x="40" y="40" width="1120" height="16" rx="8" fill="{accent}"/>
  <text x="40" y="110" font-size="48" font-weight="700" fill="#9a3412">{html.escape(title)}</text>
  <text x="40" y="140" font-size="28" fill="#64748b">{html.escape(subtitle)}</text>
  {safe_lines}
  <text x="40" y="592" font-size="22" fill="#64748b">Tamil Nadu 2026 Voter Facts • Source dated records</text>
</svg>
"""


def render_home(
    site_meta: dict[str, Any],
    summaries: list[dict[str, Any]],
    full_rows: list[dict[str, Any]],
    validation: dict[str, Any],
) -> None:
    top_constituencies = sorted(summaries, key=lambda row: row["candidate_count_2026"], reverse=True)[:6]
    party_counts: Counter[str] = Counter()
    party_labels: dict[str, str] = {}
    party_name_counts: dict[str, Counter[str]] = {}
    for row in full_rows:
        party_key = row.get("party_abbrev") or row.get("party_name") or "UNKNOWN"
        party_name = (row.get("party_name") or party_key).strip()
        party_counts[party_key] += 1
        party_name_counts.setdefault(party_key, Counter())[party_name] += 1
    for party_key, counts in party_name_counts.items():
        party_labels[party_key] = sorted(counts.items(), key=lambda item: (-item[1], item[0]))[0][0]
    top_parties = sorted(
        party_counts.items(),
        key=lambda item: (-item[1], party_labels.get(item[0], item[0])),
    )[:10]
    top_parties_rows = "".join(
        f"""
        <tr>
          <td>{html.escape(party_labels.get(party_key, party_key))}</td>
          <td>{count:,}</td>
        </tr>
        """
        for party_key, count in top_parties
    )
    body = f"""
    <section class="hero">
      <span class="pill">{bi_text('Official roster + voter context', 'அதிகாரப்பூர்வ பட்டியல் + வாக்காளர் தகவல்')}</span>
      <h1>{bi_text(UI_TEXT['brand']['en'], UI_TEXT['brand']['ta'])}</h1>
      <p>{bi_text(UI_TEXT['tagline']['en'], UI_TEXT['tagline']['ta'])}</p>
    </section>
    <div class="notice">{bi_text(UI_TEXT['facts_notice']['en'], UI_TEXT['facts_notice']['ta'])}</div>
    <section class="kpi-grid">
      <div class="kpi"><strong>{len(full_rows):,}</strong><span>{bi_text('Official 2026 candidate rows', '2026 அதிகாரப்பூர்வ வேட்பாளர் வரிகள்')}</span></div>
      <div class="kpi"><strong>{len(summaries)}</strong><span>{bi_text('Assembly constituencies', 'சட்டமன்ற தொகுதிகள்')}</span></div>
      <div class="kpi"><strong>{len({row['district'] for row in summaries if row['district']})}</strong><span>{bi_text('Districts covered', 'கவரப்பட்ட மாவட்டங்கள்')}</span></div>
      <div class="kpi"><strong>{validation['official_count_status']}</strong><span>{bi_text('Official count check vs 4,023', '4,023 எண்ணிக்கையுடன் சரிபார்ப்பு')}</span></div>
    </section>
    <div class="section-title"><h2>{bi_text('Quick voter modules', 'வாக்காளர்களுக்கான விரைவு தொகுதிகள்')}</h2></div>
    <section class="cards">
      <article class="card"><h3>{bi_text('Constituency roster', 'தொகுதி வேட்பாளர் பட்டியல்')}</h3><p class="small">{bi_text('Find everyone contesting in a seat, with district context and 2021 result data.', 'ஒவ்வொரு தொகுதியிலும் போட்டியிடும் அனைவரையும், 2021 முடிவு பின்னணியுடன் காணுங்கள்.')}</p><a class="btn" href="constituencies/index.html">{bi_text('Browse constituencies', 'தொகுதிகளைப் பார்க்க')}</a></article>
      <article class="card"><h3>{bi_text('Candidate fact cards', 'வேட்பாளர் உண்மை அட்டைகள்')}</h3><p class="small">{bi_text('Each candidate page shows official roster data and matched public facts where available.', 'ஒவ்வொரு வேட்பாளர் பக்கமும் அதிகாரப்பூர்வ பட்டியல் தகவல்களையும் பொருந்திய பொதுத் தரவுகளையும் காட்டுகிறது.')}</p><a class="btn" href="downloads/index.html">{bi_text('Open downloads', 'பதிவிறக்கங்களைத் திறக்க')}</a></article>
      <article class="card"><h3>{bi_text('Side-by-side compare', 'பக்கம்தோறும் ஒப்பீடு')}</h3><p class="small">{bi_text('Compare two candidates from the same constituency on assets, cases, age, education, and context.', 'ஒரே தொகுதியிலுள்ள இரு வேட்பாளர்களை சொத்து, வழக்குகள், வயது, கல்வி போன்ற விவரங்களில் ஒப்பிடுங்கள்.')}</p><a class="btn" href="compare/index.html">{bi_text('Compare candidates', 'வேட்பாளர்களை ஒப்பிடு')}</a></article>
    </section>
    <div class="section-title"><h2>{bi_text('Seats with the most candidates', 'அதிக வேட்பாளர்கள் உள்ள தொகுதிகள்')}</h2></div>
    <section class="cards">
      {"".join(
          f'<article class="card"><h3>{html.escape(item["constituency_name"])} ({item["constituency_no"]})</h3>'
          f'<p class="small">{html.escape(item["district"])} • {item["candidate_count_2026"]} candidates • {html.escape(item["top_parties_2026"])}</p>'
          f'<a class="btn" href="constituencies/{item["constituency_slug"]}/index.html">Open</a></article>'
          for item in top_constituencies
      )}
    </section>
    <p class="footer-note">{bi_text('Generated on ' + site_meta['generated_on'], 'உருவாக்கப்பட்ட தேதி: ' + site_meta['generated_on'])}</p>
    """
    (SITE_DIR / "index.html").write_text(render_layout("Tamil Nadu 2026 Voter Facts", body), encoding="utf-8")


def render_constituencies_index(summaries: list[dict[str, Any]], rows_by_constituency: dict[int, list[dict[str, Any]]]) -> None:
    items_html = []
    for item in summaries:
        candidate_search_blob = " ".join(
            row["candidate_name"].lower()
            for row in rows_by_constituency.get(item["constituency_no"], [])
            if row.get("candidate_name")
        )
        items_html.append(
            f"""
            <article class="card constituency-card" data-name="{html.escape(item['constituency_name'].lower())}" data-district="{html.escape(item['district'].lower())}" data-parties="{html.escape(item['top_parties_2026'].lower())}" data-candidates="{html.escape(candidate_search_blob)}">
              <h3><a href="{item['constituency_slug']}/index.html">{html.escape(item['constituency_name'])} ({item['constituency_no']})</a></h3>
              <p class="small">{html.escape(item['district'])} • {item['candidate_count_2026']} candidates • {html.escape(item['top_parties_2026'])}</p>
              <div class="meta">
                <div class="card"><div class="meta-label">{bi_text('Winner 2021', '2021 வெற்றியாளர்')}</div><div class="meta-value">{html_text(item['winner_2021'])}</div></div>
                <div class="card"><div class="meta-label">{bi_text('Margin 2021', '2021 வித்தியாசம்')}</div><div class="meta-value">{html_text(item['margin_2021'])}</div></div>
              </div>
            </article>
            """
        )
    body = f"""
    <section class="hero">
      <h1>{bi_text('All 234 constituencies', 'அனைத்து 234 தொகுதிகள்')}</h1>
      <p>{bi_text('Search by candidate, constituency, district, or party mix.', 'வேட்பாளர், தொகுதி, மாவட்டம் அல்லது கட்சி அடிப்படையில் தேடுங்கள்.')}</p>
    </section>
    <div class="filters">
      <input id="constituency-search" class="search-box" placeholder="{html.escape(UI_TEXT['search_placeholder']['en'])}">
      <select id="district-filter" class="select"><option value="">All districts</option>{"".join(f'<option value="{html.escape(item)}">{html.escape(item)}</option>' for item in sorted({row['district'] for row in summaries}))}</select>
      <select id="party-filter" class="select"><option value="">All parties</option>{"".join(f'<option value="{html.escape(item)}">{html.escape(item)}</option>' for item in sorted({abbr for row in summaries for abbr in row['top_parties_2026'].replace(" ", "").split(",") if abbr}))}</select>
    </div>
    <section id="constituency-list" class="cards">{''.join(items_html)}</section>
    <script>
      const searchInput = document.getElementById('constituency-search');
      const districtFilter = document.getElementById('district-filter');
      const partyFilter = document.getElementById('party-filter');
      const cards = Array.from(document.querySelectorAll('.constituency-card'));
      function applyFilters() {{
        const q = (searchInput.value || '').toLowerCase().trim();
        const district = (districtFilter.value || '').toLowerCase();
        const party = (partyFilter.value || '').toLowerCase();
        cards.forEach(card => {{
          const okQ = !q || card.dataset.name.includes(q) || card.dataset.district.includes(q) || card.dataset.parties.includes(q) || card.dataset.candidates.includes(q);
          const okD = !district || card.dataset.district === district;
          const okP = !party || card.dataset.parties.includes(party);
          card.style.display = okQ && okD && okP ? '' : 'none';
        }});
      }}
      [searchInput, districtFilter, partyFilter].forEach(el => el.addEventListener('input', applyFilters));
      [districtFilter, partyFilter].forEach(el => el.addEventListener('change', applyFilters));
    </script>
    """
    constituency_dir = SITE_DIR / "constituencies"
    constituency_dir.mkdir(parents=True, exist_ok=True)
    (constituency_dir / "index.html").write_text(
        render_layout("Tamil Nadu 2026 Constituencies", body, relative_prefix="../"),
        encoding="utf-8",
    )


def render_constituency_pages(summaries: list[dict[str, Any]], rows_by_constituency: dict[int, list[dict[str, Any]]]) -> None:
    base_dir = SITE_DIR / "constituencies"
    for summary in summaries:
        target_dir = base_dir / summary["constituency_slug"]
        target_dir.mkdir(parents=True, exist_ok=True)
        candidates = rows_by_constituency[summary["constituency_no"]]
        table_rows = "".join(
            f"""
            <tr class="candidate-row" data-search="{html.escape((row['candidate_name'] + ' ' + row['party_name'] + ' ' + str(row.get('gender', ''))).lower())}">
              <td><a href="../../candidates/{row['candidate_slug']}/index.html">{html.escape(row['candidate_name'])}</a></td>
              <td>{html.escape(row['party_abbrev'])}</td>
              <td>{html_text(row['gender'])}</td>
              <td>{html_text(row['age'])}</td>
              <td>{currency_text(row['declared_assets'])}</td>
              <td>{cases_flag_text(row.get('criminal_cases_flag') or row.get('criminal_cases_declared'))}</td>
            </tr>
            """
            for row in candidates
        )
        default_compare = candidates[:2]
        compare_link = "../../compare/index.html"
        if len(default_compare) == 2:
            compare_link += f"?a={urllib.parse.quote(default_compare[0]['candidate_uid'])}&b={urllib.parse.quote(default_compare[1]['candidate_uid'])}"
        body = f"""
        <section class="hero">
          <span class="pill">{html.escape(summary['district'])}</span>
          <h1>{html.escape(summary['constituency_name'])} ({summary['constituency_no']})</h1>
          <p>{bi_text('Official 2026 roster with 2021 result context and 2026 voter roll stats where available.', 'அதிகாரப்பூர்வ 2026 பட்டியல், 2021 முடிவு பின்னணி மற்றும் கிடைக்கும் 2026 வாக்காளர் விவரங்களுடன்.')}</p>
        </section>
        <section class="meta">
          <div class="card"><div class="meta-label">{bi_text('Candidates', 'வேட்பாளர்கள்')}</div><div class="meta-value">{summary['candidate_count_2026']}</div></div>
          <div class="card"><div class="meta-label">{bi_text('Winner 2021', '2021 வெற்றியாளர்')}</div><div class="meta-value">{html_text(summary['winner_2021'])}</div></div>
          <div class="card"><div class="meta-label">{bi_text('Margin 2021', '2021 வித்தியாசம்')}</div><div class="meta-value">{html_text(summary['margin_2021'])}</div></div>
          <div class="card"><div class="meta-label">{bi_text('Voters 2026', 'வாக்காளர்கள் 2026')}</div><div class="meta-value">{html_text(summary['voters_total_2026'])}</div></div>
        </section>
        <div class="notice">{bi_text('Top parties in this seat: ' + summary['top_parties_2026'], 'இந்த தொகுதியில் முக்கிய கட்சிகள்: ' + summary['top_parties_2026'])}</div>
        <div class="section-title"><h2>{bi_text('Candidate roster', 'வேட்பாளர் பட்டியல்')}</h2><a class="btn" href="{compare_link}">{bi_text('Compare first two', 'முதல் இரண்டு பேரை ஒப்பிடு')}</a></div>
        <div class="filters">
          <input id="candidate-search" class="search-box" placeholder="{html.escape(UI_TEXT['search_placeholder']['en'])}">
        </div>
        <div class="table-card">
          <table>
            <thead><tr><th>{bi_text('Candidate', 'வேட்பாளர்')}</th><th>{bi_text('Party', 'கட்சி')}</th><th>{bi_text('Age', 'வயது')}</th><th>{bi_text('Assets', 'சொத்துகள்')}</th><th>{bi_text('Cases', 'வழக்குகள்')}</th><th>{bi_text('Match', 'பொருத்தம்')}</th></tr></thead>
            <tbody>{table_rows}</tbody>
          </table>
        </div>
        <p class="footer-note">{bi_text('Source dated ' + str(summary['source_date']), 'மூல தேதி ' + str(summary['source_date']))}</p>
        """
        body = re.sub(
            r"<thead><tr>.*?</tr></thead>",
            "<thead><tr>"
            f"<th>{bi_text('Candidate', 'வேட்பாளர்')}</th>"
            f"<th>{bi_text('Party', 'கட்சி')}</th>"
            f"<th>{bi_text('Gender', 'பாலினம்')}</th>"
            f"<th>{bi_text('Age', 'வயது')}</th>"
            f"<th>{bi_text('Assets', 'சொத்துகள்')}</th>"
            f"<th>{bi_text('Cases (Y/N)', 'வழக்குகள் (Y/N)')}</th>"
            "</tr></thead>",
            body,
            count=1,
            flags=re.S,
        )
        body += """
        <script>
          const candidateSearch = document.getElementById('candidate-search');
          const candidateRows = Array.from(document.querySelectorAll('.candidate-row'));
          function filterCandidateRows() {
            const q = (candidateSearch.value || '').toLowerCase().trim();
            candidateRows.forEach(row => {
              row.style.display = !q || row.dataset.search.includes(q) ? '' : 'none';
            });
          }
          candidateSearch.addEventListener('input', filterCandidateRows);
        </script>
        """
        (target_dir / "index.html").write_text(
            render_layout(f"{summary['constituency_name']} Constituency", body, relative_prefix="../../"),
            encoding="utf-8",
        )


def render_candidate_pages(full_rows: list[dict[str, Any]]) -> None:
    base_dir = SITE_DIR / "candidates"
    base_dir.mkdir(parents=True, exist_ok=True)
    for row in full_rows:
        target_dir = base_dir / row["candidate_slug"]
        target_dir.mkdir(parents=True, exist_ok=True)
        row["affidavit_url"] = row.get("affidavit_reference_url") or row.get("affidavit_url") or ""
        affidavit = (
            f'<a class="btn" href="{html.escape(row["affidavit_url"])}" target="_blank" rel="noopener noreferrer">{bi_text("Open affidavit", "சத்தியப்பிரமாணத்தைத் திறக்க")}</a>'
            if row["affidavit_url"]
            else ""
        )
        body = f"""
        <section class="hero">
          <span class="pill">{html.escape(row['party_abbrev'])}</span>
          <h1>{html.escape(row['candidate_name'])}</h1>
          <p>{html.escape(row['constituency_name'])} ({row['constituency_no']}) • {html.escape(row['district'])}</p>
        </section>
        <section class="meta">
          <div class="card"><div class="meta-label">{bi_text('Age', 'வயது')}</div><div class="meta-value">{html_text(row['age'])}</div></div>
          <div class="card"><div class="meta-label">{bi_text('Education', 'கல்வி')}</div><div class="meta-value">{html_text(row['education'])}</div></div>
          <div class="card"><div class="meta-label">{bi_text('Declared Assets', 'அறிவித்த சொத்துகள்')}</div><div class="meta-value">{currency_text(row['declared_assets'])}</div></div>
          <div class="card"><div class="meta-label">{bi_text('Liabilities', 'பாதகத் தொகைகள்')}</div><div class="meta-value">{currency_text(row['liabilities'])}</div></div>
          <div class="card"><div class="meta-label">{bi_text('Criminal Cases', 'குற்ற வழக்குகள்')}</div><div class="meta-value">{html_text(row['criminal_cases_declared'])}</div></div>
          <div class="card"><div class="meta-label">{bi_text('2021 Vote Share', '2021 வாக்கு பங்கு')}</div><div class="meta-value">{html_text(row['vote_share_2021'])}</div></div>
        </section>
        <section class="cards">
          <article class="card"><h3>{bi_text('Official roster facts', 'அதிகாரப்பூர்வ பட்டியல் தகவல்கள்')}</h3><p class="small">{bi_text('Party: ', 'கட்சி: ')}{html.escape(row['party_name'])}</p><p class="small">{bi_text('Source document: ', 'மூல ஆவணம்: ')}{html.escape(row['source_document'])}</p><p class="small">{bi_text('Source date: ', 'மூல தேதி: ')}{html_text(row['source_date'])}</p></article>
          <article class="card"><h3>{bi_text('Constituency context', 'தொகுதி பின்னணி')}</h3><p class="small">{bi_text('Winner 2021: ', '2021 வெற்றியாளர்: ')}{html_text(row['winner_2021'])}</p><p class="small">{bi_text('Margin 2021: ', '2021 வித்தியாசம்: ')}{html_text(row['margin_2021'])}</p><p class="small">{bi_text('Turnout 2021: ', '2021 வாக்குப்பதிவு: ')}{html_text(row['turnout_2021'])}</p></article>
          <article class="card"><h3>{bi_text('Verification', 'சரிபார்ப்பு')}</h3><p class="small">{bi_text('Historical fields appear only when a deterministic 2021 match exists.', 'நிர்ணயமான 2021 பொருத்தம் இருந்தால் மட்டுமே வரலாற்றுத் தகவல்கள் காட்டப்படும்.')}</p>{affidavit}</article>
        </section>
        """
        body = body.replace(
            f"<section class=\"meta\">\n          <div class=\"card\"><div class=\"meta-label\">{bi_text('Age', 'à®µà®¯à®¤à¯')}</div><div class=\"meta-value\">{html_text(row['age'])}</div></div>",
            f"<section class=\"meta\">\n          <div class=\"card\"><div class=\"meta-label\">{bi_text('Gender', 'பாலினம்')}</div><div class=\"meta-value\">{html_text(row['gender'])}</div></div>\n          <div class=\"card\"><div class=\"meta-label\">{bi_text('Age', 'à®µà®¯à®¤à¯')}</div><div class=\"meta-value\">{html_text(row['age'])}</div></div>",
            1,
        )
        body = body.replace(
            f"<div class=\"card\"><div class=\"meta-label\">{bi_text('Criminal Cases', 'à®•à¯à®±à¯à®± à®µà®´à®•à¯à®•à¯à®•à®³à¯')}</div><div class=\"meta-value\">{html_text(row['criminal_cases_declared'])}</div></div>",
            f"<div class=\"card\"><div class=\"meta-label\">{bi_text('Criminal Cases (Y/N)', 'குற்ற வழக்குகள் (Y/N)')}</div><div class=\"meta-value\">{cases_flag_text(row.get('criminal_cases_flag') or row.get('criminal_cases_declared'))}</div></div>",
            1,
        )
        body = body.replace(
            f"<article class=\"card\"><h3>{bi_text('Verification', 'à®šà®°à®¿à®ªà®¾à®°à¯à®ªà¯à®ªà¯')}</h3><p class=\"small\">{bi_text('Historical fields appear only when a deterministic 2021 match exists.', 'à®¨à®¿à®°à¯à®£à®¯à®®à®¾à®© 2021 à®ªà¯Šà®°à¯à®¤à¯à®¤à®®à¯ à®‡à®°à¯à®¨à¯à®¤à®¾à®²à¯ à®®à®Ÿà¯à®Ÿà¯à®®à¯‡ à®µà®°à®²à®¾à®±à¯à®±à¯à®¤à¯ à®¤à®•à®µà®²à¯à®•à®³à¯ à®•à®¾à®Ÿà¯à®Ÿà®ªà¯à®ªà®Ÿà¯à®®à¯.')}</p>{affidavit}</article>",
            f"<article class=\"card\"><h3>{bi_text('Verification', 'à®šà®°à®¿à®ªà®¾à®°à¯à®ªà¯à®ªà¯')}</h3><p class=\"small\">{bi_text('Age and gender are refreshed from a 2026 affidavit browser feed sourced from affidavit.eci.gov.in. Latest PDF parsing is currently blocked by the official portal from this environment, so finance, education, and cases fall back to older public matches where available.', 'வயது மற்றும் பாலினம் 2026 affidavit.eci.gov.in தரவுகளைக் காட்டும் உலாவி மூலம் புதுப்பிக்கப்பட்டவை. அதிகாரப்பூர்வ PDF பதிவிறக்கம் இங்கிருந்த சூழலில் தடுக்கப்பட்டதால், சொத்து, கடன், கல்வி, வழக்கு தகவல்கள் கிடைக்கும் இடங்களில் பழைய பொது பொருத்தங்கள் பயன்படுத்தப்படுகின்றன.')}</p><p class=\"small\">{bi_text('Age source: ', 'வயது மூலம்: ')}{html_text(row.get('age_source'))}</p><p class=\"small\">{bi_text('Gender source: ', 'பாலின மூலம்: ')}{html_text(row.get('gender_source'))}</p><p class=\"small\">{bi_text('Affidavit status: ', 'சத்தியப்பிரமாண நிலை: ')}{html_text(row.get('affidavit_parse_status'))}</p>{affidavit}</article>",
            1,
        )
        (target_dir / "index.html").write_text(
            render_layout(f"{row['candidate_name']} Candidate Facts", body, relative_prefix="../../"),
            encoding="utf-8",
        )


def cases_flag_text(value: Any) -> str:
    if value in ("", None):
        return "-"
    text = str(value).strip().upper()
    if text in {"Y", "N"}:
        return text
    try:
        return "Y" if float(value) > 0 else "N"
    except (TypeError, ValueError):
        return html.escape(str(value))


def render_home(
    site_meta: dict[str, Any],
    summaries: list[dict[str, Any]],
    full_rows: list[dict[str, Any]],
    validation: dict[str, Any],
) -> None:
    top_constituencies = sorted(summaries, key=lambda row: row["candidate_count_2026"], reverse=True)[:6]
    party_counts: Counter[str] = Counter()
    party_labels: dict[str, str] = {}
    party_name_counts: dict[str, Counter[str]] = {}
    for row in full_rows:
        party_key = row.get("party_abbrev") or row.get("party_name") or "UNKNOWN"
        party_name = (row.get("party_name") or party_key).strip()
        party_counts[party_key] += 1
        party_name_counts.setdefault(party_key, Counter())[party_name] += 1
    for party_key, counts in party_name_counts.items():
        party_labels[party_key] = sorted(counts.items(), key=lambda item: (-item[1], item[0]))[0][0]
    top_parties = sorted(
        party_counts.items(),
        key=lambda item: (-item[1], party_labels.get(item[0], item[0])),
    )[:10]
    top_parties_rows = "".join(
        f"""
        <tr>
          <td>{html.escape(party_labels.get(party_key, party_key))}</td>
          <td>{count:,}</td>
        </tr>
        """
        for party_key, count in top_parties
    )
    body = f"""
    <section class="hero">
      <span class="pill">{bi_text('Official roster + voter context', 'அதிகாரப்பூர்வ பட்டியல் + வாக்காளர் தகவல்')}</span>
      <h1>{bi_text(UI_TEXT['brand']['en'], UI_TEXT['brand']['ta'])}</h1>
      <p>{bi_text(UI_TEXT['tagline']['en'], UI_TEXT['tagline']['ta'])}</p>
    </section>
    <div class="notice">{bi_text(UI_TEXT['facts_notice']['en'], UI_TEXT['facts_notice']['ta'])}</div>
    <section class="kpi-grid">
      <div class="kpi"><strong>{len(full_rows):,}</strong><span>{bi_text('Official 2026 candidate rows', '2026 அதிகாரப்பூர்வ வேட்பாளர் வரிகள்')}</span></div>
      <div class="kpi"><strong>{len(summaries)}</strong><span>{bi_text('Assembly constituencies', 'சட்டமன்ற தொகுதிகள்')}</span></div>
      <div class="kpi"><strong>{len({row['district'] for row in summaries if row['district']})}</strong><span>{bi_text('Districts covered', 'கவரப்பட்ட மாவட்டங்கள்')}</span></div>
      <div class="kpi"><strong>{validation['official_count_status']}</strong><span>{bi_text('Official count check vs 4,023', '4,023 எண்ணிக்கையுடன் சரிபார்ப்பு')}</span></div>
    </section>
    <div class="section-title"><h2>{bi_text('Quick voter modules', 'வாக்காளர்களுக்கான விரைவு தொகுதிகள்')}</h2></div>
    <section class="cards">
      <article class="card"><h3>{bi_text('Constituency roster', 'தொகுதி வேட்பாளர் பட்டியல்')}</h3><p class="small">{bi_text('Find everyone contesting in a seat, with district context and 2021 result data.', 'ஒவ்வொரு தொகுதியிலும் போட்டியிடும் அனைவரையும், 2021 முடிவு பின்னணியுடன் காணுங்கள்.')}</p><a class="btn" href="constituencies/index.html">{bi_text('Browse constituencies', 'தொகுதிகளைப் பார்க்க')}</a></article>
      <article class="card"><h3>{bi_text('Candidate fact cards', 'வேட்பாளர் உண்மை அட்டைகள்')}</h3><p class="small">{bi_text('Each candidate page shows official roster data, affidavit links, and matched public facts where available.', 'ஒவ்வொரு வேட்பாளர் பக்கமும் அதிகாரப்பூர்வ பட்டியல் தகவல்கள், affidavit இணைப்புகள் மற்றும் கிடைக்கும் பொது தரவு பொருத்தங்களை காட்டுகிறது.')}</p><a class="btn" href="downloads/index.html">{bi_text('Open downloads', 'பதிவிறக்கங்களைத் திறக்க')}</a></article>
    </section>
    <div class="section-title"><h2>{bi_text('Parties with the most candidates contesting', 'Parties with the most candidates contesting')}</h2></div>
    <section class="table-card">
      <table>
        <thead>
          <tr>
            <th>{bi_text('Party', 'Party')}</th>
            <th>{bi_text('# of candidates', '# of candidates')}</th>
          </tr>
        </thead>
        <tbody>{top_parties_rows}</tbody>
      </table>
    </section>
    <div class="section-title"><h2>{bi_text('Seats with the most candidates', 'அதிக வேட்பாளர்கள் உள்ள தொகுதிகள்')}</h2></div>
    <section class="cards">
      {"".join(
          f'<article class="card"><h3>{html.escape(item["constituency_name"])} ({item["constituency_no"]})</h3>'
          f'<p class="small">{html.escape(item["district"])} • {item["candidate_count_2026"]} candidates • {html.escape(item["top_parties_2026"])}</p>'
          f'<a class="btn" href="constituencies/{item["constituency_slug"]}/index.html">Open</a></article>'
          for item in top_constituencies
      )}
    </section>
    <p class="footer-note">{bi_text('Generated on ' + site_meta['generated_on'], 'உருவாக்கப்பட்ட தேதி: ' + site_meta['generated_on'])}</p>
    """
    (SITE_DIR / "index.html").write_text(render_layout("Tamil Nadu 2026 Voter Facts", body), encoding="utf-8")


def render_constituency_pages(summaries: list[dict[str, Any]], rows_by_constituency: dict[int, list[dict[str, Any]]]) -> None:
    base_dir = SITE_DIR / "constituencies"
    for summary in summaries:
        target_dir = base_dir / summary["constituency_slug"]
        target_dir.mkdir(parents=True, exist_ok=True)
        candidates = rows_by_constituency[summary["constituency_no"]]
        table_rows = "".join(
            f"""
            <tr class="candidate-row" data-search="{html.escape((row['candidate_name'] + ' ' + row['party_name'] + ' ' + row['party_abbrev']).lower())}">
              <td><a href="../../candidates/{row['candidate_slug']}/index.html">{html.escape(row['candidate_name'])}</a></td>
              <td><div class="party-cell"><span class="party-icon" title="{html.escape(row.get('symbol') or row['party_abbrev'])}" aria-label="{html.escape(row.get('symbol') or row['party_abbrev'])}">{html.escape(symbol_icon(row.get('symbol'), row['party_abbrev']))}</span><span>{html.escape(row['party_name'])}</span></div></td>
              <td>{html_text(row['gender'])}</td>
              <td>{html_text(row['age'])}</td>
              <td>{currency_text(row['declared_assets'])}</td>
              <td>{cases_flag_text(row.get('criminal_cases_flag') or row.get('criminal_cases_declared'))}</td>
              <td>{(f'<a class="affidavit-link" href="{html.escape(row.get("candidate_reference_url") or row.get("affidavit_reference_url") or row.get("affidavit_url") or "")}" target="_blank" rel="noopener noreferrer">View</a>' if (row.get("candidate_reference_url") or row.get("affidavit_reference_url") or row.get("affidavit_url")) else '-')}</td>
            </tr>
            """
            for row in candidates
        )
        body = f"""
        <section class="hero">
          <span class="pill">{html.escape(summary['district'])}</span>
          <h1>{html.escape(summary['constituency_name'])} ({summary['constituency_no']})</h1>
          <p>{bi_text('Official 2026 roster with 2021 result context and 2026 voter roll stats where available.', 'அதிகாரப்பூர்வ 2026 பட்டியல், 2021 முடிவு பின்னணி மற்றும் கிடைக்கும் 2026 வாக்காளர் விவரங்களுடன்.')}</p>
        </section>
        <section class="meta">
          <div class="card"><div class="meta-label">{bi_text('Candidates', 'வேட்பாளர்கள்')}</div><div class="meta-value">{summary['candidate_count_2026']}</div></div>
          <div class="card"><div class="meta-label">{bi_text('Winner 2021', '2021 வெற்றியாளர்')}</div><div class="meta-value">{html_text(summary['winner_2021'])}</div></div>
          <div class="card"><div class="meta-label">{bi_text('Margin 2021', '2021 வித்தியாசம்')}</div><div class="meta-value">{html_text(summary['margin_2021'])}</div></div>
          <div class="card"><div class="meta-label">{bi_text('Voters 2026', 'வாக்காளர்கள் 2026')}</div><div class="meta-value">{html_text(summary['voters_total_2026'])}</div></div>
        </section>
        <div class="notice">{bi_text('Top parties in this seat: ' + summary['top_parties_2026'], 'இந்த தொகுதியில் முக்கிய கட்சிகள்: ' + summary['top_parties_2026'])}</div>
        <div class="section-title"><h2>{bi_text('Candidate roster', 'வேட்பாளர் பட்டியல்')}</h2></div>
        <div class="filters single">
          <input id="candidate-search" class="search-box" placeholder="Search candidate or party name">
        </div>
        <div class="table-card">
          <table>
            <thead><tr><th>{bi_text('Candidate', 'வேட்பாளர்')}</th><th>{bi_text('Party', 'கட்சி')}</th><th>{bi_text('Gender', 'பாலினம்')}</th><th>{bi_text('Age', 'வயது')}</th><th>{bi_text('Assets', 'சொத்துகள்')}</th><th>{bi_text('Cases (Y/N)', 'வழக்குகள் (Y/N)')}</th><th>{bi_text('Affidavit URL', 'அஃபிடவிட் இணைப்பு')}</th></tr></thead>
            <tbody>{table_rows}</tbody>
          </table>
        </div>
        <p class="footer-note">{bi_text('Source dated ' + str(summary['source_date']), 'மூல தேதி ' + str(summary['source_date']))}</p>
        <script>
          const candidateSearch = document.getElementById('candidate-search');
          const candidateRows = Array.from(document.querySelectorAll('.candidate-row'));
          function filterCandidateRows() {{
            const q = (candidateSearch.value || '').toLowerCase().trim();
            candidateRows.forEach(row => {{
              row.style.display = !q || row.dataset.search.includes(q) ? '' : 'none';
            }});
          }}
          candidateSearch.addEventListener('input', filterCandidateRows);
        </script>
        """
        (target_dir / "index.html").write_text(
            render_layout(f"{summary['constituency_name']} Constituency", body, relative_prefix="../../"),
            encoding="utf-8",
        )


def render_candidate_pages(full_rows: list[dict[str, Any]]) -> None:
    base_dir = SITE_DIR / "candidates"
    base_dir.mkdir(parents=True, exist_ok=True)
    for row in full_rows:
        target_dir = base_dir / row["candidate_slug"]
        target_dir.mkdir(parents=True, exist_ok=True)
        row["affidavit_url"] = row.get("affidavit_reference_url") or row.get("affidavit_url") or ""
        affidavit = (
            f'<a class="btn" href="{html.escape(row["affidavit_url"])}" target="_blank" rel="noopener noreferrer">{bi_text("Open affidavit", "சத்தியப்பிரமாணத்தைத் திறக்க")}</a>'
            if row["affidavit_url"]
            else ""
        )
        verification_note = bi_text(
            "Age and gender are refreshed from a 2026 affidavit browser feed sourced from affidavit.eci.gov.in. Latest official PDF parsing is blocked from this environment, so assets, liabilities, education, and cases currently fall back to older trusted public matches when available.",
            "வயதும் பாலினமும் affidavit.eci.gov.in மூலம் கிடைக்கும் 2026 affidavit browser feed-இலிருந்து புதுப்பிக்கப்படுகின்றன. இந்த சூழலில் அதிகாரப்பூர்வ PDF பதிவிறக்கம் தடுக்கப்பட்டதால், சொத்து, கடன், கல்வி, வழக்கு தகவல்கள் கிடைக்கும் இடங்களில் பழைய நம்பகமான பொது பொருத்தங்களில் இருந்து காட்டப்படுகின்றன.",
        )
        body = f"""
        <section class="hero">
          <span class="pill">{html.escape(row['party_abbrev'])}</span>
          <h1>{html.escape(row['candidate_name'])}</h1>
          <p>{html.escape(row['constituency_name'])} ({row['constituency_no']}) • {html.escape(row['district'])}</p>
        </section>
        <section class="meta">
          <div class="card"><div class="meta-label">{bi_text('Gender', 'பாலினம்')}</div><div class="meta-value">{html_text(row['gender'])}</div></div>
          <div class="card"><div class="meta-label">{bi_text('Age', 'வயது')}</div><div class="meta-value">{html_text(row['age'])}</div></div>
          <div class="card"><div class="meta-label">{bi_text('Education', 'கல்வி')}</div><div class="meta-value">{html_text(row['education'])}</div></div>
          <div class="card"><div class="meta-label">{bi_text('Declared Assets', 'அறிவித்த சொத்துகள்')}</div><div class="meta-value">{currency_text(row['declared_assets'])}</div></div>
          <div class="card"><div class="meta-label">{bi_text('Liabilities', 'பாதகத் தொகைகள்')}</div><div class="meta-value">{currency_text(row['liabilities'])}</div></div>
          <div class="card"><div class="meta-label">{bi_text('Cases (Y/N)', 'வழக்குகள் (Y/N)')}</div><div class="meta-value">{cases_flag_text(row.get('criminal_cases_flag') or row.get('criminal_cases_declared'))}</div></div>
          <div class="card"><div class="meta-label">{bi_text('2021 Vote Share', '2021 வாக்கு பங்கு')}</div><div class="meta-value">{html_text(row['vote_share_2021'])}</div></div>
        </section>
        <section class="cards">
          <article class="card"><h3>{bi_text('Official roster facts', 'அதிகாரப்பூர்வ பட்டியல் தகவல்கள்')}</h3><p class="small">{bi_text('Party: ', 'கட்சி: ')}{html.escape(row['party_name'])}</p><p class="small">{bi_text('Source document: ', 'மூல ஆவணம்: ')}{html.escape(row['source_document'])}</p><p class="small">{bi_text('Source date: ', 'மூல தேதி: ')}{html_text(row['source_date'])}</p></article>
          <article class="card"><h3>{bi_text('Constituency context', 'தொகுதி பின்னணி')}</h3><p class="small">{bi_text('Winner 2021: ', '2021 வெற்றியாளர்: ')}{html_text(row['winner_2021'])}</p><p class="small">{bi_text('Margin 2021: ', '2021 வித்தியாசம்: ')}{html_text(row['margin_2021'])}</p><p class="small">{bi_text('Turnout 2021: ', '2021 வாக்குப்பதிவு: ')}{html_text(row['turnout_2021'])}</p></article>
          <article class="card"><h3>{bi_text('Verification', 'சரிபார்ப்பு')}</h3><p class="small">{verification_note}</p><p class="small">{bi_text('Age source: ', 'வயது மூலம்: ')}{html_text(row.get('age_source'))}</p><p class="small">{bi_text('Gender source: ', 'பாலின மூலம்: ')}{html_text(row.get('gender_source'))}</p><p class="small">{bi_text('Education source: ', 'கல்வி மூலம்: ')}{html_text(row.get('education_source'))}</p><p class="small">{bi_text('Assets source: ', 'சொத்து மூலம்: ')}{html_text(row.get('declared_assets_source'))}</p><p class="small">{bi_text('Liabilities source: ', 'கடன் மூலம்: ')}{html_text(row.get('liabilities_source'))}</p><p class="small">{bi_text('Cases source: ', 'வழக்கு மூலம்: ')}{html_text(row.get('criminal_cases_source'))}</p><p class="small">{bi_text('Affidavit status: ', 'சத்தியப்பிரமாண நிலை: ')}{html_text(row.get('affidavit_parse_status'))}</p><p class="small">{bi_text('Reference URL: ', 'குறிப்பு இணைப்பு: ')}{html.escape(row['affidavit_url']) if row['affidavit_url'] else html_text('')}</p>{affidavit}</article>
        </section>
        """
        (target_dir / "index.html").write_text(
            render_layout(f"{row['candidate_name']} Candidate Facts", body, relative_prefix="../../"),
            encoding="utf-8",
        )


def render_compare_page(full_rows: list[dict[str, Any]]) -> None:
    return None


def render_downloads_page(downloads: list[Path], validation: dict[str, Any]) -> None:
    links = "".join(
        f'<div class="link-item"><span>{html.escape(path.name)}</span><a href="{html.escape(path.name)}">Download</a></div>'
        for path in downloads
    )
    body = f"""
    <section class="hero">
      <h1>{bi_text('Download the data', 'தரவுகளைப் பதிவிறக்குங்கள்')}</h1>
      <p>{bi_text('Use these files for reporting, volunteer outreach, newsroom analysis, and public verification.', 'செய்தி வெளியீடு, தன்னார்வ குழுக்கள், தரவு பகுப்பாய்வு மற்றும் பொதுச் சரிபார்ப்புக்கு இந்தக் கோப்புகளைப் பயன்படுத்துங்கள்.')}</p>
    </section>
    <div class="notice">{bi_text('Official roster count found: ' + str(validation['official_candidate_rows']) + '. Validation target: 4,023 candidates.', 'அதிகாரப்பூர்வ பட்டியல் எண்ணிக்கை: ' + str(validation['official_candidate_rows']) + '. சரிபார்ப்பு இலக்கு: 4,023 வேட்பாளர்கள்.')}</div>
    <section class="link-list">{links}</section>
    """
    downloads_dir = SITE_DIR / "downloads"
    downloads_dir.mkdir(parents=True, exist_ok=True)
    (downloads_dir / "index.html").write_text(
        render_layout("Downloads", body, relative_prefix="../"),
        encoding="utf-8",
    )


def render_share_assets(summaries: list[dict[str, Any]], full_rows: list[dict[str, Any]], rows_by_constituency: dict[int, list[dict[str, Any]]]) -> None:
    for summary in summaries:
        svg = svg_card(
            title=f"{summary['constituency_name']} ({summary['constituency_no']})",
            subtitle=f"{summary['district']} • {summary['candidate_count_2026']} candidates",
            lines=[
                f"Winner 2021: {summary['winner_2021'] or 'N/A'}",
                f"Margin 2021: {summary['margin_2021'] or 'N/A'}",
                f"Turnout 2021: {summary['turnout_2021'] or 'N/A'}",
                f"Top parties: {summary['top_parties_2026']}",
            ],
        )
        (SITE_SHARE_DIR / "constituencies" / f"{summary['constituency_slug']}.svg").write_text(svg, encoding="utf-8")

        candidates = rows_by_constituency[summary["constituency_no"]]
        if len(candidates) >= 2:
            compare_svg = svg_card(
                title=f"{summary['constituency_name']} compare",
                subtitle=f"{candidates[0]['candidate_name']} vs {candidates[1]['candidate_name']}",
                lines=[
                    f"{candidates[0]['party_abbrev']} • Assets {currency_text(candidates[0]['declared_assets'])}",
                    f"{candidates[1]['party_abbrev']} • Assets {currency_text(candidates[1]['declared_assets'])}",
                    f"2021 winner: {summary['winner_2021'] or 'N/A'}",
                ],
                accent="#0f766e",
            )
            (SITE_SHARE_DIR / "compare" / f"{summary['constituency_slug']}.svg").write_text(compare_svg, encoding="utf-8")

    for row in full_rows:
        svg = svg_card(
            title=row["candidate_name"],
            subtitle=f"{row['party_abbrev']} • {row['constituency_name']}",
            lines=[
                f"District: {row['district']}",
                f"Assets: {currency_text(row['declared_assets'])}",
                f"Liabilities: {currency_text(row['liabilities'])}",
                f"Criminal cases: {row['criminal_cases_declared'] or 'N/A'}",
            ],
        )
        (SITE_SHARE_DIR / "candidates" / f"{row['candidate_slug']}.svg").write_text(svg, encoding="utf-8")

    verify_svg = svg_card(
        title="How to verify a candidate",
        subtitle="Tamil Nadu 2026 voter facts",
        lines=[
            "1. Open the candidate page",
            "2. Check the affidavit link when available",
            "3. Confirm constituency and party on the official district source",
            "4. Use downloads for newsroom or volunteer review",
        ],
        accent="#1d4ed8",
    )
    (SITE_SHARE_DIR / "verify.svg").write_text(verify_svg, encoding="utf-8")


def build_site(full_rows: list[dict[str, Any]], summaries: list[dict[str, Any]], validation: dict[str, Any], generated_on: str) -> None:
    rows_by_constituency: dict[int, list[dict[str, Any]]] = defaultdict(list)
    for row in full_rows:
        row["candidate_slug"] = f"{row['constituency_no']:03d}-{slugify(row['candidate_name'])}"
        rows_by_constituency[row["constituency_no"]].append(row)

    site_meta = {"generated_on": generated_on, "relativePrefix": "../"}
    write_common_assets(site_meta)

    render_home(site_meta, summaries, full_rows, validation)
    render_constituencies_index(summaries, rows_by_constituency)
    render_constituency_pages(summaries, rows_by_constituency)
    render_candidate_pages(full_rows)
    render_compare_page(full_rows)
    render_downloads_page(
        [
            SITE_DOWNLOADS_DIR / "full_candidates_2026.csv",
            SITE_DOWNLOADS_DIR / "full_candidates_2026.json",
            SITE_DOWNLOADS_DIR / "full_candidates_2026.xlsx",
            SITE_DOWNLOADS_DIR / "constituency_summary_2026.csv",
        ],
        validation,
    )
    render_share_assets(summaries, full_rows, rows_by_constituency)


def main() -> None:
    ensure_dirs()

    public_context = fetch_public_context()
    constituencies = public_context["constituencies"]
    official_rows = fetch_statewide_form7a_rows(constituencies)
    affidavit_context = fetch_affidavit_mirror_context()
    full_rows, enrichment_rows = match_and_enrich(official_rows, public_context, affidavit_context)
    summaries = make_constituency_summaries(full_rows)

    generated_on = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC")
    official_count = len(full_rows)
    constituency_count = len({row["constituency_no"] for row in full_rows})
    districts_covered = sorted({row["district"] for row in full_rows if row["district"]})
    validation = {
        "official_candidate_rows": official_count,
        "constituency_count": constituency_count,
        "district_count": len(districts_covered),
        "districts_covered": districts_covered,
        "target_candidate_count": 4023,
        "official_count_status": "PASS" if official_count == 4023 else "CHECK",
        "constituency_coverage_status": "PASS" if constituency_count == 234 else "CHECK",
        "generated_on": generated_on,
    }

    PROCESSED_DIR.mkdir(parents=True, exist_ok=True)
    outputs = {
        "full_candidates_2026.json": full_rows,
        "candidate_enrichment_2026.json": enrichment_rows,
        "constituency_summary_2026.json": summaries,
        "validation.json": validation,
    }
    for name, payload in outputs.items():
        (PROCESSED_DIR / name).write_text(json.dumps(payload, indent=2, ensure_ascii=False), encoding="utf-8")

    full_csv = OUTPUTS_DIR / "full_candidates_2026.csv"
    summary_csv = OUTPUTS_DIR / "constituency_summary_2026.csv"
    full_json = OUTPUTS_DIR / "full_candidates_2026.json"
    csv_write(full_csv, full_rows)
    csv_write(summary_csv, summaries)
    full_json.write_text(json.dumps(full_rows, indent=2, ensure_ascii=False), encoding="utf-8")
    (OUTPUTS_DIR / "validation.json").write_text(json.dumps(validation, indent=2, ensure_ascii=False), encoding="utf-8")

    copy_download_artifacts([full_csv, summary_csv, full_json])
    build_site(full_rows, summaries, validation, generated_on)

    log(json.dumps(validation, indent=2))


if __name__ == "__main__":
    try:
        main()
    except Exception as exc:  # noqa: BLE001
        print(f"ERROR: {exc}", file=sys.stderr)
        raise
