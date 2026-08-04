"""Shared OA PDF URL probing for NassilaT Tier 3 corpus tools."""

from __future__ import annotations

import hashlib
import re
from dataclasses import dataclass, field
from typing import Any
from urllib.parse import urljoin, urlparse

import requests

# fetch_status values (source_pdf_extract.output.fetch_status)
FETCH_STATUS_PDF_VERIFIED = "pdf_verified"
FETCH_STATUS_PDF_FILED = "pdf_filed"
FETCH_STATUS_PAYWALL = "paywall_or_auth"
FETCH_STATUS_HTML_ONLY = "html_only"
FETCH_STATUS_URL_ONLY = "url_resolved"

# meta.access_tier — how PDF bytes were (or were not) obtained
ACCESS_TIER_OA_VERIFIED = "oa_unpaywall_verified"
ACCESS_TIER_OA_URL_ONLY = "oa_unpaywall_url_only"
ACCESS_TIER_OPERATOR_OVERRIDE = "operator_override_url_only"
ACCESS_TIER_OPERATOR_OVERRIDE_VERIFIED = "operator_override_verified"
ACCESS_TIER_OPERATOR_ATTACHED = "operator_attached_pdf"
ACCESS_TIER_OPERATOR_GREY = "operator_grey_mirror"

PROBE_USER_AGENT = (
    "Mozilla/5.0 (compatible; NassilaT/1.0; OA PDF probe; "
    "+https://github.com/jamalesam93/NassilaT)"
)

PMC_RE = re.compile(r"ncbi\.nlm\.nih\.gov/pmc/articles/(?:PMC)?(\d+)", re.I)


@dataclass
class ProbeResult:
    fetch_status: str
    access_tier: str | None = None
    http_status: int | None = None
    content_type: str | None = None
    final_url: str | None = None
    pdf_sha256: str | None = None
    pdf_bytes: int | None = None
    error: str | None = None
    attempts: list[dict[str, Any]] = field(default_factory=list)


def is_pdf_bytes(data: bytes) -> bool:
    return bool(data) and data[:5] == b"%PDF-"


def is_pmc_url(url: str) -> bool:
    return bool(PMC_RE.search(url.lower()))


def sha256_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def classify_auth_failure(status: int | None, body_prefix: bytes) -> bool:
    if status in (401, 403, 402):
        return True
    low = body_prefix[:2000].lower()
    needles = (
        b"sign in",
        b"log in",
        b"login",
        b"purchase",
        b"subscribe",
        b"access denied",
        b"institutional access",
    )
    return any(n in low for n in needles)


def extract_pdf_links_from_html(html: bytes, base_url: str) -> list[str]:
    try:
        text = html.decode("utf-8", errors="ignore")
    except Exception:
        return []
    hrefs = re.findall(r'href=["\']([^"\']+\.pdf[^"\']*)["\']', text, flags=re.I)
    hrefs += re.findall(
        r'href=["\']([^"\']*(?:/pdf/|/pdf\b|pdf=render|download=true)[^"\']*)["\']',
        text,
        flags=re.I,
    )
    out: list[str] = []
    seen: set[str] = set()
    for href in hrefs:
        full = urljoin(base_url, href)
        if full not in seen:
            seen.add(full)
            out.append(full)
    return out[:12]


def expand_candidate_urls(url: str) -> list[str]:
    """Landing-page → likely PDF URLs (PMC Europe render, etc.)."""
    urls: list[str] = []
    if url:
        urls.append(url)
    low = url.lower()
    parsed = urlparse(url)

    m = PMC_RE.search(low)
    if m:
        pmc_id = m.group(1)
        urls.extend(
            [
                f"https://europepmc.org/backend/ptpmcrender.fcgi?accid=PMC{pmc_id}&blobtype=pdf",
                f"https://www.ncbi.nlm.nih.gov/pmc/articles/PMC{pmc_id}/pdf/",
                f"https://www.ncbi.nlm.nih.gov/pmc/articles/{pmc_id}/pdf/",
            ]
        )

    if "figshare.com" in low and "/download" not in low:
        urls.append(url.rstrip("/") + "/download")

    if "nature.com/articles/" in low and not low.endswith(".pdf"):
        urls.append(url.rstrip("/") + ".pdf")

    if "link.springer.com/article/" in low:
        path = parsed.path.replace("/article/", "/content/pdf/", 1)
        urls.append(f"{parsed.scheme}://{parsed.netloc}{path}.pdf")

    seen: set[str] = set()
    out: list[str] = []
    for u in urls:
        if u and u not in seen:
            seen.add(u)
            out.append(u)
    return out


def probe_url(
    session: requests.Session,
    url: str,
    *,
    timeout: int = 45,
    max_follow_links: int = 8,
) -> ProbeResult:
    """Try to fetch PDF bytes from url (and a few HTML-derived links)."""
    attempts: list[dict[str, Any]] = []
    queue = expand_candidate_urls(url)
    seen: set[str] = set(queue)
    idx = 0
    last_html = False
    last_auth = False

    while idx < len(queue) and idx < max_follow_links + len(expand_candidate_urls(url)):
        current = queue[idx]
        idx += 1
        meta: dict[str, Any] = {"request_url": current}
        try:
            resp = session.get(
                current,
                timeout=timeout,
                allow_redirects=True,
                headers={
                    "User-Agent": PROBE_USER_AGENT,
                    "Accept": "application/pdf,*/*;q=0.8",
                },
            )
            data = resp.content
            meta["final_url"] = str(resp.url)
            meta["status"] = resp.status_code
            meta["content_type"] = (resp.headers.get("Content-Type") or "").split(";")[0].strip().lower()

            if resp.status_code != 200:
                if classify_auth_failure(resp.status_code, data):
                    last_auth = True
                attempts.append(meta)
                continue

            if is_pdf_bytes(data) or (
                meta["content_type"] == "application/pdf" and len(data) > 500
            ):
                attempts.append(meta)
                return ProbeResult(
                    fetch_status=FETCH_STATUS_PDF_VERIFIED,
                    access_tier=ACCESS_TIER_OA_VERIFIED,
                    http_status=resp.status_code,
                    content_type=meta["content_type"],
                    final_url=meta["final_url"],
                    pdf_sha256=sha256_bytes(data),
                    pdf_bytes=len(data),
                    attempts=attempts,
                )

            if b"<html" in data[:800].lower() or "text/html" in (meta["content_type"] or ""):
                last_html = True
                if classify_auth_failure(resp.status_code, data):
                    last_auth = True
                for link in extract_pdf_links_from_html(data, meta["final_url"]):
                    if link not in seen:
                        seen.add(link)
                        queue.append(link)
                meta["error"] = "html_not_pdf"
                attempts.append(meta)
                continue

            meta["error"] = "not_pdf_bytes"
            attempts.append(meta)
        except requests.RequestException as exc:
            meta["error"] = str(exc)
            attempts.append(meta)

    if last_auth:
        status = FETCH_STATUS_PAYWALL
    elif last_html:
        status = FETCH_STATUS_HTML_ONLY
    else:
        status = FETCH_STATUS_URL_ONLY

    return ProbeResult(
        fetch_status=status,
        access_tier=ACCESS_TIER_OA_URL_ONLY,
        attempts=attempts,
        error=attempts[-1].get("error") if attempts else "no_attempts",
    )


def access_tier_for_selection(selection: str, fetch_status: str) -> str:
    if fetch_status == FETCH_STATUS_PDF_VERIFIED:
        if selection == "operator_override":
            return ACCESS_TIER_OPERATOR_OVERRIDE_VERIFIED
        return ACCESS_TIER_OA_VERIFIED
    if selection == "operator_override":
        return ACCESS_TIER_OPERATOR_OVERRIDE
    return ACCESS_TIER_OA_URL_ONLY
