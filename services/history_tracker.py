"""Cross-Day Persistent Deduplication & History Tracker for Tech Events Finder.

Maintains a durable JSON store of broadcasted events with dual-key matching (normalized title
and canonical URL) and an automatic 30-day TTL cleanup to prevent stale duplication across cron runs.
"""

import os
import json
import logging
import re
from datetime import datetime, timezone, timedelta
from typing import Dict, Any, Optional, List, Tuple
from urllib.parse import urlparse, urlunparse, parse_qsl, urlencode

logger = logging.getLogger("techyupdates.history_tracker")

DEFAULT_HISTORY_PATH = os.path.join(
    os.path.abspath(os.path.join(os.path.dirname(__file__), "..")),
    "data",
    "sent_history.json",
)


def normalize_title(title: str) -> str:
    """Normalize event title by stripping punctuation, emojis, and condensing whitespace."""
    if not title:
        return ""
    # Remove emojis and non-alphanumeric chars (keep spaces and basic alphanumerics)
    cleaned = re.sub(r"[^\w\s]", "", title.lower())
    # Condense multiple whitespaces into a single space
    return " ".join(cleaned.split())


def canonicalize_url(url: str) -> str:
    """Strip UTM parameters, query tracking artifacts, fragments, and trailing slashes."""
    if not url:
        return ""
    try:
        parsed = urlparse(url.strip())
        # Filter out tracking query parameters
        tracking_prefixes = ("utm_", "ref", "source", "ref_id", "fbclid", "gclid", "mc_eid", "aff")
        filtered_queries = [
            (k, v) for k, v in parse_qsl(parsed.query, keep_blank_values=False)
            if not any(k.lower().startswith(prefix) for prefix in tracking_prefixes)
        ]
        new_query = urlencode(sorted(filtered_queries))
        path = parsed.path.rstrip("/")
        # Reconstruct canonical URL (lowercasing domain/scheme, keeping clean path and query)
        canonical = urlunparse((
            parsed.scheme.lower(),
            parsed.netloc.lower(),
            path,
            "",
            new_query,
            "",  # Strip fragment
        ))
        return canonical
    except Exception as exc:
        logger.warning("[HistoryTracker] Error canonicalizing URL '%s': %s", url, exc)
        return url.strip().rstrip("/")


class HistoryTracker:
    """Manages cross-day historical persistence and dual-key deduplication."""

    def __init__(self, file_path: Optional[str] = None, ttl_days: int = 30):
        self.file_path = file_path or DEFAULT_HISTORY_PATH
        self.ttl_days = ttl_days
        self.history: Dict[str, Dict[str, Any]] = {}
        self._load()
        self._purge_expired()

    def _load(self) -> None:
        """Load history file from disk or initialize empty store."""
        if not os.path.exists(self.file_path):
            os.makedirs(os.path.dirname(self.file_path), exist_ok=True)
            self.history = {}
            logger.info("[HistoryTracker] No existing history file found at %s. Initialized empty store.", self.file_path)
            return

        try:
            with open(self.file_path, "r", encoding="utf-8") as f:
                data = json.load(f)
                if isinstance(data, dict):
                    self.history = data
                    logger.info("[HistoryTracker] Loaded %d historical records from %s", len(self.history), self.file_path)
                else:
                    logger.warning("[HistoryTracker] Invalid data format in %s. Resetting.", self.file_path)
                    self.history = {}
        except Exception as exc:
            logger.error("[HistoryTracker] Failed to load %s: %s. Using empty store.", self.file_path, exc)
            self.history = {}

    def _purge_expired(self) -> int:
        """Purge entries older than TTL days."""
        cutoff_date = datetime.now(timezone.utc) - timedelta(days=self.ttl_days)
        expired_keys: List[str] = []

        for key, record in self.history.items():
            sent_at_str = record.get("sent_at")
            if not sent_at_str:
                expired_keys.append(key)
                continue
            try:
                sent_at = datetime.fromisoformat(sent_at_str)
                if sent_at < cutoff_date:
                    expired_keys.append(key)
            except Exception:
                expired_keys.append(key)

        for key in expired_keys:
            del self.history[key]

        if expired_keys:
            logger.info("[HistoryTracker] Auto-TTL purged %d entries older than %d days.", len(expired_keys), self.ttl_days)
            self.save()

        return len(expired_keys)

    def is_already_sent(self, title: str, url: str) -> bool:
        """Check if an event was previously sent using dual-key matching."""
        norm_title = normalize_title(title)
        canon_url = canonicalize_url(url)

        # Primary check: direct record key
        if canon_url and canon_url in self.history:
            return True

        # Secondary check: search across normalized titles and URLs
        for key, record in self.history.items():
            if canon_url and record.get("canonical_url") == canon_url:
                return True
            if norm_title and record.get("normalized_title") == norm_title:
                return True

        return False

    def record_sent_event(
        self,
        title: str,
        url: str,
        category: str = "General",
        platform: str = "Web",
        metadata: Optional[Dict[str, Any]] = None,
    ) -> None:
        """Record an event into the persistent store."""
        canon_url = canonicalize_url(url)
        norm_title = normalize_title(title)
        key = canon_url or f"title_{norm_title}"

        self.history[key] = {
            "title": title.strip(),
            "normalized_title": norm_title,
            "original_url": url.strip(),
            "canonical_url": canon_url,
            "category": category,
            "platform": platform,
            "sent_at": datetime.now(timezone.utc).isoformat(),
            "metadata": metadata or {},
        }

    def record_batch_sent(self, events: List[Dict[str, Any]]) -> int:
        """Record a list of event dictionaries and persist changes."""
        count = 0
        for ev in events:
            title = ev.get("title") or ev.get("name") or ""
            url = ev.get("apply_url") or ev.get("registration_url") or ev.get("url") or ""
            cat = ev.get("category", "General")
            plat = ev.get("platform_or_source", ev.get("platform", "Web"))
            if title or url:
                self.record_sent_event(title=title, url=url, category=cat, platform=plat, metadata=ev)
                count += 1
        self.save()
        return count

    def save(self) -> None:
        """Persist current history dictionary to JSON on disk."""
        try:
            os.makedirs(os.path.dirname(self.file_path), exist_ok=True)
            with open(self.file_path, "w", encoding="utf-8") as f:
                json.dump(self.history, f, indent=2, ensure_ascii=False)
            logger.info("[HistoryTracker] Successfully saved %d records to %s", len(self.history), self.file_path)
        except Exception as exc:
            logger.error("[HistoryTracker] Failed saving history to %s: %s", self.file_path, exc)

    def get_stats(self) -> Dict[str, Any]:
        """Return history tracker statistics."""
        return {
            "total_tracked": len(self.history),
            "file_path": self.file_path,
            "ttl_days": self.ttl_days,
        }
