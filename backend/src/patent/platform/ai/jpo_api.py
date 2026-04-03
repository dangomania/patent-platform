"""
JPO patent data API (ip-data.jpo.go.jp) client.

Free but requires registration at:
  https://www.jpo.go.jp/system/laws/sesaku/data/api-provision.html

Set JPO_API_TOKEN in .env once you have credentials.
Limits: 400 calls/day for app_progress, 100 calls/day for document ZIP download.

Endpoints used:
  GET /api/patent/v1/app_progress/{appNum}   → prosecution history + document list
  GET /api/patent/v1/app_doc_cont_refusal_reason/{appNum}  → ZIP of OA XML (Shift_JIS)
"""

import os
import io
import time
import zipfile
import httpx
import re
from dataclasses import dataclass
from datetime import date
from xml.etree import ElementTree as ET


JPO_BASE = "https://ip-data.jpo.go.jp/api/patent/v1"
JPO_AUTH = "https://ip-data.jpo.go.jp/auth/token"

# XML namespace used in JPO documents
_NS = {"jp": "http://www.jpo.go.jp"}

# Document codes to collect, by record type
# 審査記録 (numberType='01')
_EXAM_CODES: dict[str, str] = {
    "A131": "拒絶理由通知書",
    "A160": "拒絶査定",
}
# 審判記録 (numberType='07')
_APPEAL_CODES: dict[str, str] = {
    "C21": "審判拒絶理由通知書",
    "C22": "審判拒絶理由通知書（補充）",
    "C13": "審決（拒絶）",
}
_EXAM_TYPE   = "01"
_APPEAL_TYPE = "07"
# These codes can be downloaded via app_doc_cont_refusal_reason
_DOWNLOADABLE = {"A131", "C21"}

# In-memory token cache
_cached_token: str | None = None
_token_expiry: float = 0.0


@dataclass
class OADocument:
    date: str               # YYYYMMDD
    date_display: str
    document_number: str
    sequence: int           # display index (0-based)
    doc_type: str           # e.g. "拒絶理由通知書"
    record_type: str        # "審査" or "審判"
    fetch_number: str       # number to use when downloading
    downloadable: bool      # True if content fetch is supported


def is_configured() -> bool:
    return bool(os.getenv("JPO_USERNAME") and os.getenv("JPO_PASSWORD"))


def _get_token() -> str | None:
    """Return a valid Bearer token, refreshing if expired."""
    global _cached_token, _token_expiry

    # Return cached token if still valid (with 60s buffer)
    if _cached_token and time.time() < _token_expiry - 60:
        return _cached_token

    username = os.getenv("JPO_USERNAME")
    password = os.getenv("JPO_PASSWORD")
    if not username or not password:
        return None

    try:
        r = httpx.post(
            JPO_AUTH,
            data={
                "grant_type": "password",
                "username": username,
                "password": password,
            },
            headers={"Content-Type": "application/x-www-form-urlencoded"},
            timeout=15,
        )
        if r.status_code != 200:
            return None
        data = r.json()
        _cached_token = data.get("access_token")
        expires_in = int(data.get("expires_in", 3600))
        _token_expiry = time.time() + expires_in
        return _cached_token
    except Exception:
        return None


def _headers() -> dict:
    return {
        "Authorization": f"Bearer {_get_token()}",
        "Accept": "application/json",
    }


# ── Application number normalisation ────────────────────────────────────────

def normalize_app_number(raw: str) -> str:
    """
    Normalise to 10-digit string expected by the JPO API.
    '特願2020-123456' → '2020123456'
    '特願2020-1234'   → '2020001234'   (serial zero-padded to 6 digits)
    """
    s = re.sub(r'^特願', '', raw.strip()).replace(' ', '').replace('\u3000', '')
    m = re.match(r'(\d{4})[－\-](\d+)', s)
    if m:
        year, serial = m.group(1), m.group(2)
        return f"{year}{serial.zfill(6)}"
    return re.sub(r'\D', '', s)


# ── Fetch OA list from app_progress ─────────────────────────────────────────

def fetch_oa_list(app_number_raw: str) -> list[OADocument] | None:
    """
    Return list of 拒絶理由通知書 entries for the application.
    Returns None if API not configured or request fails.
    """
    if not is_configured():
        return None

    app_num = normalize_app_number(app_number_raw)
    if not app_num:
        return None

    try:
        r = httpx.get(
            f"{JPO_BASE}/app_progress/{app_num}",
            headers=_headers(),
            timeout=15,
        )
        if r.status_code != 200:
            return None

        data = r.json()
        status = data.get("result", {}).get("statusCode")
        # 100 = found, 110 = not found / no data
        if status not in ("100",):
            return None

        bib_list = data["result"]["data"].get("bibliographyInformation", [])
        docs: list[OADocument] = []
        seq = 0
        seen = set()  # deduplicate by document_number

        for bib in bib_list:
            num_type = bib.get("numberType", "")
            bib_number = bib.get("number", "")  # app or appeal number

            if num_type == _EXAM_TYPE:
                code_map = _EXAM_CODES
                record_type = "審査"
            elif num_type == _APPEAL_TYPE:
                code_map = _APPEAL_CODES
                record_type = "審判"
            else:
                continue

            for doc in bib.get("documentList", []):
                code = doc.get("documentCode", "")
                doc_num = doc.get("documentNumber", "")
                if code not in code_map:
                    continue
                if doc_num in seen:
                    continue
                seen.add(doc_num)
                raw_date = doc.get("legalDate", "")
                docs.append(OADocument(
                    date=raw_date,
                    date_display=_format_date(raw_date),
                    document_number=doc_num,
                    sequence=seq,
                    doc_type=code_map[code],
                    record_type=record_type,
                    fetch_number=bib_number,
                    downloadable=(code in _DOWNLOADABLE),
                ))
                seq += 1

        docs.sort(key=lambda d: d.date)
        return docs

    except Exception:
        return None


# ── Fetch OA document text ───────────────────────────────────────────────────

def fetch_oa_text(app_number_raw: str, fetch_number: str | None = None) -> str | None:
    """
    Download a 拒絶理由通知書 ZIP and extract its text.

    fetch_number: the number to pass to the endpoint (app number for 審査 A131,
                  appeal number for 審判 C21).  Defaults to normalised app_number_raw.
    """
    if not is_configured():
        return None

    num = fetch_number or normalize_app_number(app_number_raw)
    if not num:
        return None

    try:
        r = httpx.get(
            f"{JPO_BASE}/app_doc_cont_refusal_reason/{num}",
            headers={**_headers(), "Accept": "*/*"},
            timeout=30,
        )
        if r.status_code != 200:
            return None

        # Unzip in memory
        zf = zipfile.ZipFile(io.BytesIO(r.content))
        xml_name = next((n for n in zf.namelist() if n.endswith(".xml")), None)
        if not xml_name:
            return None

        xml_bytes = zf.read(xml_name)
        return _parse_oa_xml(xml_bytes)

    except Exception:
        return None


def _parse_oa_xml(xml_bytes: bytes) -> str:
    """
    Parse Shift_JIS encoded JPO OA XML, return plain text.
    Handles <br/> line breaks and strips XML tags.
    """
    # Decode Shift_JIS
    try:
        xml_str = xml_bytes.decode("shift_jis")
    except UnicodeDecodeError:
        xml_str = xml_bytes.decode("shift_jis", errors="replace")

    # Strip DOCTYPE declaration which references an external DTD
    xml_str = re.sub(r'<!DOCTYPE[^>]*>', '', xml_str)

    try:
        root = ET.fromstring(xml_str)
    except ET.ParseError:
        # Fallback: strip all XML tags
        return re.sub(r'<[^>]+>', ' ', xml_str).strip()

    parts: list[str] = []

    def _collect(elem: ET.Element) -> str:
        """Recursively collect text, treating <br/> as newline."""
        buf = elem.text or ""
        for child in elem:
            tag = child.tag.split("}")[-1] if "}" in child.tag else child.tag
            if tag == "br":
                buf += "\n" + (child.tail or "")
            else:
                buf += _collect(child) + (child.tail or "")
        return buf

    # Extract conclusion and body paragraphs
    for p in root.iter():
        tag = p.tag.split("}")[-1] if "}" in p.tag else p.tag
        if tag == "p":
            text = _collect(p).strip()
            if text:
                parts.append(text)

    return "\n\n".join(parts)


# ── Helpers ──────────────────────────────────────────────────────────────────

def _format_date(yyyymmdd: str) -> str:
    if len(yyyymmdd) == 8:
        try:
            d = date(int(yyyymmdd[:4]), int(yyyymmdd[4:6]), int(yyyymmdd[6:]))
            return d.strftime("%Y年%m月%d日")
        except ValueError:
            pass
    return yyyymmdd
