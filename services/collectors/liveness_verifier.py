"""Strict Active Liveness, Soft-404 Anti-Error Probes & URL Canonicalization for Tech Events."""

import hashlib
import logging
import re
import asyncio
from datetime import datetime, timezone, date
from typing import Dict, Any, List, Optional, Tuple, Set
from urllib.parse import urlparse
import httpx

from config.targets import BLACKLIST_KEYWORDS, SOFT_404_PATTERNS

logger = logging.getLogger("techyupdates.liveness_verifier")


def generate_dedup_hash(title: str, url: str) -> str:
    """Generate deterministic MD5 fingerprint using normalized title and domain path."""
    clean_title = re.sub(r"[^\w\s]", "", (title or "").lower().strip())
    clean_title = " ".join(clean_title.split())
    parsed = urlparse(url or "")
    clean_path = f"{parsed.netloc.lower()}{parsed.path.rstrip('/').lower()}"
    raw_key = f"{clean_title}::{clean_path}"
    return hashlib.md5(raw_key.encode("utf-8")).hexdigest()


def is_scam_or_blacklisted(title: str, description: str = "", url: str = "") -> bool:
    """Check if event text contains spam, scam, MLM, or non-technical keywords."""
    corpus = f"{(title or '').lower()} {(description or '').lower()} {(url or '').lower()}"
    for kw in BLACKLIST_KEYWORDS:
        if kw in corpus:
            return True
    return False


def is_valid_event_url(url: str) -> bool:
    """Check if URL is well-formed, reachable, and not a generic root directory."""
    if not url or not isinstance(url, str):
        return False
    url = url.strip()
    if not (url.startswith("http://") or url.startswith("https://")):
        return False

    try:
        parsed = urlparse(url)
        if not parsed.netloc:
            return False

        # Filter out obvious non-event root paths
        domain = parsed.netloc.lower()
        path = parsed.path.rstrip("/")
        
        # Block bare search/filter pages
        blocked_paths = {
            "",
            "/",
            "/events",
            "/search",
            "/explore",
            "/hackathons",
            "/conferences",
            "/d",
            "/d/online",
        }
        if path in blocked_paths and not parsed.query and not domain.startswith("io.google") and not domain.startswith("build.microsoft"):
            return False

        return True
    except Exception:
        return False


def parse_flexible_date(date_str: str) -> Optional[date]:
    """Parse various date strings into standard date object."""
    if not date_str or not isinstance(date_str, str):
        return None

    clean = date_str.strip()
    # Patterns to match: YYYY-MM-DD, DD-MM-YYYY, DD Mon YYYY, Month DD, YYYY
    formats = [
        "%Y-%m-%d",
        "%d-%m-%Y",
        "%d %b %Y",
        "%d %B %Y",
        "%B %d, %Y",
        "%b %d, %Y",
        "%Y/%m/%d",
        "%d/%m/%Y",
    ]
    for fmt in formats:
        try:
            return datetime.strptime(clean, fmt).date()
        except ValueError:
            continue

    # Regex search for year-month-day or day-month-year
    m_iso = re.search(r"(\d{4})-(\d{1,2})-(\d{1,2})", clean)
    if m_iso:
        try:
            return date(int(m_iso.group(1)), int(m_iso.group(2)), int(m_iso.group(3)))
        except ValueError:
            pass

    return None


def is_upcoming_or_future_event(
    start_date_str: Optional[str] = None,
    deadline_str: Optional[str] = None,
    current_date: Optional[date] = None,
) -> bool:
    """Check if an event is still in the future or currently ongoing."""
    today = current_date or datetime.now(timezone.utc).date()

    # Check deadline if present
    if deadline_str and deadline_str.lower() not in {"open", "open registration", "rolling", "ongoing", "see page", "open rsvp", "cfp open"}:
        parsed_dl = parse_flexible_date(deadline_str)
        if parsed_dl and parsed_dl < today:
            return False

    # Check start date if present
    if start_date_str and start_date_str.lower() not in {"tba", "upcoming", "announced soon", "see event page", "2026 scheduled"}:
        parsed_st = parse_flexible_date(start_date_str)
        if parsed_st and parsed_st < today:
            # If start date is in past, reject unless event spans multiple days
            return False

    return True


def is_recent_or_past_24h_posted(
    posted_date_str: Optional[str] = None,
    max_days_old: int = 2,
    current_date: Optional[date] = None,
) -> bool:
    """Enforce that events must be recently opened/posted within past 24-48 hours or recently announced."""
    if not posted_date_str:
        return True  # If not specified, allow if other liveness criteria pass

    clean_str = posted_date_str.strip().lower()
    
    # Always allow fresh active opportunity markers
    recent_markers = {
        "past 24 hours",
        "recently added",
        "recently listed",
        "recently published",
        "recently announced",
        "call for papers open",
        "flagship announcement",
        "registrations open",
        "official flagship announcement",
        "2026 schedule",
    }
    if any(m in clean_str for m in recent_markers):
        return True

    # Check if a specific date was parsed
    today = current_date or datetime.now(timezone.utc).date()
    parsed_posted = parse_flexible_date(posted_date_str)
    if parsed_posted:
        diff_days = (today - parsed_posted).days
        # If posted within max_days_old (e.g. today or yesterday)
        if 0 <= diff_days <= max_days_old:
            return True
        elif diff_days > max_days_old:
            return False

    return True



async def check_url_liveness_and_soft_404(
    client: httpx.AsyncClient,
    url: str,
    timeout: float = 8.0,
) -> Tuple[bool, str]:
    """Active async HTTP probe verifying HTTP 200/300 status and soft-404 anti-patterns."""
    if not is_valid_event_url(url):
        return False, "Malformed or invalid URL"

    try:
        headers = {
            "User-Agent": (
                "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36"
            ),
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
            "Accept-Language": "en-US,en;q=0.9",
        }
        resp = await client.get(url, headers=headers, timeout=timeout, follow_redirects=True)
        if resp.status_code >= 400:
            return False, f"HTTP Error Status {resp.status_code}"

        # Probe response text (first 30KB) for soft-404 phrases
        body_sample = resp.text[:30000].lower()
        for marker in SOFT_404_PATTERNS:
            if marker in body_sample:
                return False, f"Soft-404 match detected: '{marker}'"

        return True, "Active & Live"
    except httpx.TimeoutException:
        # If timeout happens on legitimate sites, fail gracefully or treat as tentative pass
        logger.debug("[Liveness] Timeout probing %s", url)
        return True, "Timeout passed tentatively"
    except Exception as exc:
        logger.debug("[Liveness] Probe exception for %s: %s", url, exc)
        return False, f"Network error: {str(exc)[:60]}"


async def verify_tech_events_liveness(
    events: List[Dict[str, Any]],
    client: Optional[httpx.AsyncClient] = None,
    concurrency_limit: int = 15,
) -> List[Dict[str, Any]]:
    """Batch verify liveness and soft-404 checks for a list of collected events."""
    if not events:
        return []

    should_close_client = False
    if client is None:
        client = httpx.AsyncClient(timeout=10.0, follow_redirects=True)
        should_close_client = True

    semaphore = asyncio.Semaphore(concurrency_limit)
    verified_events: List[Dict[str, Any]] = []

    async def verify_single(ev: Dict[str, Any]):
        url = ev.get("apply_url") or ev.get("registration_url") or ev.get("url") or ""
        title = ev.get("title", "")
        desc = ev.get("description", "")
        start_date = ev.get("start_date", "")
        deadline = ev.get("registration_deadline", "")

        # 1. Spam & Blacklist Check
        if is_scam_or_blacklisted(title, desc, url):
            logger.debug("[Verifier] Dropping blacklisted event: %s", title)
            return

        # 2. Date Expiry Check
        if not is_upcoming_or_future_event(start_date, deadline):
            logger.debug("[Verifier] Dropping expired event: %s (Start: %s, DL: %s)", title, start_date, deadline)
            return

        # 3. Recent / Past 24h Posted Check
        date_posted = ev.get("date_posted", "")
        if not is_recent_or_past_24h_posted(date_posted):
            logger.debug("[Verifier] Dropping non-recent event: %s (Posted: %s)", title, date_posted)
            return

        # 4. Active Liveness Check
        async with semaphore:
            is_live, reason = await check_url_liveness_and_soft_404(client, url)
            if is_live:
                verified_events.append(ev)
            else:
                logger.debug("[Verifier] Dropping inactive/soft-404 event '%s': %s", title, reason)


    try:
        tasks = [verify_single(ev) for ev in events]
        await asyncio.gather(*tasks)
    finally:
        if should_close_client:
            await client.aclose()

    logger.info("[Verifier] Retained %d / %d live and valid events.", len(verified_events), len(events))
    return verified_events
